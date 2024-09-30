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
    get_products_collection,
)
from catalog.logging import setup_logging
from catalog.settings import SENTRY_DSN

logger = logging.getLogger(__name__)


TYPE_MAPPING = {
    "number": float,
    "integer": int,
    "string": str,
    "boolean": bool,
}


def convert_expected_value_to_string(requirement):
    requirement["dataType"] = "string"
    requirement["expectedValues"] = [str(requirement.pop("expectedValue"))]
    requirement["expectedMinItems"] = 1


def normalize_expected_values(requirement):
    requirement["dataType"] = "string"
    requirement["expectedValues"] = [
        str(value) for value in requirement["expectedValues"]
    ]
    requirement["expectedMinItems"] = 1


def convert_field_to_float(requirement, field_name):
    if isinstance(requirement[field_name], (float, int)):
        requirement[field_name] = float(requirement[field_name])
        requirement["dataType"] = "number"


def pop_min_max_values(requirement):
    requirement.pop("maxValue", None)
    requirement.pop("minValue", None)


async def get_responses_from_profile(obj, requirement, session):
    responses = set()
    async for obj in get_products_collection().find(
        {"$or": [{"relatedProfiles": obj["_id"]}, {"relatedCategory": obj["_id"]}]},
        projection={"_id": 1, "requirementResponses": 1},
        no_cursor_timeout=True,
        batch_size=1000,
        session=session,
    ):
        for resp in obj["requirementResponses"]:
            if resp["requirement"] == requirement["title"]:
                if resp.get("value") is not None:
                    responses.add(resp["value"])
                elif resp.get("values") is not None:
                    responses.update(resp["values"])
    return responses


async def get_min_value_from_responses(requirement, obj, obj_type, session):
    responses = await get_responses_from_profile(obj, requirement, session=session)
    if responses:
        responses = [obj_type(resp) for resp in responses]
        requirement["minValue"] = min(responses)
    else:
        requirement["minValue"] = 0


async def update_responses_in_product(product, session):
    category = await get_category_collection().find_one(
        {"_id": product["relatedCategory"]}, {"criteria": 1}, session=session
    )
    category_requirements = {
        r["title"]: r
        for c in category.get("criteria", "")
        for group in c["requirementGroups"]
        for r in group["requirements"]
    }
    responses = []
    updated = False
    for resp in product.get("requirementResponses", []):
        if resp["requirement"] not in category_requirements:
            # delete such response
            updated = True
            continue
        obj_type = TYPE_MAPPING[category_requirements[resp["requirement"]]["dataType"]]
        try:
            if resp.get("value") is not None:
                if not isinstance(resp["value"], obj_type):
                    resp["value"] = obj_type(resp["value"])
                    updated = True
            elif resp.get("values") is not None:
                for value in resp["values"]:
                    if not isinstance(value, obj_type):
                        break
                else:
                    responses.append(resp)
                    continue
                resp["values"] = [obj_type(val) for val in resp["values"]]
                updated = True
        except ValueError as e:
            # delete such response
            updated = True
        else:
            responses.append(resp)
    return responses if updated else None


async def requirement_not_in_category(obj, requirement, session):
    if obj.get("relatedCategory"):
        category = await get_category_collection().find_one(
            {"_id": obj["relatedCategory"]}, {"criteria": 1}, session=session
        )
        category_requirements = {
            r["title"]: r
            for c in category.get("criteria", "")
            for group in c["requirementGroups"]
            for r in group["requirements"]
        }
        if requirement["title"] not in category_requirements:
            return True


async def update_criteria(obj: dict, session):
    if not obj["criteria"]:
        return []
    updated_criteria = []

    for criterion in obj["criteria"]:
        updated_criterion = deepcopy(criterion)
        updated_req_group = []
        for req_group in updated_criterion.get("requirementGroups", []):
            updated_requirements = []
            for requirement in req_group.get("requirements", []):
                # check whether there is requirement in profile but not in category
                if await requirement_not_in_category(obj, requirement, session):
                    continue

                # Remove min/max values if expected values exist
                if (
                    ("expectedValue" in requirement or "expectedValues" in requirement)
                    and ("minValue" in requirement or "maxValue" in requirement)
                ):
                    pop_min_max_values(requirement)

                # Handle different data types
                if requirement["dataType"] == "integer":
                    if "expectedValues" in requirement:
                        normalize_expected_values(requirement)
                    elif (
                        "minValue" in requirement
                        or "maxValue" in requirement
                        or "expectedValue" in requirement
                    ):
                        for field_name in ("minValue", "maxValue", "expectedValue"):
                            if field_name in requirement:
                                if isinstance(requirement[field_name], float):
                                    requirement["dataType"] = "number"
                                elif (
                                    field_name == "expectedValue"
                                    and isinstance(requirement["expectedValue"], (bool, str))
                                ):
                                    convert_expected_value_to_string(requirement)
                    else:
                        await get_min_value_from_responses(requirement, obj, int, session)
                elif requirement["dataType"] == "number":
                    if "expectedValues" in requirement:
                        normalize_expected_values(requirement)
                    elif (
                        "minValue" in requirement
                        or "maxValue" in requirement
                        or "expectedValue" in requirement
                    ):
                        for field_name in ("minValue", "maxValue", "expectedValue"):
                            if field_name in requirement:
                                if (
                                    field_name == "expectedValue"
                                    and isinstance(requirement["expectedValue"], (bool, str))
                                ):
                                    convert_expected_value_to_string(requirement)
                                else:
                                    convert_field_to_float(requirement, field_name)
                    else:
                        await get_min_value_from_responses(requirement, obj, float, session)
                elif requirement["dataType"] == "string":
                    if "expectedValues" in requirement:
                        normalize_expected_values(requirement)
                    elif "expectedValue" in requirement:
                        convert_expected_value_to_string(requirement)
                    # maxValue + minValue одночасно
                    elif "minValue" in requirement and "maxValue" in requirement:
                        responses = await get_responses_from_profile(obj, requirement, session)
                        if responses:
                            requirement["expectedValues"] = [str(resp) for resp in responses]
                        else:
                            requirement["expectedValues"] = [str(requirement["minValue"]), str(requirement["maxValue"])]
                        requirement["expectedMinItems"] = 1
                        pop_min_max_values(requirement)
                    elif "minValue" in requirement or "maxValue" in requirement:
                        for field_name in ("minValue", "maxValue"):
                            if field_name in requirement:
                                responses = await get_responses_from_profile(obj, requirement, session)
                                if responses:
                                    requirement["expectedValues"] = [str(resp) for resp in responses]
                                else:
                                    requirement["expectedValues"] = [str(requirement[field_name])]
                                requirement["expectedMinItems"] = 1
                                pop_min_max_values(requirement)
                    else:
                        responses = await get_responses_from_profile(obj, requirement, session)
                        if responses:
                            requirement["expectedValues"] = [str(resp) for resp in responses]
                            requirement["expectedMinItems"] = 1
                        else:
                            requirement["dataType"] = "boolean"

                elif requirement["dataType"] == "boolean":
                    if "expectedValues" in requirement:
                        if len(requirement["expectedValues"]) == 1:
                            if isinstance(requirement["expectedValues"][0], bool):
                                requirement["expectedValue"] = requirement[
                                    "expectedValues"
                                ][0]
                                for field_name in (
                                    "expectedValues",
                                    "expectedMinItems",
                                    "expectedMaxItems",
                                ):
                                    requirement.pop(field_name, None)
                        elif set(requirement["expectedValues"]) == {True, False}:
                            for field_name in (
                                "expectedValues",
                                "expectedMinItems",
                                "expectedMaxItems",
                            ):
                                requirement.pop(field_name, None)
                        # check whether expectedValues is left
                        if requirement.get("expectedValues"):
                            normalize_expected_values(requirement)
                    elif "expectedValue" in requirement:
                        convert_expected_value_to_string(requirement)

                # delete unit from string and boolean requirements
                if requirement["dataType"] in ("string", "boolean"):
                    requirement.pop("unit", None)
                updated_requirements.append(requirement)
            req_group["requirements"] = updated_requirements
            updated_req_group.append(req_group)

        updated_criterion["requirementGroups"] = updated_req_group
        updated_criteria.append(updated_criterion)
    return updated_criteria


async def migrate_categories_and_profiles(session):
    migrated_objects = {
        "categories": get_category_collection(),
        "profiles": get_profiles_collection(),
    }

    for criteria_obj in migrated_objects.keys():
        collection = migrated_objects[criteria_obj]
        bulk = []
        counter = 0
        cursor = collection.find(
            {"criteria": {"$exists": True}},
            projection={"_id": 1, "criteria": 1, "relatedCategory": 1},
            no_cursor_timeout=True,
            batch_size=200,
        )
        async for obj in cursor:
            try:
                if updated_criteria := await update_criteria(obj, session):
                    counter += 1
                    bulk.append(
                        UpdateOne(
                            filter={"_id": obj["_id"]},
                            update={"$set": {"criteria": updated_criteria}},
                        )
                    )

                if bulk and len(bulk) % 500 == 0:
                    await bulk_update(collection, bulk, session, counter, criteria_obj)
                    bulk = []
            except Exception as e:
                logger.info(
                    f"ERROR: {criteria_obj} with id {obj['_id']}. Caught {type(e).__name__}."
                )
                traceback.print_exc()
                break

        if bulk:
            await bulk_update(collection, bulk, session, counter, criteria_obj)
        await cursor.close()

        logger.info(f"Finished. Processed {counter} records of migrated {criteria_obj}")


async def migrate_products(session):
    collection = get_products_collection()
    bulk = []
    counter = 0
    cursor = collection.find(
        {"requirementResponses": {"$exists": True}},
        projection={
            "_id": 1,
            "requirementResponses": 1,
            "relatedCategory": 1,
            "relatedProfiles": 1,
        },
        no_cursor_timeout=True,
        batch_size=200,
    )
    async for obj in cursor:
        if updated_responses := await update_responses_in_product(obj, session):
            counter += 1
            bulk.append(
                UpdateOne(
                    filter={"_id": obj["_id"]},
                    update={"$set": {"requirementResponses": updated_responses}},
                )
            )
        if bulk and len(bulk) % 500 == 0:
            await bulk_update(collection, bulk, session, counter, "products")
            bulk = []
    if bulk:
        await bulk_update(collection, bulk, session, counter, "products")
    await cursor.close()

    logger.info(f"Finished. Processed {counter} records of migrated products")


async def bulk_update(collection, bulk, session, counter, migrated_obj):
    result = await collection.bulk_write(bulk, session=session)
    logger.info(f"Processed {counter} records of migrated {migrated_obj}")
    if result.modified_count != len(bulk):
        logger.error(
            f"Unexpected modified_count: {result.modified_count}; expected {len(bulk)}"
        )


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


if __name__ == "__main__":
    main()
