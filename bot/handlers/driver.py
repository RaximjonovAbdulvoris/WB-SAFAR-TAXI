from telegram import (
    InputMediaPhoto,
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

from bot.config import DRIVER_GROUPS, template_path
from bot.handlers.start import MAIN_KEYBOARD, MENU_DRIVER, cancel

(
    NAME,
    PHONE,
    WARN_DOCS,
    PASSPORT_FRONT,
    PASSPORT_BACK,
    LICENSE_FRONT,
    LICENSE_BACK,
    TECH_FRONT,
    TECH_BACK,
    SELFIE,
    LITSENZIYA,
    CAR_PHOTOS,
    CAR_PLATE,
) = range(13)

CONTINUE_BTN = "✅ Davom etish"
CONTINUE_KB = ReplyKeyboardMarkup(
    [[CONTINUE_BTN]], resize_keyboard=True, one_time_keyboard=True
)


async def _send_prompt(update: Update, text: str, template_name: str | None = None,
                       reply_markup=None):
    """Send a prompt with optional template image."""
    path = template_path(template_name) if template_name else None
    if path:
        with open(path, "rb") as f:
            await update.message.reply_photo(
                photo=f, caption=text, reply_markup=reply_markup
            )
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)


# ---------- entry ----------
async def start_driver(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "📝 *Haydovchilik uchun ariza*\n\n"
        "Iltimos, *ism va familiyangizni* yozing:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return NAME


# ---------- 1. name ----------
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = (update.message.text or "").strip()
    if len(name) < 3:
        await update.message.reply_text(
            "❗ Iltimos, to'liq ism va familiyangizni yozing:"
        )
        return NAME
    context.user_data["name"] = name
    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("📞 Raqamni jo'natish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await update.message.reply_text(
        "📞 Iltimos, telefon raqamingizni jo'nating (knopka orqali):",
        reply_markup=kb,
    )
    return PHONE


# ---------- 2. phone ----------
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone = None
    if update.message.contact:
        phone = update.message.contact.phone_number
    elif update.message.text:
        phone = update.message.text.strip()
    if not phone or len(phone) < 7:
        await update.message.reply_text(
            "❗ Iltimos, telefon raqamingizni jo'nating (knopkani bosing):"
        )
        return PHONE
    context.user_data["phone"] = phone

    await update.message.reply_text(
        "⚠️ *Diqqat!*\n\n"
        "Endi sizdan hujjatlaringizning *originalini rasmga olib* jo'natishingiz so'raladi.\n\n"
        "❌ Soliqdan olingan skrinshot QABUL QILINMAYDI!\n\n"
        "Davom etish uchun pastdagi knopkani bosing.",
        parse_mode="Markdown",
        reply_markup=CONTINUE_KB,
    )
    return WARN_DOCS


# ---------- 3. warn ----------
async def warn_docs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _send_prompt(
        update,
        "📄 1/12 — *Passport (old tarafi)* rasmini jo'nating:",
        "passport_front",
        reply_markup=ReplyKeyboardRemove(),
    )
    return PASSPORT_FRONT


# ---------- helper for photo collecting ----------
async def _collect_photo(update: Update, context: ContextTypes.DEFAULT_TYPE,
                          field: str, next_text: str, next_template: str | None,
                          next_state: int) -> int:
    if not update.message.photo:
        await update.message.reply_text("❗ Iltimos, *rasm tashlang*!", parse_mode="Markdown")
        return context.user_data.get("_state", PASSPORT_FRONT)
    file_id = update.message.photo[-1].file_id
    context.user_data[field] = file_id
    await _send_prompt(update, next_text, next_template)
    context.user_data["_state"] = next_state
    return next_state


# ---------- 4. passport front ----------
async def get_passport_front(update, context):
    return await _collect_photo(
        update, context, "passport_front",
        "📄 2/12 — *Passport (orqa tarafi)* rasmini jo'nating:",
        "passport_back", PASSPORT_BACK,
    )


# ---------- 5. passport back ----------
async def get_passport_back(update, context):
    return await _collect_photo(
        update, context, "passport_back",
        "🪪 3/12 — *Haydovchilik guvohnomasi (old tarafi)* rasmini jo'nating:",
        "license_front", LICENSE_FRONT,
    )


# ---------- 6. license front ----------
async def get_license_front(update, context):
    return await _collect_photo(
        update, context, "license_front",
        "🪪 4/12 — *Haydovchilik guvohnomasi (orqa tarafi)* rasmini jo'nating:",
        "license_back", LICENSE_BACK,
    )


# ---------- 7. license back ----------
async def get_license_back(update, context):
    return await _collect_photo(
        update, context, "license_back",
        "🚘 5/12 — *Texnik passport (old tarafi)* rasmini jo'nating:",
        "tech_front", TECH_FRONT,
    )


# ---------- 8. tech front ----------
async def get_tech_front(update, context):
    return await _collect_photo(
        update, context, "tech_front",
        "🚘 6/12 — *Texnik passport (orqa tarafi)* rasmini jo'nating:",
        "tech_back", TECH_BACK,
    )


# ---------- 9. tech back ----------
async def get_tech_back(update, context):
    return await _collect_photo(
        update, context, "tech_back",
        "🤳 7/12 — *Selfie* rasmingizni jo'nating:",
        "selfie", SELFIE,
    )


# ---------- 10. selfie ----------
async def get_selfie(update, context):
    return await _collect_photo(
        update, context, "selfie",
        "📜 8/12 — *Litsenziya* rasmini jo'nating:",
        "litsenziya", LITSENZIYA,
    )


# ---------- 11. litsenziya -> ask car photos ----------
async def get_litsenziya(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message.photo:
        await update.message.reply_text("❗ Iltimos, *rasm tashlang*!", parse_mode="Markdown")
        return LITSENZIYA
    context.user_data["litsenziya"] = update.message.photo[-1].file_id
    context.user_data["car_photos"] = []
    await _send_prompt(
        update,
        "🚗 9-12/12 — Mashinangizning *4 ta tarafidan* rasmga olib jo'nating "
        "(old, orqa, chap, o'ng).\n\n"
        "Hammasini birin-ketin (4 ta rasm) jo'natishingiz kerak.",
        "car_sides",
    )
    return CAR_PHOTOS


# ---------- 12. car photos (4) ----------
async def get_car_photos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photos = context.user_data.setdefault("car_photos", [])
    if not update.message.photo:
        await update.message.reply_text(
            f"❗ *4 ta rasm yukleng*! Hozir {len(photos)}/4 ta yuborildi.",
            parse_mode="Markdown",
        )
        return CAR_PHOTOS

    photos.append(update.message.photo[-1].file_id)

    if len(photos) < 4:
        await update.message.reply_text(
            f"✅ {len(photos)}/4 ta rasm qabul qilindi. "
            f"Yana {4 - len(photos)} ta rasm jo'nating."
        )
        return CAR_PHOTOS

    await update.message.reply_text(
        "🔢 Endi mashinangizning *davlat raqamini* yozing (masalan: `01A123BC`):",
        parse_mode="Markdown",
    )
    return CAR_PLATE


# ---------- 13. car plate -> finish ----------
async def get_car_plate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    plate = (update.message.text or "").strip().upper()
    if len(plate) < 5:
        await update.message.reply_text("❗ Iltimos, to'g'ri davlat raqami kiriting:")
        return CAR_PLATE
    context.user_data["car_plate"] = plate

    user = update.effective_user
    context.user_data["user_id"] = user.id
    context.user_data["user_link"] = (
        f"@{user.username}" if user.username else f"tg://user?id={user.id}"
    )
    context.user_data["user_display"] = (
        f"@{user.username}" if user.username else (user.full_name or str(user.id))
    )

    await _send_to_driver_groups(context)

    await update.message.reply_text(
        "🎉 *Tabriklaymiz!*\n\n"
        "Arizangiz qabul qilindi. Tez orada operatorlarimiz siz bilan bog'lanishadi.\n\n"
        "Yangi ariza tashlash uchun /start bosing.",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD,
    )
    context.user_data.clear()
    return ConversationHandler.END


async def _send_to_driver_groups(context: ContextTypes.DEFAULT_TYPE):
    d = context.user_data
    caption_main = (
        "📝 *YANGI ARIZA*\n\n"
        f"👤 Foydalanuvchi: {d.get('user_link', '-')}\n"
        f"🪪 Ism familiya: {d.get('name', '-')}\n"
        f"📞 Tel: {d.get('phone', '-')}\n"
        f"🚗 Mashina raqami: {d.get('car_plate', '-')}"
    )
    caption_selfie = f"🤳 {d.get('name', '-')} — litsenziya va selfie"

    main_album_ids = [
        d.get("passport_front"),
        d.get("passport_back"),
        d.get("tech_front"),
        d.get("tech_back"),
        d.get("license_front"),
        d.get("license_back"),
        *d.get("car_photos", []),
    ]
    main_album_ids = [pid for pid in main_album_ids if pid]
    selfie_album_ids = [d.get("selfie"), d.get("litsenziya")]
    selfie_album_ids = [pid for pid in selfie_album_ids if pid]

    for chat_id in DRIVER_GROUPS:
        try:
            if main_album_ids:
                main_media = [
                    InputMediaPhoto(
                        media=fid,
                        caption=caption_main if i == 0 else None,
                        parse_mode="Markdown" if i == 0 else None,
                    )
                    for i, fid in enumerate(main_album_ids)
                ]
                await context.bot.send_media_group(chat_id=chat_id, media=main_media)
            if selfie_album_ids:
                selfie_media = [
                    InputMediaPhoto(
                        media=fid,
                        caption=caption_selfie if i == 0 else None,
                    )
                    for i, fid in enumerate(selfie_album_ids)
                ]
                await context.bot.send_media_group(chat_id=chat_id, media=selfie_media)
        except Exception as e:
            print(f"[driver] failed to send to {chat_id}: {e}")


def build_driver_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(f"^{MENU_DRIVER}$"), start_driver),
        ],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [
                MessageHandler(filters.CONTACT | (filters.TEXT & ~filters.COMMAND),
                               get_phone)
            ],
            WARN_DOCS: [
                MessageHandler(filters.Regex(f"^{CONTINUE_BTN}$"), warn_docs),
                MessageHandler(filters.TEXT & ~filters.COMMAND, warn_docs),
            ],
            PASSPORT_FRONT: [MessageHandler(filters.ALL & ~filters.COMMAND, get_passport_front)],
            PASSPORT_BACK: [MessageHandler(filters.ALL & ~filters.COMMAND, get_passport_back)],
            LICENSE_FRONT: [MessageHandler(filters.ALL & ~filters.COMMAND, get_license_front)],
            LICENSE_BACK: [MessageHandler(filters.ALL & ~filters.COMMAND, get_license_back)],
            TECH_FRONT: [MessageHandler(filters.ALL & ~filters.COMMAND, get_tech_front)],
            TECH_BACK: [MessageHandler(filters.ALL & ~filters.COMMAND, get_tech_back)],
            SELFIE: [MessageHandler(filters.ALL & ~filters.COMMAND, get_selfie)],
            LITSENZIYA: [MessageHandler(filters.ALL & ~filters.COMMAND, get_litsenziya)],
            CAR_PHOTOS: [MessageHandler(filters.ALL & ~filters.COMMAND, get_car_photos)],
            CAR_PLATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_car_plate)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", cancel)],
        allow_reentry=True,
    )
