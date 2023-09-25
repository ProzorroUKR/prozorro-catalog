from copy import deepcopy
from datetime import timedelta

from catalog.utils import get_now
from catalog.doc_service import generate_test_url
from .base import TEST_AUTH
from .conftest import set_requirements_to_responses
from .utils import create_criteria

request_review_data = {
    "administrator": {
        "identifier": {
            "id": "42574629",
            "scheme": "UA-EDR",
            "legalName_en": "STATE ENTERPRISE \"MEDICAL PROCUREMENT OF UKRAINE\"",
            "legalName_uk": "ДЕРЖАВНЕ ПІДПРИЄМСТВО \"МЕДИЧНІ ЗАКУПІВЛІ УКРАЇНИ\""
        }
    }
}


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


async def test_product_request_acception_validations(api, product_request):
    resp = await api.post(
        "api/crowd-sourcing/requests/some_id/accept",
        json={"data": request_review_data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 404, result
    assert {'errors': ['404: Not Found']} == result

    resp = await api.post(
        f"api/crowd-sourcing/requests/{product_request['data']['id']}/accept",
        json={"data": {}},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['field required: data.administrator']} == result

    invalid_data = deepcopy(request_review_data)
    invalid_data["administrator"]["identifier"]["id"] = "12121212"
    resp = await api.post(
        f"api/crowd-sourcing/requests/{product_request['data']['id']}/accept",
        json={"data": invalid_data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['must be one of market administrators: data.administrator.identifier']} == result


async def test_product_request_acception(api, product_request):
    resp = await api.post(
        f"api/crowd-sourcing/requests/{product_request['data']['id']}/accept",
        json={"data": request_review_data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 201, result
    assert "data" in result
    data = result["data"]
    assert "owner" in result["access"]
    assert "token" in result["access"]
    product_token = result["access"]["token"]
    product_id = data["product"]["id"]

    # check generated data
    additional_fields = {k: v for k, v in data.items() if k not in product_request["data"]}
    assert set(additional_fields.keys()) == {'acception'}
    assert "date" in data["acception"]

    for field_name in ("id", "dateModified", "owner"):
        assert field_name in data["product"].keys()

    # check product creation
    resp = await api.get(f"api/products/{data['product']['id']}")
    result = await resp.json()
    assert resp.status == 200, result
    assert "data" in result
    data = result["data"]
    for field_name in ("id", "dateModified", "owner", "dateCreated"):
        assert field_name in data.keys()

    # check access token by patching product
    patch_product = {
        "data": {
            "status": "hidden",
            "title": "Маски (приховані)"
        },
        "access": {"token": product_token},
    }
    resp = await api.patch(f'/api/products/{product_id}', json=patch_product, auth=TEST_AUTH)
    assert resp.status == 200
    resp_json = await resp.json()
    for key, patch_value in patch_product['data'].items():
        assert resp_json['data'][key] == patch_value


async def test_product_request_rejection_validations(api, product_request):
    rejection_data = deepcopy(request_review_data)
    rejection_data.update({"reason": "INVALID", "description": "Невірно заповнені дані"})
    resp = await api.post(
        "api/crowd-sourcing/requests/some_id/reject",
        json={"data": rejection_data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 404, result
    assert {'errors': ['404: Not Found']} == result

    resp = await api.post(
        f"api/crowd-sourcing/requests/{product_request['data']['id']}/reject",
        json={"data": {}},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    errors = [
        'field required: data.administrator',
        'field required: data.reason',
        'field required: data.description',
    ]
    assert {'errors': errors} == result

    rejection_data["administrator"]["identifier"]["id"] = "12121212"
    resp = await api.post(
        f"api/crowd-sourcing/requests/{product_request['data']['id']}/reject",
        json={"data": rejection_data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['must be one of market administrators: data.administrator.identifier']} == result


async def test_product_request_rejection(api, product_request):
    rejection_data = deepcopy(request_review_data)
    rejection_data.update({"reason": "INVALID", "description": "Невірно заповнені дані"})
    resp = await api.post(
        f"api/crowd-sourcing/requests/{product_request['data']['id']}/reject",
        json={"data": rejection_data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 201, result
    assert "data" in result
    assert "access" not in result
    data = result["data"]

    # check generated data
    additional_fields = {k: v for k, v in data.items() if k not in product_request["data"]}
    assert set(additional_fields.keys()) == {'rejection'}
    assert "date" in data["rejection"]


async def test_product_request_second_review(api, product_request):
    # first review
    resp = await api.post(
        f"api/crowd-sourcing/requests/{product_request['data']['id']}/accept",
        json={"data": request_review_data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 201, result

    # accept one more time
    resp = await api.post(
        f"api/crowd-sourcing/requests/{product_request['data']['id']}/accept",
        json={"data": request_review_data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['product request is already reviewed']} == result

    # reject already reviewed request
    rejection_data = deepcopy(request_review_data)
    rejection_data.update({"reason": "INVALID", "description": "Невірно заповнені дані"})
    resp = await api.post(
        f"api/crowd-sourcing/requests/{product_request['data']['id']}/reject",
        json={"data": rejection_data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['product request is already reviewed']} == result


async def test_product_request_get(api, product_request, contributor):
    product_request = product_request["data"]
    resp = await api.get(f'/api/crowd-sourcing/requests/{product_request["id"]}')
    assert resp.status == 200
    result = await resp.json()
    assert set(result.keys()) == {'data'}
    assert set(result["data"].keys()) == {'id', 'contributor_id', 'owner', 'dateCreated', 'dateModified', 'product'}
    assert contributor["data"]["owner"] == result["data"]["owner"]


async def test_product_request_list(api, product_request):
    product_request = product_request["data"]
    resp = await api.get('/api/crowd-sourcing/requests')
    assert resp.status == 200
    result = await resp.json()
    assert set(result.keys()) == {'data', 'next_page'}
    assert len(result["data"]) == 1
    assert set(result["data"][0].keys()) == {'dateModified', 'id'}
    assert result["data"][0]["id"] == product_request["id"]

    resp = await api.get('/api/crowd-sourcing/requests?opt_fields=product.relatedCategory,owner')
    assert resp.status == 200
    result = await resp.json()
    assert "relatedCategory" in result["data"][0]["product"]
    assert "owner" in result["data"][0]
