from uuid import uuid4
from unittest.mock import patch, AsyncMock
import pytest

from catalog.api import create_application
from catalog.db import flush_database, init_mongo, get_database, get_offers_collection, insert_object
from catalog.doc_service import generate_test_url
from .base import TEST_AUTH
from .utils import get_fixture_json, create_profile, create_criteria


def set_requirements_to_responses(requirement_responses, category):
    for item, rr in enumerate(requirement_responses):
        rr["requirement"] = category["data"]["criteria"][0]["requirementGroups"][0]["requirements"][item]["title"]


@pytest.fixture
async def mock_agreement():
    data = get_fixture_json('category')
    with patch('catalog.state.category.CategoryState.validate_agreement') as m:
        m.return_value = AsyncMock()
        yield m


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
async def category(api, mock_agreement):
    data = get_fixture_json('category')
    resp = await api.put(
        f"/api/categories/{data['id']}",
        json={"data": data},
        auth=TEST_AUTH
    )
    assert resp.status == 201
    data = await resp.json()
    category = await create_criteria(api, "categories", data)
    return category


@pytest.fixture
async def profile_without_criteria(api, category):
    data = await create_profile(api, category)
    return data


@pytest.fixture
async def profile(api, profile_without_criteria):
    profile = await create_criteria(api, "profiles", profile_without_criteria)
    return profile


@pytest.fixture
async def product(api, category):
    data = get_fixture_json('product')
    data['relatedCategory'] = category["data"]["id"]
    set_requirements_to_responses(data["requirementResponses"], category)

    resp = await api.post(
        "/api/products",
        json={"data": data, "access": category["access"]},
        auth=TEST_AUTH,
    )
    assert resp.status == 201
    return await resp.json()


@pytest.fixture
async def offer(db, api, product):
    data = get_fixture_json('offer')
    data['relatedProduct'] = product["data"]["id"]
    data['id'] = uuid4().hex
    offer_id = await insert_object(get_offers_collection(), data)
    resp = await api.get(f"/api/offers/{offer_id}")
    assert resp.status == 200, await resp.json()
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
async def vendor_product(api, vendor, category, profile):
    data = get_fixture_json('vendor_product')
    data['relatedCategory'] = category["data"]["id"]
    set_requirements_to_responses(data["requirementResponses"], category)

    resp = await api.post(
        f"/api/vendors/{vendor['data']['id']}/products?access_token={vendor['access']['token']}",
        json={"data": data},
        auth=TEST_AUTH,
    )
    assert resp.status == 201, await resp.json()
    return await resp.json()


@pytest.fixture
async def vendor_document(api, vendor, profile):
    vendor, access = vendor["data"], vendor["access"]
    doc_hash = "0" * 32
    doc_data = {
        "title": "name.doc",
        "url": generate_test_url(doc_hash),
        "hash": f"md5:{doc_hash}",
        "format": "application/msword",
    }
    resp = await api.post(
        f'/api/vendors/{vendor["id"]}/documents',
        json={
            "data": doc_data,
            "access": access,
        },
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 201, result
    return result

