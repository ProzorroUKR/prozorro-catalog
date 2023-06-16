from dataclasses import dataclass
import asyncio
import logging

from pymongo.errors import PyMongoError
from pymongo import UpdateOne

import sentry_sdk

from catalog.db import get_offers_collection, init_mongo, transaction_context_manager
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
    async with transaction_context_manager() as session:
        bulk = []
        async for p in offers_collection.find({}, session=session):
            bulk.append(
                UpdateOne(
                    filter={"_id": p["_id"]},
                    update={"$set": {
                        "status": "hidden", "dateModified": get_now().isoformat()}
                    }
                )
            )
            counters.updated_offers += 1

        if bulk:
            bulk_len = len(bulk)
            result = await offers_collection.bulk_write(bulk, session=session)
            if result.modified_count != len(bulk):
                logger.error(f"Unexpected modified_count: {result.modified_count}; expected {len(bulk)}")
            counters.skipped_offers += bulk_len - result.modified_count
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
