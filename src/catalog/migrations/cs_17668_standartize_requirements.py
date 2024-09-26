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


def convert_expected_value_to_string(requirement):
    requirement["dataType"] = "string"
    requirement["expectedValues"] = [str(requirement.pop("expectedValue"))]
    requirement["expectedMinItems"] = 1


def normalize_expected_values(requirement):
    requirement["dataType"] = "string"
    requirement["expectedValues"] = [str(value) for value in requirement["expectedValues"]]
    requirement["expectedMinItems"] = 1


def convert_field_to_float(requirement, field_name):
    if isinstance(requirement[field_name], (float, int)):
        requirement[field_name] = float(requirement[field_name])
        requirement["dataType"] = "number"
        return True
    return False


def pop_min_max_values(requirement):
    requirement.pop("maxValue", None)
    requirement.pop("minValue", None)


async def get_responses_from_profile(obj, requirement):
    responses = set()
    async for obj in get_products_collection().find(
            {"$or": [{"relatedProfiles": obj["_id"]}, {"relatedCategory": obj["_id"]}]},
            projection={"_id": 1, "requirementResponses": 1},
    ):
        for resp in obj["requirementResponses"]:
            if resp["requirement"] == requirement["title"]:
                if resp.get("value") is not None:
                    responses.add(resp["value"])
                elif resp.get("values") is not None:
                    responses.update(resp["values"])
    return responses


async def get_min_value_from_responses(requirement, obj, obj_type):
    responses = await get_responses_from_profile(obj, requirement)
    if responses:
        responses = [obj_type(resp) for resp in responses]
        requirement["minValue"] = min(responses)
    else:
        requirement["minValue"] = 0


async def update_responses_in_product(products, parent_obj, requirement, obj_type):
    products_collection = get_products_collection()
    async for obj in products_collection.find(
        {"$or": [{"relatedProfiles": parent_obj["_id"]}, {"relatedCategory": parent_obj["_id"]}]},
        projection={"_id": 1, "requirementResponses": 1},
    ):
        req_resp = []
        updated = False
        requirement_responses = products.get(obj["_id"]) or obj["requirementResponses"]
        for resp in deepcopy(requirement_responses):
            try:
                if resp["requirement"] == requirement["title"]:
                    if resp.get("value") is not None:
                        if not isinstance(resp["value"], obj_type):
                            resp["value"] = obj_type(resp["value"])
                            updated = True
                    elif resp.get("values") is not None:
                        for value in resp["values"]:
                            if not isinstance(value, obj_type):
                                break
                        else:
                            continue
                        resp["values"] = [obj_type(val) for val in resp["values"]]
                        updated = True
            except ValueError as e:
                # delete such response
                updated = True
            else:
                req_resp.append(resp)

        if updated:
            products[obj["_id"]] = req_resp
    return products


async def update_criteria(obj: dict, products: dict):
    if not obj["criteria"]:
        return [], products
    updated_criteria = []

    for criterion in obj["criteria"]:
        updated_criterion = deepcopy(criterion)
        for req_group in updated_criterion.get("requirementGroups", []):
            for requirement in req_group.get("requirements", []):
                # Remove min/max values if expected values exist
                if ("expectedValue" in requirement or "expectedValues" in requirement) and ("minValue" in requirement or "maxValue" in requirement):
                    pop_min_max_values(requirement)

                # Handle different data types
                if requirement["dataType"] == "integer":
                    if "expectedValues" in requirement:
                        normalize_expected_values(requirement)
                        products = await update_responses_in_product(products, obj, requirement, str)
                    elif "minValue" in requirement or "maxValue" in requirement or "expectedValue" in requirement:
                        for field_name in ("minValue", "maxValue", "expectedValue"):
                            if field_name in requirement:
                                if isinstance(requirement[field_name], float):
                                    requirement["dataType"] = "number"
                                    products = await update_responses_in_product(products, obj, requirement, float)
                                elif field_name == "expectedValue" and isinstance(requirement["expectedValue"], (bool, str)):
                                    convert_expected_value_to_string(requirement)
                                    products = await update_responses_in_product(products, obj, requirement, str)
                    else:
                        await get_min_value_from_responses(requirement, obj, int)
                elif requirement["dataType"] == "number":
                    if "expectedValues" in requirement:
                        normalize_expected_values(requirement)
                        products = await update_responses_in_product(products, obj, requirement, str)
                    elif "minValue" in requirement or "maxValue" in requirement or "expectedValue" in requirement:
                        for field_name in ("minValue", "maxValue", "expectedValue"):
                            if field_name in requirement:
                                if field_name == "expectedValue" and isinstance(requirement["expectedValue"], (bool, str)):
                                    convert_expected_value_to_string(requirement)
                                    products = await update_responses_in_product(products, obj, requirement, str)
                                elif convert_field_to_float(requirement, field_name):
                                    products = await update_responses_in_product(products, obj, requirement, float)
                    else:
                        await get_min_value_from_responses(requirement, obj, float)
                elif requirement["dataType"] == "string":
                    if "expectedValues" in requirement:
                        normalize_expected_values(requirement)
                    elif "expectedValue" in requirement:
                        convert_expected_value_to_string(requirement)
                    # maxValue + minValue одночасно
                    elif "minValue" in requirement and "maxValue" in requirement:
                        responses = await get_responses_from_profile(obj, requirement)
                        if responses:
                            requirement["expectedValues"] = [str(resp) for resp in responses]
                        else:
                            requirement["expectedValues"] = [str(requirement["minValue"]), str(requirement["maxValue"])]
                        requirement["expectedMinItems"] = 1
                        pop_min_max_values(requirement)
                    elif "minValue" in requirement or "maxValue" in requirement:
                        for field_name in ("minValue", "maxValue"):
                            if field_name in requirement:
                                responses = await get_responses_from_profile(obj, requirement)
                                if responses:
                                    requirement["expectedValues"] = [str(resp) for resp in responses]
                                else:
                                    requirement["expectedValues"] = [str(requirement[field_name])]
                                requirement["expectedMinItems"] = 1
                                pop_min_max_values(requirement)
                    else:
                        responses = await get_responses_from_profile(obj, requirement)
                        if responses:
                            requirement["expectedValues"] = [str(resp) for resp in responses]
                            requirement["expectedMinItems"] = 1
                        else:
                            requirement["dataType"] = "boolean"
                    products = await update_responses_in_product(products, obj, requirement, str)

                elif requirement["dataType"] == "boolean":
                    if "expectedValues" in requirement:
                        if len(requirement["expectedValues"]) == 1:
                            if isinstance(requirement["expectedValues"][0], bool):
                                requirement["expectedValue"] = requirement["expectedValues"][0]
                                for field_name in ("expectedValues", "expectedMinItems", "expectedMaxItems"):
                                    requirement.pop(field_name, None)
                                products = await update_responses_in_product(products, obj, requirement, bool)
                        elif set(requirement["expectedValues"]) == {True, False}:
                            for field_name in ("expectedValues", "expectedMinItems", "expectedMaxItems"):
                                requirement.pop(field_name, None)
                            products = await update_responses_in_product(products, obj, requirement, bool)
                        # check whether expectedValues is left
                        if requirement.get("expectedValues"):
                            normalize_expected_values(requirement)
                            products = await update_responses_in_product(products, obj, requirement, str)
                    elif "expectedValue" in requirement:
                        convert_expected_value_to_string(requirement)
                        products = await update_responses_in_product(products, obj, requirement, str)

                # delete unit from string and boolean requirements
                if requirement["dataType"] in ("string", "boolean"):
                    requirement.pop("unit", None)

        updated_criteria.append(updated_criterion)
    return updated_criteria, products


async def migrate_categories_and_profiles(session):
    migrated_objects = {
        "categories": get_category_collection(),
        "profiles": get_profiles_collection(),
    }
    products_collection = get_products_collection()

    for criteria_obj in migrated_objects.keys():
        collection = migrated_objects[criteria_obj]
        bulk = []
        counter = 0
        bulk_products = []
        counter_products = 0
        products = {}
        async for obj in collection.find({"criteria": {"$exists": True}}, projection={"_id": 1, "criteria": 1, "status": 1}):
            try:
                updated_criteria, products = await update_criteria(obj, products)
                if updated_criteria:
                    counter += 1
                    bulk.append(
                        UpdateOne(
                            filter={"_id": obj["_id"]},
                            update={"$set": {"criteria": updated_criteria}}
                        )
                    )

                if bulk and len(bulk) % 500 == 0:
                    await bulk_update(collection, bulk, session, counter, criteria_obj)
                    bulk = []
                if len(products) >= 200:
                    for product_id, product_responses in products.items():
                        bulk_products.append(
                            UpdateOne(
                                filter={"_id": product_id},
                                update={"$set": {"requirementResponses": product_responses}}
                            )
                        )
                if bulk_products and len(bulk_products) >= 200:
                    counter_products += len(bulk_products)
                    await bulk_update(products_collection, bulk_products, session, counter_products, "products")
                    bulk_products = []
                    products = {}
            except Exception as e:
                logger.info(f"ERROR: {criteria_obj} with id {obj['_id']}. Caught {type(e).__name__}.")
                traceback.print_exc()
                break

        if bulk:
            await bulk_update(collection, bulk, session, counter, criteria_obj)

        if products:
            for product_id, product_responses in products.items():
                bulk_products.append(
                    UpdateOne(
                        filter={"_id": product_id},
                        update={"$set": {"requirementResponses": product_responses}}
                    )
                )

        if bulk_products:
            counter_products += len(bulk_products)
            await bulk_update(products_collection, bulk_products, session, counter_products, "products")

        logger.info(f"Finished. Processed {counter} records of migrated {criteria_obj}")


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
