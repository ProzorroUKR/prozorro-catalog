from copy import deepcopy
from urllib.parse import quote
from uuid import uuid4

from catalog.db import get_prices_collection, get_product_bids_collection, insert_object
from catalog.utils import get_now


async def test_price_get_single(api, price):
    price_id = price["data"]["id"]
    resp = await api.get(f"/api/prices/{price_id}")
    assert resp.status == 200
    resp_json = await resp.json()
    assert resp_json["data"]["id"] == price_id
    assert resp_json["data"]["productId"] == "some-product-id"
    assert resp_json["data"]["sampleSize"] == 50
    assert "dateCreated" in resp_json["data"]
    assert "dateModified" in resp_json["data"]


async def test_price_not_found(api, db):
    resp = await api.get(f"/api/prices/{uuid4().hex}")
    assert resp.status == 404


PRICE_FEED_FIELDS = {
    "id",
    "productId",
    "dateCreated",
    "dateModified",
    "sampleSize",
    "lowerQuartile",
    "medianQuartile",
    "upperQuartile",
}


async def test_price_list_pagination(api, db):
    test_price = api.get_fixture_json("price")

    price_map = {}
    for i in range(11):
        price_copy = deepcopy(test_price)
        price_copy["id"] = price_id = uuid4().hex
        price_copy["dateModified"] = get_now().isoformat()
        price_copy["dateCreated"] = get_now().isoformat()

        await insert_object(get_prices_collection(), price_copy)

        resp = await api.get(f"/api/prices/{price_id}")
        assert resp.status == 200
        resp_json = await resp.json()
        assert resp_json["data"]["id"] == price_id

        price_map[price_id] = resp_json["data"]["dateModified"]

    offset = ""
    prev_resp_next = None
    while True:
        resp = await api.get("/api/prices?limit=5&offset=" + quote(offset))
        assert resp.status == 200
        resp_json = await resp.json()
        if len(resp_json["data"]) == 0:
            assert prev_resp_next == resp_json["next_page"]
            break
        assert "next_page" in resp_json
        prev_resp_next = resp_json["next_page"]
        assert "offset" in resp_json["next_page"]
        offset = resp_json["next_page"]["offset"]

        assert len(resp_json["data"]) <= 5
        prev = resp_json["data"][0]
        assert PRICE_FEED_FIELDS.issubset(prev.keys())
        assert price_map.pop(prev["id"]) == prev["dateModified"]
        for item in resp_json["data"][1:]:
            assert prev["dateModified"] < item["dateModified"]
            assert price_map.pop(item["id"]) == item["dateModified"]

    assert len(price_map) == 0


async def test_product_prices(api, product):
    product_id = product["data"]["id"]
    test_price = api.get_fixture_json("price")

    for i in range(3):
        price_copy = deepcopy(test_price)
        price_copy["id"] = uuid4().hex
        price_copy["productId"] = product_id
        price_copy["dateModified"] = get_now().isoformat()
        price_copy["dateCreated"] = get_now().isoformat()
        await insert_object(get_prices_collection(), price_copy)

    # insert a price for a different product
    other_price = deepcopy(test_price)
    other_price["id"] = uuid4().hex
    other_price["productId"] = uuid4().hex
    other_price["dateModified"] = get_now().isoformat()
    other_price["dateCreated"] = get_now().isoformat()
    await insert_object(get_prices_collection(), other_price)

    resp = await api.get(f"/api/products/{product_id}/prices")
    assert resp.status == 200
    resp_json = await resp.json()
    assert len(resp_json["data"]) == 3
    for item in resp_json["data"]:
        assert PRICE_FEED_FIELDS.issubset(item.keys())
        assert item["productId"] == product_id


async def test_product_prices_not_found(api, db):
    resp = await api.get(f"/api/products/{uuid4().hex}/prices")
    assert resp.status == 404


async def test_product_bid_unique_constraint(db):
    test_bid = {
        "id": uuid4().hex,
        "tenderId": "tender-unique-001",
        "bidId": "bid-unique-001",
        "itemId": "item-unique-001",
        "unit": {"code": "KGM", "name": "кілограм"},
        "date": "2024-01-15T10:00:00+02:00",
        "itemClassification": {
            "id": "33600000-6",
            "scheme": "ДК021",
            "description": "Фармацевтична продукція",
        },
        "lotValueStatus": "active",
        "dateModified": get_now().isoformat(),
        "dateCreated": get_now().isoformat(),
    }

    await insert_object(get_product_bids_collection(), test_bid)

    duplicate_bid = deepcopy(test_bid)
    duplicate_bid["id"] = uuid4().hex

    try:
        await insert_object(get_product_bids_collection(), duplicate_bid)
        assert False, "Should have raised an exception for duplicate"
    except Exception:
        pass
