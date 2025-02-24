import asyncio
import logging

import sentry_sdk
from pymongo import UpdateOne

from catalog.db import (
    get_vendor_collection,
    init_mongo,
    transaction_context_manager,
)
from catalog.logging import setup_logging
from catalog.settings import SENTRY_DSN

logger = logging.getLogger(__name__)


async def bulk_update(collection, bulk, session, counter):
    await collection.bulk_write(bulk, session=session)
    logger.info(f"Processed {counter} records of migrated vendors")


async def migrate_vendors():
    logger.info("Start migration")
    collection = get_vendor_collection()
    counter = 0
    bulk = []
    cursor = collection.find(
        {},
        projection={"_id": 1},
        no_cursor_timeout=True,
        batch_size=200,
    )
    async for obj in cursor:
        counter += 1
        bulk.append(
            UpdateOne(
                filter={"_id": obj["_id"]},
                update={"$unset": {"categories": ""}},
            )
        )
        if bulk and len(bulk) % 500 == 0:
            async with transaction_context_manager() as session:
                await bulk_update(collection, bulk, session, counter)
            bulk = []
    if bulk:
        async with transaction_context_manager() as session:
            await bulk_update(collection, bulk, session, counter)
    await cursor.close()
    logger.info(f"Finished. Processed {counter} records of migrated vendors")
    logger.info("Successfully migrated")


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate_vendors())


if __name__ == "__main__":
    main()
