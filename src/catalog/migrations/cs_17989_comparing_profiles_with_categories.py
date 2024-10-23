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


TYPE_MAPPING = {
    "number": float,
    "integer": int,
    "string": str,
    "boolean": bool,
}


async def requirement_diff_type_in_category(obj, requirement):
    if obj.get("relatedCategory"):
        category = await get_category_collection().find_one(
            {"_id": obj["relatedCategory"]}, {"criteria": 1, "status": 1}
        )
        updated = False
        if category:
            category_requirements = {
                r["title"]: r
                for c in category.get("criteria", "")
                for group in c["requirementGroups"]
                for r in group["requirements"]
            }
            if (
                category_requirements.get(requirement["title"])
                and category_requirements[requirement["title"]]["dataType"] != requirement["dataType"]
            ):
                if (
                    category_requirements[requirement["title"]]["dataType"] in ("number", "integer")
                    and requirement["dataType"] == "string"
                ):
                    try:
                        if len(requirement["expectedValues"]) == 1:
                            obj_type = TYPE_MAPPING[category_requirements[requirement["title"]]["dataType"]]
                            requirement["expectedValue"] = obj_type(requirement["expectedValues"][0])
                            requirement["dataType"] = category_requirements[requirement["title"]]["dataType"]
                            for field_name in ("expectedValues", "expectedMinItems", "expectedMaxItems"):
                                requirement.pop(field_name, None)
                    except ValueError:
                        pass
                elif (
                    category_requirements[requirement["title"]]["dataType"] == "boolean"
                    and requirement["dataType"] == "string"
                ):
                    for field_name in ("expectedValues", "expectedMinItems", "expectedMaxItems"):
                        requirement.pop(field_name, None)
                    requirement["dataType"] = category_requirements[requirement["title"]]["dataType"]
                    if category_requirements[requirement["title"]].get("expectedValue") is not None:
                        requirement["expectedValue"] = category_requirements[requirement["title"]]["expectedValue"]
                    updated = True
                elif category_requirements[requirement["title"]]["dataType"] == "string":
                    if "expectedValues" in requirement and requirement["expectedValues"]:  # not empty list
                        requirement["expectedValues"] = [
                            str(value) for value in requirement["expectedValues"]
                        ]
                        requirement["expectedMinItems"] = 1
                        requirement["dataType"] = "string"
                        updated = True
                    elif "expectedValue" in requirement:
                        requirement["expectedValues"] = [str(requirement.pop("expectedValue"))]
                        requirement["expectedMinItems"] = 1
                        requirement["dataType"] = "string"
                        updated = True
                    elif "minValue" in requirement and "maxValue" in requirement:
                        requirement["expectedValues"] = [str(requirement["minValue"]), str(requirement["maxValue"])]
                        requirement["expectedMinItems"] = 1
                        for field_name in ("minValue", "maxValue"):
                            requirement.pop(field_name, None)
                        requirement["dataType"] = "string"
                        updated = True
                    elif "minValue" in requirement or "maxValue" in requirement:
                        for field_name in ("minValue", "maxValue"):
                            if field_name in requirement:
                                requirement["expectedValues"] = [str(requirement[field_name])]
                                requirement["expectedMinItems"] = 1
                                for field_name in ("minValue", "maxValue"):
                                    requirement.pop(field_name, None)
                        requirement["dataType"] = "string"
                        updated = True
                elif (
                    category_requirements[requirement["title"]]["dataType"] in ("number", "integer")
                    and requirement["dataType"] in ("number", "integer")
                ):
                    try:
                        for field_name in ("maxValue", "minValue", "expectedValue"):
                            if field_name in requirement:
                                obj_type = TYPE_MAPPING[category_requirements[requirement["title"]]["dataType"]]
                                requirement[field_name] = obj_type(requirement[field_name])
                                requirement["dataType"] = category_requirements[requirement["title"]]["dataType"]
                                updated = True
                    except ValueError:
                        pass
            if requirement["dataType"] in ("string", "boolean") and requirement.get("unit"):
                requirement.pop("unit")
                updated = True
            elif requirement["dataType"] in ("number", "integer"):
                if category_requirements[requirement["title"]].get("unit") and not requirement.get("unit"):
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
        projection={"_id": 1, "criteria": 1, "status": 1, "relatedCategory": 1},
        no_cursor_timeout=True,
        batch_size=200,
    )
    async for obj in cursor:
        updated = False
        for criterion in obj.get("criteria", ""):
            for req_group in criterion["requirementGroups"]:
                for requirement in req_group["requirements"]:
                    if await requirement_diff_type_in_category(obj, requirement):
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
