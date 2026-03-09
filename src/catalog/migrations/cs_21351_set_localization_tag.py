import asyncio
import logging
from uuid import uuid4

import sentry_sdk
from aiohttp import web
from pymongo import UpdateOne

from catalog.db import (
    get_category_collection,
    get_profiles_collection,
    init_mongo,
    insert_tag,
    read_tag,
    transaction_context_manager,
)
from catalog.logging import setup_logging
from catalog.migrations.cs_16303_requirement_iso_migration import bulk_update
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now

logger = logging.getLogger(__name__)

TAG_DATA = {
    "code": "LOCAL",
    "name": "Локалізація",
    "name_en": "Localisation",
}

COLLECTION_FUNCS = {
    "category": get_category_collection,
    "profiles": get_profiles_collection,
}


async def get_or_create_localization_tag():
    """
    Function gets or creates LOCAL tag if it did not exist
    Returns tag code
    """
    try:
        await read_tag(TAG_DATA["code"])
    except web.HTTPNotFound:
        await insert_tag(
            {
                **TAG_DATA,
                "id": uuid4().hex,
            }
        )
    return TAG_DATA["code"]


async def migrate_collection_tags(tag_code, collection_name):
    logger.info(f"Start {collection_name} migration")
    counter = 0
    bulk = []
    db_collection = COLLECTION_FUNCS[collection_name]()
    async for doc in db_collection.find(
        {
            "criteria.classification.id": "CRITERION.OTHER.SUBJECT_OF_PROCUREMENT.LOCAL_ORIGIN_LEVEL",
            "tags": {"$not": {"$elemMatch": {"$eq": tag_code}}},
        }
    ):
        now = get_now().isoformat()
        tags = doc.get("tags", [])
        tags.append(tag_code)
        bulk.append(
            UpdateOne(
                filter={"_id": doc["_id"]},
                update={
                    "$set": {
                        "dateModified": now,
                        "tags": tags,
                    }
                },
            )
        )
        counter += 1

        if bulk and len(bulk) % 500 == 0:
            async with transaction_context_manager() as session:
                await bulk_update(db_collection, bulk, session, counter, migrated_obj=collection_name)
            bulk = []

    if bulk:
        async with transaction_context_manager() as session:
            await bulk_update(db_collection, bulk, session, counter, migrated_obj=collection_name)

    logger.info(f"Finished. Processed {counter} objects in {collection_name} collection")
    logger.info("Successfully migrated")


async def migrate():
    tag_code = await get_or_create_localization_tag()
    for collection_name in COLLECTION_FUNCS.keys():
        await migrate_collection_tags(tag_code, collection_name)


def main():
    """
    python catalog/migrations/cs_21351_set_localization_tag.py
    """
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate())


if __name__ == "__main__":
    main()
