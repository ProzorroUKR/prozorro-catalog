from dataclasses import dataclass
import asyncio
import logging

from pymongo.errors import PyMongoError

import sentry_sdk

from catalog.db import get_profiles_collection, get_products_collection, init_mongo, transaction_context_manager
from catalog.logging import setup_logging
from catalog.settings import SENTRY_DSN
from catalog.models.product import ProductStatus


logger = logging.getLogger(__name__)


@dataclass
class Counters:
    total_profiles: int = 0
    total_products: int = 0
    good_products: int = 0
    broken_active_products: int = 0
    broken_hidden_products: int = 0
    total_responses: int = 0
    broken_responses: int = 0

    def __post_init__(self):
        self.total_products = self.total_products or (
            self.good_products +
            self.broken_active_products +
            self.broken_hidden_products
        )

    def __add__(self, other):
        return Counters(
            self.total_profiles + other.total_profiles,
            self.total_products + other.total_products,
            self.good_products + other.good_products,
            self.broken_active_products + other.broken_active_products,
            self.broken_hidden_products + other.broken_hidden_products,
            self.total_responses + other.total_responses,
            self.broken_responses + other.broken_responses
        )


async def analyze():
    logger.info("Start migration")
    counters = Counters()
    async for profile in get_profiles_collection().find({}, projection={"_id": 1}):
        try:
            stats = await analyze_products(profile["_id"])
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


async def analyze_products(profile_id: str):
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
            async for p in products_collection.find(query,
                                                    projection={"requirementResponses": 1, "status": 1},
                                                    session=session):
                is_product_broken, counters = analyze_product_responses(counters, titles_map, p)
                counters.total_products += 1
                if is_product_broken:
                    if p["status"] == ProductStatus.active:
                        counters.broken_active_products += 1
                    else:
                        counters.broken_hidden_products += 1
                else:
                    counters.good_products += 1

    return counters


#   --- model operations
def analyze_product_responses(counters, titles_map, product):
    is_product_broken = False
    for response in product.get("requirementResponses", ""):
        requirement_title = titles_map.get(response["requirement"])
        if not requirement_title:
            is_product_broken = True
            counters.broken_responses += 1
        counters.total_responses += 1
    return is_product_broken, counters


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(analyze())


if __name__ == '__main__':
    main()
