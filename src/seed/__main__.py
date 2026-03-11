"""
Combined seed & price calculation script.

Steps:
  1. Seed categories and products
  2. Seed product bids
  3. Full price recalculation

Usage:
    python -m seed
"""

import asyncio
import logging
import sys
from datetime import timedelta

from catalog.db import get_category_collection, get_products_collection, init_mongo
from catalog.logging import setup_logging

logger = logging.getLogger(__name__)


async def step_seed_data():
    """Seed categories and products using async motor (reuses catalog.db)."""
    from catalog.utils import get_now
    from seed.data import (
        CARTRIDGE_PRODUCTS,
        CARTRIDGE_REQUIREMENTS,
        PAPER_BRANDS_PRODUCTS,
        PAPER_REQUIREMENTS,
        STATIONERY_PRODUCTS,
        STATIONERY_REQUIREMENTS,
        build_category,
        build_product,
        detect_format,
        make_cartridge_responses,
        make_paper_responses,
        make_stationery_responses,
    )

    logger.info("Step 1: Seeding categories and products")

    cat_col = get_category_collection()
    prod_col = get_products_collection()

    cat_col.delete_many({})
    prod_col.delete_many({})

    paper_cat = build_category(
        cat_id="30197630-100001-42574629",
        title="Папір офісний",
        classification={"id": "30197630-1", "description": "Папір для друку на комп'ютері", "scheme": "ДК021"},
        unit_code="PK",
        unit_name="пачка",
        raw_requirements=PAPER_REQUIREMENTS,
    )
    stationery_cat = build_category(
        cat_id="30192000-100002-42574629",
        title="Канцелярське приладдя",
        classification={"id": "30192000-1", "description": "Канцелярське приладдя", "scheme": "ДК021"},
        unit_code="H87",
        unit_name="штука",
        raw_requirements=STATIONERY_REQUIREMENTS,
    )
    cartridge_cat = build_category(
        cat_id="30125100-100003-42574629",
        title="Картриджі для принтерів",
        classification={"id": "30125100-2", "description": "Картриджі з тонером", "scheme": "ДК021"},
        unit_code="H87",
        unit_name="штука",
        raw_requirements=CARTRIDGE_REQUIREMENTS,
    )

    categories = [paper_cat, stationery_cat, cartridge_cat]
    for cat in categories:
        await cat_col.replace_one({"_id": cat["_id"]}, cat, upsert=True)
    logger.info(f"Inserted {len(categories)} categories")

    products = []

    for brand, title, density, whiteness, sheets, qclass in PAPER_BRANDS_PRODUCTS:
        fmt = detect_format(title)
        responses = make_paper_responses(paper_cat, brand, density, whiteness, sheets, qclass)
        responses[0] = {"requirement": responses[0]["requirement"], "values": [fmt]}
        products.append(
            build_product(
                title=title,
                classification=paper_cat["classification"],
                category_id=paper_cat["_id"],
                requirement_responses=responses,
            )
        )

    for title, item_type, color, thickness, has_grip in STATIONERY_PRODUCTS:
        products.append(
            build_product(
                title=title,
                classification=stationery_cat["classification"],
                category_id=stationery_cat["_id"],
                requirement_responses=make_stationery_responses(stationery_cat, item_type, color, thickness, has_grip),
            )
        )

    for title, print_type, color, page_yield in CARTRIDGE_PRODUCTS:
        products.append(
            build_product(
                title=title,
                classification=cartridge_cat["classification"],
                category_id=cartridge_cat["_id"],
                requirement_responses=make_cartridge_responses(cartridge_cat, print_type, color, page_yield),
            )
        )

    base_time = get_now() - timedelta(hours=len(products))
    for i, p in enumerate(products):
        ts = (base_time + timedelta(hours=i)).isoformat()
        p["dateCreated"] = ts
        p["dateModified"] = ts

    for p in products:
        await prod_col.replace_one({"_id": p["_id"]}, p, upsert=True)

    logger.info(f"Inserted {len(products)} products")


async def step_seed_product_bids():
    """Seed product bids."""
    logger.info("Step 2: Seeding product bids")
    from seed.product_bids import main as seed_bids_main

    await seed_bids_main()


async def step_calculate_prices():
    """Run full price recalculation."""
    logger.info("Step 3: Full price recalculation")
    from catalog.prices import run_task

    await run_task()


async def main():
    await init_mongo()

    await step_seed_data()
    await step_seed_product_bids()
    await step_calculate_prices()

    logger.info("All steps completed successfully")


if __name__ == "__main__":
    setup_logging()
    try:
        asyncio.run(main())
    except Exception:
        logger.exception("Seed and calculate failed")
        sys.exit(1)
