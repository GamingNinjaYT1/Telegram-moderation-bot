"""
handlers/moderation.py - ban / mute / kick / warn commands.
"""
from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import database as db


async def is_admin(update: Update, user_id: int) -> bool:
    member = await update.effective_chat.get_member(user_id)
    return member.status in ("administrator", "creator")


async def get_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resolve target user from a reply or @username/id argument."""
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user
    if context.args:
        arg = context.args[0]
        if arg.startswith("@"):
            # Note: resolving @username to ID generally requires the user
            # to be known to the bot already (e.g. seen in chat before).
            return None  # Telegram Bot API has no direct username->id lookup
        try:
            user_id = int(arg)
            member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
            return member.user
        except (ValueError, Exception):
            return None
    return None


async def require_admin(update: Update) -> bool:
    user = update.effective_user
    if not await is_admin(update, user.id):
        await update.message.reply_text("You need to be an admin to use this command.")
        return False
    return True


async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("Reply to a user's message or give their user ID to ban.")
        return
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "No reason given"
    await context.bot.ban_chat_member(update.effective_chat.id, target.id)
    await update.message.reply_text(f"🚫 Banned {target.mention_html()}\nReason: {reason}",
                                     parse_mode=ParseMode.HTML)


async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("Reply to a user's message or give their user ID to unban.")
        return
    await context.bot.unban_chat_member(update.effective_chat.id, target.id)
    await update.message.reply_text(f"✅ Unbanned {target.mention_html()}", parse_mode=ParseMode.HTML)


async def kick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("Reply to a user's message or give their user ID to kick.")
        return
    chat_id = update.effective_chat.id
    await context.bot.ban_chat_member(chat_id, target.id)
    await context.bot.unban_chat_member(chat_id, target.id)  # unban = kick (not permanent)
    await update.message.reply_text(f"👋 Kicked {target.mention_html()}", parse_mode=ParseMode.HTML)


async def mute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("Reply to a user's message or give their user ID to mute.")
        return
    await context.bot.restrict_chat_member(
        update.effective_chat.id,
        target.id,
        permissions=ChatPermissions(can_send_messages=False)
    )
    await update.message.reply_text(f"🔇 Muted {target.mention_html()}", parse_mode=ParseMode.HTML)


async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("Reply to a user's message or give their user ID to unmute.")
        return
    await context.bot.restrict_chat_member(
        update.effective_chat.id,
        target.id,
        permissions=ChatPermissions(
            can_send_messages=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
        )
    )
    await update.message.reply_text(f"🔊 Unmuted {target.mention_html()}", parse_mode=ParseMode.HTML)


async def warn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("Reply to a user's message or give their user ID to warn.")
        return
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "No reason given"
    chat_id = update.effective_chat.id
    count = db.add_warn(chat_id, target.id, reason)
    settings = db.get_chat_settings(chat_id)
    limit = settings["warn_limit"]

    if count >= limit:
        await context.bot.ban_chat_member(chat_id, target.id)
        db.reset_warns(chat_id, target.id)
        await update.message.reply_text(
            f"⚠️ {target.mention_html()} reached {count}/{limit} warnings and has been banned.",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            f"⚠️ {target.mention_html()} warned ({count}/{limit})\nReason: {reason}",
            parse_mode=ParseMode.HTML
        )


async def warns_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context) or update.effective_user
    count, reasons = db.get_warns(update.effective_chat.id, target.id)
    if count == 0:
        await update.message.reply_text(f"{target.mention_html()} has no warnings.", parse_mode=ParseMode.HTML)
        return
    text = f"{target.mention_html()} has {count} warning(s):\n"
    text += "\n".join(f"- {r}" for r in reasons)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def resetwarn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("Reply to a user's message or give their user ID.")
        return
    db.reset_warns(update.effective_chat.id, target.id)
    await update.message.reply_text(f"✅ Warnings reset for {target.mention_html()}", parse_mode=ParseMode.HTML)
