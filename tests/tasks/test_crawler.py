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
    assert inserted_bid["amount"] == 100.0
    assert inserted_bid["currency"] == "UAH"
    assert inserted_bid["valueAddedTaxIncluded"] is True

    from datetime import datetime, timedelta, timezone

    expected_date = datetime(2024, 1, 1, 10, 0, tzinfo=timezone(timedelta(hours=2)))
    inserted_date = datetime.fromisoformat(inserted_bid["date"])

    assert inserted_date.astimezone(timezone.utc) == expected_date.astimezone(timezone.utc)


@pytest.mark.asyncio
async def test_process_tender_inactive_bid(db):
    await flush_database()
    session = MagicMock()
    tender = deepcopy(get_fixture_json("tender"))
    tender["bids"][0]["status"] = "invalid"  # Not active

    await process_tender(session, tender)
    bids_count = await get_product_bids_collection().count_documents({})
    assert bids_count == 0
