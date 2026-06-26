"""
handlers/greetings.py - Welcome & goodbye messages for new/leaving members.
"""
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import database as db


def format_text(template: str, user, chat) -> str:
    return (template
            .replace("{mention}", user.mention_html())
            .replace("{first}", user.first_name or "")
            .replace("{last}", user.last_name or "")
            .replace("{username}", f"@{user.username}" if user.username else user.first_name)
            .replace("{chatname}", chat.title or "this chat"))


async def greet_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = db.get_chat_settings(chat_id)
    if not settings["welcome_enabled"]:
        return
    for member in update.message.new_chat_members:
        if member.is_bot and member.id == context.bot.id:
            continue  # don't greet the bot itself when added to a group
        text = format_text(settings["welcome_text"], member, update.effective_chat)
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def announce_left_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = db.get_chat_settings(chat_id)
    if not settings["goodbye_enabled"]:
        return
    member = update.message.left_chat_member
    if member.id == context.bot.id:
        return
    text = format_text(settings["goodbye_text"], member, update.effective_chat)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def setwelcome_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: /setwelcome <text>\nPlaceholders: {mention} {first} {last} {username} {chatname}"
        )
        return
    text = " ".join(context.args)
    db.update_chat_settings(update.effective_chat.id, welcome_text=text)
    await update.message.reply_text("✅ Welcome message updated.")


async def setgoodbye_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: /setgoodbye <text>\nPlaceholders: {mention} {first} {last} {username} {chatname}"
        )
        return
    text = " ".join(context.args)
    db.update_chat_settings(update.effective_chat.id, goodbye_text=text)
    await update.message.reply_text("✅ Goodbye message updated.")


async def welcome_toggle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or context.args[0].lower() not in ("on", "off"):
        await update.message.reply_text("Usage: /welcome <on|off>")
        return
    enabled = 1 if context.args[0].lower() == "on" else 0
    db.update_chat_settings(update.effective_chat.id, welcome_enabled=enabled)
    await update.message.reply_text(f"Welcome messages turned {'ON' if enabled else 'OFF'}.")


async def goodbye_toggle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or context.args[0].lower() not in ("on", "off"):
        await update.message.reply_text("Usage: /goodbye <on|off>")
        return
    enabled = 1 if context.args[0].lower() == "on" else 0
    db.update_chat_settings(update.effective_chat.id, goodbye_enabled=enabled)
    await update.message.reply_text(f"Goodbye messages turned {'ON' if enabled else 'OFF'}.")
