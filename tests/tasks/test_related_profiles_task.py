from copy import deepcopy

from cron.related_profiles_task import run_task
from tests.integration.base import TEST_AUTH
from tests.integration.utils import create_criteria
from tests.integration.conftest import (
    get_fixture_json,
    api,
    db,
    category,
    product,
    profile,
    mock_agreement,
    profile_without_criteria,
)


async def test_migrate_profiles(db, api, category, profile, product):

    profile_fixture = get_fixture_json("profile")
    product_fixture = get_fixture_json("product")

    product_without_responses = deepcopy(product_fixture)
    product_without_responses["_id"] = "1" * 32
    product_without_responses["relatedCategory"] = category["data"]["id"]
    del product_without_responses["requirementResponses"]
    await db.products.insert_one(product_without_responses)

    product_with_not_all_responses = deepcopy(product_fixture)
    product_with_not_all_responses["_id"] = "2" * 32
    product_with_not_all_responses["relatedCategory"] = category["data"]["id"]
    req_responses = deepcopy(product["data"]["requirementResponses"])
    product_with_not_all_responses["requirementResponses"] = req_responses[2:]
    await db.products.insert_one(product_with_not_all_responses)

    #
    # profile_data_1 = deepcopy(profile_fixture)
    # profile_data_1["_id"] = "1" * 32
    # profile_data_1["unit"] = {"unit":  "unit"}
    # await db.profiles.insert_one(profile_data_1)

    profile_data_2 = deepcopy(profile_fixture)
    profile_data_2["_id"] = "2" * 32
    profile_data_2["value"] = "value"
    profile_data_2["relatedCategory"] = profile["data"]["relatedCategory"]
    await db.profiles.insert_one(profile_data_2)

    profile_data_3 = deepcopy(profile_fixture)
    profile_3_id = "3" * 32
    profile_data_3['id'] = profile_3_id
    profile_data_3['relatedCategory'] = category["data"]["id"]
    resp = await api.put(
        f"/api/profiles/{profile_3_id}",
        json={"data": profile_data_3, "access": category["access"]},
        auth=TEST_AUTH,
    )
    assert resp.status == 201

    profile_data_4 = deepcopy(profile_fixture)
    profile_4_id = "4" * 32
    profile_data_4['id'] = profile_4_id
    profile_data_4['relatedCategory'] = category["data"]["id"]
    criteria = deepcopy(profile["data"]["criteria"])
    criteria[0]["requirementGroups"][0]["requirements"][0]["expectedValues"] = ["Одноразова1"]
    profile_data_4['criteria'] = criteria
    await db.profiles.insert_one(profile_data_4)

    res = await run_task()

    resp = await api.get(f'/api/products/{product["data"]["id"]}')
    assert resp.status == 200
    resp_json = await resp.json()
    prod = resp_json["data"]
    for criterion in profile_data_4["criteria"]:
        for rg in criterion["requirementGroups"]:
            req = [req["title"] for req in rg["requirements"]]
    assert prod["relatedProfiles"] == [profile["data"]["id"]]

    resp = await api.get(f'/api/products/{product_without_responses["_id"]}')
    assert resp.status == 200
    resp_json = await resp.json()
    prod = resp_json["data"]
    assert "requirementResponses" not in prod
    assert "relatedProfiles" not in prod

    resp = await api.get(f'/api/products/{product_with_not_all_responses["_id"]}')
    assert resp.status == 200
    resp_json = await resp.json()
    prod = resp_json["data"]
    assert "requirementResponses" in prod
    assert "relatedProfiles" not in prod
