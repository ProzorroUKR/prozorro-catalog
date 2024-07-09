import asyncio
import logging
import sentry_sdk
from dataclasses import dataclass

from pymongo import UpdateOne

from catalog.db import (
    init_mongo,
    transaction_context_manager,
    get_profiles_collection,
    get_category_collection,
    get_products_collection,
)
from catalog.logging import setup_logging
from catalog.migrations.cs_16303_requirement_iso_migration import bulk_update
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now

logger = logging.getLogger(__name__)


@dataclass
class Counters:
    total_categories: int = 0
    total_profiles: int = 0
    total_products: int = 0


async def migrate_categories(session):
    bulk = []
    counter = 0
    collection = get_category_collection()

    async for category in collection.find(
        {"procuringEntity": {"$exists": True}},
        projection={"_id": 1, "procuringEntity": 1}
    ):
        counter += 1
        now = get_now().isoformat()

        bulk.append(
            UpdateOne(
                filter={"_id": category["_id"]},
                update={
                    "$set": {"marketAdministrator": category["procuringEntity"], "dateModified": now},
                    "$unset": {"procuringEntity": ""},
                }
            )
        )

        if bulk and len(bulk) % 500 == 0:
            await bulk_update(collection, bulk, session, counter, migrated_obj="categories")
            bulk = []

    if bulk:
        await bulk_update(collection, bulk, session, counter, migrated_obj="categories")

    logger.info(f"Finished. Processed {counter} Category records")


async def migrate_profiles(session):
    bulk = []
    counter = 0
    collection = get_profiles_collection()

    pipeline = [
        {"$match": {"relatedCategory": {"$exists": True}}},
        {"$lookup": {
            "from": get_category_collection().name,
            "localField": "relatedCategory",
            "foreignField": "_id",
            "as": "category"
        }},
        {"$unwind": "$category"},
        {"$project": {
            "_id": 1,
            "relatedCategory": 1,
            "procuringEntity": "$category.procuringEntity"
        }}
    ]

    async for obj in collection.aggregate(pipeline):
        if not obj.get("procuringEntity"):
            continue
        counter += 1
        now = get_now().isoformat()
        bulk.append(
            UpdateOne(
                filter={"_id": obj["_id"]},
                update={"$set": {"marketAdministrator": obj["procuringEntity"], "dateModified": now}}
            )
        )

        if bulk and len(bulk) % 500 == 0:
            await bulk_update(collection, bulk, session, counter, migrated_obj="profiles")
            bulk = []

    if bulk:
        await bulk_update(collection, bulk, session, counter, migrated_obj="profiles")

    logger.info(f"Finished. Processed {counter} Profiles records")


async def migrate_products(session):
    bulk = []
    counter = 0
    collection = get_products_collection()

    pipeline = [
        {"$match": {"relatedCategory": {"$exists": True}}},
        {"$lookup": {
            "from": get_category_collection().name,
            "localField": "relatedCategory",
            "foreignField": "_id",
            "as": "category"
        }},
        {"$unwind": "$category"},
        {"$project": {
            "_id": 1,
            "relatedCategory": 1,
            "procuringEntity": "$category.procuringEntity"
        }}
    ]

    async for obj in collection.aggregate(pipeline):
        if not obj.get("procuringEntity"):
            continue
        counter += 1
        now = get_now().isoformat()
        bulk.append(
            UpdateOne(
                filter={"_id": obj["_id"]},
                update={"$set": {"marketAdministrator": obj["procuringEntity"], "dateModified": now}}
            )
        )

        if bulk and len(bulk) % 500 == 0:
            await bulk_update(collection, bulk, session, counter, migrated_obj="products")
            bulk = []

    if bulk:
        await bulk_update(collection, bulk, session, counter, migrated_obj="products")

    logger.info(f"Finished. Processed {counter} Products records")


async def migrate():
    logger.info("Start migration")
    async with transaction_context_manager() as session:
        await migrate_categories(session)
        await migrate_profiles(session)
        await migrate_products(session)
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
