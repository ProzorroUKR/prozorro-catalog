import asyncio
from copy import deepcopy
from uuid import uuid4
from unittest.mock import patch, AsyncMock
import pytest

import pydantic
print(pydantic.__version__)

from catalog.api import create_application
from catalog.db import flush_database, init_mongo, get_database, get_offers_collection, insert_object
from catalog.doc_service import generate_test_url
from .base import TEST_AUTH, TEST_AUTH_CPB
from .utils import get_fixture_json, create_profile, create_criteria


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def set_requirements_to_responses(requirement_responses, category):
    for item, rr in enumerate(requirement_responses):
        if "requirement" not in rr:
            rr["requirement"] = category["data"]["criteria"][0]["requirementGroups"][0]["requirements"][item]["title"]


@pytest.fixture
async def mock_agreement():
    data = get_fixture_json('category')
    with patch('catalog.state.category.validate_agreement') as m:
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
async def vendor(db, api):
    data = get_fixture_json('vendor')
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


@pytest.fixture
async def contributor(api):
    data = deepcopy(get_fixture_json('contributor'))
    data["contributor"]["identifier"]["id"] = "10037654"
    resp = await api.post(
        "/api/crowd-sourcing/contributors",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 201, result
    return result


@pytest.fixture
async def contributor_document(api, contributor):
    contributor = contributor["data"]
    doc_hash = "0" * 32
    doc_data = {
        "title": "name.doc",
        "url": generate_test_url(doc_hash),
        "hash": f"md5:{doc_hash}",
        "format": "application/msword",
    }
    resp = await api.post(
        f'/api/crowd-sourcing/contributors/{contributor["id"]}/documents',
        json={"data": doc_data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 201, result
    return result


@pytest.fixture
async def ban(api, contributor):
    contributor = contributor["data"]
    data = get_fixture_json('ban')
    doc_hash = "0" * 32
    data['documents'][0]['url'] = generate_test_url(doc_hash)
    data['documents'][0]['hash'] = f"md5:{doc_hash}"
    resp = await api.post(
        f'/api/crowd-sourcing/contributors/{contributor["id"]}/bans',
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 201, result
    return result


@pytest.fixture
async def ban_document(api, ban, contributor):
    contributor = contributor["data"]
    ban = ban["data"]
    doc_hash = "0" * 32
    doc_data = {
        "title": "name.doc",
        "url": generate_test_url(doc_hash),
        "hash": f"md5:{doc_hash}",
        "format": "application/msword",
    }
    resp = await api.post(
        f'/api/crowd-sourcing/contributors/{contributor["id"]}/bans/{ban["id"]}/documents',
        json={"data": doc_data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 201, result
    return result


@pytest.fixture
async def product_request(api, contributor, category):
    contributor = contributor["data"]
    test_request = get_fixture_json('product_request')
    category_id = category['data']['id']
    set_requirements_to_responses(test_request["product"]["requirementResponses"], category)
    test_request["product"]['relatedCategory'] = category_id

    resp = await api.post(
        f"api/crowd-sourcing/contributors/{contributor['id']}/requests",
        json={"data": test_request},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 201, result
    return result


@pytest.fixture
async def product_request_document(api, product_request):
    product_request = product_request["data"]
    doc_hash = "0" * 32
    doc_data = {
        "title": "name.doc",
        "url": generate_test_url(doc_hash),
        "hash": f"md5:{doc_hash}",
        "format": "application/msword",
    }
    resp = await api.post(
        f'/api/crowd-sourcing/requests/{product_request["id"]}/documents',
        json={"data": doc_data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 201, result
    return result


@pytest.fixture
async def vendor_ban(api, vendor):
    data = get_fixture_json('ban')
    del data["dueDate"]
    doc_hash = "0" * 32
    data['documents'][0]['url'] = generate_test_url(doc_hash)
    data['documents'][0]['hash'] = f"md5:{doc_hash}"
    resp = await api.post(
        f'/api/vendors/{vendor["data"]["id"]}/bans',
        json={"data": data},
        auth=TEST_AUTH_CPB,
    )
    result = await resp.json()
    assert resp.status == 201, result
    return result
