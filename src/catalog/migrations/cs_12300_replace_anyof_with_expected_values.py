import asyncio
import logging
from collections import defaultdict

from pymongo import UpdateOne
from pymongo.errors import PyMongoError
import sentry_sdk

from catalog.db import get_profiles_collection, get_products_collection, init_mongo, transaction_context_manager
from catalog.logging import setup_logging
from catalog.utils import get_now
from catalog.settings import SENTRY_DSN


logger = logging.getLogger(__name__)


async def migrate():
    logger.info("Start migration")

    counters = defaultdict(int)
    async for item in get_profiles_collection().find({}, projection={"_id": 1}):
        while True:
            try:
                stats = await migrate_profile(item["_id"])
            except PyMongoError as e:
                logger.warning(f"Handled mongo error: {e}")
            else:
                break
        for k, v in stats.items():
            counters[k] += v

        if counters["total_profiles"] % 500 == 0:
            logger.info(f"Stats: {dict(counters)}")
    logger.info(f"Finished. Stats: {dict(counters)}")


async def migrate_profile(profile_id: str):
    counters = defaultdict(int)
    products_collection = get_products_collection()

    async with transaction_context_manager() as session:
        profile = await get_profiles_collection().find_one(
            {"_id": profile_id},
            projection={"criteria": 1},
            session=session
        )
        updated_criteria, requirements_id = get_new_criteria_requirements(counters, profile)

        if requirements_id:
            now = get_now().isoformat()
            counters["profiles"] += 1
            result = await get_profiles_collection().update_one(
                {"_id": profile_id},
                {"$set": {"criteria": updated_criteria, "dateModified": now}},
                session=session
            )
            if result.modified_count != 1:
                logger.error(f"Updating {profile_id} has unexpected modified_count: {result.modified_count}")

            bulk = []
            async for p in products_collection.find({"relatedProfile": profile_id},
                                                    projection={"requirementResponses": 1},
                                                    session=session):
                new_responses = get_new_responses(counters, p, requirements_id)
                if new_responses:
                    bulk.append(
                        UpdateOne(
                            filter={"_id": p["_id"]},
                            update={"$set": {"requirementResponses": new_responses, "dateModified": now}}
                        )
                    )
                    counters["products"] += 1
                else:
                    counters["skipped_products"] += 1

            if bulk:
                result = await products_collection.bulk_write(bulk, session=session)
                if result.modified_count != len(bulk):
                    logger.error(f"Unexpected modified_count: {result.modified_count}; expected {len(bulk)}")
        else:
            counters["skipped_profiles"] += 1
        counters["total_profiles"] += 1
        return counters

#   --- model operations


def get_new_criteria_requirements(counters, profile):
    updated_requirements = []
    for criteria in profile.get("criteria", ""):
        for group in criteria.get("requirementGroups", ""):
            for requirement in group.get("requirements", ""):
                expected_values = get_new_expected_values(requirement)
                if expected_values:
                    requirement["expectedValues"] = expected_values
                    updated_requirements.append(requirement["id"])
                    counters["requirements"] += 1
    return profile["criteria"], updated_requirements


def get_new_expected_values(requirement):
    of_fields = ["anyOf", "allOf", "oneOf"]
    for field in of_fields:
        if requirement.get(field):
            expected_values = requirement[field]
            del requirement[field]
            return expected_values


def get_new_responses(counters, product, requirements_id):
    update_product = False
    for response in product.get("requirementResponses", ""):
        if response["requirement"] in requirements_id:
            response["values"] = [response["value"]]
            del response["value"]
            counters["responses"] += 1
            update_product = True

    if update_product:
        return product["requirementResponses"]


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate())


if __name__ == '__main__':
    main()
