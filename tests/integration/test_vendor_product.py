from catalog.models.product import VENDOR_PRODUCT_IDENTIFIER_SCHEME

from .base import TEST_AUTH


async def test_vendor_product_create(api, vendor, profile):
    profile_id = profile['data']['id']
    profile_token = profile['access']['token']

    vendor_token = vendor['access']['token']
    vendor = vendor['data']

    test_product = api.get_fixture_json('vendor_product')
    test_product['relatedProfile'] = profile_id
    del test_product['requirementResponses']

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

    assert resp.status == 201
    result = await resp.json()
    product = result['data']
    assert 'data' in result
    # assert "access" in result
    assert 'vendor' in product
    assert product['identifier']['scheme'] == VENDOR_PRODUCT_IDENTIFIER_SCHEME
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
    failure_product['relatedProfile'] = profile_id
    del failure_product['requirementResponses']

    resp = await api.post(
        f'/api/vendors/{vendor["id"]}/products?access_token={vendor_token}',
        json={'data': failure_product},
        auth=TEST_AUTH,
    )

    assert resp.status == 400
    result = await resp.json()
    assert result == {'errors': [
        'extra fields not permitted: data.identifier.scheme',
        'extra fields not permitted: data.additionalProperties',
        'extra fields not permitted: data.alternativeIdentifiers',
        'extra fields not permitted: data.images',
        'extra fields not permitted: data.manufacturers',
    ]}

    resp = await api.patch(
        f'/api/profiles/{profile_id}?access_token={profile_token}',
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
    assert result == {"errors": ["relatedProfile should be in `active` status"]}

    test_product["relatedProfile"] = "0" * 32
    resp = await api.post(
        f'/api/vendors/{vendor["id"]}/products?access_token={vendor_token}',
        json={'data': test_product},
        auth=TEST_AUTH,
    )

    assert resp.status == 404
