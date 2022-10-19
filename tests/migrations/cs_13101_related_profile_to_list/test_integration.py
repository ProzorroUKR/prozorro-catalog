from copy import deepcopy

from catalog.migrations.cs_13101_related_profile_to_list import migrate
from tests.integration.base import TEST_AUTH
from tests.integration.conftest import (
    get_fixture_json,
    api,
    db,
)


async def test_migrate_products(db, api):

    product_fixture = get_fixture_json("product")

    product_data_1 = deepcopy(product_fixture)
    product_data_1["_id"] = "1" * 32
    product_data_1["relatedProfile"] = "0" * 32
    await db.products.insert_one(product_data_1)

    product_data_2 = deepcopy(product_fixture)
    product_data_2["_id"] = "2" * 32
    product_data_2["relatedProfiles"] = ["0" * 32]
    await db.products.insert_one(product_data_2)
    counters = await migrate()

    assert counters.total_products == 1
    assert counters.succeeded_products == 1
    assert counters.skipped_products == 0

    resp = await api.get(f'/api/products/{product_data_1["_id"]}')
    assert resp.status == 200
    resp_json = await resp.json()
    product = resp_json["data"]

    assert "relatedProfiles" in product
    assert "relatedProfile" in product
    assert product_data_1["relatedProfile"] == product["relatedProfiles"][0]

    resp = await api.get(f'/api/products/{product_data_1["_id"]}')
    assert resp.status == 200
    resp_json = await resp.json()
    product = resp_json["data"]
    resp = await api.get(f'/api/products/{product_data_2["_id"]}')
    assert "relatedProfiles" in product
    assert "relatedProfile" in product

    product = await db.products.find_one({"_id": product_data_2["_id"]})
    assert "relatedProfiles" in product
    assert "relatedProfile" not in product

