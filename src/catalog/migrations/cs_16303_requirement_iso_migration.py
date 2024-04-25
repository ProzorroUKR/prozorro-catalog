import asyncio
import logging
import sentry_sdk

from copy import deepcopy
from pymongo import UpdateOne

from catalog.db import (
    get_category_collection,
    init_mongo,
    transaction_context_manager,
    get_products_collection,
)
from catalog.logging import setup_logging
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now

logger = logging.getLogger(__name__)

CATEGORY_IDS = (
    "03140000-031488-40996564",
    "03140000-185550-40996564",
    "03210000-310700-40996564",
    "03210000-310950-40996564",
    "03210000-310830-40996564",
    "15130000-773637-40996564",
    "15240000-107114-40996564",
    "15330000-277600-40996564",
    "15330000-634450-40996564",
    "15330000-367711-40996564",
    "15330000-901700-40996564",
    "15330000-901800-40996564",
    "15330000-901900-40996564",
    "15510000-098222-40996564",
    "15510000-980777-40996564",
    "15510000-378012-40996564",
    "15510000-467820-40996564",
    "15510000-567660-40996564",
    "15540000-200200-40996564",
    "15540000-198750-40996564",
    "15540000-345670-40996564",
    "15540000-922450-40996564",
    "15540000-506770-40996564",
    "15550000-096633-40996564",
    "15550000-178091-40996564",
    "15550000-456773-40996564",
    "15550000-346780-40996564",
    "15610000-900990-40996564",
    "15610000-000900-40996564",
    "15610000-170600-40996564",
    "15610000-900200-40996564",
    "15610000-777666-40996564",
    "15610000-621690-40996564",
    "15610000-800710-40996564",
    "15610000-800530-40996564",
    "15620000-758320-40996564",
    "15810000-144450-40996564",
    "15820000-556180-40996564",
    "15820000-410915-40996564",
    "15830000-500310-40996564",
    "15840000-126110-40996564",
    "15840000-554360-40996564",
    "15870000-546680-40996564",
    "15870000-579040-40996564",
    "15870000-806930-40996564",
    "15870000-806995-40996564",
    "15870000-300400-40996564",
    "15890000-911932-40996564",
    "15980000-990103-40996564",
)


def update_criteria(criteria: list) -> list:
    updated_criteria = []
    updated = False

    for criterion in criteria:
        updated_criterion = deepcopy(criterion)
        for req_group in updated_criterion.get("requirementGroups", []):
            for requirement in req_group.get("requirements", []):
                if "ДСТУ" in requirement["title"] or "ГОСТ" in requirement["title"]:
                    requirement["expectedValue"] = True
                    requirement["dataType"] = "boolean"
                    requirement.pop("expectedValues", None)
                    requirement.pop("expectedMinItems", None)
                    requirement.pop("expectedMaxItems", None)
                    updated = True
        updated_criteria.append(updated_criterion)
    return updated_criteria if updated else []


async def migrate_categories(session):
    collection = get_category_collection()
    bulk = []
    counter = 0
    async for obj in collection.find({"_id": {"$in": CATEGORY_IDS}}, projection={"_id": 1, "criteria": 1}):
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
            await bulk_update(collection, bulk, session, counter, migrated_obj="categories")
            bulk = []

    if bulk:
        await bulk_update(collection, bulk, session, counter, migrated_obj="categories")

    logger.info(f"Finished. Processed {counter} records of migrated categories")


def update_requirement_responses(req_responses: list) -> list:
    if not req_responses:
        return []
    updated = False
    updated_req_responses = []

    for req_response in req_responses:
        updated_response = deepcopy(req_response)
        if "ДСТУ" in updated_response["requirement"] or "ГОСТ" in updated_response["requirement"]:
            updated_response["value"] = True
            updated_response.pop("values", None)
            updated = True
        updated_req_responses.append(updated_response)
    return updated_req_responses if updated else []


async def migrate_products(session):
    collection = get_products_collection()
    bulk = []
    counter = 0
    async for product in collection.find(
            {"relatedCategory": {"$in": CATEGORY_IDS}},
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
        await migrate_categories(session)
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
