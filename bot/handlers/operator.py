"""Operator-side callbacks: Tayyor / Izoh berish buttons under each application.

Two-way relay chat:
  Operator -> "Izoh berish" -> user receives comment + "💬 Javob yozish" button
  User presses button -> types reply -> forwarded back to operator group
  Operator can reply again via "Izoh berish" — cycle continues.
"""
import logging
from html import escape as h

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logger = logging.getLogger(__name__)

READY_TEXT = (
    "✅ WB TAXI HUMO ga arizangiz muvaffaqiyatli qabul qilindi!\n\n"
    "📩 Iltimos, SMS xabarnomani kuting.  \n"
    "Agar savollaringiz bo‘lsa, @wb_taxi_Humo orqali murojaat qilishingiz mumkin."
)


def build_operator_keyboard(applicant_user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ Tayyor", callback_data=f"op:ready:{applicant_user_id}"
                ),
                InlineKeyboardButton(
                    "💬 Izoh berish", callback_data=f"op:comment:{applicant_user_id}"
                ),
            ]
        ]
    )


def _reply_keyboard(group_chat_id: int) -> InlineKeyboardMarkup:
    """Inline button shown to the user under the operator's comment."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("💬 Javob yozish", callback_data=f"user:reply:{group_chat_id}")]]
    )


# ------------------------------------------------------------------ #
#  OPERATOR SIDE                                                       #
# ------------------------------------------------------------------ #

async def on_operator_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    parts = query.data.split(":", 2)
    if len(parts) != 3 or parts[0] != "op":
        return
    action, applicant_id_str = parts[1], parts[2]
    try:
        applicant_id = int(applicant_id_str)
    except ValueError:
        return

    operator = update.effective_user
    op_name = operator.full_name if operator else "Operator"

    if action == "ready":
        try:
            await context.bot.send_message(
                chat_id=applicant_id,
                text=READY_TEXT,
                parse_mode="Markdown",
            )
            await query.edit_message_text(
                f"✅ *Tayyor* — xabar arizachiga yuborildi.\n"
                f"👤 Operator: {op_name}",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.exception("ready: failed to notify applicant %s", applicant_id)
            await query.edit_message_text(
                f"⚠️ Xabar yuborilmadi: {e}\n\n"
                f"Sabab: foydalanuvchi botni bloklagan yoki /start bosmagan."
            )

    elif action == "comment":
        pending = context.bot_data.setdefault("pending_comments", {})
        chat_id = update.effective_chat.id if update.effective_chat else None
        op_id = operator.id if operator else None
        if chat_id is None or op_id is None:
            return
        pending[(chat_id, op_id)] = applicant_id

        # Build applicant link for the prompt
        info = context.bot_data.get("applicant_info", {}).get(applicant_id, {})
        ap_name = h(info.get("name") or "Arizachi")
        ap_username = info.get("username") or ""
        if ap_username:
            applicant_link = f'<a href="https://t.me/{ap_username}">{ap_name} (@{ap_username})</a>'
        else:
            applicant_link = f'<a href="tg://user?id={applicant_id}">{ap_name}</a>'

        prompt = await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"💬 <b>Izoh kiriting</b> → {applicant_link}\n"
                f"👤 Operator: {op_name}\n\n"
                f"Bekor qilish uchun: /bekor"
            ),
            parse_mode="HTML",
            reply_to_message_id=query.message.message_id if query.message else None,
        )
        pending_msgs = context.bot_data.setdefault("pending_prompts", {})
        pending_msgs[(chat_id, op_id)] = prompt.message_id


async def on_operator_text_in_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Catch operator text in a group when a comment is pending."""
    msg = update.message
    if not msg or not msg.text:
        return
    chat = update.effective_chat
    operator = update.effective_user
    if not chat or not operator:
        return

    pending = context.bot_data.get("pending_comments", {})
    key = (chat.id, operator.id)
    applicant_id = pending.get(key)
    if applicant_id is None:
        return

    text = msg.text.strip()

    if text.lower() in ("/bekor", "bekor"):
        pending.pop(key, None)
        await msg.reply_text("❌ Izoh bekor qilindi.")
        return

    op_name = operator.full_name or "Operator"
    try:
        await context.bot.send_message(
            chat_id=applicant_id,
            text=f"💬 <b>WB TAXI HUMO — Operator izohi:</b>\n\n{h(text)}",
            parse_mode="HTML",
            reply_markup=_reply_keyboard(chat.id),
        )
        await msg.reply_text(
            f"✅ Izoh arizachiga yuborildi.\n👤 Operator: {op_name}"
        )
    except Exception as e:
        logger.exception("comment: failed to send to %s", applicant_id)
        await msg.reply_text(
            f"⚠️ Izoh yuborilmadi: {e}\n"
            f"Sabab: foydalanuvchi botni bloklagan yoki /start bosmagan."
        )
    finally:
        pending.pop(key, None)


# ------------------------------------------------------------------ #
#  USER SIDE  (reply to operator comment)                              #
# ------------------------------------------------------------------ #

async def on_user_reply_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User pressed '💬 Javob yozish' under an operator comment."""
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    parts = query.data.split(":", 2)
    if len(parts) != 3 or parts[0] != "user" or parts[1] != "reply":
        return
    try:
        group_chat_id = int(parts[2])
    except ValueError:
        return

    user_id = update.effective_user.id if update.effective_user else None
    if user_id is None:
        return

    context.bot_data.setdefault("pending_user_replies", {})[user_id] = group_chat_id

    await query.message.reply_text(
        "✏️ Javobingizni yozing:\n\nBekor qilish uchun: /bekor",
    )


async def on_user_reply_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward the user's reply to the operator group."""
    msg = update.message
    if not msg:
        return
    user = update.effective_user
    if not user:
        return

    pending = context.bot_data.get("pending_user_replies", {})
    group_chat_id = pending.get(user.id)
    if group_chat_id is None:
        return

    text = (msg.text or "").strip()
    if not text:
        await msg.reply_text("❗ Iltimos, matn yozing.")
        return

    if text.lower() in ("/bekor", "bekor"):
        pending.pop(user.id, None)
        await msg.reply_text("❌ Javob bekor qilindi.")
        return

    user_link = (
        f'<a href="https://t.me/{user.username}">{h(user.full_name)}</a>'
        if user.username
        else f'<a href="tg://user?id={user.id}">{h(user.full_name or "Foydalanuvchi")}</a>'
    )

    # Keep applicant_info fresh so operator "Izoh berish" link stays correct
    context.bot_data.setdefault("applicant_info", {})[user.id] = {
        "name": user.full_name or "Arizachi",
        "username": user.username or "",
    }

    try:
        await context.bot.send_message(
            chat_id=group_chat_id,
            text=(
                f"📩 <b>Arizachi javobi:</b>\n"
                f"👤 {user_link}\n\n"
                f"{h(text)}"
            ),
            parse_mode="HTML",
            reply_markup=build_operator_keyboard(user.id),
        )
        await msg.reply_text("✅ Javobingiz operatorlarga yuborildi.")
    except Exception as e:
        logger.exception("user_reply: failed to send to group %s", group_chat_id)
        await msg.reply_text(f"⚠️ Javob yuborilmadi: {e}")
    finally:
        pending.pop(user.id, None)


# ------------------------------------------------------------------ #
#  REGISTRATION                                                        #
# ------------------------------------------------------------------ #

def register_operator_handlers(app):
    # Operator buttons in group (Tayyor / Izoh berish)
    app.add_handler(CallbackQueryHandler(on_operator_button, pattern=r"^op:"))

    # User presses "Javob yozish" in private chat
    app.add_handler(
        CallbackQueryHandler(on_user_reply_button, pattern=r"^user:reply:"),
    )

    # Operator types comment in group
    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND,
            on_operator_text_in_group,
        ),
        group=1,
    )

    # User types reply in private chat (only fires when pending_user_replies is set)
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND,
            on_user_reply_message,
        ),
        group=2,
    )
