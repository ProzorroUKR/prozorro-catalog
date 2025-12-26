import argparse
import asyncio
import logging
from datetime import datetime

import sentry_sdk
from pymongo import UpdateOne

from catalog.db import get_category_collection, get_profiles_collection, init_mongo, transaction_context_manager
from catalog.logging import setup_logging
from catalog.migrations.cs_16303_requirement_iso_migration import bulk_update
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now

logger = logging.getLogger(__name__)


COLLECTION_MAPPING = {
    "categories": get_category_collection,
    "profiles": get_profiles_collection,
}


async def migrate_objects(min_value, obj_name):
    logger.info(f"Start updating localization min value for {obj_name} migration")
    counter = 0
    bulk = []
    obj_collection = COLLECTION_MAPPING[obj_name]()

    async for obj in obj_collection.find(
            {"status": "active"},
            projection={"_id": 1, "criteria": 1},
    ):
        new_criteria = get_new_criteria(obj, min_value)
        if new_criteria is not None:
            now = get_now().isoformat()
            bulk.append(
                UpdateOne(
                    filter={"_id": obj["_id"]},
                    update={"$set": {"criteria": new_criteria, "dateModified": now}}
                )
            )
            counter += 1

            if bulk and len(bulk) % 500 == 0:
                async with transaction_context_manager() as session:
                    await bulk_update(obj_collection, bulk, session, counter, migrated_obj=obj_name)
                bulk = []

    if bulk:
        async with transaction_context_manager() as session:
            await bulk_update(obj_collection, bulk, session, counter, migrated_obj=obj_name)

    logger.info(f"Finished {obj_name}. Processed {counter} updated localization min value for {obj_name}.")


def get_new_criteria(obj: dict, min_value: float) -> dict:
    update_obj = False
    criteria = obj.get("criteria", [])

    for criterion in criteria:
        if criterion["classification"]["id"] == "CRITERION.OTHER.SUBJECT_OF_PROCUREMENT.LOCAL_ORIGIN_LEVEL":
            for rg in criterion.get("requirementGroups", ""):
                for req in rg.get("requirements", ""):
                    if "minValue" in req:
                        req["minValue"] = min_value
                        update_obj = True
    if update_obj:
        return criteria


async def migrate(args):
    min_value = float(args.new_min_value)
    await migrate_objects(min_value, obj_name="categories")
    await migrate_objects(min_value, obj_name="profiles")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--new_min_value",
        type=str,
        help="New min value",
        required=True,
    )
    return parser.parse_args()


def main():
    """
    MIN_VALUE=<new min value>
    PYTHONPATH=/app python catalog/migrations/cs_20866_update_localization_min_value.py --new_min_value="${MIN_VALUE}"
    """
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate(parse_args()))


if __name__ == "__main__":
    main()
