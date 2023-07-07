from dataclasses import dataclass
import asyncio
import logging

from pymongo.errors import PyMongoError
from pymongo import UpdateOne

import sentry_sdk

from catalog.db import get_offers_collection, init_mongo
from catalog.logging import setup_logging
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now


logger = logging.getLogger(__name__)


@dataclass
class Counters:
    total_offers: int = 0
    updated_offers: int = 0
    skipped_offers: int = 0


async def migrate():
    logger.info("Start migration")
    stats = Counters()
    try:
        stats = await migrate_offers()
    except PyMongoError as e:
        logger.warning(f"Handled mongo error: {e}")

    logger.info(f"Finished. Stats: {stats}")
    return stats


async def migrate_offers():
    counters = Counters()

    offers_collection = get_offers_collection()
    bulk = []
    async for o in offers_collection.find({}, {"_id": 1, "status": 1}):
        if o["status"] != "hidden":
            bulk.append(
                UpdateOne(
                    filter={"_id": o["_id"]},
                    update={"$set": {
                        "status": "hidden", "dateModified": get_now().isoformat()}
                    }
                )
            )
            counters.updated_offers += 1
        else:
            counters.skipped_offers += 1

        if bulk and len(bulk) % 500 == 0:
            skipped_offers = await offers_bulk_write(bulk)
            counters.skipped_offers += skipped_offers
            bulk = []
        counters.total_offers += 1

    if bulk:
        skipped_offers = await offers_bulk_write(bulk)
        counters.skipped_offers += skipped_offers
    return counters


async def offers_bulk_write(bulk):
    bulk_len = len(bulk)
    result = await get_offers_collection().bulk_write(bulk)
    if result.modified_count != len(bulk):
        logger.error(f"Unexpected modified_count: {result.modified_count}; expected {len(bulk)}")
    return bulk_len - result.modified_count


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate())


if __name__ == '__main__':
    main()
