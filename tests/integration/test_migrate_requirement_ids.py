from .base import TEST_AUTH
from migrations.cs_12095_hash_requirement_ids import migrate, get_new_responses
from hashlib import md5
from unittest.mock import patch, call
from time import sleep
from copy import deepcopy
import asyncio


async def test_on_fixtures(db, profile, product):

    with patch("migrations.cs_12095_hash_requirement_ids.logger") as logger:
        await migrate()
    stats = {'requirements': 7, 'profiles': 1, 'responses': 7, 'products': 1, 'total_profiles': 1}
    assert logger.info.call_args_list == [call("Start migration"), call(f"Finished. Stats: {stats}")]

    # test profiles
    profiles = await db.profiles.find({}).to_list(None)
    assert len(profiles) == 1
    assert profiles[0]["_id"] == profile["data"]["id"]
    assert len(profile["data"]["criteria"]) == len(profiles[0]["criteria"])

    for before, after in zip(
        (r for c in profile["data"]["criteria"] for g in c["requirementGroups"] for r in g["requirements"]),
        (r for c in profiles[0]["criteria"] for g in c["requirementGroups"] for r in g["requirements"]),
    ):
        expected_id = md5(f"{profile['data']['id']} {before['id']}".encode()).hexdigest()
        assert after["id"] == expected_id

    # test products
    products = await db.products.find({}).to_list(None)
    assert len(products) == 1
    assert products[0]["_id"] == product["data"]["id"]
    assert products[0]["relatedProfile"] == profile["data"]["id"]
    assert len(product["data"]["requirementResponses"]) == len(products[0]["requirementResponses"])

    for before, after in zip(
        (r for r in product["data"]["requirementResponses"]),
        (r for r in products[0]["requirementResponses"]),
    ):
        expected_id = md5(f"{profile['data']['id']} {before['requirement']}".encode()).hexdigest()
        assert after["requirement"] == expected_id

    # run again
    with patch("migrations.cs_12095_hash_requirement_ids.logger") as logger:
        await migrate()

    stats = {"skipped_profiles": 1, "total_profiles": 1}
    assert logger.info.call_args_list == [call("Start migration"), call(f"Finished. Stats: {stats}")]


additional_criteria = {
    "code": "OCDS-WHATEVER",
    "description": "Спосіб використання (одноразова або багаторазова)",
    "id": "00099",
    "requirementGroups": [
        {
            "description": "Спосіб використання - одноразова",
            "id": "0009999",
            "requirements": [
                {
                    "dataType": "string",
                    "expectedValue": "одноразова",
                    "id": "000099999999",
                    "title": "Одноразова"
                }
            ]
        }
    ],
    "title": "Спосіб використання"
}


async def test_transaction(db, profile, api):

    # sleep calls ensure that profile update is made during it's migration
    # so without transaction updated requirement remain its id
    def slow_get_new_responses(*args, **kwargs):
        sleep(0.2)
        return get_new_responses(*args, **kwargs)

    async def update_profile():
        sleep(0.1)
        profile_id = profile["data"]["id"]

        data = {"criteria": deepcopy(profile["data"]["criteria"])}
        data["criteria"].append(additional_criteria)
        resp = await api.patch(f'/api/profiles/{profile_id}',
                               json={"data": data,
                                     "access": profile["access"]},
                               auth=TEST_AUTH)
        assert 200 == resp.status

    with patch("migrations.cs_12095_hash_requirement_ids.logger") as logger:
        with patch("migrations.cs_12095_hash_requirement_ids.get_new_responses", slow_get_new_responses):
            await asyncio.gather(
                migrate(),
                update_profile()
            )

    stats = {'requirements': 8,  # with an additional item
             'profiles': 1,
             'total_profiles': 1}
    assert logger.info.call_args_list == [
        call('Start migration'),
        call(f"Finished. Stats: {stats}")
    ]
