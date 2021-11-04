from random import randint
from copy import deepcopy
from urllib.parse import quote
from .base import TEST_AUTH_NO_PERMISSION, TEST_AUTH, TEST_AUTH_ANOTHER


async def test_310_profile_create(api, category):
    category_id = category['data']['id']
    profile_id = '{}-{}'.format(randint(100000, 900000), category_id)

    profile = api.get_fixture_json('profile')
    profile['id'] = profile_id
    profile['relatedCategory'] = category_id
    test_profile = {
        "access": dict(category['access']),
        "data": profile,
    }

    resp = await api.get('/api/profiles/%s' % profile_id)
    assert resp.status == 404

    resp = await api.patch('/api/profiles/%s' % profile_id,
                           json=test_profile, auth=TEST_AUTH)
    assert resp.status == 404
    assert await resp.json() == {"errors": ["Profile not found"]}

    resp = await api.put('/api/profiles/%s' % profile_id + '-1', json=test_profile, auth=TEST_AUTH)
    assert resp.status == 400
    assert await resp.json() == {'errors': ['id mismatch']}

    resp = await api.put('/api/profiles/%s' % profile_id, json=test_profile, auth=TEST_AUTH_NO_PERMISSION)
    assert resp.status == 403
    assert await resp.json() == {'errors': ["Forbidden 'profile' write operation"]}

    resp = await api.put('/api/profiles/%s' % profile_id, json=test_profile, auth=TEST_AUTH_ANOTHER)
    assert resp.status == 403
    assert await resp.json() == {'errors': ['Owner mismatch']}

    resp = await api.put('/api/profiles/%s' % profile_id, json=test_profile, auth=TEST_AUTH)
    assert resp.status == 201
    resp_json = await resp.json()
    assert resp_json['data']['id'] == test_profile['data']['id']
    assert 'access' in resp_json
    assert 'token' in resp_json['access']
    test_date_modified = resp_json['data']['dateModified']

    # test data type
    for criteria in resp_json['data']["criteria"]:
        for r_group in criteria["requirementGroups"]:
            for requirement in r_group["requirements"]:
                if requirement["dataType"] == "integer":
                    # pq bot converts it to str and then it passed to api to be converted to int
                    assert requirement["minValue"] == int(str(requirement["minValue"]))

    test_profile_copy = test_profile.copy()
    test_profile['access'] = resp_json['access']

    resp = await api.put('/api/profiles/%s' % profile_id, json=test_profile_copy, auth=TEST_AUTH)
    assert resp.status == 400

    resp = await api.get('/api/profiles')
    assert resp.status == 200
    resp_json = await resp.json()
    assert len(resp_json['data']) > 0
    assert set(resp_json['data'][0].keys()) == {'id', 'dateModified'}
    assert profile_id in [i['id'] for i in resp_json['data']]

    resp = await api.get('/api/profiles/%s' % profile_id)
    assert resp.status == 200
    resp_json = await resp.json()
    assert resp_json['data']['id'] == test_profile['data']['id']
    assert resp_json['data']['dateModified'] == test_date_modified
    test_profile['data']['dateModified'] = test_date_modified


async def test_311_profile_limit_offset(api, category):
    category_id = category['data']['id']

    profile = api.get_fixture_json('profile')

    # create 11 profiles
    profile_map = {}
    for i in range(11):
        profile_copy = deepcopy(profile)
        if i > 0:
            profile_copy['title'] += f" copy {i}"
        profile_id = '{}-{}'.format(randint(100000, 900000), category_id)
        profile_copy['id'] = profile_id
        profile_copy['relatedCategory'] = category_id

        resp = await api.put(f"/api/profiles/{profile_id}",
                             json={"data": profile_copy,
                                   "access": category['access']},
                             auth=TEST_AUTH)
        assert resp.status == 201
        resp_json = await resp.json()
        assert resp_json['data']['id'] == profile_copy['id']
        assert 'access' in resp_json
        assert 'token' in resp_json['access']
        profile_map[profile_id] = resp_json['data']['dateModified']

    offset = ''
    for i in range(4):
        resp = await api.get(f"/api/profiles?limit=5&offset={quote(offset)}")
        assert resp.status == 200
        resp_json = await resp.json()
        if i == 3:
            assert len(resp_json['data']) == 0
            assert 'next_page' not in resp_json
            break
        assert len(resp_json['data']) > 0
        assert len(resp_json['data']) <= 5
        assert 'next_page' in resp_json
        assert 'offset' in resp_json['next_page']
        offset = resp_json['next_page']['offset']
        prev = resp_json['data'][0]
        assert profile_map[prev['id']] == prev['dateModified']
        for item in resp_json['data'][1:]:
            assert prev['dateModified'] < item['dateModified']
            assert profile_map[item['id']] == item['dateModified']

    resp = await api.get('/api/profiles?reverse=1')
    assert resp.status == 200
    resp_json = await resp.json()
    assert len(resp_json['data']) > 0
    assert 'next_page' in resp_json
    assert 'offset' in resp_json['next_page']
    prev = resp_json['data'][0]
    assert profile_map.pop(prev['id']) == prev['dateModified']
    for item in resp_json['data'][1:]:
        assert prev['dateModified'] > item['dateModified']
        assert profile_map.pop(item['id']) == item['dateModified']

    assert len(profile_map) == 0


async def test_320_profile_patch(api, profile):
    profile_id = profile['data']['id']

    resp = await api.get(f'/api/profiles/{profile_id}')
    assert resp.status == 200
    resp_json = await resp.json()
    assert profile_id == resp_json['data']['id']

    patch_profile_bad = {"data": {"id": "new-id"}}
    resp = await api.patch(f'/api/profiles/{profile_id}', json=patch_profile_bad)
    assert resp.status == 401, await resp.json()
    assert await resp.json(), {'errors': ['Authorization header not found']}

    patch_profile_bad = {"data": {"id": "new-id"}}
    resp = await api.patch(f'/api/profiles/{profile_id}', json=patch_profile_bad, auth=TEST_AUTH)
    assert resp.status == 400, await resp.json()
    assert await resp.json(), {'errors': ['Access token not found']}

    patch_profile_bad_token = {
        "data": {"title": "new title"},
        "access": {'token': "a" * 32},
    }
    resp = await api.patch(f'/api/profiles/{profile_id}',
                           json=patch_profile_bad_token,
                           auth=TEST_AUTH)
    assert resp.status == 403, await resp.json()

    patch_profile_bad['access'] = profile['access']

    resp = await api.patch(f'/api/profiles/{profile_id}', json=patch_profile_bad, auth=TEST_AUTH)
    assert resp.status == 400

    patch_profile = {
        "data": {
            "title": "Маска (прихована)",
            "status": "hidden"
        },
        "access": profile['access']
    }

    resp = await api.patch(f'/api/profiles/{profile_id}', json=patch_profile, auth=TEST_AUTH)
    assert resp.status == 200
    resp_json = await resp.json()
    for key, patch_value in patch_profile['data'].items():
        assert resp_json['data'][key] == patch_value

    resp = await api.get(f'/api/profiles/{profile_id}')
    assert resp.status == 200
    resp_json = await resp.json()
    for key, patch_value in patch_profile['data'].items():
        assert resp_json['data'][key] == patch_value

    patch_profile["data"]["status"] = "active"
    resp = await api.patch(f'/api/profiles/{profile_id}', json=patch_profile, auth=TEST_AUTH)
    assert resp.status == 200
    resp_json = await resp.json()
    assert resp_json['data']['status'] == 'active'
