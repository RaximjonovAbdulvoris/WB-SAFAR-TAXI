from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        WELCOME_TEXT,
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD,
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Bekor qilindi. Qaytadan boshlash uchun /start bosing.",
        reply_markup=MAIN_KEYBOARD,
    )
    return ConversationHandler.END
