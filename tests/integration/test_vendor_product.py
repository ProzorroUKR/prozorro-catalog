from copy import deepcopy
from datetime import datetime
from unittest.mock import AsyncMock, patch

from catalog.doc_service import generate_test_url
from catalog.models.product import VendorProductIdentifierScheme
from catalog.utils import get_now

from .base import TEST_AUTH, TEST_AUTH_CPB
from .conftest import set_requirements_to_responses
from .utils import create_criteria, create_profile


async def test_vendor_product_create(api, vendor, category, profile):
    category_id = category['data']['id']
    category_token = category['access']['token']

    vendor_token = vendor['access']['token']
    vendor = vendor['data']

    test_product = api.get_fixture_json('vendor_product')
    test_product['relatedCategory'] = category_id
    set_requirements_to_responses(test_product['requirementResponses'], category)

    resp = await api.post(
        '/api/vendors/some_vendor/products',
        json={"data": test_product},
        auth=TEST_AUTH,
    )
    assert resp.status == 404

    resp = await api.post(
        f'/api/vendors/{vendor["id"]}/products',
        json={"data": test_product},
        auth=TEST_AUTH,
    )
    assert resp.status == 401
    result = await resp.json()
    assert result == {'errors': ['Require access token']}

    resp = await api.post(
        f'/api/vendors/{vendor["id"]}/products?access_token={vendor_token}',
        json={'data': test_product},
        auth=TEST_AUTH,
    )

    # assert resp.status == 201
    result = await resp.json()
    product_data = result['data']
    assert 'data' in result
    # assert "access" in result
    assert 'vendor' in product_data
    assert product_data['identifier']['scheme'] == VendorProductIdentifierScheme.ean_13
    assert vendor['id'] == product_data['vendor']['id']
    assert vendor['vendor']['name'] == product_data['vendor']['name']
    assert vendor['vendor']['identifier'] == product_data['vendor']['identifier']
    assert product_data['expirationDate'] == datetime(
        year=get_now().year, month=12, day=31, hour=23, minute=59, second=59, tzinfo=get_now().tzinfo,
    ).isoformat()

    resp = await api.get('/api/products')
    result = await resp.json()
    assert len(result['data']) == 1

    resp = await api.get(f'/api/products/{product_data["id"]}')
    result = await resp.json()
    assert vendor['vendor']['name'] == result['data']['vendor']['name']
    assert vendor['vendor']['identifier'] == result['data']['vendor']['identifier']

    failure_product = api.get_fixture_json('product')
    failure_product['relatedCategory'] = category_id
    del failure_product['requirementResponses']

    resp = await api.post(
        f'/api/vendors/{vendor["id"]}/products?access_token={vendor_token}',
        json={'data': failure_product},
        auth=TEST_AUTH,
    )

    assert resp.status == 400
    result = await resp.json()
    assert result == {'errors': [
        "value is not a valid enumeration member; permitted: 'EAN-13': data.identifier.scheme",
        'extra fields not permitted: data.alternativeIdentifiers',
    ]}

    invalid_product = deepcopy(test_product)
    invalid_product["status"] = "hidden"
    resp = await api.post(
        f'/api/vendors/{vendor["id"]}/products?access_token={vendor_token}',
        json={'data': invalid_product},
        auth=TEST_AUTH,
    )

    assert resp.status == 400
    result = await resp.json()
    assert result == {'errors': [
        "unexpected value; permitted: <ProductStatus.active: 'active'>: data.status"
    ]}

    invalid_product = deepcopy(test_product)
    invalid_product["additionalClassifications"] = [{
        "id": "test",
        "description": "test",
        "scheme": "ATC",
    }]
    with patch('catalog.validations.CachedSession.get') as medicine_resp:
        medicine_resp.return_value = AsyncMock()
        medicine_resp.return_value.__aenter__.return_value.status = 200
        medicine_resp.return_value.__aenter__.return_value.json.return_value = {"data": {"foo": "bar"}}
        resp = await api.post(
            f'/api/vendors/{vendor["id"]}/products?access_token={vendor_token}',
            json={'data': invalid_product},
            auth=TEST_AUTH,
        )
        assert resp.status == 400
        assert {"errors": ["values {'test'} don't exist in ATC dictionary"]} == await resp.json()

    resp = await api.patch(
        f'/api/categories/{category_id}?access_token={category_token}',
        json={'data': {"status": "hidden"}},
        auth=TEST_AUTH,
    )
    assert resp.status == 200

    resp = await api.post(
        f'/api/vendors/{vendor["id"]}/products?access_token={vendor_token}',
        json={'data': test_product},
        auth=TEST_AUTH,
    )

    assert resp.status == 400
    result = await resp.json()
    assert result == {"errors": ["relatedCategory should be in `active` status."]}

    test_product["relatedCategory"] = "0" * 32
    resp = await api.post(
        f'/api/vendors/{vendor["id"]}/products?access_token={vendor_token}',
        json={'data': test_product},
        auth=TEST_AUTH,
    )

    assert resp.status == 404


async def test_vendor_product_update(api, vendor, category, vendor_product):
    vendor_token = vendor['access']['token']
    resp = await api.patch(
        f'/api/products/{vendor_product["data"]["id"]}?access_token={vendor_token}',
        json={'data': {"status": "active"}},
        auth=TEST_AUTH,
    )

    assert resp.status == 403
    result = await resp.json()
    assert 'errors' in result
    assert result['errors'][0] == 'Access token mismatch'

    resp = await api.patch(
        f'/api/products/{vendor_product["data"]["id"]}?access_token={vendor_token}',
        json={'data': {"description": "foobar"}},
        auth=TEST_AUTH_CPB,
    )
    assert resp.status == 400
    result = await resp.json()
    assert 'errors' in result
    assert result['errors'][0] == 'extra fields not permitted: data.description'

    # update status and documents in one request
    doc_hash = "0" * 32
    doc_data = {
        "title": "name.doc",
        "url": generate_test_url(doc_hash),
        "hash": f"md5:{doc_hash}",
        "format": "application/msword",
    }
    resp = await api.patch(
        f'/api/products/{vendor_product["data"]["id"]}?access_token={vendor_token}',
        json={'data': {
            "documents": [doc_data],
            "status": "inactive",
        }},
        auth=TEST_AUTH_CPB,
    )
    assert resp.status == 200
    result = await resp.json()
    assert "expirationDate" in result["data"]
    assert result["data"]["expirationDate"] == result["data"]["dateModified"]

    resp = await api.patch(
        f'/api/products/{vendor_product["data"]["id"]}?access_token={vendor_token}',
        json={'data': {"status": "active"}},
        auth=TEST_AUTH_CPB,
    )
    assert resp.status == 403
    result = await resp.json()
    assert 'errors' in result
    assert result['errors'][0] == 'Patch product in inactive status is disallowed'

    # try to add doc in inactive status
    resp = await api.post(
        f'/api/products/{vendor_product["data"]["id"]}/documents?access_token={vendor_token}',
        json={'data': doc_data},
        auth=TEST_AUTH_CPB,
    )
    assert resp.status == 201


async def test_vendor_product_with_different_formats_of_expected_values(api, vendor, mock_agreement):
    # create category with expectedValues
    data = deepcopy(api.get_fixture_json('category'))
    data["id"] = "33190000-1000-42574629"
    resp = await api.put(
        f"/api/categories/{data['id']}",
        json={"data": data},
        auth=TEST_AUTH
    )
    assert resp.status == 201
    data = await resp.json()
    criteria_data = {"criteria": [{
        "title": "Технічні характеристики предмета закупівлі",
        "description": "Тести швидкі для визначення інфекційних захворювань",
        "legislation": [{
            "identifier": {
                "id": "identifier_id",
                "legalName": "legal_name",
                "uri": "http://example.com",
            },
            "version": "1.0.0",
            "article": "22.2.3"
        }],
        "classification": {
            "id": "CRITERION.OTHER.SUBJECT_OF_PROCUREMENT.TECHNICAL_FEATURES",
            "scheme": "ESPD211",
        },
        "requirementGroups": [{
            "description": "Технічні характеристики",
            "requirements": [
                {
                    "title": "Метод аналізу",
                    "dataType": "string",
                    "expectedMinItems": 1,
                    "expectedValues": ["ІХА", "FOO", "BAR"]
                },
                {
                    "title": "Специфічність",
                    "dataType": "integer",
                    "unit": {
                        "code": "P1",
                        "name": "%"
                    },
                    "minValue": 90,
                    "maxValue": 110,
                }
            ]
        }]
    }]}
    category = await create_criteria(api, "categories", data, criteria=criteria_data)

    # create profile with expectedValue
    profile = await create_profile(api, category)
    criteria_data = {"criteria": [{
        "title": "Технічні характеристики предмета закупівлі",
        "description": "Тести швидкі для визначення інфекційних захворювань",
        "legislation": [{
            "identifier": {
                "id": "identifier_id",
                "legalName": "legal_name",
                "uri": "http://example.com",
            },
            "version": "1.0.0",
            "article": "22.2.3"
        }],
        "classification": {
            "id": "CRITERION.OTHER.SUBJECT_OF_PROCUREMENT.TECHNICAL_FEATURES",
            "scheme": "ESPD211",
        },
        "requirementGroups": [{
            "description": "Технічні характеристики",
            "requirements": [
                {
                    "title": "Метод аналізу",
                    "dataType": "string",
                    "expectedValues": ["ІХА", "FOO"],
                },
                {
                    "title": "Специфічність",
                    "dataType": "integer",
                    "unit": {
                        "code": "P1",
                        "name": "%"
                    },
                    "minValue": 95,
                    "maxValue": 103,
                }
            ]
        }]
    }]}
    profile = await create_criteria(api, "profiles", profile, criteria=criteria_data)

    # create product for this category and profile
    category_id = category['data']['id']

    vendor_token = vendor['access']['token']
    vendor = vendor['data']

    test_product = api.get_fixture_json('vendor_product')
    test_product['relatedCategory'] = category_id
    test_product['relatedProfiles'] = [profile['data']['id']]
    del test_product['requirementResponses']

    resp = await api.post(
        f'/api/vendors/{vendor["id"]}/products?access_token={vendor_token}',
        json={'data': test_product},
        auth=TEST_AUTH,
    )

    assert resp.status == 400
    result = await resp.json()
    assert result == {'errors': ['should be responded at least on one category requirement']}

    # response with both variants 'value' and 'values'
    test_product['requirementResponses'] = [{
        "value": "IXA",
        "values": ["ІХА"],
        "requirement": "Метод аналізу"
    }]
    resp = await api.post(
        f'/api/vendors/{vendor["id"]}/products?access_token={vendor_token}',
        json={'data': test_product},
        auth=TEST_AUTH,
    )

    assert resp.status == 400
    result = await resp.json()
    assert result == {'errors': ["only 'values' allowed in response for requirement Метод аналізу"]}

    # response with values
    test_product['requirementResponses'] = [
        {
            "values": ["ІХА"],
            "requirement": "Метод аналізу"
        },
        {
            "values": [95, 102, 98],
            "requirement": "Специфічність"
        },
    ]
    resp = await api.post(
        f'/api/vendors/{vendor["id"]}/products?access_token={vendor_token}',
        json={'data': test_product},
        auth=TEST_AUTH,
    )

    assert resp.status == 400
    result = await resp.json()
    assert result == {'errors': ["only 'value' allowed in response for requirement Специфічність"]}

    # response with value
    test_product['requirementResponses'] = [
        {
            "values": ["ІХА"],
            "requirement": "Метод аналізу"
        },
        {
            "value": 96,
            "requirement": "Специфічність"
        },
    ]
    resp = await api.post(
        f'/api/vendors/{vendor["id"]}/products?access_token={vendor_token}',
        json={'data': test_product},
        auth=TEST_AUTH,
    )

    assert resp.status == 201
