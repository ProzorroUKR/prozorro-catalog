from copy import deepcopy
from datetime import timedelta

import pytest

from catalog.db import flush_database, get_prices_collection, get_product_bids_collection, insert_object
from catalog.prices import calculate_price, calculate_price_for_product
from catalog.utils import get_now
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
        bid.update(
            {
                "id": f"bid-d1-{i}",
                "productId": product_id,
                "date": (day1 + timedelta(hours=i)).isoformat(),
                "tenderId": f"tender-d1-{i}",
                "bidId": f"bid-d1-{i}",
                "itemId": f"item-d1-{i}",
                "currency": "UAH",
                "valueAddedTaxIncluded": False,
            }
        )
        bid["amount"] = amount
        await insert_object(get_product_bids_collection(), bid)

    # Add some bids that should be ignored
    ignored_bid = deepcopy(bid_fixture)
    ignored_bid.update(
        {
            "id": "bid-ignored-1",
            "productId": product_id,
            "date": (day1).isoformat(),
            "currency": "USD",
            "valueAddedTaxIncluded": False,
            "amount": 10000,
            "tenderId": "tender-ignored-1",
            "bidId": "bid-ignored-1",
            "itemId": "item-ignored-1",
        }
    )
    await insert_object(get_product_bids_collection(), ignored_bid)

    ignored_bid2 = deepcopy(bid_fixture)
    ignored_bid2.update(
        {
            "id": "bid-ignored-2",
            "productId": product_id,
            "date": (day1).isoformat(),
            "currency": "UAH",
            "valueAddedTaxIncluded": True,
            "amount": 20000,
            "tenderId": "tender-ignored-2",
            "bidId": "bid-ignored-2",
            "itemId": "item-ignored-2",
        }
    )
    await insert_object(get_product_bids_collection(), ignored_bid2)

    amounts2 = [1000, 2000, 3000]
    for i, amount in enumerate(amounts2):
        bid = deepcopy(bid_fixture)
        bid.update(
            {
                "id": f"bid-d2-{i}",
                "productId": product_id,
                "date": (day2 + timedelta(hours=i)).isoformat(),
                "tenderId": f"tender-d2-{i}",
                "bidId": f"bid-d2-{i}",
                "itemId": f"item-d2-{i}",
                "currency": "UAH",
                "valueAddedTaxIncluded": False,
            }
        )
        bid["amount"] = amount
        print(f"Inserting bid: {bid}")  # --- IGNORE ---
        await insert_object(get_product_bids_collection(), bid)

    inserted_ids = await calculate_price_for_product(product_id)
    assert len(inserted_ids) == 2

    # [100, 200, 300, 400, 500], n=5
    # The ignored bids (USD or VAT=True) should not affect these quartiles
    price1 = await get_prices_collection().find_one(
        {"productId": product_id, "date": {"$lt": (day2.replace(hour=0, minute=0, second=0, microsecond=0)).isoformat()}}
    )
    assert price1 is not None
    assert price1["sampleSize"] == 5
    assert float(price1["lowerQuartile"]) == 150.0
    assert float(price1["medianQuartile"]) == 300.0
    assert float(price1["upperQuartile"]) == 450.0
    assert price1["currency"] == "UAH"
    assert price1["valueAddedTaxIncluded"] is False

    # [100, 200, 300, 400, 500, 1000, 2000, 3000], n=8
    price2 = await get_prices_collection().find_one(
        {"productId": product_id, "date": {"$gte": (day2.replace(hour=0, minute=0, second=0, microsecond=0)).isoformat()}}
    )
    assert price2 is not None
    assert price2["sampleSize"] == 8
    assert float(price2["lowerQuartile"]) == 225.0
    assert float(price2["medianQuartile"]) == 450.0
    assert float(price2["upperQuartile"]) == 1750.0
    assert price2["currency"] == "UAH"
    assert price2["valueAddedTaxIncluded"] is False


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
        bid.update(
            {
                "id": f"bid-inc-d1-{i}",
                "productId": product_id,
                "date": (day1 + timedelta(hours=i)).isoformat(),
                "dateCreated": (now + timedelta(hours=i)).isoformat(),
                "tenderId": f"tender-inc-d1-{i}",
                "bidId": f"bid-inc-d1-{i}",
                "itemId": f"item-inc-d1-{i}",
            }
        )
        bid["amount"] = amount
        await insert_object(get_product_bids_collection(), bid)

    await calculate_price()
    prices_count = await get_prices_collection().count_documents({"productId": product_id})
    assert prices_count == 1

    day2 = now - timedelta(days=1)
    amounts2 = [1000, 2000]
    for i, amount in enumerate(amounts2):
        bid = deepcopy(bid_fixture)
        bid.update(
            {
                "id": f"bid-inc-d2-{i}",
                "productId": product_id,
                "date": (day2 + timedelta(hours=i)).isoformat(),
                "dateCreated": (now + timedelta(hours=i)).isoformat(),
                "tenderId": f"tender-inc-d2-{i}",
                "bidId": f"bid-inc-d2-{i}",
                "itemId": f"item-inc-d2-{i}",
            }
        )
        bid["amount"] = amount
        await insert_object(get_product_bids_collection(), bid)

    await calculate_price()
    prices_count = await get_prices_collection().count_documents({"productId": product_id})
    assert prices_count == 2


@pytest.mark.asyncio
async def test_calculate_price_ignored_bids(db):
    await flush_database()

    product_id = "test-product-ignored"
    now = get_now()
    day1 = now - timedelta(days=2)

    bid_fixture = get_fixture_json("product_bid")

    # Bid with different currency
    bid_usd = deepcopy(bid_fixture)
    bid_usd.update(
        {
            "id": "bid-usd",
            "productId": product_id,
            "date": (day1).isoformat(),
            "currency": "USD",
            "valueAddedTaxIncluded": False,
            "amount": 100,
            "tenderId": "tender-usd",
            "bidId": "bid-usd",
            "itemId": "item-usd",
        }
    )
    await insert_object(get_product_bids_collection(), bid_usd)

    # Bid with VAT included
    bid_vat = deepcopy(bid_fixture)
    bid_vat.update(
        {
            "id": "bid-vat",
            "productId": product_id,
            "date": (day1 + timedelta(hours=1)).isoformat(),
            "currency": "UAH",
            "valueAddedTaxIncluded": True,
            "amount": 120,
            "tenderId": "tender-vat",
            "bidId": "bid-vat",
            "itemId": "item-vat",
        }
    )
    await insert_object(get_product_bids_collection(), bid_vat)

    inserted_ids = await calculate_price_for_product(product_id)
    assert len(inserted_ids) == 0

    prices_count = await get_prices_collection().count_documents({"productId": product_id})
    assert prices_count == 0
