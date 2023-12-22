from dataclasses import dataclass
import asyncio
import logging

from pymongo import UpdateOne

import sentry_sdk

from catalog.db import get_category_collection, get_profiles_collection, init_mongo, transaction_context_manager
from catalog.logging import setup_logging
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now


logger = logging.getLogger(__name__)

NEW_REQ_MIN_VALUE = 20
NEW_REQ_DESCRP = "на 2024 рік"
LOCALIZED_CATEGORY_ID = "99999999-919912-02426097"


@dataclass
class Counters:
    total_profiles: int = 0
    updated_profiles: int = 0
    skipped_profiles: int = 0
    updated_category: int = 0
    total_requirements: int = 0
    updated_requirements: int = 0
    skipped_requirements: int = 0

    def __post_init__(self):
        self.total_profiles = self.total_profiles or (
            self.updated_profiles +
            self.skipped_profiles
        )

        self.total_requirements = self.total_requirements or (
            self.updated_requirements +
            self.skipped_requirements
        )

    def __add__(self, other):
        return Counters(
            self.total_profiles + other.total_profiles,
            self.updated_profiles + other.updated_profiles,
            self.skipped_profiles + other.skipped_profiles,
            self.total_requirements + other.total_requirements,
            self.updated_requirements + other.updated_requirements,
            self.skipped_requirements + other.skipped_requirements,
        )


async def migrate():
    logger.info("Start migration")
    counters = Counters()
    bulk = []
    profiles_collection = get_profiles_collection()
    category_collection = get_category_collection()
    async with transaction_context_manager() as session:

        category = await category_collection.find_one(
            {"_id": LOCALIZED_CATEGORY_ID},
            projection={"_id": 1, "criteria": 1},
            session=session
        )
        new_criteria = get_new_criteria(counters, category)
        result = await category_collection.update_one(
            {"_id": LOCALIZED_CATEGORY_ID},
            {"$set": {"criteria": new_criteria, "dateModified": get_now().isoformat()}}
        )
        counters.updated_category = result.modified_count

        async for profile in profiles_collection.find(
                {"relatedCategory": LOCALIZED_CATEGORY_ID, "status": "active"},
                projection={"_id": 1, "criteria": 1},
                session=session
        ):
            now = get_now().isoformat()
            new_criteria = get_new_criteria(counters, profile)
            if new_criteria is not None:
                bulk.append(
                    UpdateOne(
                        filter={"_id": profile["_id"]},
                        update={"$set": {"criteria": new_criteria, "dateModified": now}}
                    )
                )

        if bulk:
            result = await profiles_collection.bulk_write(bulk, session=session)
            expected_modified_count = len(bulk)
            if result.modified_count != expected_modified_count:
                logger.error(f"Unexpected modified_count: {result.modified_count}; expected {expected_modified_count}")
            counters.updated_profiles += result.modified_count
            counters.skipped_profiles += expected_modified_count - result.modified_count
            counters.total_profiles += expected_modified_count

        if counters.total_profiles % 500 == 0:
            logger.info(f"Stats: {counters}")
    logger.info(f"Finished. Stats: {counters}")
    return counters


def get_new_criteria(counters: Counters, obj: dict):
    update_profile = False
    criteria = obj.get("criteria", "")

    for criterion in criteria:
        for rg in criterion.get("requirementGroups", ""):
            for req in rg.get("requirements", ""):
                if "minValue" in req:
                    req["minValue"] = NEW_REQ_MIN_VALUE
                    req["description"] = NEW_REQ_DESCRP
                    update_profile = True
                    counters.updated_requirements += 1
                else:
                    counters.skipped_requirements += 1
                counters.total_requirements += 1
    if update_profile:
        return criteria


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate())


if __name__ == '__main__':
    main()
