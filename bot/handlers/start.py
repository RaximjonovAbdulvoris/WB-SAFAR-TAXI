from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters

MENU_DRIVER = "📝 Ulanish uchun Ariza"
MENU_BRAND = "🎨 Brend Ariza"
MENU_PAYOUT = "💰 PUL YECHISH BOTI"

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [[MENU_DRIVER], [MENU_BRAND], [MENU_PAYOUT]],
    resize_keyboard=True,
)

WELCOME_TEXT = (
    "🚖 *WB SAFAR TAXI* botiga xush kelibsiz!\n\n"
    "Quyidagi menyulardan birini tanlang:\n\n"
    "📝 *Ulanish uchun Ariza* — Haydovchilik uchun ariza\n"
    "🎨 *Brend Ariza* — Mashinangizni brendlash uchun ariza\n"
    "💰 *PUL YECHISH BOTI* — Pul yechish va aloqa ma'lumotlari"
)

PAYOUT_TEXT = (
    "💰 *PUL YECHISH BOTI:* @safar_taxi_bot\n\n"
    "📞 *PARK NOMERI:* +998908233334\n\n"
    "✉️ *TELEGRAM ORQALI MUROJAT:* @WBsafarTAXI"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        WELCOME_TEXT,
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD,
    )
    return ConversationHandler.END


async def show_payout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        PAYOUT_TEXT,
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD,
        disable_web_page_preview=True,
    )


def build_payout_handler() -> MessageHandler:
    return MessageHandler(filters.Regex(f"^{MENU_PAYOUT}$"), show_payout)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Bekor qilindi. Qaytadan boshlash uchun /start bosing.",
        reply_markup=MAIN_KEYBOARD,
    )
    return ConversationHandler.END
