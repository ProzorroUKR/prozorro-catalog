from copy import deepcopy

from catalog.migrations.cs_13265_add_relatedCategory_to_products import migrate
from tests.integration.base import TEST_AUTH
from tests.integration.conftest import (
    get_fixture_json,
    api,
    db,
    category,
    profile,
    profile_without_criteria,
)


async def test_migrate_products(db, api, profile):

    # profile = profile["data"]
    product_fixture = get_fixture_json("product")

    product_data_1 = deepcopy(product_fixture)
    product_data_1["_id"] = "1" * 32
    product_data_1["relatedProfiles"] = [profile["data"]["id"]]
    await db.products.insert_one(product_data_1)

    product_data_2 = deepcopy(product_fixture)
    product_data_2["_id"] = "2" * 32
    product_data_2["relatedProfiles"] = [profile["data"]["id"]]
    await db.products.insert_one(product_data_2)

    product_data_3 = deepcopy(product_fixture)
    product_data_3["_id"] = "3" * 32
    product_data_3["relatedProfiles"] = [profile["data"]["id"]]
    await db.products.insert_one(product_data_3)
    counters = await migrate()

    assert counters.total_profiles == 1
    assert counters.total_products == 3
    assert counters.updated_products == 3
    assert counters.skipped_products == 0

    resp = await api.get(f'/api/products/{product_data_1["_id"]}')
    assert resp.status == 200
    resp_json = await resp.json()
    product_1 = resp_json["data"]

    assert product_1["relatedCategory"] == profile["data"]["relatedCategory"]

    resp = await api.get(f'/api/products/{product_data_2["_id"]}')
    assert resp.status == 200
    resp_json = await resp.json()
    product_2 = resp_json["data"]

    assert product_1["dateModified"] != product_2["dateModified"]

