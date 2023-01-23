from catalog.models.product import VendorProductIdentifierScheme

from .base import TEST_AUTH
from .conftest import set_requirements_to_responses


async def test_vendor_product_create(api, vendor, category, profile):
    category_id = category['data']['id']
    category_token = category['access']['token']

    vendor_token = vendor['access']['token']
    vendor = vendor['data']

    test_product = api.get_fixture_json('vendor_product')
    test_product['relatedProfiles'] = [profile['data']['id']]
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
    failure_product['relatedProfiles'] = [profile['data']['id']]
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
