import logging

from telegram.ext import Application, CommandHandler
from telegram.request import HTTPXRequest

from bot.config import BOT_TOKEN
from bot.handlers.brand import build_brand_conversation
from bot.handlers.driver import build_driver_conversation
from bot.handlers.operator import register_operator_handlers
from bot.handlers.start import start

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


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
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(build_driver_conversation())
    app.add_handler(build_brand_conversation())
    register_operator_handlers(app)

    logger.info("🚖 WB TAXI HUMO bot ishga tushdi...")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
