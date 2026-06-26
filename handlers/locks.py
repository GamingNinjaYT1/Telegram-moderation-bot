"""
handlers/locks.py - Lock certain content types (links, stickers, forwards, etc.)
and basic antiflood protection.
"""
import time
from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes
import database as db
from handlers.moderation import is_admin

VALID_LOCKS = ["links", "stickers", "forward", "photo", "video", "gif", "voice", "document"]

# in-memory flood tracker: {(chat_id, user_id): [timestamps]}
_flood_tracker = {}


async def lock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(update, user.id):
        await update.message.reply_text("You need to be an admin to set locks.")
        return
    if not context.args or context.args[0].lower() not in VALID_LOCKS:
        await update.message.reply_text(f"Usage: /lock <{'|'.join(VALID_LOCKS)}>")
        return
    lock_type = context.args[0].lower()
    db.set_lock(update.effective_chat.id, lock_type, True)
    await update.message.reply_text(f"🔒 Locked: {lock_type}")


async def unlock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(update, user.id):
        await update.message.reply_text("You need to be an admin to remove locks.")
        return
    if not context.args or context.args[0].lower() not in VALID_LOCKS:
        await update.message.reply_text(f"Usage: /unlock <{'|'.join(VALID_LOCKS)}>")
        return
    lock_type = context.args[0].lower()
    db.set_lock(update.effective_chat.id, lock_type, False)
    await update.message.reply_text(f"🔓 Unlocked: {lock_type}")


async def locks_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    locks = db.get_locks(update.effective_chat.id)
    if not locks:
        await update.message.reply_text("No locks set in this chat.")
        return
    text = "Current locks:\n" + "\n".join(f"- {k}: {'ON' if v else 'OFF'}" for k, v in locks.items())
    await update.message.reply_text(text)


async def enforce_locks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete messages that violate active locks. Admins are exempt."""
    msg = update.message
    if not msg:
        return
    user = update.effective_user
    if await is_admin(update, user.id):
        return

    locks = db.get_locks(update.effective_chat.id)
    if not locks:
        return

    violated = False
    if locks.get("links") and msg.entities:
        if any(e.type in ("url", "text_link") for e in msg.entities):
            violated = True
    if locks.get("stickers") and msg.sticker:
        violated = True
    if locks.get("forward") and msg.forward_date:
        violated = True
    if locks.get("photo") and msg.photo:
        violated = True
    if locks.get("video") and msg.video:
        violated = True
    if locks.get("gif") and msg.animation:
        violated = True
    if locks.get("voice") and msg.voice:
        violated = True
    if locks.get("document") and msg.document:
        violated = True

    if violated:
        try:
            await msg.delete()
        except Exception:
            pass


async def antiflood_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mutes users who send too many messages too quickly."""
    msg = update.message
    if not msg:
        return
    chat_id = update.effective_chat.id
    user = update.effective_user

    settings = db.get_chat_settings(chat_id)
    limit = settings["flood_limit"]
    if not limit or limit <= 0:
        return
    if await is_admin(update, user.id):
        return

    key = (chat_id, user.id)
    now = time.time()
    timestamps = _flood_tracker.get(key, [])
    timestamps = [t for t in timestamps if now - t < 10]  # 10 second window
    timestamps.append(now)
    _flood_tracker[key] = timestamps

    if len(timestamps) > limit:
        try:
            await context.bot.restrict_chat_member(
                chat_id, user.id,
                permissions=ChatPermissions(can_send_messages=False)
            )
            await msg.reply_text(f"🔇 {user.mention_html()} has been muted for flooding.",
                                  parse_mode="HTML")
        except Exception:
            pass
        _flood_tracker[key] = []


async def setflood_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(update, user.id):
        await update.message.reply_text("You need to be an admin to set antiflood.")
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /setflood <number> (0 to disable)\nMessages per 10 seconds allowed.")
        return
    limit = int(context.args[0])
    db.update_chat_settings(update.effective_chat.id, flood_limit=limit)
    if limit == 0:
        await update.message.reply_text("Antiflood disabled.")
    else:
        await update.message.reply_text(f"Antiflood set: max {limit} messages per 10 seconds.")
