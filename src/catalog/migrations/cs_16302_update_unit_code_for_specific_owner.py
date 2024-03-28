import asyncio
import logging
import sentry_sdk

from pymongo import UpdateOne

from catalog.db import (
    get_category_collection,
    get_profiles_collection,
    init_mongo,
    transaction_context_manager,
)
from catalog.logging import setup_logging
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now

logger = logging.getLogger(__name__)

OWNER = "40996564"
PREVIOUS_UNIT_CODE = "RM"
NEW_UNIT_DATA = {
    "code": "PK",
    "name": "пачка",
}


async def migrate_categories_and_profiles(session):
    migrated_objects = {
        "categories": get_category_collection(),
        "profiles": get_profiles_collection(),
    }

    for obj_name in migrated_objects.keys():
        collection = migrated_objects[obj_name]
        bulk = []
        counter = 0
        async for obj in collection.find(
            {"access.owner": OWNER, "unit.code": PREVIOUS_UNIT_CODE}, projection={"_id": 1, "access": 1, "unit": 1}
        ):
            counter += 1
            now = get_now().isoformat()
            bulk.append(
                UpdateOne(
                    filter={"_id": obj["_id"]},
                    update={"$set": {"unit": NEW_UNIT_DATA, "dateModified": now}},
                )
            )

            if bulk and len(bulk) % 500 == 0:
                await bulk_update(collection, bulk, session, counter, obj_name)
                bulk = []

        if bulk:
            await bulk_update(collection, bulk, session, counter, obj_name)

        logger.info(f"Finished. Processed {counter} records of migrated {obj_name}")


async def bulk_update(collection, bulk, session, counter, migrated_obj):
    result = await collection.bulk_write(bulk, session=session)
    logger.info(f"Processed {counter} records of migrated {migrated_obj}")
    if result.modified_count != len(bulk):
        logger.error(f"Unexpected modified_count: {result.modified_count}; expected {len(bulk)}")


async def migrate():
    logger.info("Start migration")
    async with transaction_context_manager() as session:
        await migrate_categories_and_profiles(session)
    logger.info("Successfully migrated")


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate())


if __name__ == '__main__':
    main()
