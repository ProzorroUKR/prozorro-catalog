from random import randint
from copy import deepcopy
from urllib.parse import quote
from .base import TEST_AUTH, TEST_AUTH_ANOTHER, TEST_AUTH_NO_PERMISSION


async def test_410_product_create(api, profile):
    profile_id = profile['data']['id']

    test_product = {"data": api.get_fixture_json('product')}
    test_product["data"]["relatedProfiles"] = [profile["data"]["id"]]
    for item, rr in enumerate(test_product["data"]["requirementResponses"]):
        if item < 5:
            rr["requirement"] = profile["data"]["criteria"][item]["requirementGroups"][0]["requirements"][0]["id"]
        elif item == 5:
            rr["requirement"] = profile["data"]["criteria"][4]["requirementGroups"][1]["requirements"][0]["id"]
        elif item == 6:
            rr["requirement"] = profile["data"]["criteria"][4]["requirementGroups"][2]["requirements"][0]["id"]

    cpv = test_product['data']['classification']['id']
    test_product['data']['classification']['id'] = '12345678'
    test_product['data']['relatedProfiles'] = [profile_id]
    test_product['access'] = profile['access']

    resp = await api.patch(
        '/api/products/some_id',
        json=test_product,
        auth=TEST_AUTH,
    )
    assert resp.status == 404, await resp.json()

    resp = await api.post(
        '/api/products',
        json=test_product,
        auth=TEST_AUTH,
    )
    assert resp.status == 400, await resp.json()
    assert {'errors': ['product and profile classification mismatch']} == await resp.json()

    test_product['data']['classification']['id'] = '87654321'

    resp = await api.post('/api/products', json=test_product, auth=TEST_AUTH)
    assert resp.status == 400
    assert {'errors': ['product and profile classification mismatch']} == await resp.json()

    test_product['data']['classification']['id'] = cpv

    resp = await api.post('/api/products', json=test_product, auth=TEST_AUTH)
    assert resp.status == 201, await resp.json()
    resp_json = await resp.json()
    assert 'id' in resp_json['data']
    assert 'access' in resp_json
    assert 'token' in resp_json['access']
    product_id = resp_json['data']['id']

    resp = await api.patch(
        '/api/products/%s' % product_id,
        json=test_product,
    )
    assert resp.status == 401, await resp.json()
    assert await resp.json() == {'errors': ['Authorization header not found']}

    test_product_copy = deepcopy(test_product)
    test_product['access'] = resp_json['access']

    for i in range(3):
        test_product_copy['data']['requirementResponses'].pop()

    resp = await api.post('/api/products', json=test_product_copy, auth=TEST_AUTH)
    assert resp.status == 400, await resp.json()
    resp = await resp.json()
    assert "criteria" in resp["errors"][0]
    assert "not satisfied" in resp["errors"][0]

    resp = await api.get('/api/products')
    assert resp.status == 200
    resp_json = await resp.json()
    assert len(resp_json['data']) > 0
    assert set(resp_json['data'][0].keys()) == {'id', 'dateModified'}
    assert product_id in [i['id'] for i in resp_json['data']]

    resp = await api.get('/api/products/%s' % product_id)
    assert resp.status == 200
    resp_json = await resp.json()
    assert 'id' in resp_json['data']


async def test_411_product_rr_create(api, profile):
    profile_id = profile['data']['id']
    test_product = {"data": api.get_fixture_json('product')}
    test_product["data"]["relatedProfiles"] = [profile["data"]["id"]]
    for item, rr in enumerate(test_product["data"]["requirementResponses"]):
        if item < 5:
            rr["requirement"] = profile["data"]["criteria"][item]["requirementGroups"][0]["requirements"][0]["id"]
        elif item == 5:
            rr["requirement"] = profile["data"]["criteria"][4]["requirementGroups"][1]["requirements"][0]["id"]
        elif item == 6:
            rr["requirement"] = profile["data"]["criteria"][4]["requirementGroups"][2]["requirements"][0]["id"]

    product_id = '{}-{}-{}-{}'.format(
        test_product['data']['classification']['id'][:4],
        test_product['data']['brand']['name'][:4],
        test_product['data']['identifier']['id'][:13],
        randint(100000, 900000))

    test_product['data']['requirementResponses'][2]["value"] = 49.91

    test_product['data']['relatedProfiles'] = [profile_id]
    test_product['access'] = profile['access']

    resp = await api.post('/api/products', json=test_product, auth=TEST_AUTH)
    assert resp.status == 201, await resp.json()


async def test_420_product_patch(api, product):
    product_id = product['data']['id']

    resp = await api.get('/api/products/%s' % product_id)
    assert resp.status == 200
    resp_json = await resp.json()
    assert product_id == resp_json['data']['id']

    resp = await api.patch('/api/products/%s' % product_id, json={"data": {}}, auth=TEST_AUTH)
    assert resp.status == 401, await resp.json()
    assert {'errors': ['Require access token']} == await resp.json()

    resp = await api.patch('/api/products/%s' % product_id,
                           json={
                               "data": {},
                               "access": {'token': "a" * 32},
                           },
                           auth=TEST_AUTH)
    assert resp.status == 403, await resp.json()

    patch_product_bad = {
        "data": {
            "status": "unknown"
        },
        "access": product['access'],
    }
    resp = await api.patch('/api/products/%s' % product_id, json=patch_product_bad, auth=TEST_AUTH)
    assert resp.status == 400, await resp.json()

    patch_product_identifier = {
        "data": {
            "identifier": {
                "id": "0463234567819"
            }
        },
        "access": product['access']
    }

    resp = await api.patch('/api/products/%s' % product_id, json=patch_product_identifier, auth=TEST_AUTH)
    assert resp.status == 400

    patch_product = {
        "data": {
            "status": "hidden",
            "title": "Маски (приховані)"
        },
        "access": product['access']
    }

    resp = await api.patch('/api/products/%s' % product_id, json=patch_product, auth=TEST_AUTH)
    assert resp.status == 200
    resp_json = await resp.json()
    for key, patch_value in patch_product['data'].items():
        assert resp_json['data'][key] == patch_value

    test_date_modified = resp_json['data']['dateModified']
    assert test_date_modified > product["data"]["dateModified"]

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

    patch_product = {
        "data": {
            "relatedProfiles": ["1"*32],
        },
        "access": product['access']
    }
    resp = await api.patch('/api/products/%s' % product_id, json=patch_product, auth=TEST_AUTH)
    assert resp.status == 404


async def test_430_product_limit_offset(api, profile):
    profile_id = profile["data"]['id']
    test_product = {"data": api.get_fixture_json('product')}
    test_product["data"]["relatedProfiles"] = [profile["data"]["id"]]
    for item, rr in enumerate(test_product["data"]["requirementResponses"]):
        if item < 5:
            rr["requirement"] = profile["data"]["criteria"][item]["requirementGroups"][0]["requirements"][0]["id"]
        elif item == 5:
            rr["requirement"] = profile["data"]["criteria"][4]["requirementGroups"][1]["requirements"][0]["id"]
        elif item == 6:
            rr["requirement"] = profile["data"]["criteria"][4]["requirementGroups"][2]["requirements"][0]["id"]

    test_product_map = dict()
    for i in range(11):

        test_product_copy = deepcopy(test_product)
        test_product_copy['data']['relatedProfiles'] = [profile_id]
        test_product_copy['access'] = profile['access']

        resp = await api.post('/api/products', json=test_product_copy, auth=TEST_AUTH)
        assert resp.status == 201
        resp_json = await resp.json()
        assert 'id' in resp_json['data']
        assert 'access' in resp_json
        assert 'token' in resp_json['access']
        product_id = resp_json['data']['id']

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
    prev_resp_next = None
    while True:
        resp = await api.get('/api/products?limit=5&offset=' + quote(offset))
        assert resp.status == 200
        resp_json = await resp.json()
        if len(resp_json['data']) == 0:
            assert prev_resp_next == resp_json["next_page"]
            break
        assert 'next_page' in resp_json
        prev_resp_next = resp_json['next_page']
        assert 'offset' in resp_json['next_page']
        offset = resp_json['next_page']['offset']

        assert len(resp_json['data']) <= 5
        prev = resp_json['data'][0]
        assert test_product_map.pop(prev['id']) == prev['dateModified']
        for item in resp_json['data'][1:]:
            assert prev['dateModified'] < item['dateModified']
            assert test_product_map.pop(item['id']) == item['dateModified']

    assert len(test_product_map) == 0
