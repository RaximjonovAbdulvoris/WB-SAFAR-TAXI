import logging

from telegram import Update
from telegram.error import Conflict, NetworkError, TimedOut
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.request import HTTPXRequest

from bot.config import BOT_TOKEN
from bot.handlers.brand import build_brand_conversation
from bot.handlers.driver import build_driver_conversation
from bot.handlers.operator import register_operator_handlers
from bot.handlers.start import start
from bot.warmup import warmup_templates

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global error handler.

    - Conflict (another bot instance polling): warn once, do not spam tracebacks.
    - Network/Timeout: warn briefly, the polling loop will recover automatically.
    - Other errors: full traceback + a friendly message to the user if possible.
    """
    err = context.error

    if isinstance(err, Conflict):
        logger.warning(
            "Conflict: another instance is polling with the same bot token. "
            "Check Render: stop duplicate services or wait for the old container "
            "to drain."
        )
        return

    if isinstance(err, (NetworkError, TimedOut)):
        logger.warning("Network/Timeout while polling: %s", err)
        return

    logger.error("Unhandled error: %s", err, exc_info=err)
    try:
        if isinstance(update, Update) and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=(
                    "⚠️ Texnik xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring "
                    "yoki /start bosing."
                ),
            )
    except Exception:
        pass


def main() -> None:
    request = HTTPXRequest(
        connection_pool_size=20,
        connect_timeout=30.0,
        read_timeout=60.0,
        write_timeout=60.0,
        pool_timeout=10.0,
    )
    get_updates_request = HTTPXRequest(
        connection_pool_size=8,
        connect_timeout=30.0,
        read_timeout=40.0,
        write_timeout=40.0,
    )

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .get_updates_request(get_updates_request)
        .post_init(warmup_templates)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(build_driver_conversation())
    app.add_handler(build_brand_conversation())
    register_operator_handlers(app)
    app.add_error_handler(on_error)

    logger.info("🚖 WB TAXI HUMO bot ishga tushdi...")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
