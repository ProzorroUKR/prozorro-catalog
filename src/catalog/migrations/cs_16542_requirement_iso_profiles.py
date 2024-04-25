import asyncio
import logging
import sentry_sdk

from pymongo import UpdateOne

from catalog.db import (
    init_mongo,
    transaction_context_manager,
    get_profiles_collection,
)
from catalog.logging import setup_logging
from catalog.migrations.cs_16303_requirement_iso_migration import bulk_update, update_criteria, CATEGORY_IDS
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now

logger = logging.getLogger(__name__)


async def migrate():
    logger.info("Start migration")
    bulk = []
    counter = 0
    async with transaction_context_manager() as session:
        collection = get_profiles_collection()
        async for obj in collection.find(
                {"relatedCategory": {"$in": CATEGORY_IDS}},
                projection={"_id": 1, "criteria": 1}
        ):
            if updated_criteria := update_criteria(obj["criteria"]):
                counter += 1
                now = get_now().isoformat()
                bulk.append(
                    UpdateOne(
                        filter={"_id": obj["_id"]},
                        update={"$set": {"criteria": updated_criteria, "dateModified": now}}
                    )
                )

            if bulk and len(bulk) % 500 == 0:
                await bulk_update(collection, bulk, session, counter, migrated_obj="profiles")
                bulk = []

        if bulk:
            await bulk_update(collection, bulk, session, counter, migrated_obj="profiles")

    logger.info(f"Finished. Processed {counter} records of migrated profiles")

def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate())


if __name__ == '__main__':
    main()
