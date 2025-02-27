import asyncio
import logging
import sentry_sdk

from pymongo import UpdateOne

from catalog.db import (
    init_mongo,
    transaction_context_manager,
    get_profiles_collection,
    get_category_collection,
)
from catalog.logging import setup_logging
from catalog.migrations.cs_16303_requirement_iso_migration import bulk_update
from catalog.models.common import COUNTRY_NAMES, DataSchemaEnum
from catalog.settings import SENTRY_DSN, LOCALIZATION_CRITERIA
from catalog.utils import get_now

logger = logging.getLogger(__name__)


def update_criteria(criteria):
    changed = False
    for criterion in criteria:
        if criterion.get("classification", {}).get("id") == LOCALIZATION_CRITERIA:
            for rg in criterion.get("requirementGroups", ""):
                for req in rg.get("requirements", ""):
                    if req.get("expectedValues") is not None and not set(req["expectedValues"]) - set(COUNTRY_NAMES.keys()):
                        req["dataSchema"] = DataSchemaEnum.ISO_3166.value
                        changed = True
    if changed:
        return criteria


async def migrate_criteria(collection, obj_name):
    bulk = []
    counter = 0

    async for obj in collection.find(
        {"criteria": {"$exists": True}},
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
            async with transaction_context_manager() as session:
                await bulk_update(collection, bulk, session, counter, migrated_obj=obj_name)
            bulk = []

    if bulk:
        async with transaction_context_manager() as session:
            await bulk_update(collection, bulk, session, counter, migrated_obj=obj_name)

    logger.info(f"Finished. Processed {counter} records of migrated {obj_name}")


async def migrate_categories():
    collection = get_category_collection()
    await migrate_criteria(collection, "categories")


async def migrate_profiles():
    collection = get_profiles_collection()
    await migrate_criteria(collection, "profiles")


async def migrate():
    logger.info("Start migration")
    await migrate_categories()
    await migrate_profiles()
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
