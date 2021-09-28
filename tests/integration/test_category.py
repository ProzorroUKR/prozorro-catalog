from copy import deepcopy
from random import randint
from urllib.parse import quote
from .base import TEST_AUTH_NO_PERMISSION, TEST_AUTH, TEST_AUTH_ANOTHER


async def test_110_category_create(api):
    test_category = api.get_fixture_json('category')
    resp = await api.post('/api/categories', json=test_category, auth=TEST_AUTH)
    assert resp.status == 405, await resp.json()

    resp = await api.put('/api/categories/123', auth=TEST_AUTH)
    assert resp.status == 400

    resp = await api.post('/api/categories', json=test_category,
                          auth=TEST_AUTH,
                          headers={'X-HTTP-METHOD-OVERRIDE': 'GET'})
    assert resp.status == 405

    resp = await api.put('/api/categories', json=test_category, auth=TEST_AUTH)
    assert resp.status == 405

    category_id = '{}-{}-{}'.format(
        test_category['classification']['id'][:8],
        randint(1000, 9999),
        test_category['procuringEntity']['identifier']['id']
    )
    test_category['id'] = category_id

    resp = await api.put('/api/categories/%s' % category_id + '-1',
                         json=test_category,
                         auth=TEST_AUTH)
    assert resp.status == 400, await resp.json()
    assert {'errors': [{'loc': 'data', 'msg': 'field required',
                        'type': 'value_error.missing', 'values': None}]} == await resp.json()

    resp = await api.put('/api/categories/%s' % category_id + '-1',
                         json={"data": test_category},
                         auth=TEST_AUTH)
    assert resp.status == 400, await resp.json()
    assert {'errors': ['id mismatch']} == await resp.json()

    test_category['id'] = category_id[:18]

    resp = await api.put('/api/categories/%s' % category_id[:18],
                         json={"data": test_category},
                         auth=TEST_AUTH)
    assert resp.status == 400, await resp.json()
    assert {'errors': [{'loc': 'data.id', 'msg': 'string does not match regex "^[0-9A-Za-z_-]{20,32}$"',
                        'type': 'value_error.str.regex',
                        'values': {'pattern': '^[0-9A-Za-z_-]{20,32}$'}}]} == await resp.json()

    test_category['id'] = category_id

    resp = await api.put(f"/api/categories/{category_id}",
                         json=test_category,
                         auth=TEST_AUTH_NO_PERMISSION)
    assert resp.status == 403
    assert {'errors': ["Forbidden 'category' write operation"]} == await resp.json()

    resp = await api.put(f'/api/categories/{category_id}',
                         json={"data": test_category},
                         auth=TEST_AUTH)
    assert resp.status == 201, await resp.json()
    resp_json = await resp.json()
    assert 'access' in resp_json
    assert 'token' in resp_json['access']

    test_category['access'] = dict(resp_json['access'])
    test_date_modified = resp_json['data']['dateModified']

    resp = await api.head('/api/categories')
    assert resp.status == 200

    resp = await api.get('/api/categories')
    assert resp.status == 200
    resp_json = await resp.json()
    assert set(resp_json['data'][0].keys()) == {'id', 'dateModified'}
    assert category_id in [i['id'] for i in resp_json['data']]
    items = [i for i in resp_json['data'] if i['id'] == category_id]
    assert len(items) == 1
    assert items[0]['dateModified'] == test_date_modified
    test_category['dateModified'] = test_date_modified

    resp = await api.get('/api/categories/..')
    assert resp.status == 404

    resp = await api.get('/api/categories/../../../../../../../../../../etc/passwd')
    assert resp.status == 404

    resp = await api.get('/api/categories/%s-bad' % category_id)
    assert resp.status == 404

    resp = await api.get('/api/categories/%s' % category_id)
    assert resp.status == 200
    resp_json = await resp.json()
    assert resp_json['data']['id'] == category_id


async def test_111_limit_offset(api):
    test_category = api.get_fixture_json('category')
    test_category_map = dict()

    for i in range(11):
        test_category_copy = deepcopy(test_category)
        test_category_copy['title'] += " copy {}".format(i + 1)
        category_id = '{}-{}-{}'.format(
            test_category['classification']['id'][:8],
            randint(1000, 9999),
            test_category['procuringEntity']['identifier']['id']
        )
        test_category_copy['id'] = category_id
        resp = await api.put(f'/api/categories/{category_id}',
                             json={"data": test_category_copy},
                             auth=TEST_AUTH)
        assert resp.status == 201
        resp_json = await resp.json()
        assert 'access' in resp_json
        assert 'token' in resp_json['access']
        test_category_map[category_id] = resp_json['data']['dateModified']

    # check for empty limit
    resp = await api.get('/api/categories')
    assert resp.status == 200, await resp.json()
    resp_json = await resp.json()
    assert len(resp_json['data']) > 0

    # check for negative limit
    resp = await api.get('/api/categories?limit=-1')
    assert resp.status == 200
    resp_json = await resp.json()
    assert len(resp_json['data']) > 0

    # first page forward
    resp = await api.get('/api/categories?limit=5')
    assert resp.status == 200
    resp_json = await resp.json()
    assert len(resp_json['data']) == 5
    prev = resp_json['data'][0]
    assert test_category_map[prev['id']] == prev['dateModified']
    for item in resp_json['data'][1:]:
        assert prev['dateModified'] < item['dateModified']
        assert test_category_map[item['id']] == item['dateModified']
    assert 'next_page' in resp_json
    assert 'offset' in resp_json['next_page']
    offset_normal = resp_json['next_page']['offset']

    # first page backward
    resp = await api.get('/api/categories?limit=8&reverse=1')
    assert resp.status == 200
    resp_json = await resp.json()
    assert len(resp_json['data']) == 8
    prev = resp_json['data'][0]
    assert test_category_map[prev['id']] == prev['dateModified']
    for item in resp_json['data'][1:]:
        assert prev['dateModified'] > item['dateModified']
        assert test_category_map[item['id']] == item['dateModified']
    assert 'next_page' in resp_json
    assert 'offset' in resp_json['next_page']
    offset_reverse = resp_json['next_page']['offset']

    assert offset_normal != offset_reverse

    # second page fowrard
    resp = await api.get('/api/categories?limit=10&offset=' + quote(offset_normal))
    assert resp.status == 200
    resp_json = await resp.json()
    assert len(resp_json['data']) == 6  # 11 total, first page 5, second 6
    prev = resp_json['data'][0]
    assert test_category_map[prev['id']] == prev['dateModified']
    for item in resp_json['data'][1:]:
        assert prev['dateModified'] < item['dateModified']
        assert test_category_map[item['id']] == item['dateModified']
    assert 'next_page' in resp_json
    assert 'offset' in resp_json['next_page']
    offset_normal = resp_json['next_page']['offset']

    # third page forward (must be empty)
    resp = await api.get('/api/categories?limit=10&offset=' + quote(offset_normal))
    assert resp.status == 200
    resp_json = await resp.json()
    assert len(resp_json['data']) == 0
    assert 'next_page' not in resp_json

    # second page backward
    resp = await api.get('/api/categories?limit=8&reverse=1&offset=' + quote(offset_reverse))
    assert resp.status == 200
    resp_json = await resp.json()
    assert len(resp_json['data']) == 3  # 11 total, 8 on first, 3 on second
    prev = resp_json['data'][0]
    assert test_category_map[prev['id']] == prev['dateModified']
    for item in resp_json['data'][1:]:
        assert prev['dateModified'] > item['dateModified']
        assert test_category_map[item['id']] == item['dateModified']
    assert 'next_page' in resp_json
    assert 'offset' in resp_json['next_page']
    offset_reverse = resp_json['next_page']['offset']

    # third page backward (must be empty)
    resp = await api.get('/api/categories?limit=8&reverse=1&offset=' + quote(offset_reverse))
    assert resp.status == 200
    resp_json = await resp.json()
    assert len(resp_json['data']) == 0


async def test_120_category_patch(api, category):
    category_id = category["data"]['id']
    patch_category_bad = {
        "data": {
            "procuringEntity": {
                "address": {
                    "countryName": "Україна",
                    "locality": "Київ",
                    "postalCode": "02200",
                    "region": "Київ",
                    "streetAddress": "вулиця Ушинського, 40"
                }
            }
        }
    }

    resp = await api.patch('/api/categories/%s' % category_id,
                           json=patch_category_bad)
    assert resp.status == 401
    assert await resp.json() == {'errors': ['Authorization header not found']}

    patch_category_bad['access'] = {'token': 'bad token value, but long enough'}

    resp = await api.patch('/api/categories/%s' % category_id,
                           json=patch_category_bad,
                           auth=TEST_AUTH_NO_PERMISSION)
    assert resp.status == 403, await resp.json()

    patch_category_bad['access'] = category['access']

    resp = await api.patch('/api/categories/%s' % category_id,
                           json={"data": {}, "access": category['access']},
                           auth=TEST_AUTH_ANOTHER)
    assert resp.status == 403, await resp.json()
    assert {'errors': ['Owner mismatch']} == await resp.json()

    resp = await api.patch('/api/categories/%s' % category_id,
                           json=patch_category_bad,
                           auth=TEST_AUTH)
    assert resp.status == 400, await resp.json()

    patch_category = {
        "data": {
            "title": "Респіратори та маски без клапану (приховані)",
            "status": "hidden"
        }
    }
    resp = await api.patch('/api/categories/%s' % category_id, json=patch_category,
                           headers={'X-Access-Token': category['access']['token']},
                           auth=TEST_AUTH)
    assert resp.status == 200
    resp_json = await resp.json()
    for key, patch_value in patch_category['data'].items():
        assert resp_json['data'][key] == patch_value

    test_date_modified = resp_json['data']['dateModified']

    resp = await api.get('/api/categories')
    assert resp.status == 200
    resp_json = await resp.json()
    items = [i for i in resp_json['data'] if i['id'] == category_id]
    assert len(items) == 1
    assert items[0]['dateModified'] == test_date_modified

    patch_category['access'] = category['access']

    resp = await api.get('/api/categories/%s' % category_id)
    assert resp.status == 200
    resp_json = await resp.json()
    for key, patch_value in patch_category['data'].items():
        assert resp_json['data'][key] == patch_value

    patch_category["data"]["status"] = "active"
    resp = await api.patch('/api/categories/%s' % category_id,
                           json=patch_category,
                           auth=TEST_AUTH)
    assert resp.status == 200
    resp_json = await resp.json()
    assert resp_json['data']['status'] == 'active'
