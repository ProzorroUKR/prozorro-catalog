from random import randint
from copy import deepcopy
from urllib.parse import quote
from .base import TEST_AUTH, TEST_AUTH_ANOTHER, TEST_AUTH_NO_PERMISSION


async def test_410_product_create(api, profile):
    profile_id = profile['data']['id']

    test_product = {"data": api.get_fixture_json('product')}
    cpv = test_product['data']['classification']['id']
    test_product['data']['classification']['id'] = '12345678'

    product_id = '{}-{}-{}-{}'.format(
        test_product['data']['classification']['id'][:4],
        test_product['data']['brand']['name'][:4],
        test_product['data']['identifier']['id'][:13],
        randint(100000, 900000)
    )

    test_product['data']['id'] = product_id
    test_product['data']['relatedProfile'] = profile_id
    test_product['access'] = profile['access']

    resp = await api.patch(
        '/api/products/%s' % product_id,
        json=test_product,
    )
    assert resp.status == 401, await resp.json()
    assert await resp.json() == {'errors': ['Authorization header not found']}

    resp = await api.patch(
        '/api/products/%s' % product_id,
        json=test_product,
        auth=TEST_AUTH,
    )
    assert resp.status == 404, await resp.json()

    resp = await api.put('/api/products/%s' % product_id,
                         json=test_product,
                         auth=TEST_AUTH)
    assert resp.status == 400, await resp.json()
    assert {'errors': ['product and profile classification mismatch']} == await resp.json()

    test_product['data']['classification']['id'] = '87654321'

    resp = await api.put('/api/products/%s' % product_id, json=test_product, auth=TEST_AUTH)
    assert resp.status == 400
    assert {'errors': [{'loc': 'data.id', 'msg': 'id must include classification',
                        'type': 'value_error', 'values': None}]} == await resp.json()

    test_product['data']['classification']['id'] = cpv

    product_id = '{}-{}-{}-{}'.format(
        test_product['data']['classification']['id'][:4],
        test_product['data']['brand']['name'][:4],
        test_product['data']['identifier']['id'][:13],
        randint(100000, 900000))
    test_product['data']['id'] = product_id

    resp = await api.put('/api/products/%s' % product_id + '-1', json=test_product, auth=TEST_AUTH)
    assert resp.status == 400
    assert {'errors': ['id mismatch']} == await resp.json()

    resp = await api.put('/api/products/%s' % product_id, json=test_product, auth=TEST_AUTH)
    assert resp.status == 201, await resp.json()
    resp_json = await resp.json()
    assert resp_json['data']['id'] == test_product['data']['id']
    assert 'access' in resp_json
    assert 'token' in resp_json['access']

    test_product_copy = deepcopy(test_product)
    test_product['access'] = resp_json['access']

    resp = await api.put('/api/products/%s' % product_id, json=test_product_copy, auth=TEST_AUTH)
    assert resp.status == 400
    assert {'errors': [f'Document with id {product_id} already exists']} == await resp.json()

    product_id_copy = product_id + '1'
    test_product_copy['data']['id'] = product_id_copy
    for i in range(3):
        test_product_copy['data']['requirementResponses'].pop()

    resp = await api.put('/api/products/%s' % product_id_copy, json=test_product_copy, auth=TEST_AUTH)
    assert resp.status == 400, await resp.json()
    assert {'errors': ['criteria 0005 not satisfied']} == await resp.json()

    resp = await api.get('/api/products')
    assert resp.status == 200
    resp_json = await resp.json()
    assert len(resp_json['data']) > 0
    assert set(resp_json['data'][0].keys()) == {'id', 'dateModified'}
    assert product_id in [i['id'] for i in resp_json['data']]

    resp = await api.get('/api/products/%s' % product_id)
    assert resp.status == 200
    resp_json = await resp.json()
    assert resp_json['data']['id'] == test_product['data']['id']


async def test_420_product_patch(api, product):
    product_id = product['data']['id']

    resp = await api.get('/api/products/%s' % product_id)
    assert resp.status == 200
    resp_json = await resp.json()
    assert product_id == resp_json['data']['id']

    patch_product_bad = {
        "data": {
            "status": "unknown"
        }
    }

    resp = await api.patch('/api/products/%s' % product_id, json=patch_product_bad, auth=TEST_AUTH)
    assert resp.status == 401

    patch_product_bad['access'] = {'token': 'bad access token, but long enough'}

    resp = await api.patch('/api/products/%s' % product_id, json=patch_product_bad, auth=TEST_AUTH)
    assert resp.status == 403

    patch_product_bad['access'] = dict(test_product['access'])

    resp = await api.patch('/api/products/%s' % product_id, json=patch_product_bad, auth=TEST_AUTH)
    assert resp.status == 400

    patch_product_identifier = {
        "data": {
            "identifier": {
                "id": "0463234567819",
                "scheme": "EAN-13"
            }
        },
        "access": test_product['access']
    }

    resp = await api.patch('/api/products/%s' % product_id, json=patch_product_identifier, auth=TEST_AUTH)
    assert resp.status == 400

    patch_product = {
        "data": {
            "status": "hidden",
            "title": "Маски (приховані)"
        },
        "access": test_product['access']
    }

    resp = await api.patch('/api/products/%s' % product_id, json=patch_product, auth=TEST_AUTH)
    assert resp.status == 200
    resp_json = await resp.json()
    for key, patch_value in patch_product['data'].items():
        assert resp_json['data'][key] == patch_value

    resp = await api.get('/api/products/%s' % product_id)
    assert resp.status == 200
    resp_json = await resp.json()
    for key, patch_value in patch_product['data'].items():
        assert resp_json['data'][key] == patch_value

    patch_product['data']['status'] = 'active'
    resp = await api.patch('/api/products/%s' % product_id, json=patch_product, auth=TEST_AUTH)
    assert resp.status == 200
    resp_json = await resp.json()
    assert resp_json['data']['status'] == 'active'


async def test_430_product_limit_offset(api, profile):
    profile_id = profile['id']
    test_product = {"data": api.get_fixture_json('product')}

    test_product_map = dict()
    for i in range(11):
        product_id = '{}-{}-{}-{}'.format(
            test_product['data']['classification']['id'][:4],
            test_product['data']['brand']['name'][:4],
            test_product['data']['identifier']['id'][:13],
            randint(100000, 900000))

        test_product_copy = deepcopy(test_product)
        test_product_copy['data']['id'] = product_id
        test_product_copy['data']['relatedProfile'] = profile_id
        test_product_copy['access'] = profile['access']

        resp = await api.put('/api/products/%s' % product_id, json=test_product_copy, auth=TEST_AUTH)
        assert resp.status == 201
        resp_json = await resp.json()
        assert resp_json['data']['id'] == test_product_copy['data']['id']
        assert 'access' in resp_json
        assert 'token' in resp_json['access']

        test_product_map[product_id] = resp_json['data']['dateModified']

    resp = await api.get('/api/products?reverse=1')
    assert resp.status == 200
    resp_json = await resp.json()
    assert len(resp_json['data']) > 10
    prev = resp_json['data'][0]
    assert test_product_map[prev['id']] == prev['dateModified']
    for item in resp_json['data'][1:]:
        assert prev['dateModified'] > item['dateModified']
        assert test_product_map[item['id']] == item['dateModified']

    offset = ''
    while True:
        resp = await api.get('/api/products?limit=5&offset=' + quote(offset))
        assert resp.status == 200
        resp_json = await resp.json()
        if len(resp_json['data']) == 0:
            assert 'next_page' not in resp_json
            break
        assert 'next_page' in resp_json
        assert 'offset' in resp_json['next_page']
        offset = resp_json['next_page']['offset']

        assert len(resp_json['data']) <= 5
        prev = resp_json['data'][0]
        assert test_product_map.pop(prev['id']) == prev['dateModified']
        for item in resp_json['data'][1:]:
            assert prev['dateModified'] < item['dateModified']
            assert test_product_map.pop(item['id']) == item['dateModified']

    assert len(test_product_map) == 0
