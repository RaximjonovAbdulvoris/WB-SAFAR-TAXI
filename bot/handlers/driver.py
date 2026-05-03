import logging
from html import escape as h

from telegram import (
    InputMediaPhoto,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.config import DRIVER_GROUPS, template_path
from bot.counter import next_index
from bot.handlers.operator import build_operator_keyboard
from bot.handlers.start import MAIN_KEYBOARD, MENU_DRIVER, cancel

logger = logging.getLogger(__name__)

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


# -------------------- prompt sender --------------------
async def _send_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE,
                       text: str, template_name: str | None = None,
                       reply_markup=None):
    """Send a prompt, attaching the cached template image if available.
    Falls back to text-only on any error so the flow never gets stuck."""
    if not template_name:
        await update.message.reply_text(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )
        return

    cache = context.bot_data.setdefault("template_file_ids", {})
    file_id = cache.get(template_name)

    try:
        if file_id:
            await update.message.reply_photo(
                photo=file_id, caption=text,
                parse_mode="Markdown", reply_markup=reply_markup,
            )
            return

        path = template_path(template_name)
        if not path:
            await update.message.reply_text(
                text, reply_markup=reply_markup, parse_mode="Markdown"
            )
            return

        with open(path, "rb") as f:
            sent = await update.message.reply_photo(
                photo=f, caption=text,
                parse_mode="Markdown", reply_markup=reply_markup,
            )
        if sent and sent.photo:
            cache[template_name] = sent.photo[-1].file_id
    except Exception as e:
        logger.warning("template '%s' yuborilmadi: %s", template_name, e)
        await update.message.reply_text(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )


# -------------------- entry --------------------
async def start_driver(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "📝 *Haydovchilik uchun ariza*\n\n"
        "Iltimos, *ism va familiyangizni* yozing:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return NAME


# -------------------- 1. name --------------------
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


async def name_wrong(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "❗ Iltimos, *matn* ko'rinishida ism va familiyangizni yozing:",
        parse_mode="Markdown",
    )
    return NAME


# -------------------- 2. phone --------------------
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone = None
    if update.message.contact:
        phone = update.message.contact.phone_number
    elif update.message.text:
        phone = update.message.text.strip()
    if not phone or len(phone) < 7 or not any(c.isdigit() for c in phone):
        await update.message.reply_text(
            "❗ Iltimos, telefon raqamingizni knopka orqali jo'nating "
            "yoki to'g'ri raqam kiriting (masalan: +998901234567):"
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


async def phone_wrong(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "❗ Iltimos, *📞 Raqamni jo'natish* knopkasini bosing yoki raqamingizni yozing:",
        parse_mode="Markdown",
    )
    return PHONE


# -------------------- 3. warn --------------------
async def warn_docs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _send_prompt(
        update, context,
        "📄 1/12 — *Passport (old tarafi)* rasmini jo'nating:",
        "passport_front",
        reply_markup=ReplyKeyboardRemove(),
    )
    return PASSPORT_FRONT


async def warn_wrong(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        f"❗ Iltimos, *{CONTINUE_BTN}* knopkasini bosing:",
        parse_mode="Markdown",
        reply_markup=CONTINUE_KB,
    )
    return WARN_DOCS


# -------------------- photo step factory --------------------
def _make_photo_step(field: str, next_text: str,
                     next_template: str | None, current_state: int,
                     next_state: int):
    """Create (handler, wrong-input handler) for a single-photo step."""

    async def get(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if not update.message.photo:
            return await wrong(update, context)
        context.user_data[field] = update.message.photo[-1].file_id
        await _send_prompt(update, context, next_text, next_template)
        return next_state

    async def wrong(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text(
            "❗ Iltimos, *rasm jo'nating*! Matn yoki boshqa tur qabul qilinmaydi.",
            parse_mode="Markdown",
        )
        return current_state

    return get, wrong


get_passport_front, _wrong_pf = _make_photo_step(
    "passport_front",
    "📄 2/12 — *Passport (orqa tarafi)* rasmini jo'nating:",
    "passport_back", PASSPORT_FRONT, PASSPORT_BACK,
)
get_passport_back, _wrong_pb = _make_photo_step(
    "passport_back",
    "🪪 3/12 — *Haydovchilik guvohnomasi (old tarafi)* rasmini jo'nating:",
    "license_front", PASSPORT_BACK, LICENSE_FRONT,
)
get_license_front, _wrong_lf = _make_photo_step(
    "license_front",
    "🪪 4/12 — *Haydovchilik guvohnomasi (orqa tarafi)* rasmini jo'nating:",
    "license_back", LICENSE_FRONT, LICENSE_BACK,
)
get_license_back, _wrong_lb = _make_photo_step(
    "license_back",
    "🚘 5/12 — *Texnik passport (old tarafi)* rasmini jo'nating:",
    "tech_front", LICENSE_BACK, TECH_FRONT,
)
get_tech_front, _wrong_tf = _make_photo_step(
    "tech_front",
    "🚘 6/12 — *Texnik passport (orqa tarafi)* rasmini jo'nating:",
    "tech_back", TECH_FRONT, TECH_BACK,
)
get_tech_back, _wrong_tb = _make_photo_step(
    "tech_back",
    "🤳 7/12 — *Selfie* rasmingizni jo'nating:",
    "selfie", TECH_BACK, SELFIE,
)
get_selfie, _wrong_se = _make_photo_step(
    "selfie",
    "📜 8/12 — *Litsenziya* rasmini jo'nating:",
    "litsenziya", SELFIE, LITSENZIYA,
)


# -------------------- 11. litsenziya -> ask car photos --------------------
async def get_litsenziya(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message.photo:
        return await litsenziya_wrong(update, context)
    context.user_data["litsenziya"] = update.message.photo[-1].file_id
    context.user_data["car_photos"] = []
    await _send_prompt(
        update, context,
        "🚗 9-12/12 — Mashinangizning *4 ta tarafidan* rasmga olib jo'nating "
        "(old, orqa, chap, o'ng).\n\n"
        "Hammasini birin-ketin (4 ta rasm) jo'natishingiz kerak.",
        "car_sides",
    )
    return CAR_PHOTOS


async def litsenziya_wrong(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "❗ Iltimos, *litsenziya rasmini* jo'nating!",
        parse_mode="Markdown",
    )
    return LITSENZIYA


# -------------------- 12. car photos (4) --------------------
async def get_car_photos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Accept car photos one-by-one OR as a media group (album).

    Rules:
    - Photos in an album arrive as separate updates with the same media_group_id.
    - Album photos: collect silently, send ONE message only when total reaches 4.
    - Individual photos: send a progress message after each one.
    - If user already sent 4+, ignore extras and stay on CAR_PLATE quietly.
    """
    photos = context.user_data.setdefault("car_photos", [])

    if not update.message.photo:
        await update.message.reply_text(
            f"❗ *Mashina rasmlari kerak*! Hozir {len(photos)}/4 ta yuborildi. "
            "Iltimos, *rasm* jo'nating.",
            parse_mode="Markdown",
        )
        return CAR_PHOTOS

    # Already have 4 — ignore extra photos that may arrive late from a big album
    if len(photos) >= 4:
        return CAR_PLATE

    photos.append(update.message.photo[-1].file_id)
    is_album = bool(update.message.media_group_id)

    if len(photos) >= 4:
        # Done — clean up and ask for plate number
        context.user_data.pop("car_photo_replied_groups", None)
        await update.message.reply_text(
            "✅ *4 ta rasm qabul qilindi!*\n\n"
            "🔢 Endi mashinangizning *davlat raqamini* yozing (masalan: `01A123BC`):",
            parse_mode="Markdown",
        )
        return CAR_PLATE

    if is_album:
        # Part of an album but haven't reached 4 yet — stay silent.
        # This avoids spamming "1/4", "2/4" when photos arrive milliseconds apart.
        return CAR_PHOTOS

    # Single photo, not an album — show progress so user knows how many more to send
    await update.message.reply_text(
        f"✅ {len(photos)}/4 ta rasm qabul qilindi. "
        f"Yana *{4 - len(photos)} ta* rasm jo'nating.",
        parse_mode="Markdown",
    )
    return CAR_PHOTOS


async def car_photos_wrong(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photos = context.user_data.get("car_photos", [])
    await update.message.reply_text(
        f"❗ Iltimos, *mashina rasmini* jo'nating! ({len(photos)}/4 yuborildi)",
        parse_mode="Markdown",
    )
    return CAR_PHOTOS


# -------------------- 13. car plate -> finish --------------------
async def get_car_plate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    plate = (update.message.text or "").strip().upper()
    if len(plate) < 5 or not any(c.isalnum() for c in plate):
        await update.message.reply_text(
            "❗ Iltimos, to'g'ri davlat raqami kiriting (masalan: `01A123BC`):",
            parse_mode="Markdown",
        )
        return CAR_PLATE
    context.user_data["car_plate"] = plate

    user = update.effective_user
    context.user_data["user_id"] = user.id
    context.user_data["user_username"] = user.username or ""
    context.user_data["user_full_name"] = user.full_name or ""

    try:
        await _send_to_driver_group(context)
    except Exception as e:
        logger.exception("driver: send_to_driver_group failed: %s", e)
        await update.message.reply_text(
            "⚠️ Texnik xatolik yuz berdi. Iltimos, qaytadan /start bosib urinib ko'ring."
        )
        context.user_data.clear()
        return ConversationHandler.END

    await update.message.reply_text(
        "🎉 *Tabriklaymiz!*\n\n"
        "Arizangiz qabul qilindi. Tez orada operatorlarimiz "
        "tomonidan ko'rib chiqilib, qayta javob yozib yuboriladi.\n\n"
        "Qandaydir savollaringiz bo'lsa, "
        "[@wbhumoadmin](https://t.me/wbhumoadmin) ga yozishingiz mumkin!\n\n"
        "Yangi ariza tashlash uchun /start bosing.",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD,
        disable_web_page_preview=True,
    )
    context.user_data.clear()
    return ConversationHandler.END


async def car_plate_wrong(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "❗ Iltimos, davlat raqamini *matn ko'rinishida* yozing (masalan: `01A123BC`):",
        parse_mode="Markdown",
    )
    return CAR_PLATE


# -------------------- group dispatch --------------------
async def _send_to_driver_group(context: ContextTypes.DEFAULT_TYPE):
    """Send the application to ONE driver group, rotating through them."""
    d = context.user_data
    idx = next_index("driver_group_rr", len(DRIVER_GROUPS))
    chat_id = DRIVER_GROUPS[idx]

    user_id = d.get("user_id")
    username = d.get("user_username", "")
    full_name = d.get("user_full_name", "") or "Foydalanuvchi"
    display = f"@{username}" if username else full_name
    user_link_html = (
        f'<a href="tg://user?id={user_id}">{h(display)}</a>' if user_id else h(display)
    )

    caption_main = (
        "📝 <b>YANGI ARIZA</b>\n\n"
        f"👤 Foydalanuvchi: {user_link_html}\n"
        f"🪪 Ism familiya: {h(d.get('name', '-'))}\n"
        f"📞 Tel: {h(d.get('phone', '-'))}\n"
        f"🚗 Mashina raqami: {h(d.get('car_plate', '-'))}"
    )
    caption_selfie = f"🤳 {h(d.get('name', '-'))} — selfie va litsenziya"

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

    sent_msg_ids: list[int] = []

    if main_album_ids:
        main_media = [
            InputMediaPhoto(
                media=fid,
                caption=caption_main if i == 0 else None,
                parse_mode=ParseMode.HTML if i == 0 else None,
            )
            for i, fid in enumerate(main_album_ids)
        ]
        main_sent = await context.bot.send_media_group(chat_id=chat_id, media=main_media)
        sent_msg_ids.extend(m.message_id for m in main_sent)

    if selfie_album_ids:
        selfie_media = [
            InputMediaPhoto(
                media=fid,
                caption=caption_selfie if i == 0 else None,
                parse_mode=ParseMode.HTML if i == 0 else None,
            )
            for i, fid in enumerate(selfie_album_ids)
        ]
        selfie_sent = await context.bot.send_media_group(chat_id=chat_id, media=selfie_media)
        sent_msg_ids.extend(m.message_id for m in selfie_sent)

    if user_id:
        # Cache applicant info so operator.py can build a proper mention link
        applicant_cache = context.bot_data.setdefault("applicant_info", {})
        applicant_cache[user_id] = {
            "name": d.get("name") or full_name or "Arizachi",
            "username": username,
        }

        kb_msg = await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "👇 Ariza bo'yicha amal tanlang:\n"
                f"👤 Arizachi: {user_link_html}"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=build_operator_keyboard(user_id),
        )
        sent_msg_ids.append(kb_msg.message_id)

        # Store all message IDs so "Tayyor" can delete them and copy to archive
        context.bot_data.setdefault("app_messages", {})[user_id] = {
            "group_chat_id": chat_id,
            "message_ids": sent_msg_ids,
        }

    logger.info("[driver] sent application to group #%s (%s)", idx + 1, chat_id)


# -------------------- conversation builder --------------------
def _photo_state(get_handler, wrong_handler):
    """Photo states accept ONLY photos; everything else triggers wrong handler."""
    return [
        MessageHandler(filters.PHOTO, get_handler),
        MessageHandler(~filters.COMMAND, wrong_handler),
    ]


def build_driver_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(f"^{MENU_DRIVER}$"), start_driver),
        ],
        states={
            NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_name),
                MessageHandler(~filters.COMMAND, name_wrong),
            ],
            PHONE: [
                MessageHandler(filters.CONTACT, get_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone),
                MessageHandler(~filters.COMMAND, phone_wrong),
            ],
            WARN_DOCS: [
                MessageHandler(filters.Regex(f"^{CONTINUE_BTN}$"), warn_docs),
                MessageHandler(~filters.COMMAND, warn_wrong),
            ],
            PASSPORT_FRONT: _photo_state(get_passport_front, _wrong_pf),
            PASSPORT_BACK: _photo_state(get_passport_back, _wrong_pb),
            LICENSE_FRONT: _photo_state(get_license_front, _wrong_lf),
            LICENSE_BACK: _photo_state(get_license_back, _wrong_lb),
            TECH_FRONT: _photo_state(get_tech_front, _wrong_tf),
            TECH_BACK: _photo_state(get_tech_back, _wrong_tb),
            SELFIE: _photo_state(get_selfie, _wrong_se),
            LITSENZIYA: _photo_state(get_litsenziya, litsenziya_wrong),
            CAR_PHOTOS: _photo_state(get_car_photos, car_photos_wrong),
            CAR_PLATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_car_plate),
                MessageHandler(~filters.COMMAND, car_plate_wrong),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", cancel)],
        allow_reentry=True,
    )
