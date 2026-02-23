#!/usr/bin/env python3
"""Transparent Twitch chat assistant bot.

This bot is intentionally designed for compliant use:
- one explicit bot account
- configurable, slow message interval
- optional dry-run mode
- never pretends to be multiple viewers
"""

from __future__ import annotations

import argparse
import asyncio
import random
import re
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional


IRC_HOST = "irc.chat.twitch.tv"
IRC_PORT = 6667


@dataclass
class StreamContext:
    streamer: str
    category: str = "Unknown"
    title: str = ""


class TwitchIrcClient:
    def __init__(self, username: str, oauth_token: str, channel: str) -> None:
        self.username = username
        self.oauth_token = oauth_token if oauth_token.startswith("oauth:") else f"oauth:{oauth_token}"
        self.channel = channel.lower().lstrip("#")
        self.sock: Optional[socket.socket] = None

    def connect(self) -> None:
        self.sock = socket.create_connection((IRC_HOST, IRC_PORT), timeout=15)
        self._send_raw(f"PASS {self.oauth_token}")
        self._send_raw(f"NICK {self.username}")
        self._send_raw(f"JOIN #{self.channel}")

    def _send_raw(self, payload: str) -> None:
        if not self.sock:
            raise RuntimeError("Socket is not connected")
        self.sock.send((payload + "\r\n").encode("utf-8"))

    def send_message(self, message: str) -> None:
        self._send_raw(f"PRIVMSG #{self.channel} :{message}")

    def recv_line(self) -> str:
        if not self.sock:
            raise RuntimeError("Socket is not connected")
        data = self.sock.recv(4096).decode("utf-8", errors="ignore")
        if data.startswith("PING"):
            self._send_raw("PONG :tmi.twitch.tv")
        return data

    def close(self) -> None:
        if self.sock:
            try:
                self.sock.close()
            finally:
                self.sock = None


def fetch_stream_context(streamer: str, client_id: str, app_access_token: str) -> StreamContext:
    req = urllib.request.Request(
        f"https://api.twitch.tv/helix/streams?user_login={streamer}",
        headers={
            "Client-Id": client_id,
            "Authorization": f"Bearer {app_access_token}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = resp.read().decode("utf-8", errors="ignore")
    except urllib.error.URLError:
        return StreamContext(streamer=streamer)

    match_category = re.search(r'"game_name":"([^"]*)"', payload)
    match_title = re.search(r'"title":"([^"]*)"', payload)
    return StreamContext(
        streamer=streamer,
        category=(match_category.group(1) if match_category else "Unknown"),
        title=(match_title.group(1) if match_title else ""),
    )


class MessagePlanner:
    def __init__(self, context: StreamContext):
        self.context = context
        self.last_messages: list[str] = []

    def update_chat(self, raw_chunk: str) -> None:
        for line in raw_chunk.splitlines():
            if "PRIVMSG" in line:
                parts = line.split(" :", maxsplit=1)
                if len(parts) == 2:
                    self.last_messages.append(parts[1].strip())
        self.last_messages = self.last_messages[-30:]

    def next_message(self) -> str:
        cat = self.context.category.lower()
        recent = " ".join(self.last_messages[-10:]).lower()

        if any(token in recent for token in ["rtp", "слот", "slot", "bonus", "бонуска"]) or "casino" in cat:
            variants = [
                "Как тебе этот слот по волатильности, есть смысл дать ему ещё 20-30 спинов?",
                "Ты обычно смотришь RTP перед заходом в слот или больше по ощущению и бонускам?",
                "Если сравнить этот автомат с прошлым, где, по твоему, шанс на хороший бонус выше?",
                "Есть фаворит из слотов на сегодня или продолжаем тестить новые?",
            ]
        else:
            variants = [
                f"Как тебе текущая категория {self.context.category}? Что больше всего нравится в этом стриме?",
                "Какой момент на стриме за последний час тебе показался самым интересным?",
                "Есть ли план на следующую цель в эфире, чтобы чат мог поддержать?",
                "Какой формат контента хочешь протестировать в одном из следующих стримов?",
            ]

        if self.context.title and random.random() < 0.3:
            return f"В названии стрима упомянуто: «{self.context.title[:80]}». Это основной план на эфир?"
        return random.choice(variants)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compliant Twitch assistant bot (single account).")
    parser.add_argument("--streamer", required=True, help="Twitch channel login (without #)")
    parser.add_argument("--bot-username", required=True, help="Bot account login")
    parser.add_argument("--bot-oauth", required=True, help="OAuth token (with or without oauth: prefix)")
    parser.add_argument(
        "--interval",
        type=float,
        default=30.0,
        help="Interval between bot messages in seconds (minimum enforced: 15)",
    )
    parser.add_argument("--client-id", help="Twitch app Client-ID for stream category detection")
    parser.add_argument("--app-access-token", help="Twitch app access token for Helix API")
    parser.add_argument("--max-messages", type=int, default=0, help="0 means unlimited")
    parser.add_argument("--dry-run", action="store_true", help="Do not send messages, print only")
    return parser.parse_args()


async def run_bot(args: argparse.Namespace) -> None:
    interval = max(15.0, args.interval)
    if args.interval < 15.0:
        print("[safety] Interval increased to 15s to reduce spam risk.")

    context = StreamContext(streamer=args.streamer)
    if args.client_id and args.app_access_token:
        context = fetch_stream_context(args.streamer, args.client_id, args.app_access_token)

    print(f"[info] Streamer: {context.streamer}")
    print(f"[info] Category: {context.category}")
    if context.title:
        print(f"[info] Title: {context.title}")

    planner = MessagePlanner(context)
    client = TwitchIrcClient(args.bot_username, args.bot_oauth, args.streamer)
    client.connect()
    print("[info] Connected to Twitch IRC.")

    sent_count = 0
    next_at = time.monotonic() + interval

    try:
        while True:
            raw = client.recv_line()
            if raw:
                planner.update_chat(raw)

            now = time.monotonic()
            if now >= next_at:
                msg = planner.next_message()
                if args.dry_run:
                    print(f"[dry-run] -> {msg}")
                else:
                    client.send_message(msg)
                    print(f"[sent] {msg}")

                sent_count += 1
                next_at = now + interval
                if args.max_messages > 0 and sent_count >= args.max_messages:
                    print(f"[info] Reached max-messages={args.max_messages}. Stopping.")
                    break

            await asyncio.sleep(0.2)
    finally:
        client.close()
        print("[info] Disconnected.")


def main() -> None:
    args = parse_args()
    print("[notice] Use only your own authorized bot account and comply with Twitch rules.")
    asyncio.run(run_bot(args))


if __name__ == "__main__":
    main()
