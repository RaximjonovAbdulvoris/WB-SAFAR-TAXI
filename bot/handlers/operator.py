"""Operator-side callbacks: Tayyor / Izoh berish buttons under each application."""
import logging

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
    "✅ *WB TAXI HUMO*\n\n"
    "Hurmatli mijoz, biz operatorlarimiz bilan sizni "
    "*Wildberries Taxi* uchun *HUMO Taxoparki* tomonidan "
    "ariza tashlab qo'ydik.\n\n"
    "📩 SMS xabarnoma *10–15 daqiqa* ichida keladi. "
    "Iltimos,Savollaringiz bo'lsa @wbhumoadmin ga murojat qilishingiz mumkin\n\n"
    "Rahmat 🤝"
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


async def on_operator_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    parts = query.data.split(":", 2)
    if len(parts) != 3 or parts[0] != "op":
        return
    action, applicant_id_str = parts[1], parts[2]
    

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
        # Mark this operator as awaiting a comment for this applicant
        pending = context.bot_data.setdefault("pending_comments", {})
        chat_id = update.effective_chat.id if update.effective_chat else None
        op_id = operator.id if operator else None
        if chat_id is None or op_id is None:
            return
        pending[(chat_id, op_id)] = applicant_id

        prompt = await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"💬 *Izoh kiriting* (arizachiga yuboriladi)\n"
                f"👤 Operator: {op_name}\n\n"
                f"Bekor qilish uchun: /bekor"
            ),
            parse_mode="Markdown",
            reply_to_message_id=query.message.message_id if query.message else None,
        )
        # Remember which prompt we showed so we can clean up later
        pending_msgs = context.bot_data.setdefault("pending_prompts", {})
        pending_msgs[(chat_id, op_id)] = prompt.message_id


async def on_operator_text_in_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Catch any text from an operator in a driver group when we're awaiting a comment."""
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
        return  # not awaiting a comment from this operator

    text = msg.text.strip()

    if text.lower() in ("/bekor", "bekor"):
        pending.pop(key, None)
        await msg.reply_text("❌ Izoh bekor qilindi.")
        return

    op_name = operator.full_name or "Operator"
    try:
        await context.bot.send_message(
            chat_id=applicant_id,
            text=(
                f"💬 *WB TAXI HUMO — Operator izohi:*\n\n"
                f"{text}"
            ),
            parse_mode="Markdown",
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


def register_operator_handlers(app):
    app.add_handler(CallbackQueryHandler(on_operator_button, pattern=r"^op:"))
    # Catch operator text replies in groups (only acts when a comment is pending)
    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND,
            on_operator_text_in_group,
        ),
        group=1,
    )
