import asyncio
import logging

import sentry_sdk

from pymongo import UpdateOne

from catalog.db import (
    get_category_collection,
    init_mongo,
    transaction_context_manager,
    get_products_collection,
)
from catalog.logging import setup_logging
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now

logger = logging.getLogger(__name__)


async def update_responses_in_product(product):
    category = await get_category_collection().find_one(
        {"_id": product["relatedCategory"]}, {"criteria": 1}
    )
    if not category:
        return None
    category_requirements = {
        req["title"]: req
        for c in category.get("criteria", "")
        for group in c["requirementGroups"]
        for req in group["requirements"]
        if req.get("dataType") == "string"
    }
    responses = []
    updated = False
    for resp in product.get("requirementResponses", []):
        if resp["requirement"] in category_requirements and "value" in resp:
            resp["values"] = [str(resp.pop("value"))]
            updated = True
        responses.append(resp)
    return responses if updated else None


async def migrate():
    logger.info("Start migration")
    collection = get_products_collection()
    bulk = []
    counter = 0
    cursor = collection.find(
        {"requirementResponses": {"$exists": True}},
        projection={
            "_id": 1,
            "requirementResponses": 1,
            "relatedCategory": 1,
        },
        no_cursor_timeout=True,
        batch_size=200,
    )
    async for obj in cursor:
        if updated_responses := await update_responses_in_product(obj):
            counter += 1
            bulk.append(
                UpdateOne(
                    filter={"_id": obj["_id"]},
                    update={"$set": {
                        "requirementResponses": updated_responses,
                        "dateModified": get_now().isoformat(),
                    }},
                )
            )
        if bulk and len(bulk) % 500 == 0:
            async with transaction_context_manager() as session:
                await bulk_update(collection, bulk, session, counter, "products")
            bulk = []
    if bulk:
        async with transaction_context_manager() as session:
            await bulk_update(collection, bulk, session, counter, "products")
    await cursor.close()

    logger.info(f"Finished. Processed {counter} records of migrated products")
    logger.info("Successfully migrated")


async def bulk_update(collection, bulk, session, counter, migrated_obj):
    await collection.bulk_write(bulk, session=session)
    logger.info(f"Processed {counter} records of migrated {migrated_obj}")


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate())


if __name__ == "__main__":
    main()
