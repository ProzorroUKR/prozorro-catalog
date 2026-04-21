import asyncio
import logging

import sentry_sdk

from catalog.db import init_mongo
from catalog.logging import setup_logging
from catalog.prices import calculate_price
from catalog.settings import SENTRY_DSN

logger = logging.getLogger(__name__)


async def run_task():
    logger.info("Starting price calculation")
    await calculate_price()
    logger.info("Finished price calculation")

    return None


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(run_task())


if __name__ == "__main__":
    main()
