"""
handlers/notes.py - Save and retrieve notes with #notename or /get.
"""
from telegram import Update
from telegram.ext import ContextTypes
import database as db
from handlers.moderation import is_admin


async def save_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(update, user.id):
        await update.message.reply_text("You need to be an admin to save notes.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /save <notename> <content> (or reply to a message with /save <notename>)")
        return
    name = context.args[0].lower()
    if update.message.reply_to_message and len(context.args) == 1:
        content = update.message.reply_to_message.text or update.message.reply_to_message.caption or ""
    else:
        content = " ".join(context.args[1:])
    if not content:
        await update.message.reply_text("Note content is empty.")
        return
    db.add_note(update.effective_chat.id, name, content)
    await update.message.reply_text(f"✅ Note '{name}' saved. Get it with /get {name} or #{name}.")


async def get_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /get <notename>")
        return
    name = context.args[0].lower()
    content = db.get_note(update.effective_chat.id, name)
    if not content:
        await update.message.reply_text(f"No note named '{name}'.")
        return
    await update.message.reply_text(content)


async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(update, user.id):
        await update.message.reply_text("You need to be an admin to delete notes.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /clear <notename>")
        return
    name = context.args[0].lower()
    db.remove_note(update.effective_chat.id, name)
    await update.message.reply_text(f"🗑️ Note '{name}' deleted.")


async def notes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    notes = db.get_all_notes(update.effective_chat.id)
    if not notes:
        await update.message.reply_text("No notes saved in this chat.")
        return
    text = "Saved notes:\n" + "\n".join(f"- #{n}" for n in notes)
    await update.message.reply_text(text)


async def hashnote_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detects #notename anywhere in a text message and replies with the note."""
    if not update.message or not update.message.text:
        return
    words = update.message.text.split()
    for w in words:
        if w.startswith("#") and len(w) > 1:
            name = w[1:].lower()
            content = db.get_note(update.effective_chat.id, name)
            if content:
                await update.message.reply_text(content)
                return
