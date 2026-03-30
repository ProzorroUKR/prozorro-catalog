"""
Seed script: generates synthetic product_bids for E2E testing of price calculation pipeline.
Uses catalog.db services (same path as crawler) with proper codec_options.

Scenarios (100 products, 2-year period, ~35-40K bids total):
  Intervals tuned for 3-7 bids per 7-day window (price calc uses days_back=7).
  - Normal market (30 products): 1 bid/2 days, random ±10%  (~3-4 per window)
  - Low sample (10): 1 bid/14 days, random                  (~0-1 per window, that's the point)
  - Extreme outliers (10): 1 bid/day, normal + occasional x5 (~7 per window)
  - Constant price (10): 1 bid/2 days, same price            (~3-4 per window)
  - Growing trend (10): 1 bid/2 days, +1% per month          (~3-4 per window)
  - Falling trend (10): 1 bid/2 days, -1% per month          (~3-4 per window)
  - High volatility (10): 1 bid/day, random ±40%             (~7 per window)
  - Sparse data (5): clusters of 5-8 bids, gaps of 2-4 weeks
  - Duplicate bids (3): 1 bid/2 days, same tender/bid/item (tests unique constraint)
  - Invalid bids (2): 1 bid/3 days, amount=0
  - Billion prices (3): 1 bid/2 days, base ~3B UAH → quartiles > 1B

"""

import asyncio
import random
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

from catalog import db
from catalog.db import init_mongo
from catalog.models.product_bid import BaseProductBidData
from catalog.utils import get_next_rev, get_now

TZ = ZoneInfo("Europe/Kyiv")

BATCH_SIZE = 500

# 2-year period
END_DATE = datetime(2026, 3, 1, tzinfo=TZ)
START_DATE = END_DATE - timedelta(days=730)


def decimal_amount(val):
    return Decimal(str(max(0, round(val, 2))))


def make_bid_data(product_id, amount, date, unitCode="PK", unitName="пачка"):
    """Create a validated bid dict via BaseProductBidData (stable id field)."""
    data = BaseProductBidData(
        id=uuid4().hex,
        tenderId=f"UA-{date.strftime('%Y-%m-%d')}-{uuid4().hex[:8]}",
        bidId=uuid4().hex,
        itemId=uuid4().hex[:16],
        productId=product_id,
        currency="UAH",
        valueAddedTaxIncluded=False,
        unitCode=unitCode,
        unitName=unitName,
        amount=decimal_amount(amount),
        date=date.isoformat(),
        dateModified=get_now().isoformat(),
        dateCreated=get_now().isoformat(),
    ).model_dump(exclude_none=True)
    data["date"] = data["date"].isoformat()
    data["dateCreated"] = data["dateCreated"].isoformat()
    data["dateModified"] = data["dateModified"].isoformat()
    return data


def generate_dates(start, end, interval_days):
    dates = []
    current = start
    while current <= end:
        jitter = timedelta(hours=random.randint(8, 17), minutes=random.randint(0, 59))
        dates.append(current.replace(hour=0, minute=0, second=0) + jitter)
        current += timedelta(days=interval_days)
    return dates


def generate_normal_market(product_id, base_price, unitCode, unitName):
    """1 bid/2 days, ±10% → ~3-4 per 7-day window."""
    bids = []
    for d in generate_dates(START_DATE, END_DATE, 2):
        price = base_price * random.uniform(0.9, 1.1)
        bids.append(make_bid_data(product_id, price, d, unitCode, unitName))
    return bids


def generate_low_sample(product_id, base_price, unitCode, unitName):
    """1 bid/14 days → 0-1 per window (tests small sample behaviour)."""
    bids = []
    for d in generate_dates(START_DATE, END_DATE, 14):
        price = base_price * random.uniform(0.7, 1.3)
        bids.append(make_bid_data(product_id, price, d, unitCode, unitName))
    return bids


def generate_extreme_outliers(product_id, base_price, unitCode, unitName):
    """1 bid/day, 5% chance of x5 outlier → ~7 per window."""
    bids = []
    for d in generate_dates(START_DATE, END_DATE, 1):
        if random.random() < 0.05:
            price = base_price * random.uniform(4.0, 6.0)
        else:
            price = base_price * random.uniform(0.9, 1.1)
        bids.append(make_bid_data(product_id, price, d, unitCode, unitName))
    return bids


def generate_constant_price(product_id, base_price, unitCode, unitName):
    """1 bid/2 days, same price → ~3-4 per window, Q1=Q2=Q3."""
    bids = []
    for d in generate_dates(START_DATE, END_DATE, 2):
        bids.append(make_bid_data(product_id, base_price, d, unitCode, unitName))
    return bids


def generate_growing_trend(product_id, base_price, unitCode, unitName):
    """1 bid/2 days, +1%/month → ~3-4 per window."""
    bids = []
    for d in generate_dates(START_DATE, END_DATE, 2):
        months_elapsed = (d - START_DATE).days / 30.0
        price = base_price * (1 + 0.01 * months_elapsed) * random.uniform(0.98, 1.02)
        bids.append(make_bid_data(product_id, price, d, unitCode, unitName))
    return bids


def generate_falling_trend(product_id, base_price, unitCode, unitName):
    """1 bid/2 days, -1%/month → ~3-4 per window."""
    bids = []
    for d in generate_dates(START_DATE, END_DATE, 2):
        months_elapsed = (d - START_DATE).days / 30.0
        price = base_price * (1 - 0.01 * months_elapsed) * random.uniform(0.98, 1.02)
        price = max(price, base_price * 0.1)
        bids.append(make_bid_data(product_id, price, d, unitCode, unitName))
    return bids


def generate_high_volatility(product_id, base_price, unitCode, unitName):
    """1 bid/day, ±40% → ~7 per window."""
    bids = []
    for d in generate_dates(START_DATE, END_DATE, 1):
        price = base_price * random.uniform(0.6, 1.4)
        bids.append(make_bid_data(product_id, price, d, unitCode, unitName))
    return bids


def generate_sparse_data(product_id, base_price, unitCode, unitName):
    """Clusters of 5-8 bids over 3-5 days, then gap of 2-4 weeks."""
    bids = []
    current = START_DATE
    while current <= END_DATE:
        cluster_size = random.randint(5, 8)
        for _ in range(cluster_size):
            d = current + timedelta(days=random.randint(0, 4))
            if d > END_DATE:
                break
            jitter = timedelta(hours=random.randint(8, 17), minutes=random.randint(0, 59))
            price = base_price * random.uniform(0.85, 1.15)
            bids.append(make_bid_data(product_id, price, d + jitter, unitCode, unitName))
        current += timedelta(days=random.randint(14, 28))
    return bids


def generate_duplicate_bids(product_id, base_price, unitCode, unitName):
    """1 bid/2 days, same tender/bid/item — tests unique constraint handling."""
    bids = []
    dates = generate_dates(START_DATE, END_DATE, 2)
    tender_id = f"UA-{START_DATE.strftime('%Y-%m-%d')}-{uuid4().hex[:8]}"
    bid_id = uuid4().hex
    item_id = uuid4().hex[:16]
    for d in dates:
        bid = make_bid_data(product_id, base_price, d, unitCode, unitName)
        bid["tenderId"] = tender_id
        bid["bidId"] = bid_id
        bid["itemId"] = item_id
        bids.append(bid)
    return bids


def generate_invalid_bids(product_id, base_price, unitCode, unitName):
    """1 bid/3 days, amount=0 or near-zero."""
    bids = []
    for d in generate_dates(START_DATE, END_DATE, 3):
        amount = 0 if random.random() < 0.5 else random.uniform(0, 0.01)
        bids.append(make_bid_data(product_id, amount, d, unitCode, unitName))
    return bids


SCENARIO_CONFIG = [
    ("normal_market", 30, generate_normal_market, 100),
    ("low_sample", 15, generate_low_sample, 100),
    ("extreme_outliers", 15, generate_extreme_outliers, 100),
    ("constant_price", 15, generate_constant_price, 100),
    ("growing_trend", 15, generate_growing_trend, 100),
    ("falling_trend", 15, generate_falling_trend, 100),
    ("high_volatility", 15, generate_high_volatility, 100),
    ("sparse_data", 10, generate_sparse_data, 100),
    ("duplicate_bids", 5, generate_duplicate_bids, 100),
    ("invalid_bids", 5, generate_invalid_bids, 100),
    ("billion_prices", 10, generate_normal_market, 3_000_000_000),
]  # total: 150 products


async def get_product_ids():
    """Fetch real product IDs from the products collection."""
    collection = db.get_products_collection()
    products = (
        await collection.find({"status": "active"}, {"_id": 1, "relatedCategory": 1, "title": 1})
        .sort("_id", 1)
        .to_list(None)
    )

    by_category = {}
    for p in products:
        cat = p["relatedCategory"]
        by_category.setdefault(cat, []).append(p["_id"])
    return products, by_category


async def get_units_by_category(category_ids):
    """Get unit code/name for each category."""
    collection = db.get_category_collection()
    units = {}
    for cat_id in category_ids:
        category = await collection.find_one({"_id": cat_id})
        if category and "unit" in category:
            units[cat_id] = (
                category["unit"]["code"],
                category["unit"]["name"],
            )  # category.unit uses code/name (common.Unit)
        else:
            units[cat_id] = ("PK", "пачка")
    return units


def prepare_documents(bids):
    """Convert bid dicts to MongoDB documents (id→_id, add _rev)."""
    docs = []
    for bid in bids:
        doc = dict(**bid)
        doc["_id"] = doc.pop("id")
        doc["_rev"] = get_next_rev()
        docs.append(doc)
    return docs


async def bulk_insert(collection, bids):
    """Insert bids in batches using insert_many, skip duplicates."""
    inserted = 0
    for i in range(0, len(bids), BATCH_SIZE):
        batch = prepare_documents(bids[i : i + BATCH_SIZE])
        try:
            result = await collection.insert_many(batch, ordered=False)
            inserted += len(result.inserted_ids)
        except Exception as e:
            if "BulkWriteError" in type(e).__name__:
                inserted += e.details.get("nInserted", 0)
            else:
                print(f"  Error inserting batch: {e}")
    return inserted


async def main():
    random.seed(42)

    await init_mongo()

    products, by_category = await get_product_ids()
    if not products:
        print("No products found in DB. Please seed products first.")
        return

    print(f"Found {len(products)} products across {len(by_category)} categories")

    # Build product_id → category mapping and fetch units per category
    product_category = {p["_id"]: p["relatedCategory"] for p in products}
    units_by_category = await get_units_by_category(by_category.keys())

    # Clear old bids
    bids_collection = db.get_product_bids_collection()
    deleted = await bids_collection.delete_many({})
    print(f"Cleared {deleted.deleted_count} old product_bids")

    product_ids = [p["_id"] for p in products]
    total_needed = sum(cfg[1] for cfg in SCENARIO_CONFIG)

    # Billion-price scenarios must use unique product IDs to avoid mixing
    # drastically different price ranges in the same product's bid history.
    normal_needed = sum(cfg[1] for cfg in SCENARIO_CONFIG if cfg[3] < 1_000_000_000)
    if len(product_ids) < total_needed:
        print(f"Warning: need {total_needed} products but only have {len(product_ids)}.")
        if len(product_ids) < normal_needed:
            print("Will reuse product IDs for normal-price scenarios.")
            while len(product_ids) < normal_needed:
                product_ids.extend(product_ids[: normal_needed - len(product_ids)])
        if len(product_ids) < total_needed:
            print("Not enough unique products for billion-price scenarios — they will be skipped.")
            # Pad with None so the loop can detect and skip them
            product_ids.extend([None] * (total_needed - len(product_ids)))

    idx = 0
    total_bids = 0

    for scenario_name, count, generator_func, base_price in SCENARIO_CONFIG:
        scenario_bids = []
        for _ in range(count):
            pid = product_ids[idx]
            idx += 1
            if pid is None:
                continue
            cat_id = product_category.get(pid)
            unitCode, unitName = units_by_category.get(cat_id, ("PK", "пачка"))
            product_base = base_price * random.uniform(0.5, 3.0)
            bids = generator_func(pid, product_base, unitCode, unitName)
            scenario_bids.extend(bids)

        inserted = await bulk_insert(bids_collection, scenario_bids)
        total_bids += inserted
        print(f"  {scenario_name}: {count} products, {inserted} bids inserted")

    print(f"\nTotal: {total_bids} product_bids inserted for {idx} products")
    print(f"Period: {START_DATE.date()} — {END_DATE.date()}")


if __name__ == "__main__":
    asyncio.run(main())
