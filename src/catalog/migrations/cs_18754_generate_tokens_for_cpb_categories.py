import asyncio
import logging
from secrets import token_hex

import sentry_sdk
from pymongo import UpdateOne

from catalog.auth import hash_access_token
from catalog.db import (
    get_category_collection,
    init_mongo,
    transaction_context_manager,
)
from catalog.logging import setup_logging
from catalog.settings import CPB_USERNAME, SENTRY_DSN

logger = logging.getLogger(__name__)


async def migrate():
    logger.info("Start migration")
    async with transaction_context_manager() as session:
        collection = get_category_collection()
        bulk = []
        counter = 0
        async for obj in collection.find({"access.owner": CPB_USERNAME}, projection={"_id": 1}):
            new_token = token_hex(16)
            bulk.append(
                UpdateOne(
                    filter={"_id": obj["_id"]},
                    update={"$set": {"access.token": hash_access_token(new_token)}},
                )
            )
            counter += 1
            logger.info(f"CATEGORY ID {obj['_id']} TOKEN: {new_token}")

            if bulk and len(bulk) % 500 == 0:
                await bulk_update(collection, bulk, session, counter)
                bulk = []

        if bulk:
            await bulk_update(collection, bulk, session, counter)

        logger.info(f"Finished. Processed {counter} records of migrated categories")
    logger.info("Successfully migrated")


async def bulk_update(collection, bulk, session, counter):
    await collection.bulk_write(bulk, session=session)
    logger.info(f"Processed {counter} records of migrated categories")


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate())


if __name__ == "__main__":
    main()
