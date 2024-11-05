import asyncio
import logging
import sentry_sdk

from pymongo import UpdateOne

from catalog.db import (
    init_mongo,
    transaction_context_manager,
    get_category_collection,
)
from catalog.logging import setup_logging
from catalog.migrations.cs_16303_requirement_iso_migration import bulk_update
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now

logger = logging.getLogger(__name__)


def update_criteria(criteria):
    changed = False
    for criterion in criteria:
        for rg in criterion.get("requirementGroups", ""):
            for req in rg.get("requirements", ""):
                if "isArchived" not in req:
                    req["isArchived"] = False
                    changed = True
    if changed:
        return criteria


async def migrate():
    logger.info("Start migration")
    collection = get_category_collection()
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
                await bulk_update(collection, bulk, session, counter, migrated_obj="categories")
            bulk = []

    if bulk:
        async with transaction_context_manager() as session:
            await bulk_update(collection, bulk, session, counter, migrated_obj="categories")

    logger.info(f"Finished. Processed {counter} records of migrated categories")
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
