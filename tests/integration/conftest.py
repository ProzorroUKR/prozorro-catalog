from catalog.api import create_application
from catalog.db import flush_database, init_mongo, get_database
from json import loads
from .base import TEST_AUTH
from uuid import uuid4
import os.path
import pytest


def get_fixture_json(name):
    fixture_file = os.path.join("tests/fixtures", f"{name}.json")
    with open(fixture_file) as f:
        data = loads(f.read())
    return data


async def create_criteria(api, profile):
    criteria = get_fixture_json('criteria')
    for criterion in criteria["criteria"]:
        rgs = criterion.pop("requirementGroups")
        resp = await api.post(
            f"/api/profiles/{profile['data']['id']}/criteria",
            json={"data": criterion, "access": profile["access"]},
            auth=TEST_AUTH,
        )

        criterion_data = await resp.json()
        criterion_id = criterion_data["data"]["id"]
        for rg in rgs:
            reqs = rg.pop("requirements")
            rg_resp = await api.post(
                f"/api/profiles/{profile['data']['id']}/criteria/{criterion_id}/requirementGroups",
                json={"data": rg, "access": profile["access"]},
                auth=TEST_AUTH,
            )
            rg_data = await rg_resp.json()
            rg_id = rg_data["data"]["id"]
            await api.post(
                f"/api/profiles/{profile['data']['id']}/criteria/{criterion_id}/requirementGroups/{rg_id}/requirements",
                json={"data": reqs, "access": profile["access"]},
                auth=TEST_AUTH,
            )

    resp = await api.get(
        f"/api/profiles/{profile['data']['id']}",
        auth=TEST_AUTH,
    )
    data = await resp.json()
    data["access"] = profile["access"]
    return data


def set_requirements_to_responses(requirement_responses, profile):
    for item, rr in enumerate(requirement_responses):
        if item < 5:
            rr["requirement"] = profile["data"]["criteria"][item]["requirementGroups"][0]["requirements"][0]["id"]
        elif item == 5:
            rr["requirement"] = profile["data"]["criteria"][4]["requirementGroups"][1]["requirements"][0]["id"]
        elif item == 6:
            rr["requirement"] = profile["data"]["criteria"][4]["requirementGroups"][2]["requirements"][0]["id"]

@pytest.fixture
async def db(event_loop):
    try:
        await init_mongo()
        yield get_database()
    except Exception:
        await flush_database()


@pytest.fixture
async def api(event_loop, aiohttp_client):
    app = await aiohttp_client(create_application(on_cleanup=flush_database))
    app.get_fixture_json = get_fixture_json
    app.create_criteria = create_criteria
    return app


@pytest.fixture
async def category(api):
    data = get_fixture_json('category')
    resp = await api.put(
        f"/api/categories/{data['id']}",
        json={"data": data},
        auth=TEST_AUTH
    )
    assert resp.status == 201
    return await resp.json()


@pytest.fixture
async def profile(api, category):
    data = get_fixture_json('profile')
    profile_id = f'0000000-{category["data"]["id"]}'
    data['id'] = profile_id
    data['relatedCategory'] = category["data"]["id"]
    resp = await api.put(
        f"/api/profiles/{profile_id}",
        json={"data": data, "access": category["access"]},
        auth=TEST_AUTH,
    )
    assert resp.status == 201
    data = await resp.json()
    profile = await create_criteria(api, data)
    return profile


@pytest.fixture
async def product(api, profile):
    data = get_fixture_json('product')
    data['relatedProfile'] = profile["data"]["id"]
    set_requirements_to_responses(data["requirementResponses"], profile)

    resp = await api.post(
        "/api/products",
        json={"data": data, "access": profile["access"]},
        auth=TEST_AUTH,
    )
    assert resp.status == 201, await resp.json()
    return await resp.json()


@pytest.fixture
async def offer(api, product):
    data = get_fixture_json('offer')
    data['relatedProduct'] = product["data"]["id"]
    resp = await api.put(
        f"/api/offers/{uuid4().hex}",
        json={"data": data},
        auth=TEST_AUTH,
    )
    assert resp.status == 201, await resp.json()
    return await resp.json()


@pytest.fixture
async def vendor(api, category):
    data = get_fixture_json('vendor')
    data['categories'] = [{"id": category["data"]["id"]}]
    resp = await api.post(
        f"/api/vendors",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 201, result
    uid, access = result["data"]["id"], result["access"]

    patch_data = {"isActivated": True}
    resp = await api.patch(
        f'/api/vendors/{uid}?access_token={access["token"]}',
        json={"data": patch_data},
        auth=TEST_AUTH,
    )
    assert resp.status == 200
    return result


@pytest.fixture
async def vendor_product(api, vendor, profile):
    data = get_fixture_json('vendor_product')
    data['relatedProfile'] = profile["data"]["id"]
    set_requirements_to_responses(data["requirementResponses"], profile)

    resp = await api.post(
        f"/api/vendors/{vendor['data']['id']}/products?access_token={vendor['access']['token']}",
        json={"data": data},
        auth=TEST_AUTH,
    )
    assert resp.status == 201, await resp.json()
    return await resp.json()
