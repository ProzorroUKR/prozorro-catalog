from copy import deepcopy
from datetime import timedelta

import pytest

from catalog.db import flush_database, get_prices_collection, get_product_bids_collection, insert_object
from catalog.utils import get_now
from cron.calculate_price import calculate_price, calculate_price_for_product
from tests.utils import get_fixture_json


@pytest.mark.asyncio
async def test_calculate_price_empty_db(db):
    await flush_database()

    await calculate_price()
    prices_count = await get_prices_collection().count_documents({})
    assert prices_count == 0

@pytest.mark.asyncio
async def test_calculate_price_for_product(db):
    await flush_database()

    product_id = "test-product-1"
    
    now = get_now()
    day1 = now - timedelta(days=2)
    day2 = now - timedelta(days=1)
    
    bid_fixture = get_fixture_json("product_bid")

    amounts1 = [100, 200, 300, 400, 500]
    for i, amount in enumerate(amounts1):
        bid = deepcopy(bid_fixture)
        bid.update({
            "id": f"bid-d1-{i}",
            "productId": product_id,
            "date": day1 + timedelta(hours=i),
            "tenderId": f"tender-d1-{i}",
            "bidId": f"bid-d1-{i}",
            "itemId": f"item-d1-{i}",
        })
        bid["unit"]["value"]["amount"] = amount
        await insert_object(get_product_bids_collection(), bid)

    amounts2 = [1000, 2000, 3000]
    for i, amount in enumerate(amounts2):
        bid = deepcopy(bid_fixture)
        bid.update({
            "id": f"bid-d2-{i}",
            "productId": product_id,
            "date": day2 + timedelta(hours=i),
            "tenderId": f"tender-d2-{i}",
            "bidId": f"bid-d2-{i}",
            "itemId": f"item-d2-{i}",
        })
        bid["unit"]["value"]["amount"] = amount
        await insert_object(get_product_bids_collection(), bid)

    inserted_ids = await calculate_price_for_product(product_id)
    assert len(inserted_ids) == 2
    
    # [100, 200, 300, 400, 500], n=5
    price1 = await get_prices_collection().find_one({"productId": product_id, "date": {"$lt": day2.replace(hour=0, minute=0, second=0, microsecond=0)}})
    assert price1 is not None
    assert price1["sampleSize"] == 5
    assert float(price1["lowerQuartile"]) == 150.0
    assert float(price1["medianQuartile"]) == 300.0
    assert float(price1["upperQuartile"]) == 450.0

    # [100, 200, 300, 400, 500, 1000, 2000, 3000], n=8
    price2 = await get_prices_collection().find_one({"productId": product_id, "date": {"$gte": day2.replace(hour=0, minute=0, second=0, microsecond=0)}})
    assert price2 is not None
    assert price2["sampleSize"] == 8
    assert float(price2["lowerQuartile"]) == 225.0
    assert float(price2["medianQuartile"]) == 450.0
    assert float(price2["upperQuartile"]) == 1750.0

@pytest.mark.asyncio
async def test_calculate_price_incrementality(db):
    await flush_database()

    product_id = "test-product-2"
    now = get_now()
    day1 = now - timedelta(days=2)
    
    bid_fixture = get_fixture_json("product_bid")

    amounts1 = [100, 200, 300, 400, 500]
    for i, amount in enumerate(amounts1):
        bid = deepcopy(bid_fixture)
        bid.update({
            "id": f"bid-inc-d1-{i}",
            "productId": product_id,
            "date": day1 + timedelta(hours=i),
            "tenderId": f"tender-inc-d1-{i}",
            "bidId": f"bid-inc-d1-{i}",
            "itemId": f"item-inc-d1-{i}",
        })
        bid["unit"]["value"]["amount"] = amount
        await insert_object(get_product_bids_collection(), bid)

    await calculate_price()
    prices_count = await get_prices_collection().count_documents({"productId": product_id})
    assert prices_count == 1
    
    day2 = now - timedelta(days=1)
    amounts2 = [1000, 2000]
    for i, amount in enumerate(amounts2):
        bid = deepcopy(bid_fixture)
        bid.update({
            "id": f"bid-inc-d2-{i}",
            "productId": product_id,
            "date": day2 + timedelta(hours=i),
            "tenderId": f"tender-inc-d2-{i}",
            "bidId": f"bid-inc-d2-{i}",
            "itemId": f"item-inc-d2-{i}",
        })
        bid["unit"]["value"]["amount"] = amount
        await insert_object(get_product_bids_collection(), bid)

    await calculate_price()
    prices_count = await get_prices_collection().count_documents({"productId": product_id})
    assert prices_count == 2
