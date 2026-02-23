# game-showspeed

Легальный пример **Twitch AI chat assistant** с одним прозрачным бот-аккаунтом.

> Этот проект **не** предназначен для имитации «живых» людей с массовых аккаунтов.
> Используйте только собственный авторизованный бот-аккаунт и соблюдайте правила Twitch.

## Возможности

- Подключение к чату Twitch (IRC).
- Чтение последних сообщений чата.
- Генерация контекстных реплик (вопросы и обсуждение по теме стрима).
- Определение категории/названия стрима через Twitch Helix API (опционально).
- Anti-spam safeguard: минимальный интервал сообщений 15 секунд.
- `--dry-run` режим: проверка без отправки сообщений.

## Быстрый старт

Требуется Python 3.10+.

```bash
python3 twitch_assistant_bot.py \
  --streamer streamer_login \
  --bot-username your_bot_login \
  --bot-oauth oauth:your_token \
  --interval 30 \
  --dry-run
```

## Параметры

- `--streamer` — ник стримера (канал).
- `--bot-username` — логин бота.
- `--bot-oauth` — OAuth токен бота (`oauth:...` или без префикса).
- `--interval` — интервал между сообщениями, сек. (минимум 15).
- `--client-id` — Client-ID Twitch приложения (для Helix API).
- `--app-access-token` — app access token (для Helix API).
- `--max-messages` — лимит сообщений, `0` = без лимита.
- `--dry-run` — печатает сообщения в консоль, не отправляет в чат.

## Пример реального запуска

```bash
python3 twitch_assistant_bot.py \
  --streamer some_streamer \
  --bot-username mybot \
  --bot-oauth oauth:xxxxxxxxxxxxxxxxxxxx \
  --interval 35 \
  --max-messages 20
```

## Важно

- Не используйте чужие аккаунты.
- Не обходите rate limits.
- Не отправляйте агрессивный или вводящий в заблуждение контент.
