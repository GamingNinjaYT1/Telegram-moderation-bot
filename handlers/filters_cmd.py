"""
handlers/filters_cmd.py - Custom keyword auto-reply filters.
"""
from telegram import Update
from telegram.ext import ContextTypes
import database as db
from handlers.moderation import is_admin


async def addfilter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(update, user.id):
        await update.message.reply_text("You need to be an admin to add filters.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /filter <keyword> <reply text>")
        return
    keyword = context.args[0]
    reply_text = " ".join(context.args[1:])
    db.add_filter(update.effective_chat.id, keyword, reply_text)
    await update.message.reply_text(f"✅ Filter added for '{keyword}'.")


async def stopfilter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(update, user.id):
        await update.message.reply_text("You need to be an admin to remove filters.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /stop <keyword>")
        return
    keyword = context.args[0]
    db.remove_filter(update.effective_chat.id, keyword)
    await update.message.reply_text(f"🗑️ Filter '{keyword}' removed.")


async def listfilters_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    filters_dict = db.get_filters(update.effective_chat.id)
    if not filters_dict:
        await update.message.reply_text("No filters set in this chat.")
        return
    text = "Active filters:\n" + "\n".join(f"- {k}" for k in filters_dict)
    await update.message.reply_text(text)


async def check_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggered on every text message; replies if a filter keyword matches."""
    if not update.message or not update.message.text:
        return
    filters_dict = db.get_filters(update.effective_chat.id)
    if not filters_dict:
        return
    text_lower = update.message.text.lower()
    for keyword, reply_text in filters_dict.items():
        if keyword in text_lower:
            await update.message.reply_text(reply_text)
            return
