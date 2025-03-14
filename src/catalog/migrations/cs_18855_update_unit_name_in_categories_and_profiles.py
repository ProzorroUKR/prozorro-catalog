import asyncio
import logging
import traceback

import sentry_sdk

from copy import deepcopy
from pymongo import UpdateOne

from catalog.db import (
    get_category_collection,
    get_profiles_collection,
    init_mongo,
    transaction_context_manager,
)
from catalog.logging import setup_logging
from catalog.models.common import UNIT_CODES_DATA
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now

logger = logging.getLogger(__name__)


async def get_unit_from_category(obj, requirement=None):
    category = await get_category_collection().find_one(
        {"_id": obj["relatedCategory"]}, {"criteria": 1, "unit": 1}
    )
    if category:
        if requirement:  # get unit from requirement
            for criterion in category.get("criteria", []):
                for group in criterion["requirementGroups"]:
                    for req in group["requirements"]:
                        if req["title"] == requirement["title"] and req.get("unit"):
                            return req["unit"]
        elif category.get("unit"):
            return category["unit"]


def get_unit_name_from_standard(obj, unit):
    try:
        if unit["name"] != UNIT_CODES_DATA[unit["code"]]["name_uk"]:
            return UNIT_CODES_DATA[obj["unit"]["code"]]["name_uk"]
    except KeyError:
        logger.info(f"Unit code not from standard {obj['_id']}, status: {obj['status']}, unit: {unit['name']}")
    return


async def update_unit(obj: dict):
    updated = False

    # for profiles
    if obj.get("relatedCategory"):
        if category_unit := await get_unit_from_category(obj):
            if category_unit != obj.get("unit"):
                obj["unit"] = category_unit
                updated = True
        elif obj.get("unit"):
            if correct_unit_name := get_unit_name_from_standard(obj, obj["unit"]):
                obj["unit"]["name"] = correct_unit_name
                updated = True

    # for categories
    elif obj.get("unit"):
        if correct_unit_name := get_unit_name_from_standard(obj, obj["unit"]):
            obj["unit"]["name"] = correct_unit_name
            updated = True
    return obj["unit"] if updated else None


async def update_criteria(obj: dict):
    if not obj.get("criteria"):
        return []
    updated = False
    updated_criteria = []

    for criterion in obj["criteria"]:
        updated_criterion = deepcopy(criterion)
        updated_req_group = []
        for req_group in updated_criterion.get("requirementGroups", []):
            updated_requirements = []
            for requirement in req_group.get("requirements", []):
                if requirement.get("dataType") in ("number", "integer"):
                    # for profiles
                    if obj.get("relatedCategory") and (category_unit := await get_unit_from_category(obj, requirement)):
                        if category_unit != requirement.get("unit"):
                            requirement["unit"] = category_unit
                            updated = True
                    # for categories or profiles that has requirement that doesn't exist in category criteria
                    elif unit := requirement.get("unit"):
                        if correct_unit_name := get_unit_name_from_standard(obj, unit):
                            unit["name"] = correct_unit_name
                            updated = True
                updated_requirements.append(requirement)
            req_group["requirements"] = updated_requirements
            updated_req_group.append(req_group)

        updated_criterion["requirementGroups"] = updated_req_group
        updated_criteria.append(updated_criterion)
    return updated_criteria if updated else None


async def migrate_categories_and_profiles():
    migrated_objects = {
        "categories": get_category_collection(),
        "profiles": get_profiles_collection(),
    }

    for criteria_obj in migrated_objects.keys():
        collection = migrated_objects[criteria_obj]
        bulk = []
        counter = 0
        cursor = collection.find(
            {"$or": [{"criteria": {"$exists": True}}, {"unit": {"$exists": True}}]},
            projection={"_id": 1, "criteria": 1, "relatedCategory": 1, "unit": 1, "status": 1},
            no_cursor_timeout=True,
            batch_size=200,
        )
        async for obj in cursor:
            try:
                set_data = dict()
                if updated_criteria := await update_criteria(obj):
                    set_data["criteria"] = updated_criteria
                if updated_unit := await update_unit(obj):
                    set_data["unit"] = updated_unit
                if set_data:
                    counter += 1
                    set_data["dateModified"] = get_now().isoformat()
                    bulk.append(
                        UpdateOne(
                            filter={"_id": obj["_id"]},
                            update={"$set": set_data},
                        )
                    )

                if bulk and len(bulk) % 500 == 0:
                    async with transaction_context_manager() as session:
                        await bulk_update(collection, bulk, session, counter, criteria_obj)
                    bulk = []
            except Exception as e:
                logger.info(
                    f"ERROR: {criteria_obj} with id {obj['_id']}. Caught {type(e).__name__}."
                )
                traceback.print_exc()
                break

        if bulk:
            async with transaction_context_manager() as session:
                await bulk_update(collection, bulk, session, counter, criteria_obj)
        await cursor.close()

        logger.info(f"Finished. Processed {counter} records of migrated {criteria_obj}")


async def bulk_update(collection, bulk, session, counter, migrated_obj):
    await collection.bulk_write(bulk, session=session)
    logger.info(f"Processed {counter} records of migrated {migrated_obj}")


async def migrate():
    logger.info("Start migration")
    await migrate_categories_and_profiles()
    logger.info("Successfully migrated")


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate())


if __name__ == "__main__":
    main()
