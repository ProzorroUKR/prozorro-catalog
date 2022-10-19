import asyncio
import logging
from dataclasses import dataclass

from pymongo import UpdateOne
import sentry_sdk

from catalog.db import get_products_collection, init_mongo, transaction_context_manager
from catalog.logging import setup_logging
from catalog.utils import get_now
from catalog.settings import SENTRY_DSN


logger = logging.getLogger(__name__)


@dataclass
class Counters:
    total_products: int = 0
    succeeded_products: int = 0
    skipped_products: int = 0


async def migrate():
    logger.info("Start migration")

    counters = Counters()
    bulk = []
    products_collection = get_products_collection()

    async for p in products_collection.find({"relatedProfile": {"$exists": True}}, projection={"relatedProfile": 1}):
        now = get_now().isoformat()
        bulk.append(
            UpdateOne(
                filter={"_id": p["_id"]},
                update={
                    "$set": {"relatedProfiles": [p["relatedProfile"]], "dateModified": now},
                    "$unset": {"relatedProfile": ""},
                },
            )
        )

    if bulk:
        result = await products_collection.bulk_write(bulk)
        bulk_len = len(bulk)
        if result.modified_count != len(bulk):
            logger.error(f"Unexpected modified_count: {result.modified_count}; expected {len(bulk)}")
        counters.total_products = bulk_len
        counters.succeeded_products = result.modified_count
        counters.skipped_products = bulk_len - result.modified_count

    logger.info(f"Finished. Stats: {counters}")
    return counters


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate())


if __name__ == '__main__':
    main()
