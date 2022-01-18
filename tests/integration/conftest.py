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


@pytest.fixture
async def db(loop):
    try:
        await init_mongo()
        yield get_database()
    except Exception:
        await flush_database()


@pytest.fixture
async def api(loop, aiohttp_client):
    app = await aiohttp_client(create_application(on_cleanup=flush_database))
    app.get_fixture_json = get_fixture_json
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
    assert resp.status == 201, await resp.json()
    return await resp.json()


@pytest.fixture
async def product(api, profile):
    data = get_fixture_json('product')
    data["id"] = '{}-{}-{}-000000'.format(
        data['classification']['id'][:4],
        data['brand']['name'][:4],
        data['identifier']['id'][:13]
    )
    data['relatedProfile'] = profile["data"]["id"]
    resp = await api.put(
        f"/api/products/{data['id']}",
        json={"data": data,
              "access": profile["access"]},
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
