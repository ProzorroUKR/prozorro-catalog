from collections import defaultdict
from hashlib import md5
from pymongo.errors import PyMongoError
from pymongo import UpdateOne
from catalog.db import get_profiles_collection, get_products_collection, init_mongo, transaction_context_manager
from catalog.logging import setup_logging
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now
import asyncio
import logging
import sentry_sdk


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

        # update global counters
        for k, v in stats.items():
            counters[k] += v

        if counters["total_profiles"] % 500 == 0:
            logger.info(f"Stats: {dict(counters)}")
    logger.info(f"Finished. Stats: {dict(counters)}")


async def migrate_profile(profile_id):
    counters = defaultdict(int)

    products_collection = get_products_collection()

    async with transaction_context_manager() as session:
        profile = await get_profiles_collection().find_one(
            {"_id": profile_id},
            projection={"criteria": 1},
            session=session
        )
        new_criteria = get_new_profile_criteria(counters, profile_id, profile)
        if new_criteria:
            now = get_now().isoformat()
            # update profile
            counters["profiles"] += 1
            result = await get_profiles_collection().update_one(
                {"_id": profile_id},
                {"$set": {"criteria": new_criteria, "dateModified": now}},
                session=session
            )
            if result.modified_count != 1:
                logger.error(f"Updating {profile_id} has unexpected modified_count: {result.modified_count}")

            # then update products
            bulk = []
            async for p in products_collection.find({"relatedProfile": profile_id},
                                                    projection={"requirementResponses": 1},
                                                    session=session):
                new_responses = get_new_responses(counters, profile_id, p)
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
def get_new_responses(counters, profile_id, product):
    update_product = False
    for response in product.get("requirementResponses", ""):
        new_uid = get_new_uid(profile_id, response["requirement"])
        if new_uid:
            response["requirement"] = new_uid

            counters["responses"] += 1
            update_product = True

    if update_product:
        return product["requirementResponses"]


def get_new_profile_criteria(counters, profile_id, profile):
    update_profile = False

    for criteria in profile.get("criteria", ""):
        for group in criteria.get("requirementGroups", ""):
            for requirement in group.get("requirements", ""):
                requirement_id = requirement["id"]
                new_uid = get_new_uid(profile_id, requirement_id)
                if new_uid:
                    requirement["id"] = new_uid

                    update_profile = True
                    counters["requirements"] += 1
                else:
                    continue  # already md5

    if update_profile:
        return profile["criteria"]


def get_new_uid(profile_id, requirement_id):
    try:  # test for a valid md5
        assert len(requirement_id) == 32
        int(requirement_id, 16)
    except (ValueError, AssertionError):
        hex_uid = md5(f"{profile_id} {requirement_id}".encode()).hexdigest()
        return hex_uid


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate())


if __name__ == '__main__':
    main()
