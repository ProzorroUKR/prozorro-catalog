from json import loads
from random import randrange
import os

from .base import TEST_AUTH


def get_fixture_json(name):
    fixture_file = os.path.join("tests/fixtures", f"{name}.json")
    with open(fixture_file) as f:
        data = loads(f.read())
    return data


async def create_profile(api, category, custom_data=None):
    category_id = category["data"]["id"]
    data = get_fixture_json('profile')

    profile_id = f'{randrange(1000000, 9999999)}-{category_id}'
    data['id'] = profile_id
    data['relatedCategory'] = category_id
    if custom_data:
        data.update(custom_data)
    resp = await api.put(
        f"/api/profiles/{profile_id}",
        json={"data": data, "access": category["access"]},
        auth=TEST_AUTH,
    )
    assert resp.status == 201
    data = await resp.json()

    return data


async def create_criteria(api, obj_path, profile, criteria=None):
    if not criteria:
        criteria = get_fixture_json('criteria')

    for criterion in criteria["criteria"]:
        rgs = criterion.pop("requirementGroups")
        resp = await api.post(
            f"/api/{obj_path}/{profile['data']['id']}/criteria",
            json={"data": criterion, "access": profile["access"]},
            auth=TEST_AUTH,
        )

        criterion_data = await resp.json()
        criterion_id = criterion_data["data"][-1]["id"]
        for rg in rgs:
            reqs = rg.pop("requirements")
            rg_resp = await api.post(
                f"/api/{obj_path}/{profile['data']['id']}/criteria/{criterion_id}/requirementGroups",
                json={"data": rg, "access": profile["access"]},
                auth=TEST_AUTH,
            )
            rg_data = await rg_resp.json()
            rg_id = rg_data["data"]["id"]
            await api.post(
                f"/api/{obj_path}/{profile['data']['id']}/criteria/"
                f"{criterion_id}/requirementGroups/{rg_id}/requirements",
                json={"data": reqs, "access": profile["access"]},
                auth=TEST_AUTH,
            )

    resp = await api.get(
        f"/api/{obj_path}/{profile['data']['id']}",
        auth=TEST_AUTH,
    )
    data = await resp.json()
    data["access"] = profile["access"]
    return data
