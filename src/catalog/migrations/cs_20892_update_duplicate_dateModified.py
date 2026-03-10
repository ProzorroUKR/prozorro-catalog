import argparse
import asyncio
import logging
from datetime import datetime, timedelta

import sentry_sdk
from pymongo import UpdateOne

from catalog.db import (
    get_category_collection,
    get_contributor_collection,
    get_offers_collection,
    get_product_request_collection,
    get_products_collection,
    get_profiles_collection,
    get_vendor_collection,
    init_mongo,
    transaction_context_manager,
)
from catalog.logging import setup_logging
from catalog.migrations.utils import bulk_update
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now

logger = logging.getLogger(__name__)

COLLECTION_FUNCS = {
    "category": get_category_collection,
    "profiles": get_profiles_collection,
    "products": get_products_collection,
    "offers": get_offers_collection,
    "vendors": get_vendor_collection,
    "contributors": get_contributor_collection,
    "requests": get_product_request_collection,
}


def __get_aggregation_query(collection_name: str) -> list[dict]:
    return [
        {"$group": {"_id": "$dateModified", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}},
        {
            "$lookup": {
                "from": collection_name,
                "localField": "_id",
                "foreignField": "dateModified",
                "as": "docs",
            }
        },
        {"$unwind": "$docs"},
        {"$replaceRoot": {"newRoot": "$docs"}},
    ]


async def migrate_collection_dateModified(collection_name):
    logger.info(f"Start {collection_name} collection migration")
    counter = 0
    bulk = []
    db_collection = COLLECTION_FUNCS[collection_name]()
    async for doc in db_collection.aggregate(__get_aggregation_query(collection_name)):
        dt = doc.get("dateModified", get_now().isoformat())
        dt = datetime.fromisoformat(dt) + timedelta(microseconds=counter + 1)
        bulk.append(
            UpdateOne(
                filter={"_id": doc["_id"]},
                update={"$set": {"dateModified": dt.isoformat()}},
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


def parse_args() -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "collection_name",
        type=str,
        help=f"Collection name, one of: {list(COLLECTION_FUNCS.keys())}",
    )

    collection_name = parser.parse_args().collection_name
    if collection_name not in COLLECTION_FUNCS:
        raise Exception(f"Unknown collection {collection_name}")

    return collection_name


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate_collection_dateModified((parse_args())))


if __name__ == "__main__":
    """
    COLLECTION_NAME=<collection name>
    PYTHONPATH=/app python catalog/migrations/cs_20892_update_duplicate_dateModified.py $COLLECTION_NAME"
    """
    main()
