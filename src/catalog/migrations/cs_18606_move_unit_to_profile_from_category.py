import asyncio
import logging

import sentry_sdk
from pymongo import UpdateOne

from catalog.db import (
    get_profiles_collection,
    init_mongo,
    get_category_collection,
    transaction_context_manager,
)
from catalog.logging import setup_logging
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now

logger = logging.getLogger(__name__)


async def move_requirement_unit_from_category(obj, requirement):
    if obj.get("relatedCategory"):
        category = await get_category_collection().find_one(
            {"_id": obj["relatedCategory"]}, {"criteria": 1}
        )
        updated = False
        if category:
            category_requirements = {
                r["title"]: r
                for c in category.get("criteria", "")
                for group in c["requirementGroups"]
                for r in group["requirements"]
                if r["dataType"] in ("number", "integer")
            }
            if (
                category_requirements.get(requirement["title"])
                and category_requirements[requirement["title"]].get("unit") is not None
                and requirement.get("unit") is None
            ):
                requirement["unit"] = category_requirements[requirement["title"]]["unit"]
                updated = True
            return updated


async def bulk_update(collection, bulk, session, counter):
    await collection.bulk_write(bulk, session=session)
    logger.info(f"Processed {counter} records of migrated")


async def migrate_profiles():
    logger.info("Start migration")
    collection = get_profiles_collection()
    counter = 0
    bulk = []
    cursor = collection.find(
        {},
        projection={"_id": 1, "criteria": 1, "relatedCategory": 1},
        no_cursor_timeout=True,
        batch_size=200,
    )
    async for obj in cursor:
        updated = False
        for criterion in obj.get("criteria", ""):
            for req_group in criterion["requirementGroups"]:
                for requirement in req_group["requirements"]:
                    if (
                        requirement.get("dataType") in ("number", "integer")
                        and await move_requirement_unit_from_category(obj, requirement)
                    ):
                        updated = True
        if updated:
            counter += 1
            bulk.append(
                UpdateOne(
                    filter={"_id": obj["_id"]},
                    update={"$set": {
                        "criteria": obj["criteria"],
                        "dateModified": get_now().isoformat(),
                    }},
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
    logger.info(f"Finished. Processed {counter} records of migrated profiles")
    logger.info("Successfully migrated")


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate_profiles())


if __name__ == "__main__":
    main()
