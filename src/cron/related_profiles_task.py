import asyncio
import logging
import re
from dataclasses import dataclass

import sentry_sdk
from pymongo import UpdateOne

from catalog.db import get_category_collection, get_products_collection, get_profiles_collection, init_mongo
from catalog.logging import setup_logging
from catalog.models.criteria import TYPEMAP
from catalog.models.product import ProductStatus
from catalog.settings import LOCALIZATION_CRITERIA, SENTRY_DSN
from catalog.utils import get_now

logger = logging.getLogger(__name__)


@dataclass
class Counters:
    total_products: int = 0
    succeeded_products: int = 0
    skipped_products: int = 0


async def run_task():
    category_collection = get_category_collection()
    products_collection = get_products_collection()
    profiles_collection = get_profiles_collection()
    counters = Counters()
    bulk = []

    async for category in category_collection.find({}, projection={"_id": 1}, no_cursor_timeout=True):
        category_id = category["_id"]
        profiles = await profiles_collection.find(
            {
                "relatedCategory": category_id,
                "status": ProductStatus.active,
                "criteria.requirementGroups.requirements": {"$exists": True},
            },
            projection={"criteria": 1},
            no_cursor_timeout=True,
        ).to_list(None)

        product_cursor = products_collection.find(
            {"relatedCategory": category_id, "requirementResponses": {"$exists": True}, "status": ProductStatus.active},
            projection={"requirementResponses": 1, "relatedProfiles": 1, "relatedCategory": 1},
            no_cursor_timeout=True,
        )
        product_cursor.batch_size(1000)

        async for product in product_cursor:
            related_profiles = await get_product_relatedProfiles(product, profiles)

            if product.get("relatedProfiles", []) != related_profiles:
                bulk.append(
                    UpdateOne(
                        filter={"_id": product["_id"]},
                        update={
                            "$set": {"relatedProfiles": related_profiles, "dateModified": get_now().isoformat()},
                        },
                    )
                )
            counters.total_products += 1

    if bulk:
        result = await products_collection.bulk_write(bulk)
        bulk_len = len(bulk)
        if result.modified_count != bulk_len:
            logger.error(f"Unexpected modified_count: {result.modified_count}; expected {bulk_len}")
        counters.succeeded_products = result.modified_count
        counters.skipped_products = counters.total_products - result.modified_count

    logger.info(f"Finished. Stats: {counters}")
    return counters


async def get_product_relatedProfiles(product, profiles):
    related_profiles = []
    for profile in profiles:
        profile_requirements = get_criteria_requirements(profile)

        # there should be requirements in profile
        if not profile_requirements:
            continue

        # all profile criteria must meet requirements
        if not check_profile_criteria_meets_requirements(profile, product):
            continue

        # profile requirements must be valid
        if not validate_profile_requirements(product, profile_requirements):
            continue

        related_profiles.append(profile["_id"])

    return related_profiles


def get_criteria_requirements(profile: dict) -> dict:
    profile_requirements = {}
    for criterion in profile.get("criteria", []):
        for group in criterion.get("requirementGroups", []):
            for req in group.get("requirements", []):
                profile_requirements[req["title"]] = req
    return profile_requirements


def check_profile_criteria_meets_requirements(profile: dict, product: dict) -> bool:
    product_requirement_responses = {rr["requirement"] for rr in product.get("requirementResponses", [])}
    criteria_meets_requirements = []
    for criterion in profile.get("criteria", []):
        group_meets_requirements = []
        for group in criterion.get("requirementGroups", []):
            req_ids = {req["title"] for req in group.get("requirements", [])}
            group_meets_requirements.append(req_ids.issubset(product_requirement_responses))
        # LOCALIZATION_CRITERIA must have only ONE group to meet requirements, no more, no less
        if criterion.get("classification", {}).get("id") == LOCALIZATION_CRITERIA:
            criteria_meets_requirements.append(group_meets_requirements.count(True) == 1)
        # other criteria needs all the groups to meet requirements
        else:
            criteria_meets_requirements.append(all(group_meets_requirements))

    return all(criteria_meets_requirements)


def validate_profile_requirements(product: dict, profile_requirements: dict) -> bool:
    is_valid_profile = False
    for rr in product.get("requirementResponses", {}):
        req_key = rr["requirement"]

        requirement = profile_requirements.get(req_key)
        if not requirement:
            continue

        if any(i in requirement for i in ("expectedValue", "minValue", "maxValue", "pattern")):
            value = get_value(rr)
            is_valid_profile = is_valid_req_response_value(requirement, value)

        elif "expectedValues" in requirement:
            value = get_value(rr, is_list=True)
            is_valid_profile = is_valid_req_response_values(requirement, value)

        else:
            value = get_value(rr)
            is_valid_profile = is_valid_data_type(requirement, value)

        if not is_valid_profile:
            break

    return is_valid_profile


def is_valid_data_type(requirement, value):
    data_type = requirement.get("dataType")
    data_type = TYPEMAP.get(data_type)
    return isinstance(value, data_type) if data_type else False


def is_valid_req_response_value(requirement, value):
    if value is None:
        return False

    if not is_valid_data_type(requirement, value):
        return False

    try:
        if "expectedValue" in requirement and value != requirement["expectedValue"]:
            return False
        if "minValue" in requirement and float(value) < float(requirement["minValue"]):
            return False
        if "maxValue" in requirement and float(value) > float(requirement["maxValue"]):
            return False
        if "pattern" in requirement and not re.match(requirement["pattern"], str(value)):
            return False
    except (ValueError, TypeError):
        return False

    return True


def is_valid_req_response_values(requirement, values):
    if not values:
        return False
    if not set(values).issubset(set(requirement["expectedValues"])):
        return False
    if "expectedMinItems" in requirement and len(values) < requirement["expectedMinItems"]:
        return False
    if "expectedMaxItems" in requirement and len(values) > requirement["expectedMaxItems"]:
        return False

    return True


def get_value(rr, is_list=False):
    if "value" in rr:
        if not is_list:
            return rr["value"]
        else:
            return [rr["value"]]
    elif "values" in rr:
        if not is_list:
            return rr["values"][0]
        else:
            return rr["values"]


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(run_task())


if __name__ == "__main__":
    main()
