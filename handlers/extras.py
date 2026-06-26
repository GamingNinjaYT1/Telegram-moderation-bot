"""
handlers/extras.py - Rules, blacklists, pin/unpin, purge, info, id commands.
"""
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import database as db
from handlers.moderation import is_admin, get_target_user


# ---------- Rules ----------

async def setrules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(update, user.id):
        await update.message.reply_text("You need to be an admin to set rules.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /setrules <text>")
        return
    text = " ".join(context.args)
    db.update_chat_settings(update.effective_chat.id, rules_text=text)
    await update.message.reply_text("✅ Rules updated.")


async def rules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings = db.get_chat_settings(update.effective_chat.id)
    rules = settings.get("rules_text") or "No rules set for this chat yet."
    await update.message.reply_text(rules)


# ---------- Blacklist (banned words) ----------

async def addblacklist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(update, user.id):
        await update.message.reply_text("You need to be an admin to manage the blacklist.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /addblacklist <word>")
        return
    word = " ".join(context.args).lower()
    db.add_blacklist_word(update.effective_chat.id, word)
    await update.message.reply_text(f"✅ '{word}' added to blacklist.")


async def rmblacklist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(update, user.id):
        await update.message.reply_text("You need to be an admin to manage the blacklist.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /rmblacklist <word>")
        return
    word = " ".join(context.args).lower()
    db.remove_blacklist_word(update.effective_chat.id, word)
    await update.message.reply_text(f"🗑️ '{word}' removed from blacklist.")


async def blacklist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    words = db.get_blacklist_words(update.effective_chat.id)
    if not words:
        await update.message.reply_text("No blacklisted words in this chat.")
        return
    await update.message.reply_text("Blacklisted words:\n" + "\n".join(f"- {w}" for w in words))


async def enforce_blacklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return
    user = update.effective_user
    if await is_admin(update, user.id):
        return
    words = db.get_blacklist_words(update.effective_chat.id)
    if not words:
        return
    text_lower = msg.text.lower()
    for w in words:
        if w in text_lower:
            try:
                await msg.delete()
            except Exception:
                pass
            return


# ---------- Pin / Unpin / Purge ----------

async def pin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(update, user.id):
        await update.message.reply_text("You need to be an admin to pin messages.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the message you want to pin.")
        return
    loud = context.args and context.args[0].lower() in ("loud", "notify")
    await context.bot.pin_chat_message(
        update.effective_chat.id,
        update.message.reply_to_message.message_id,
        disable_notification=not loud
    )
    await update.message.reply_text("📌 Pinned.")


async def unpin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(update, user.id):
        await update.message.reply_text("You need to be an admin to unpin messages.")
        return
    if update.message.reply_to_message:
        await context.bot.unpin_chat_message(
            update.effective_chat.id,
            message_id=update.message.reply_to_message.message_id
        )
    else:
        await context.bot.unpin_chat_message(update.effective_chat.id)
    await update.message.reply_text("📌 Unpinned.")


async def purge_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(update, user.id):
        await update.message.reply_text("You need to be an admin to purge messages.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the message you want to purge from.")
        return
    chat_id = update.effective_chat.id
    start_id = update.message.reply_to_message.message_id
    end_id = update.message.message_id
    deleted = 0
    for msg_id in range(start_id, end_id + 1):
        try:
            await context.bot.delete_message(chat_id, msg_id)
            deleted += 1
        except Exception:
            pass
    # confirmation msg deletes itself isn't necessary; just report
    await context.bot.send_message(chat_id, f"🧹 Purged {deleted} messages.")


# ---------- Info / ID ----------

async def info_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context) or update.effective_user
    text = (
        f"<b>User Info</b>\n"
        f"ID: <code>{target.id}</code>\n"
        f"First name: {target.first_name}\n"
        f"Username: @{target.username if target.username else 'N/A'}\n"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        await update.message.reply_text(f"Chat ID: {chat.id}\n{target.first_name}'s ID: {target.id}")
    else:
        await update.message.reply_text(f"Chat ID: {chat.id}")
