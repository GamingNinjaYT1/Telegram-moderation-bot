# Group Management Bot

A Telegram group-management bot (your own version, inspired by bots like Rose) built with `python-telegram-bot`. Includes moderation, warnings, welcome/goodbye messages, custom filters, content locks, and antiflood.

## Features

- **Moderation**: `/ban`, `/unban`, `/kick`, `/mute`, `/unmute`
- **Warnings**: `/warn`, `/warns`, `/resetwarn`, `/setwarnlimit`
- **Welcome/Goodbye**: `/setwelcome`, `/setgoodbye`, `/welcome on|off`, `/goodbye on|off`
- **Filters**: `/filter <keyword> <reply>`, `/stop <keyword>`, `/filters`
- **Locks**: `/lock`, `/unlock`, `/locks` (links, stickers, forwards, photo, video, gif, voice, document)
- **Antiflood**: `/setflood <n>`

## Setup

1. **Create a bot & get a token**
   - Message [@BotFather](https://t.me/BotFather) on Telegram
   - Send `/newbot`, follow the prompts, choose a unique name/username
   - Copy the token it gives you

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set your token**
   ```bash
   export BOT_TOKEN="123456:ABC-your-token-here"
   ```
   (On Windows: `set BOT_TOKEN=...` in cmd, or `$env:BOT_TOKEN="..."` in PowerShell)

4. **Run the bot**
   ```bash
   python main.py
   ```

5. **Add it to a group**
   - Add your bot to a Telegram group
   - Promote it to **admin** with permissions: delete messages, ban users, restrict users, pin messages, invite users
   - Use `/help` in the group to see all commands

## Notes on limitations

- Banning/muting/kicking by `@username` only works if the bot has already seen that user in the chat (Telegram's Bot API has no direct username→ID lookup). **Reply to a message from the user** instead — this always works reliably.
- Data is stored locally in `botdata.db` (SQLite). Back this up if you move servers.
- This runs in **polling mode** — no public URL or webhook needed, works on any machine with internet access (laptop, VPS, Railway, Render, etc.). Just keep it running.

## Deploying for 24/7 uptime

Polling mode needs to stay running. Options:
- A cheap VPS (DigitalOcean, Hetzner) + `tmux`/`screen` or a systemd service
- Railway.app or Render.com (set `BOT_TOKEN` as an environment variable, run `python main.py` as the start command)
- A Raspberry Pi at home

## Extending it

The code is split into clear modules so you can add features:
- `handlers/moderation.py` — user actions
- `handlers/greetings.py` — welcome/goodbye
- `handlers/filters_cmd.py` — keyword replies
- `handlers/locks.py` — content locks & antiflood
- `database.py` — all storage logic

Want federations (shared banlists), inline button menus, or a "notes" system (`/save` and `#notename`)? Those follow the same pattern — add a table in `database.py`, write command handlers in a new file under `handlers/`, register them in `main.py`.
