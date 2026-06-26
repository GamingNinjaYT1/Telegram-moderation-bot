"""
main.py - Entry point. Run with: python main.py
Set your bot token as an environment variable: BOT_TOKEN
(Get a token from @BotFather on Telegram)
"""
import os
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes
)

import database as db
from handlers import moderation, greetings, filters_cmd, locks, notes, extras

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "PUT_YOUR_TOKEN_HERE")


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi! I'm your group management bot.\n"
        "Add me to a group and make me admin to get started.\n"
        "Send /help to see what I can do."
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "*Moderation*\n"
        "/ban /unban /kick /mute /unmute - manage users (reply or give user ID)\n"
        "/warn /warns /resetwarn - warning system\n"
        "/setwarnlimit <n> - set warns before ban\n\n"
        "*Greetings*\n"
        "/setwelcome <text> /setgoodbye <text>\n"
        "/welcome <on|off> /goodbye <on|off>\n"
        "Placeholders: {mention} {first} {last} {username} {chatname}\n\n"
        "*Filters*\n"
        "/filter <keyword> <reply> - add auto-reply\n"
        "/stop <keyword> - remove a filter\n"
        "/filters - list filters\n\n"
        "*Locks*\n"
        "/lock <type> /unlock <type> /locks\n"
        "Types: links, stickers, forward, photo, video, gif, voice, document\n\n"
        "*Antiflood*\n"
        "/setflood <n> - max messages per 10s (0 = off)\n\n"
        "*Notes*\n"
        "/save <name> <text> (or reply) - save a note\n"
        "/get <name> or #name - retrieve it\n"
        "/clear <name> /notes\n\n"
        "*Rules*\n"
        "/setrules <text> /rules\n\n"
        "*Blacklist*\n"
        "/addblacklist <word> /rmblacklist <word> /blacklist\n\n"
        "*Pin/Purge/Info*\n"
        "/pin [loud] /unpin /purge - reply to a message\n"
        "/info /id"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def setwarnlimit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await moderation.is_admin(update, user.id):
        await update.message.reply_text("You need to be an admin to set the warn limit.")
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /setwarnlimit <number>")
        return
    limit = int(context.args[0])
    db.update_chat_settings(update.effective_chat.id, warn_limit=limit)
    await update.message.reply_text(f"Warn limit set to {limit}.")


async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Runs lock enforcement, antiflood, blacklist, filter, and note checks on every message."""
    await locks.enforce_locks(update, context)
    await locks.antiflood_check(update, context)
    await extras.enforce_blacklist(update, context)
    await filters_cmd.check_filters(update, context)
    await notes.hashnote_trigger(update, context)


def main():
    db.init_db()

    if BOT_TOKEN == "PUT_YOUR_TOKEN_HERE":
        print("⚠️  Set the BOT_TOKEN environment variable before running!")
        print("   export BOT_TOKEN='your-token-from-botfather'")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    # Basic
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))

    # Moderation
    app.add_handler(CommandHandler("ban", moderation.ban_cmd))
    app.add_handler(CommandHandler("unban", moderation.unban_cmd))
    app.add_handler(CommandHandler("kick", moderation.kick_cmd))
    app.add_handler(CommandHandler("mute", moderation.mute_cmd))
    app.add_handler(CommandHandler("unmute", moderation.unmute_cmd))
    app.add_handler(CommandHandler("warn", moderation.warn_cmd))
    app.add_handler(CommandHandler("warns", moderation.warns_cmd))
    app.add_handler(CommandHandler("resetwarn", moderation.resetwarn_cmd))
    app.add_handler(CommandHandler("setwarnlimit", setwarnlimit_cmd))

    # Greetings
    app.add_handler(CommandHandler("setwelcome", greetings.setwelcome_cmd))
    app.add_handler(CommandHandler("setgoodbye", greetings.setgoodbye_cmd))
    app.add_handler(CommandHandler("welcome", greetings.welcome_toggle_cmd))
    app.add_handler(CommandHandler("goodbye", greetings.goodbye_toggle_cmd))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, greetings.greet_new_member))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, greetings.announce_left_member))

    # Filters
    app.add_handler(CommandHandler("filter", filters_cmd.addfilter_cmd))
    app.add_handler(CommandHandler("stop", filters_cmd.stopfilter_cmd))
    app.add_handler(CommandHandler("filters", filters_cmd.listfilters_cmd))

    # Locks
    app.add_handler(CommandHandler("lock", locks.lock_cmd))
    app.add_handler(CommandHandler("unlock", locks.unlock_cmd))
    app.add_handler(CommandHandler("locks", locks.locks_cmd))
    app.add_handler(CommandHandler("setflood", locks.setflood_cmd))

    # Notes
    app.add_handler(CommandHandler("save", notes.save_cmd))
    app.add_handler(CommandHandler("get", notes.get_cmd))
    app.add_handler(CommandHandler("clear", notes.clear_cmd))
    app.add_handler(CommandHandler("notes", notes.notes_cmd))

    # Rules
    app.add_handler(CommandHandler("setrules", extras.setrules_cmd))
    app.add_handler(CommandHandler("rules", extras.rules_cmd))

    # Blacklist
    app.add_handler(CommandHandler("addblacklist", extras.addblacklist_cmd))
    app.add_handler(CommandHandler("rmblacklist", extras.rmblacklist_cmd))
    app.add_handler(CommandHandler("blacklist", extras.blacklist_cmd))

    # Pin / Purge / Info
    app.add_handler(CommandHandler("pin", extras.pin_cmd))
    app.add_handler(CommandHandler("unpin", extras.unpin_cmd))
    app.add_handler(CommandHandler("purge", extras.purge_cmd))
    app.add_handler(CommandHandler("info", extras.info_cmd))
    app.add_handler(CommandHandler("id", extras.id_cmd))

    # Catch-all: lock enforcement / antiflood / filter replies on normal messages
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, message_router))

    logger.info("Bot starting (polling mode)...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
