import asyncio
import logging
import sentry_sdk

from copy import deepcopy
from pymongo import UpdateOne

from catalog.db import (
    get_category_collection,
    get_profiles_collection,
    init_mongo,
    transaction_context_manager,
    get_products_collection,
)
from catalog.logging import setup_logging
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now

logger = logging.getLogger(__name__)


def update_criteria(criteria: list) -> list:
    if not criteria:
        return []
    updated_criteria = deepcopy(criteria[0])
    updated = False

    for req_group in updated_criteria.get("requirementGroups", []):
        for requirement in req_group.get("requirements", []):
            if "expectedValue" in requirement:
                requirement["expectedValues"] = [requirement["expectedValue"]]
                del requirement["expectedValue"]
                updated = True
    return [updated_criteria] if updated else []


async def migrate_categories_and_profiles(session):
    migrated_objects = {
        "categories": get_category_collection(),
        "profiles": get_profiles_collection(),
    }

    for criteria_obj in migrated_objects.keys():
        collection = migrated_objects[criteria_obj]
        bulk = []
        counter = 0
        async for obj in collection.find({"criteria": {"$exists": True}}, projection={"_id": 1, "criteria": 1}):
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
                await bulk_update(collection, bulk, session, counter, criteria_obj)
                bulk = []

        if bulk:
            await bulk_update(collection, bulk, session, counter, criteria_obj)

        logger.info(f"Finished. Processed {counter} records of migrated {criteria_obj}")


def update_requirement_responses(req_responses: list) -> list:
    if not req_responses:
        return []
    updated = False
    updated_req_responses = []

    for req_response in req_responses:
        updated_response = deepcopy(req_response)
        if "value" in updated_response:
            updated_response["values"] = [updated_response["value"]]
            del updated_response["value"]
            updated = True
        updated_req_responses.append(updated_response)
    return updated_req_responses if updated else []


async def migrate_products(session):
    collection = get_products_collection()
    bulk = []
    counter = 0
    async for product in collection.find(
            {"requirementResponses": {"$exists": True}},
            projection={"_id": 1, "requirementResponses": 1}
    ):
        if updated_rr := update_requirement_responses(product["requirementResponses"]):
            counter += 1
            now = get_now().isoformat()
            bulk.append(
                UpdateOne(
                    filter={"_id": product["_id"]},
                    update={"$set": {"requirementResponses": updated_rr, "dateModified": now}}
                )
            )

        if bulk and len(bulk) % 500 == 0:
            await bulk_update(collection, bulk, session, counter, migrated_obj="products")
            bulk = []

    if bulk:
        await bulk_update(collection, bulk, session, counter, migrated_obj="products")

    logger.info(f"Finished. Processed {counter} records of migrated products")


async def bulk_update(collection, bulk, session, counter, migrated_obj):
    result = await collection.bulk_write(bulk, session=session)
    logger.info(f"Processed {counter} records of migrated {migrated_obj}")
    if result.modified_count != len(bulk):
        logger.error(f"Unexpected modified_count: {result.modified_count}; expected {len(bulk)}")


async def migrate():
    logger.info("Start migration")
    async with transaction_context_manager() as session:
        await migrate_categories_and_profiles(session)
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
