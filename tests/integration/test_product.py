from random import randint
from copy import deepcopy
from urllib.parse import quote
from .base import TEST_AUTH, TEST_AUTH_ANOTHER, TEST_AUTH_NO_PERMISSION


async def test_410_product_create(api, category, profile):
    category_id = category['data']['id']

    test_product = {"data": api.get_fixture_json('product')}
    test_product["data"]["relatedCategory"] = category["data"]["id"]
    for item, rr in enumerate(test_product["data"]["requirementResponses"]):
        if item < 5:
            rr["requirement"] = category["data"]["criteria"][item]["requirementGroups"][0]["requirements"][0]["title"]
        elif item == 5:
            rr["requirement"] = category["data"]["criteria"][4]["requirementGroups"][1]["requirements"][0]["title"]
        elif item == 6:
            rr["requirement"] = category["data"]["criteria"][4]["requirementGroups"][2]["requirements"][0]["title"]

    cpv = test_product['data']['classification']['id']
    test_product['data']['classification']['id'] = '12345678'
    test_product['data']['relatedCategory'] = category_id
    test_product['data']['relatedProfiles'] = [profile['data']['id']]
    test_product['access'] = category['access']

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
    assert {'errors': ['product and category classification mismatch']} == await resp.json()

    test_product['data']['classification']['id'] = '87654321'

    resp = await api.post('/api/products', json=test_product, auth=TEST_AUTH)
    assert resp.status == 400
    assert {'errors': ['product and category classification mismatch']} == await resp.json()

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


async def test_411_product_rr_create(api, category, profile):
    category_id = category['data']['id']
    test_product = {"data": api.get_fixture_json('product')}
    test_product["data"]["relatedCategory"] = category["data"]["id"]
    test_product["data"]["relatedProfiles"] = [profile["data"]["id"]]
    for item, rr in enumerate(test_product["data"]["requirementResponses"]):
        if item < 5:
            rr["requirement"] = category["data"]["criteria"][item]["requirementGroups"][0]["requirements"][0]["title"]
        elif item == 5:
            rr["requirement"] = category["data"]["criteria"][4]["requirementGroups"][1]["requirements"][0]["title"]
        elif item == 6:
            rr["requirement"] = category["data"]["criteria"][4]["requirementGroups"][2]["requirements"][0]["title"]

    product_id = '{}-{}-{}-{}'.format(
        test_product['data']['classification']['id'][:4],
        test_product['data']['brand']['name'][:4],
        test_product['data']['identifier']['id'][:13],
        randint(100000, 900000))

    test_product['data']['requirementResponses'][2]["value"] = 49.91

    test_product['data']['relatedCategory'] = category_id
    test_product['access'] = category['access']

    resp = await api.post('/api/products', json=test_product, auth=TEST_AUTH)
    assert resp.status == 201, await resp.json()

    criterion_id = category['data']['criteria'][0]['id']
    rg_id = category['data']['criteria'][0]['requirementGroups'][0]['id']
    req = category['data']['criteria'][0]['requirementGroups'][0]['requirements'][0]

    resp = await api.patch(
        f'/api/categories/{category_id}/criteria/{criterion_id}/requirementGroups/{rg_id}/requirements/{req["id"]}',
        json={"data": {"isArchived": True}, "access": category["access"]},
        auth=TEST_AUTH
    )
    assert resp.status == 200
    json_data = await resp.json()
    assert json_data['data']['isArchived'] is True

    resp = await api.post('/api/products', json=test_product, auth=TEST_AUTH)
    assert resp.status == 400
    json_data = await resp.json()
    assert json_data["errors"] == [f'requirement {req["title"]} is archived']


async def test_420_product_patch(api, category, profile, product):
    product_id = product['data']['id']

    resp = await api.get(f'/api/products/{product_id}')
    assert resp.status == 200
    resp_json = await resp.json()
    assert product_id == resp_json['data']['id']

    resp = await api.patch(f'/api/products/{product_id}', json={"data": {}}, auth=TEST_AUTH)
    assert resp.status == 401, await resp.json()
    assert {'errors': ['Require access token']} == await resp.json()

    resp = await api.patch(f'/api/products/{product_id}',
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
    resp = await api.patch(f'/api/products/{product_id}', json=patch_product_bad, auth=TEST_AUTH)
    assert resp.status == 400, await resp.json()

    patch_product_identifier = {
        "data": {
            "identifier": {
                "id": "0463234567819"
            }
        },
        "access": product['access']
    }

    resp = await api.patch(f'/api/products/{product_id}', json=patch_product_identifier, auth=TEST_AUTH)
    assert resp.status == 400

    patch_product = {
        "data": {
            "status": "hidden",
            "title": "Маски (приховані)"
        },
        "access": product['access']
    }

    resp = await api.patch(f'/api/products/{product_id}', json=patch_product, auth=TEST_AUTH)
    assert resp.status == 200
    resp_json = await resp.json()
    for key, patch_value in patch_product['data'].items():
        assert resp_json['data'][key] == patch_value

    test_date_modified = resp_json['data']['dateModified']
    assert test_date_modified > product["data"]["dateModified"]

    resp = await api.get(f'/api/products/{product_id}')
    assert resp.status == 200
    resp_json = await resp.json()
    for key, patch_value in patch_product['data'].items():
        assert resp_json['data'][key] == patch_value

    patch_product['data']['status'] = 'active'
    resp = await api.patch(f'/api/products/{product_id}', json=patch_product, auth=TEST_AUTH)
    assert resp.status == 200
    resp_json = await resp.json()
    assert resp_json['data']['status'] == 'active'

    patch_product = {
        "data": {
            "relatedCategory": "1"*32,
        },
        "access": product['access']
    }
    resp = await api.patch(f'/api/products/{product_id}', json=patch_product, auth=TEST_AUTH)
    assert resp.status == 404

    criterion_id = category['data']['criteria'][0]['id']
    rg_id = category['data']['criteria'][0]['requirementGroups'][0]['id']
    req_id = category['data']['criteria'][0]['requirementGroups'][0]['requirements'][0]['id']
    resp = await api.patch(
        f'/api/categories/{category["data"]["id"]}/criteria/{criterion_id}/requirementGroups/{rg_id}/requirements/{req_id}',
        json={"data": {"isArchived": True}, "access": category["access"]},
        auth=TEST_AUTH
    )
    assert resp.status == 200
    resp_json = await resp.json()
    assert resp_json['data']['isArchived'] is True

    patch_product = {
        "data": {
            "status": "hidden",
        },
        "access": product['access']
    }
    resp = await api.patch(f'/api/products/{product_id}', json=patch_product, auth=TEST_AUTH)
    assert resp.status == 200
    resp_json = await resp.json()
    assert resp_json['data']['status'] == 'hidden'

    requirement_data = {
        "dataType": "number",
        "expectedValue": 1,
        "title": "Дворазова",
        "isArchived": True
    }
    resp = await api.post(
        f'/api/categories/{category["data"]["id"]}/criteria/{criterion_id}/requirementGroups/{rg_id}/requirements',
        json={"data": requirement_data, "access": category["access"]},
        auth=TEST_AUTH
    )
    assert resp.status == 201
    resp_json = await resp.json()
    assert resp_json['data'][0]['isArchived'] is True
    req_title = resp_json['data'][0]['title']

    new_req_response = {
        'requirement': req_title,
        'value': 1,
    }
    patch_product["data"] = {
        "requirementResponses": [new_req_response, *product['data']['requirementResponses']]
    }
    resp = await api.patch(f'/api/products/{product_id}', json=patch_product, auth=TEST_AUTH)
    assert resp.status == 400
    resp_json = await resp.json()
    assert resp_json['errors'] == [f'requirement {req_title} is archived']


async def test_430_product_limit_offset(api, category, profile):
    category_id = category["data"]["id"]
    profile_id = profile["data"]["id"]
    test_product = {"data": api.get_fixture_json('product')}
    test_product["data"]["relatedProfiles"] = [profile_id]
    test_product["data"]["relatedCategory"] = category["data"]["id"]
    for item, rr in enumerate(test_product["data"]["requirementResponses"]):
        if item < 5:
            rr["requirement"] = category["data"]["criteria"][item]["requirementGroups"][0]["requirements"][0]["title"]
        elif item == 5:
            rr["requirement"] = category["data"]["criteria"][4]["requirementGroups"][1]["requirements"][0]["title"]
        elif item == 6:
            rr["requirement"] = category["data"]["criteria"][4]["requirementGroups"][2]["requirements"][0]["title"]

    test_product_map = dict()
    for i in range(11):

        test_product_copy = deepcopy(test_product)
        test_product["data"]["relatedProfiles"] = [profile_id]
        test_product_copy['data']['relatedCategory'] = category_id
        test_product_copy['access'] = category['access']

        resp = await api.post('/api/products', json=test_product_copy, auth=TEST_AUTH)
        # assert resp.status == 201
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
