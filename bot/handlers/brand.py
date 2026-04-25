from telegram import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.config import BRAND_GROUP
from bot.handlers.start import MAIN_KEYBOARD, MENU_BRAND, cancel

(
    BRAND_WARN,
    BRAND_NAME,
    BRAND_PHONE,
    BRAND_MODEL,
    BRAND_YEAR,
    BRAND_COLOR,
) = range(20, 26)

CONTINUE_BTN = "✅ Davom etish"
CONTINUE_KB = ReplyKeyboardMarkup(
    [[CONTINUE_BTN]], resize_keyboard=True, one_time_keyboard=True
)

WARN_TEXT = (
    "⚠️ *DIQQAT! BRENDLASH SHARTLARI:*\n\n"
    "❌ SPARK — brendlanmaydi\n"
    "❌ NEXIA 3 — brendlanmaydi\n"
    "❌ Yili 2015 va undan past mashinalar — brendlanmaydi\n\n"
    "✅ Boshqa mashinalar (yili 2016 va undan yuqori) — brendlanadi\n\n"
    "_SPARK va NEXIA 3 yili nechi bo'lishidan qat'iy nazar BREND qilinmaydi._\n"
    "_2016 dan past mashinalar ham brend qilinmaydi (2016 — qilinadi, 2015 — qilinmaydi)._\n\n"
    "Davom etish uchun pastdagi knopkani bosing."
)


async def start_brand(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        WARN_TEXT,
        parse_mode="Markdown",
        reply_markup=CONTINUE_KB,
    )
    return BRAND_WARN


async def brand_warn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "🎨 *Brend Ariza*\n\n"
        "Iltimos, *ism va familiyangizni* yozing:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return BRAND_NAME


async def brand_get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = (update.message.text or "").strip()
    if len(name) < 3:
        await update.message.reply_text("❗ Iltimos, to'liq ism familiyangizni yozing:")
        return BRAND_NAME
    context.user_data["b_name"] = name
    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("📞 Raqamni jo'natish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await update.message.reply_text(
        "📞 Telefon raqamingizni jo'nating:",
        reply_markup=kb,
    )
    return BRAND_PHONE


async def brand_get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone = None
    if update.message.contact:
        phone = update.message.contact.phone_number
    elif update.message.text:
        phone = update.message.text.strip()
    if not phone or len(phone) < 7:
        await update.message.reply_text("❗ Iltimos, telefon raqamingizni jo'nating:")
        return BRAND_PHONE
    context.user_data["b_phone"] = phone
    await update.message.reply_text(
        "🚗 Mashinangizning *rusumini (modelini)* yozing (masalan: Cobalt, Lacetti):",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return BRAND_MODEL


async def brand_get_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    model = (update.message.text or "").strip()
    if len(model) < 2:
        await update.message.reply_text("❗ Iltimos, mashina rusumini yozing:")
        return BRAND_MODEL
    context.user_data["b_model"] = model
    await update.message.reply_text(
        "📅 Mashinangizning *yilini* yozing (masalan: 2018):",
        parse_mode="Markdown",
    )
    return BRAND_YEAR


async def brand_get_year(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    year_text = (update.message.text or "").strip()
    if not year_text.isdigit() or not (1990 <= int(year_text) <= 2030):
        await update.message.reply_text("❗ Iltimos, to'g'ri yil kiriting (masalan: 2018):")
        return BRAND_YEAR
    context.user_data["b_year"] = year_text
    await update.message.reply_text(
        "🎨 Mashinangizning *rangini* yozing (masalan: Oq, Qora, Kumush):",
        parse_mode="Markdown",
    )
    return BRAND_COLOR


async def brand_get_color(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    color = (update.message.text or "").strip()
    if len(color) < 2:
        await update.message.reply_text("❗ Iltimos, mashina rangini yozing:")
        return BRAND_COLOR
    context.user_data["b_color"] = color

    await _send_brand_to_group(update, context)

    await update.message.reply_text(
        "🎉 *Tabriklaymiz!*\n\n"
        "Brend arizangiz qabul qilindi. Tez orada operatorlarimiz siz bilan bog'lanishadi.\n\n"
        "Yangi ariza tashlash uchun /start bosing.",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD,
    )
    context.user_data.clear()
    return ConversationHandler.END


async def _send_brand_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = context.user_data
    text = (
        "🎨 *YANGI BREND ARIZA*\n\n"
        f"👤 FIO: {d.get('b_name', '-')}\n"
        f"📞 Tel: {d.get('b_phone', '-')}\n"
        f"🚗 Model: {d.get('b_model', '-')}\n"
        f"📅 Yili: {d.get('b_year', '-')}\n"
        f"🎨 Rangi: {d.get('b_color', '-')}"
    )
    try:
        await context.bot.send_message(
            chat_id=BRAND_GROUP, text=text, parse_mode="Markdown"
        )
    except Exception as e:
        print(f"[brand] failed to send to {BRAND_GROUP}: {e}")


def build_brand_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(f"^{MENU_BRAND}$"), start_brand),
        ],
        states={
            BRAND_WARN: [
                MessageHandler(filters.Regex(f"^{CONTINUE_BTN}$"), brand_warn),
            ],
            BRAND_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, brand_get_name)],
            BRAND_PHONE: [
                MessageHandler(
                    filters.CONTACT | (filters.TEXT & ~filters.COMMAND), brand_get_phone
                )
            ],
            BRAND_MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, brand_get_model)],
            BRAND_YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, brand_get_year)],
            BRAND_COLOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, brand_get_color)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", cancel)],
        allow_reentry=True,
    )
