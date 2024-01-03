from copy import deepcopy
from datetime import timedelta

from aiohttp import BasicAuth
from freezegun import freeze_time

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


async def test_create_product_request_no_authorization(api, category, contributor):
    test_request = api.get_fixture_json('product_request')
    category_id = category['data']['id']
    set_requirements_to_responses(test_request["product"]["requirementResponses"], category)
    test_request["product"]['relatedCategory'] = category_id
    resp = await api.post(
        f"/api/crowd-sourcing/contributors/{contributor['data']['id']}/requests",
        json={"data": test_request},
    )
    result = await resp.json()
    assert resp.status == 401, result
    assert {'errors': ['Authorization header not found']} == result


async def test_create_product_request_permission(api, category, contributor):
    test_request = api.get_fixture_json('product_request')
    category_id = category['data']['id']
    set_requirements_to_responses(test_request["product"]["requirementResponses"], category)
    test_request["product"]['relatedCategory'] = category_id
    resp = await api.post(
        f"/api/crowd-sourcing/contributors/{contributor['data']['id']}/requests",
        json={"data": test_request},
        auth=BasicAuth(login="boo"),
    )
    result = await resp.json()
    assert resp.status == 403, result
    assert {'errors': ["Forbidden 'contributors' write operation"]} == result


async def test_product_request_create(api, category, contributor):
    contributor = contributor["data"]
    test_request = api.get_fixture_json('product_request')
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
    assert "data" in result
    data = result["data"]
    assert "owner" in data
    assert data["contributor_id"] == contributor["id"]

    # check generated data
    additional_fields = {k: v for k, v in data.items() if k not in test_request}
    assert set(additional_fields.keys()) == {'id', 'dateCreated', 'dateModified', 'owner', 'contributor_id'}


async def test_product_request_create_invalid_fields(api, category, contributor):
    contributor = contributor["data"]
    resp = await api.post(
        f"/api/crowd-sourcing/contributors/{contributor['id']}/requests",
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
        f"/api/crowd-sourcing/contributors/{contributor['id']}/requests",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['Can add document only from document service: data.documents.0.__root__']} == result

    data['documents'][0]['url'] = generate_test_url(data["documents"][0]["hash"])
    resp = await api.post(
        f"/api/crowd-sourcing/contributors/{contributor['id']}/requests",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['Document url signature is invalid: data.documents.0.__root__']} == result

    del data["documents"]

    data["product"]["classification"]["id"] = "0000000000"
    resp = await api.post(
        f"/api/crowd-sourcing/contributors/{contributor['id']}/requests",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': [
        'product classification should have the same digits at the beginning as in related category.'
    ]} == result

    data["product"]["classification"]["id"] = category["data"]["classification"]["id"]
    data["product"]['relatedCategory'] = "some_id"
    resp = await api.post(
        f"/api/crowd-sourcing/contributors/{contributor['id']}/requests",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 404, result
    assert {'errors': ['Category not found']} == result

    data["product"]['relatedCategory'] = category_id
    del data["product"]["requirementResponses"]
    resp = await api.post(
        f"/api/crowd-sourcing/contributors/{contributor['id']}/requests",
        json={"data": data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['should be responded at least on one category requirement']} == result


async def test_product_request_in_banned_category(api, mock_agreement, contributor):
    contributor = contributor["data"]

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
        f"api/crowd-sourcing/contributors/{contributor['id']}/requests",
        json={"data": test_request},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['request for product with this relatedCategory is forbidden due to ban']} == result


async def test_product_request_in_banned_category_with_due_date(api, mock_agreement, contributor):
    contributor = contributor["data"]

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
        f"api/crowd-sourcing/contributors/{contributor['id']}/requests",
        json={"data": test_request},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['request for product with this relatedCategory is forbidden due to ban']} == result


async def test_product_request_in_banned_category_with_expired_due_date(api, mock_agreement, contributor):
    contributor = contributor["data"]

    # create ban without dueDate
    ban = api.get_fixture_json('ban')
    ban["dueDate"] = (get_now() + timedelta(days=1)).isoformat()
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

    with freeze_time((get_now() + timedelta(days=2)).isoformat()):
        resp = await api.post(
            f"api/crowd-sourcing/contributors/{contributor['id']}/requests",
            json={"data": test_request},
            auth=TEST_AUTH,
        )
        assert resp.status == 201


async def test_product_request_acception_permission(api, product_request):
    resp = await api.post(
        f"api/crowd-sourcing/requests/{product_request['data']['id']}/accept",
        json={"data": request_review_data},
        auth=BasicAuth(login="boo"),
    )
    result = await resp.json()
    assert resp.status == 403, result
    assert {'errors': ["Forbidden 'category' write operation"]} == result


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
    assert data["dateModified"] == data["product"]["dateModified"] == data["acception"]["date"]

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


async def test_product_request_accept_if_category_id_diff_procuring_entity_identifier(api, contributor, mock_agreement):
    # create category 33190000-0000-425746299 with procuringEntity.identifier.id 42574629
    data = deepcopy(api.get_fixture_json('category'))
    data["id"] = "33190000-0000-425746299"
    resp = await api.put(
        f"/api/categories/{data['id']}",
        json={"data": data},
        auth=TEST_AUTH
    )
    assert resp.status == 201
    data = await resp.json()
    category = await create_criteria(api, "categories", data)

    # create product request with category ending with 425746299
    contributor = contributor["data"]
    test_request = api.get_fixture_json('product_request')
    category_id = category['data']['id']
    set_requirements_to_responses(test_request["product"]["requirementResponses"], category)
    test_request["product"]['relatedCategory'] = category_id

    resp = await api.post(
        f"api/crowd-sourcing/contributors/{contributor['id']}/requests",
        json={"data": test_request},
        auth=TEST_AUTH,
    )
    product_request = await resp.json()
    assert resp.status == 201, product_request

    # successfully accept product request: administrator.identifier.id == procuringEntity.identifier.id of category
    resp = await api.post(
        f"api/crowd-sourcing/requests/{product_request['data']['id']}/accept",
        json={"data": request_review_data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 201, result


async def test_product_request_rejection_permission(api, product_request):
    rejection_data = deepcopy(request_review_data)
    rejection_data.update({"reason": ["invalidTitle"], "description": "Невірно зазначена назва товару"})
    resp = await api.post(
        f"api/crowd-sourcing/requests/{product_request['data']['id']}/reject",
        json={"data": rejection_data},
        auth=BasicAuth(login="boo"),
    )
    result = await resp.json()
    assert resp.status == 403, result
    assert {'errors': ["Forbidden 'category' write operation"]} == result


async def test_product_request_rejection_validations(api, product_request):
    rejection_data = deepcopy(request_review_data)
    rejection_data.update({"reason": ["invalidTitle"], "description": "Невірно зазначена назва товару"})
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

    rejection_data = deepcopy(request_review_data)
    rejection_data.update({
        "reason": "invalidTitle",
        "description": "Невірно зазначена назва товару, необхідно виправити",
    })
    resp = await api.post(
        f"api/crowd-sourcing/requests/{product_request['data']['id']}/reject",
        json={"data": rejection_data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['value is not a valid list: data.reason']} == result

    rejection_data["reason"] = []
    resp = await api.post(
        f"api/crowd-sourcing/requests/{product_request['data']['id']}/reject",
        json={"data": rejection_data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['ensure this value has at least 1 items: data.reason']} == result

    rejection_data["reason"] = ["invalidTitle", "invalidCharacteristics", "invalidTitle"]
    resp = await api.post(
        f"api/crowd-sourcing/requests/{product_request['data']['id']}/reject",
        json={"data": rejection_data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': ['there are duplicated reasons: data.reason']} == result

    rejection_data["reason"] = ["invalidTitle", "some other reason"]
    resp = await api.post(
        f"api/crowd-sourcing/requests/{product_request['data']['id']}/reject",
        json={"data": rejection_data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {'errors': [
        "invalid value: 'some other reason'. Must be one of market/product_reject_reason.json keys: data.reason"
    ]} == result


async def test_product_request_rejection(api, product_request):
    rejection_data = deepcopy(request_review_data)
    rejection_data.update({"reason": ["invalidTitle"], "description": "Невірно зазначена назва товару"})
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
    assert data["dateModified"] == data["rejection"]["date"]


async def test_product_request_moderation_by_non_related_administrator(api, contributor, mock_agreement):
    # create category
    category_data = deepcopy(api.get_fixture_json('category'))
    category_data["id"] = category_data["procuringEntity"]["identifier"]["id"] = "33190000-0000-40996564"
    resp = await api.put(
        f"/api/categories/{category_data['id']}",
        json={"data": category_data},
        auth=TEST_AUTH
    )
    assert resp.status == 201
    data = await resp.json()
    category = await create_criteria(api, "categories", data)

    # create product request
    contributor = contributor["data"]
    test_request = api.get_fixture_json('product_request')
    category_id = category['data']['id']
    set_requirements_to_responses(test_request["product"]["requirementResponses"], category)
    test_request["product"]['relatedCategory'] = category_id

    resp = await api.post(
        f"api/crowd-sourcing/contributors/{contributor['id']}/requests",
        json={"data": test_request},
        auth=TEST_AUTH,
    )
    product_request = await resp.json()
    assert resp.status == 201, product_request

    # reject product request by another administrator
    rejection_data = deepcopy(request_review_data)
    rejection_data["administrator"]["identifier"]["id"] = "42574629"
    rejection_data.update({"reason": ["invalidTitle"], "description": "Невірно зазначена назва товару"})
    resp = await api.post(
        f"api/crowd-sourcing/requests/{product_request['data']['id']}/reject",
        json={"data": rejection_data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {"errors": ["only administrator who is related to product category can moderate product request."]} == result

    # accept product request by another administrator
    resp = await api.post(
        f"api/crowd-sourcing/requests/{product_request['data']['id']}/accept",
        json={"data": request_review_data},
        auth=TEST_AUTH,
    )
    result = await resp.json()
    assert resp.status == 400, result
    assert {"errors": ["only administrator who is related to product category can moderate product request."]} == result


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
    rejection_data.update({"reason": ["invalidTitle"], "description": "Невірно зазначена назва товару"})
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
