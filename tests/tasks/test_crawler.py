from copy import deepcopy
from unittest.mock import MagicMock

import pytest

from catalog.crawler import process_tender
from catalog.db import flush_database, get_product_bids_collection
from tests.utils import get_fixture_json


@pytest.mark.asyncio
async def test_process_tender_valid(db):
    await flush_database()
    session = MagicMock()
    tender = deepcopy(get_fixture_json("tender"))
    
    await process_tender(session, tender)
    
    bids_count = await get_product_bids_collection().count_documents({})
    assert bids_count == 1
    
    inserted_bid = await get_product_bids_collection().find_one({"tenderId": tender["id"]})
    assert inserted_bid is not None
    assert inserted_bid["productId"] == "product-1"
    assert inserted_bid["unit"]["value"]["amount"] == 100.0

    from datetime import datetime, timedelta, timezone
    expected_date = datetime(2024, 1, 1, 10, 0, tzinfo=timezone(timedelta(hours=2)))
    
    assert inserted_bid["date"].replace(tzinfo=timezone.utc) == expected_date.astimezone(timezone.utc)

@pytest.mark.asyncio
async def test_process_tender_invalid_method(db):
    await flush_database()
    session = MagicMock()
    tender = deepcopy(get_fixture_json("tender"))
    tender["procurementMethodType"] = "belowThreshold" # Not priceQuotation
    
    await process_tender(session, tender)
    bids_count = await get_product_bids_collection().count_documents({})
    assert bids_count == 0

@pytest.mark.asyncio
async def test_process_tender_inactive_bid(db):
    await flush_database()
    session = MagicMock()
    tender = deepcopy(get_fixture_json("tender"))
    tender["bids"][0]["status"] = "invalid" # Not active
    
    await process_tender(session, tender)
    bids_count = await get_product_bids_collection().count_documents({})
    assert bids_count == 0

@pytest.mark.asyncio
async def test_process_tender_missing_award_period(db):
    await flush_database()
    session = MagicMock()
    tender = deepcopy(get_fixture_json("tender"))
    del tender["awardPeriod"]
    
    await process_tender(session, tender)
    bids_count = await get_product_bids_collection().count_documents({})
    assert bids_count == 0
