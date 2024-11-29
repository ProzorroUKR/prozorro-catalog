import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from pymongo import UpdateOne
import sentry_sdk

from catalog.db import get_products_collection, init_mongo
from catalog.models.product import ProductStatus
from catalog.logging import setup_logging
from catalog.utils import get_now
from catalog.settings import SENTRY_DSN


logger = logging.getLogger(__name__)


@dataclass
class Counters:
    total_products: int = 0
    succeeded_products: int = 0
    skipped_products: int = 0


async def run_task():
    products_collection = get_products_collection()
    counters = Counters()
    bulk = []

    async for product in products_collection.find(
            {"status": ProductStatus.active, "expirationDate": {"$exists": True}},
            projection={"expirationDate": 1},
            no_cursor_timeout=True,
    ):
        if datetime.fromisoformat(product["expirationDate"]) < get_now():
            bulk.append(
                UpdateOne(
                    filter={"_id": product["_id"]},
                    update={
                        "$set": {"status": ProductStatus.inactive, "dateModified": get_now().isoformat()},
                    },
                )
            )
            counters.total_products += 1

    if bulk:
        result = await products_collection.bulk_write(bulk)
        bulk_len = len(bulk)
        if result.modified_count != bulk_len:
            logger.error(f"Unexpected modified_count: {result.modified_count}; expected {bulk_len}")
        counters.succeeded_products = result.modified_count
        counters.skipped_products = counters.total_products - result.modified_count

    logger.info(f"Finished. Stats: {counters}")
    return counters


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(run_task())


if __name__ == '__main__':
    main()
