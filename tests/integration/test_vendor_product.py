from copy import deepcopy
from unittest.mock import AsyncMock, patch

from catalog.models.product import VendorProductIdentifierScheme

from .base import TEST_AUTH
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
    product = result['data']
    assert 'data' in result
    # assert "access" in result
    assert 'vendor' in product
    assert product['identifier']['scheme'] == VendorProductIdentifierScheme.ean_13
    assert vendor['id'] == product['vendor']['id']
    assert vendor['vendor']['name'] == product['vendor']['name']
    assert vendor['vendor']['identifier'] == product['vendor']['identifier']

    resp = await api.get('/api/products')
    result = await resp.json()
    assert len(result['data']) == 1

    resp = await api.get(f'/api/products/{product["id"]}')
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
        'extra fields not permitted: data.additionalProperties',
        'extra fields not permitted: data.alternativeIdentifiers',
        'extra fields not permitted: data.images',
        'extra fields not permitted: data.manufacturers',
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
    vendor_product = vendor_product['data']
    resp = await api.patch(
        f'/api/products/{vendor_product["id"]}?access_token={vendor_token}',
        json={'data': {"status": "active"}},
        auth=TEST_AUTH,
    )

    assert resp.status == 403
    result = await resp.json()
    assert 'errors' in result
    assert result['errors'][0] == 'Patch vendor product is disallowed'


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
            "id": "classification_id",
            "scheme": "scheme",
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
            "id": "classification_id",
            "scheme": "scheme",
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
    assert result == {'errors': ["please leave only one field 'values'"]}

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

    assert resp.status == 201

    # response with value
    test_product['requirementResponses'] = [
        {
            "value": "ІХА",
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
