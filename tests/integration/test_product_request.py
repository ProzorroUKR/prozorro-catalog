from datetime import timedelta

from catalog.utils import get_now
from catalog.doc_service import generate_test_url
from .base import TEST_AUTH
from .conftest import set_requirements_to_responses
from .utils import create_criteria


async def test_create_product_request_permission(api, category, contributor):
    test_request = api.get_fixture_json('product_request')
    category_id = category['data']['id']
    set_requirements_to_responses(test_request["product"]["requirementResponses"], category)
    test_request["product"]['relatedCategory'] = category_id
    resp = await api.post(
        f"/api/crowd-sourcing/contributors/{contributor['data']['id']}/requests",
        json={"data": test_request},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 401, result
    assert {'errors': ['Require access token']} == result


async def test_product_request_create(api, category, contributor):
    contributor, access = contributor["data"], contributor["access"]
    test_request = api.get_fixture_json('product_request')
    category_id = category['data']['id']
    set_requirements_to_responses(test_request["product"]["requirementResponses"], category)
    test_request["product"]['relatedCategory'] = category_id

    resp = await api.post(
        f"api/crowd-sourcing/contributors/{contributor['id']}/requests?access_token={access['token']}",
        json={"data": test_request},
        auth=TEST_AUTH,
    )
    result = await resp.json()

    assert resp.status == 201, result
    assert "data" in result
    data = result["data"]
    assert "owner" in data
    assert data["contributor_id"] == contributor["id"]

    # check generated data
    additional_fields = {k: v for k, v in data.items() if k not in test_request}
    assert set(additional_fields.keys()) == {'id', 'dateCreated', 'dateModified', 'owner', 'contributor_id'}


async def test_product_request_create_invalid_fields(api, category, contributor):
    contributor, access = contributor["data"], contributor["access"]
    resp = await api.post(
        f"/api/crowd-sourcing/contributors/{contributor['id']}/requests?access_token={access['token']}",
        json={"data": {}},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['field required: data.product']} == result

    data = api.get_fixture_json('product_request')
    category_id = category['data']['id']
    set_requirements_to_responses(data["product"]["requirementResponses"], category)
    data["product"]['relatedCategory'] = category_id
    data["documents"] = [
        {
            "title": "sign.p7s",
            "url": "http://public-docs-sandbox.prozorro.gov.ua/...",
            "hash": "md5:00000000000000000000000000000000",
            "format": "application/pk7s"
        }
    ]
    resp = await api.post(
        f"/api/crowd-sourcing/contributors/{contributor['id']}/requests?access_token={access['token']}",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['Can add document only from document service: data.documents.0.__root__']} == result

    data['documents'][0]['url'] = generate_test_url(data["documents"][0]["hash"])
    resp = await api.post(
        f"/api/crowd-sourcing/contributors/{contributor['id']}/requests?access_token={access['token']}",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['Document url signature is invalid: data.documents.0.__root__']} == result

    del data["documents"]
    data["product"]['relatedCategory'] = "some_id"
    resp = await api.post(
        f"/api/crowd-sourcing/contributors/{contributor['id']}/requests?access_token={access['token']}",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 404, result
    assert {'errors': ['Category not found']} == result

    data["product"]['relatedCategory'] = category_id
    del data["product"]["requirementResponses"]
    resp = await api.post(
        f"/api/crowd-sourcing/contributors/{contributor['id']}/requests?access_token={access['token']}",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['should be responded at least on one category requirement']} == result


async def test_product_request_in_banned_category(api, mock_agreement, contributor):
    contributor, access = contributor["data"], contributor["access"]

    # create ban without dueDate
    ban = api.get_fixture_json('ban')
    del ban["dueDate"]
    doc_hash = "0" * 32
    ban['documents'][0]['url'] = generate_test_url(doc_hash)
    ban['documents'][0]['hash'] = f"md5:{doc_hash}"
    resp = await api.post(
        f"api/crowd-sourcing/contributors/{contributor['id']}/bans",
        json={"data": ban},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 201, result

    # create category
    category_data = api.get_fixture_json('category')
    category_data["procuringEntity"]["identifier"]["id"] = ban["administrator"]["identifier"]["id"]
    category_data["id"] = f'{category_data["id"][:13]}-{ban["administrator"]["identifier"]["id"]}'
    resp = await api.put(
        f"/api/categories/{category_data['id']}",
        json={"data": category_data},
        auth=TEST_AUTH
    )
    assert resp.status == 201
    data = await resp.json()
    category = await create_criteria(api, "categories", data)

    test_request = api.get_fixture_json('product_request')
    category_id = category['data']['id']  # banned category
    set_requirements_to_responses(test_request["product"]["requirementResponses"], category)
    test_request["product"]['relatedCategory'] = category_id

    resp = await api.post(
        f"api/crowd-sourcing/contributors/{contributor['id']}/requests?access_token={access['token']}",
        json={"data": test_request},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['request for product with this relatedCategory is forbidden due to ban']} == result


async def test_product_request_in_banned_category_with_due_date(api, mock_agreement, contributor):
    contributor, access = contributor["data"], contributor["access"]

    # create ban without dueDate
    ban = api.get_fixture_json('ban')
    ban["dueDate"] = (get_now() + timedelta(days=10)).isoformat()
    doc_hash = "0" * 32
    ban['documents'][0]['url'] = generate_test_url(doc_hash)
    ban['documents'][0]['hash'] = f"md5:{doc_hash}"
    resp = await api.post(
        f"api/crowd-sourcing/contributors/{contributor['id']}/bans",
        json={"data": ban},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 201, result

    # create category
    category_data = api.get_fixture_json('category')
    category_data["procuringEntity"]["identifier"]["id"] = ban["administrator"]["identifier"]["id"]
    category_data["id"] = f'{category_data["id"][:13]}-{ban["administrator"]["identifier"]["id"]}'
    resp = await api.put(
        f"/api/categories/{category_data['id']}",
        json={"data": category_data},
        auth=TEST_AUTH
    )
    assert resp.status == 201
    data = await resp.json()
    category = await create_criteria(api, "categories", data)

    test_request = api.get_fixture_json('product_request')
    category_id = category['data']['id']  # banned category
    set_requirements_to_responses(test_request["product"]["requirementResponses"], category)
    test_request["product"]['relatedCategory'] = category_id

    resp = await api.post(
        f"api/crowd-sourcing/contributors/{contributor['id']}/requests?access_token={access['token']}",
        json={"data": test_request},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['request for product with this relatedCategory is forbidden due to ban']} == result


async def test_product_request_in_banned_category_with_expired_due_date(api, mock_agreement, contributor):
    contributor, access = contributor["data"], contributor["access"]

    # create ban without dueDate
    ban = api.get_fixture_json('ban')
    ban["dueDate"] = (get_now() - timedelta(days=10)).isoformat()
    doc_hash = "0" * 32
    ban['documents'][0]['url'] = generate_test_url(doc_hash)
    ban['documents'][0]['hash'] = f"md5:{doc_hash}"
    resp = await api.post(
        f"api/crowd-sourcing/contributors/{contributor['id']}/bans",
        json={"data": ban},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 201, result

    # create category
    category_data = api.get_fixture_json('category')
    category_data["procuringEntity"]["identifier"]["id"] = ban["administrator"]["identifier"]["id"]
    category_data["id"] = f'{category_data["id"][:13]}-{ban["administrator"]["identifier"]["id"]}'
    resp = await api.put(
        f"/api/categories/{category_data['id']}",
        json={"data": category_data},
        auth=TEST_AUTH
    )
    assert resp.status == 201
    data = await resp.json()
    category = await create_criteria(api, "categories", data)

    test_request = api.get_fixture_json('product_request')
    category_id = category['data']['id']  # banned category
    set_requirements_to_responses(test_request["product"]["requirementResponses"], category)
    test_request["product"]['relatedCategory'] = category_id

    resp = await api.post(
        f"api/crowd-sourcing/contributors/{contributor['id']}/requests?access_token={access['token']}",
        json={"data": test_request},
        auth=TEST_AUTH,
    )
    assert resp.status == 201
