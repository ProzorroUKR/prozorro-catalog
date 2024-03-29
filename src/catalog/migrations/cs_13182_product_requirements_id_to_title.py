from dataclasses import dataclass
from uuid import UUID
import asyncio
import logging
import re

from pymongo.errors import PyMongoError
from pymongo import UpdateOne

import sentry_sdk

from catalog.db import get_profiles_collection, get_products_collection, init_mongo, transaction_context_manager
from catalog.logging import setup_logging
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now


logger = logging.getLogger(__name__)


@dataclass
class Counters:
    total_profiles: int = 0
    total_products: int = 0
    updated_products: int = 0
    skipped_products: int = 0
    total_responses: int = 0
    updated_responses: int = 0
    deleted_responses: int = 0

    def __post_init__(self):
        self.total_products = self.total_products or (
            self.updated_products +
            self.skipped_products
        )

        self.total_responses = self.total_responses or (
            self.updated_responses +
            self.deleted_responses
        )

    def __add__(self, other):
        return Counters(
            self.total_profiles + other.total_profiles,
            self.total_products + other.total_products,
            self.updated_products + other.updated_products,
            self.skipped_products + other.skipped_products,
            self.total_responses + other.total_responses,
            self.updated_responses + other.updated_responses,
            self.deleted_responses + other.deleted_responses,
        )


async def migrate():
    logger.info("Start migration")
    counters = Counters()
    async for profile in get_profiles_collection().find({}, projection={"_id": 1}):
        try:
            stats = await migrate_products(profile["_id"])
        except PyMongoError as e:
            logger.warning(f"Handled mongo error: {e}")
            stats = Counters()
        counters.total_profiles += 1

        # update global counters
        counters += stats
        if counters.total_profiles % 500 == 0:
            logger.info(f"Stats: {counters}")
    logger.info(f"Finished. Stats: {counters}")
    return counters


async def migrate_products(profile_id: str):
    counters = Counters()

    products_collection = get_products_collection()
    async with transaction_context_manager() as session:
        profile = await get_profiles_collection().find_one(
            {"_id": profile_id},
            projection={"criteria": 1},
            session=session
        )
        titles_map = {
            r["id"]: r["title"]
            for c in profile.get("criteria", "")
            for rg in c.get("requirementGroups", "")
            for r in rg.get("requirements", "")
        }
        query = {"relatedProfiles": {"$in": [profile_id]}}
        if titles_map:
            now = get_now().isoformat()
            # then update products
            bulk = []
            async for p in products_collection.find(query,
                                                    projection={"requirementResponses": 1},
                                                    session=session):
                new_responses = get_new_responses(counters, titles_map, p)
                if new_responses is not None:
                    bulk.append(
                        UpdateOne(
                            filter={"_id": p["_id"]},
                            update={"$set": {"requirementResponses": new_responses, "dateModified": now}}
                        )
                    )
                    counters.updated_products += 1
                else:
                    counters.skipped_products += 1
                counters.total_products += 1

            if bulk:
                result = await products_collection.bulk_write(bulk, session=session)
                if result.modified_count != len(bulk):
                    logger.error(f"Unexpected modified_count: {result.modified_count}; expected {len(bulk)}")
        else:
            skipped_products = await products_collection.count_documents(query, session=session)
            counters.skipped_products = skipped_products
            counters.total_products = skipped_products
    return counters


#   --- model operations
def get_new_responses(counters: Counters, titles_map: dict, product: dict):
    update_product = False
    req_responses = product.get("requirementResponses", "")

    for response in req_responses[:]:
        requirement_title = titles_map.get(response["requirement"])
        if requirement_title:
            response["requirement"] = requirement_title
            counters.updated_responses += 1
            update_product = True
        elif check_uuid(response["requirement"]):
            req_responses.remove(response)
            counters.deleted_responses += 1
            update_product = True
        counters.total_responses += 1

    if update_product:
        return req_responses


def check_uuid(req_id):
    return bool(re.match(r"^[0-9A-Za-z_-]{1,32}$", req_id))


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate())


if __name__ == '__main__':
    main()
