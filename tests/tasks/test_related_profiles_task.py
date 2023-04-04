from copy import deepcopy

from cron.related_profiles_task import run_task
from tests.integration.base import TEST_AUTH
from tests.integration.conftest import (
    get_fixture_json,
    api,
    db,
    category,
    product,
    profile,
    profile_without_criteria,
    create_criteria,
)


async def test_migrate_profiles(db, api, category, profile, product):

    profile_fixture = get_fixture_json("profile")
    criteria_fixture = get_fixture_json("criteria")

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
    resp = await api.put(
        f"/api/profiles/{profile_4_id}",
        json={"data": profile_data_4, "access": category["access"]},
        auth=TEST_AUTH,
    )
    assert resp.status == 201
    profile_data_4 = await resp.json()
    criteria = deepcopy(criteria_fixture)
    criteria["criteria"][0]["requirementGroups"][0]["requirements"][0]["expectedValue"] = "Одноразова1"
    profile_data_4 = await create_criteria(api, "profiles", profile_data_4, criteria)

    res = await run_task()

    resp = await api.get(f'/api/products/{product["data"]["id"]}')
    assert resp.status == 200
    resp_json = await resp.json()
    prod = resp_json["data"]
    assert prod["relatedProfiles"] == [profile["data"]["id"]]
