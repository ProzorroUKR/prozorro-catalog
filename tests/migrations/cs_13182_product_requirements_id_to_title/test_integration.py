from copy import deepcopy

from catalog.migrations.cs_13182_product_requirements_id_to_title import migrate
from tests.integration.base import TEST_AUTH
from tests.integration.conftest import (
    get_fixture_json,
    api,
    db,
    category,
    profile,
)


def set_requirements_to_responses(requirement_responses, profile):
    for item, rr in enumerate(requirement_responses):
        if item < 5:
            rr["requirement"] = profile["data"]["criteria"][item]["requirementGroups"][0]["requirements"][0]["id"]
        elif item == 5:
            rr["requirement"] = profile["data"]["criteria"][4]["requirementGroups"][1]["requirements"][0]["id"]
        elif item == 6:
            rr["requirement"] = profile["data"]["criteria"][4]["requirementGroups"][2]["requirements"][0]["id"]


async def test_migrate_products(db, api, profile):

    # profile = profile["data"]
    product_fixture = get_fixture_json("product")

    product_data_1 = deepcopy(product_fixture)
    product_data_1["_id"] = "1" * 32
    product_data_1["relatedProfiles"] = [profile["data"]["id"]]
    set_requirements_to_responses(product_data_1["requirementResponses"], profile)
    await db.products.insert_one(product_data_1)

    product_data_2 = deepcopy(product_fixture)
    product_data_2["_id"] = "2" * 32
    product_data_2["relatedProfiles"] = [profile["data"]["id"]]
    del product_data_2["requirementResponses"]
    await db.products.insert_one(product_data_2)

    product_data_3 = deepcopy(product_fixture)
    product_data_3["_id"] = "3" * 32
    product_data_3["relatedProfiles"] = [profile["data"]["id"]]
    set_requirements_to_responses(product_data_3["requirementResponses"], profile)
    await db.products.insert_one(product_data_3)
    counters = await migrate()

    assert counters.total_products == 3
    assert counters.updated_products == 2
    assert counters.skipped_products == 1
    assert counters.responses == 14

    resp = await api.get(f'/api/products/{product_data_1["_id"]}')
    assert resp.status == 200
    resp_json = await resp.json()
    product = resp_json["data"]

    assert product["requirementResponses"][0]["requirement"] == \
           profile["data"]["criteria"][0]["requirementGroups"][0]["requirements"][0]["title"]
