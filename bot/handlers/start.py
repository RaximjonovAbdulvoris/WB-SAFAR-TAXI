from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes, ConversationHandler

from bot.config import CHANNEL

MENU_DRIVER = "📝 Ulanish uchun Ariza"
MENU_BRAND = "🎨 Brend Ariza"

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [[MENU_DRIVER], [MENU_BRAND]],
    resize_keyboard=True,
)

WELCOME_TEXT = (
    "🚖 *WB TAXI HUMO* botiga xush kelibsiz!\n\n"
    "Quyidagi menyulardan birini tanlang:\n\n"
    "📝 *Ulanish uchun Ariza* — Haydovchilik uchun ariza\n"
    "🎨 *Brend Ariza* — Mashinangizni brendlash uchun ariza"
)

SUBSCRIBE_TEXT = (
    "📢 *WB TAXI HUMO* botidan foydalanish uchun\n"
    f"kanalimizga obuna bo'lishingiz shart!\n\n"
    f"👇 Quyidagi tugmani bosib obuna bo'ling, so'ng *✅ Tekshirish* ni bosing."
)


def _subscribe_keyboard() -> InlineKeyboardMarkup:
    channel_link = f"https://t.me/{CHANNEL.lstrip('@')}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Kanalga obuna bo'lish", url=channel_link)],
        [InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub")],
    ])


async def _is_subscribed(bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    user = update.effective_user
    if not user:
        return ConversationHandler.END

    if not await _is_subscribed(context.bot, user.id):
        await update.message.reply_text(
            SUBSCRIBE_TEXT,
            parse_mode="Markdown",
            reply_markup=_subscribe_keyboard(),
        )
        return ConversationHandler.END

    await update.message.reply_text(
        WELCOME_TEXT,
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD,
    )
    return ConversationHandler.END


async def check_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    if not user:
        return

    if not await _is_subscribed(context.bot, user.id):
        await query.answer(
            "❌ Siz hali obuna bo'lmadingiz! Avval kanalga obuna bo'ling.",
            show_alert=True,
        )
        return

    await query.message.delete()
    await context.bot.send_message(
        chat_id=user.id,
        text=WELCOME_TEXT,
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD,
    )


def build_check_sub_handler() -> CallbackQueryHandler:
    return CallbackQueryHandler(check_sub_callback, pattern="^check_sub$")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Bekor qilindi. Qaytadan boshlash uchun /start bosing.",
        reply_markup=MAIN_KEYBOARD,
    )
    return ConversationHandler.END
