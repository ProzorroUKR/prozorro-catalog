from copy import deepcopy
from urllib.parse import quote
from uuid import uuid4
from .base import TEST_AUTH, TEST_AUTH_NO_PERMISSION, TEST_AUTH_ANOTHER


async def test_510_offer_create(api, product):
    product_id = product['data']['id']
    test_offer = {"data": api.get_fixture_json('offer')}
    test_offer['data']['relatedProduct'] = product_id
    valid_offer = deepcopy(test_offer)

    offer_id = uuid4().hex
    resp = await api.patch('/api/offers/%s' % offer_id, json=test_offer, auth=TEST_AUTH)
    assert resp.status == 404

    test_offer['data']['value']['currency'] = 'USD'

    resp = await api.put('/api/offers/%s' % offer_id, json=test_offer, auth=TEST_AUTH)
    assert resp.status == 400, await resp.json()
    assert {'errors': ['value.currency mismatch']} == await resp.json()

    test_offer['data']['value']['currency'] = 'UAH'
    test_offer['data']['minOrderValue']['amount'] = 1

    resp = await api.put('/api/offers/%s' % offer_id, json=test_offer, auth=TEST_AUTH)
    assert resp.status == 400
    assert {'errors': ['minOrderValue.amount mismatch']} == await resp.json()

    test_offer['data']['minOrderValue']['amount'] = 500
    test_offer['data']['minOrderValue']['currency'] = 'USD'

    resp = await api.put('/api/offers/%s' % offer_id, json=test_offer, auth=TEST_AUTH)
    assert resp.status == 400
    assert {'errors': ['minOrderValue.currency mismatch']} == await resp.json()
    test_offer['data']['minOrderValue']['currency'] = 'UAH'

    test_offer['data']['suppliers'][0]['scale'] = 'Rx'
    test_offer['data']['value']['currency'] = 'AIR'
    test_offer['data']['deliveryAddresses'][0]["region"] = 'Київ'
    test_offer['data']["suppliers"][0]['address']["region"] = 'Київ'
    resp = await api.put('/api/offers/%s' % offer_id, json=test_offer, auth=TEST_AUTH)
    assert resp.status == 400
    errors = {'errors': [
        'must be one of classifiers/ua_regions.json: deliveryAddresses.0.region',
        'must be one of organizations/scale.json keys: suppliers.0.scale',
        'must be one of classifiers/ua_regions.json: suppliers.0.address.region',
        'must be one of codelists/tender/tender_currency.json keys: value.currency'
    ]}
    assert errors == await resp.json()

    resp = await api.put('/api/offers/%s' % offer_id, json=valid_offer, auth=TEST_AUTH)
    assert resp.status == 201
    resp_json = await resp.json()
    assert resp_json['data']['id'] == offer_id
    assert 'access' in resp_json
    assert 'token' in resp_json['access']
    test_date_modified = resp_json['data']['dateModified']

    # insert second with the same id
    resp = await api.put('/api/offers/%s' % offer_id, json=valid_offer, auth=TEST_AUTH)
    assert resp.status == 400, await resp.json()
    assert {'errors': [f'Document with id {offer_id} already exists']} == await resp.json()

    resp = await api.get('/api/offers')
    assert resp.status == 200
    resp_json = await resp.json()
    assert len(resp_json['data']) > 0
    assert set(resp_json['data'][0].keys()) == {'id', 'dateModified'}
    assert offer_id in [i['id'] for i in resp_json['data']]
    items = [i for i in resp_json['data'] if i['id'] == offer_id]
    assert len(items) == 1
    assert items[0]['dateModified'] == test_date_modified

    resp = await api.get('/api/offers?offset=' + quote(resp_json['data'][-1]['dateModified']))
    assert resp.status == 200
    resp_json = await resp.json()
    assert len(resp_json['data']) == 0

    resp = await api.get('/api/offers/%s' % offer_id)
    assert resp.status == 200
    resp_json = await resp.json()
    assert resp_json['data']['id'] == offer_id


async def test_520_offer_invalid(api, product):
    test_offer = {"data": api.get_fixture_json('offer')}
    product_id = product['data']['id']
    offer_id = uuid4().hex

    test_offer['data']['relatedProduct'] = product_id
    test_offer['data']['dateModified'] = '2019-01-01T20:20:20.000+02:00'

    resp = await api.put('/api/offers/%s' % offer_id, json=test_offer, auth=TEST_AUTH)
    assert resp.status == 400
    assert {'errors': ['extra fields not permitted: dateModified']} == await resp.json()
    test_offer['data'].pop('dateModified')

    test_offer['data']['relatedProduct'] = product_id + '0'
    resp = await api.put('/api/offers/%s' % offer_id, json=test_offer, auth=TEST_AUTH)
    assert resp.status == 404
    assert {'errors': ['Product not found']} == await resp.json()

    test_offer['data']['relatedProduct'] = product_id
    test_offer['data']['value']['amount'] += 10000

    resp = await api.put('/api/offers/%s' % offer_id, json=test_offer, auth=TEST_AUTH)
    assert resp.status == 400
    assert {'errors': ['value.amount mismatch']} == await resp.json()

    test_offer['data']['value']['amount'] -= 10000
    test_offer['data'].pop('status')

    resp = await api.put('/api/offers/%s' % offer_id, json=test_offer, auth=TEST_AUTH)
    assert resp.status == 400
    assert {'errors': ['field required: status']} == await resp.json()


async def test_530_offer_patch(api, offer):
    test_offer = {"data": api.get_fixture_json('offer')}
    offer_id = offer["data"]["id"]

    test_offer['data']['id'] = offer_id

    resp = await api.get('/api/offers/%s' % offer_id)
    assert resp.status == 200
    resp_json = await resp.json()
    assert offer_id == resp_json['data']['id']

    resp = await api.patch('/api/offers/%s' % offer_id, json={"data": {}}, auth=TEST_AUTH)
    assert resp.status == 401

    resp = await api.patch(
        '/api/offers/%s' % offer_id,
        json={
            "data": {},
            "access": {"token": "a" * 32}
        },
        auth=TEST_AUTH
    )
    assert resp.status == 403

    patch_offer_bad = {
        "data": {
            "id": "unknown"
        },
        "access": offer['access']
    }
    resp = await api.patch('/api/offers/%s' % offer_id, json=patch_offer_bad, auth=TEST_AUTH)
    assert resp.status == 400

    patch_offer = {
        "data": {
            "comment": "Доставка тільки по Києву на наступний день",
            "value": {
                "amount": 33,
                "currency": "UAH",
                "valueAddedTaxIncluded": True
            }
        },
        "access": offer['access']
    }

    resp = await api.patch('/api/offers/%s' % offer_id, json=patch_offer, auth=TEST_AUTH)
    assert resp.status == 200
    resp_json = await resp.json()
    for key, patch_value in patch_offer['data'].items():
        assert str(resp_json['data'][key]) == str(patch_value)

    patch_offer = {
        "data": {
            "deliveryAddresses": [
                {
                    "countryName": "Україна",
                    "locality": "Київ"
                }
            ],
        },
        "access": offer['access']
    }

    resp = await api.patch('/api/offers/%s' % offer_id, json=patch_offer, auth=TEST_AUTH)
    assert resp.status == 200
    resp_json = await resp.json()
    assert str(resp_json['data']['deliveryAddresses']) == str([
        {
            "countryName": "Україна",
            "locality": "Київ"
        }
    ]
)
    test_date_modified = resp_json['data']['dateModified']

    resp = await api.get('/api/offers')
    assert resp.status == 200
    resp_json = await resp.json()
    assert len(resp_json['data']) > 0
    items = [i for i in resp_json['data'] if i['id'] == offer_id]
    assert len(items) == 1
    assert items[0]['dateModified'] == test_date_modified

    resp = await api.get('/api/offers/%s' % offer_id)
    assert resp.status == 200
    resp_json = await resp.json()
    for key, patch_value in patch_offer['data'].items():
        assert str(resp_json['data'][key]) == str(patch_value)


async def test_540_offer_limit_offset(api, product):
    test_offer = {"data": api.get_fixture_json('offer')}
    test_offer['data']['relatedProduct'] = product["data"]["id"]

    test_offer_map = {}
    for i in range(11):
        test_offer_copy = deepcopy(test_offer)
        test_offer_copy['data']['suppliers'][0]['identifier']['id'] = "32490244"
        test_offer_copy['data']['comment'] += " copy {}".format(i + 1)
        offer_id = uuid4().hex

        resp = await api.put('/api/offers/%s' % offer_id, json=test_offer_copy, auth=TEST_AUTH)
        assert resp.status == 201
        resp_json = await resp.json()
        assert resp_json['data']['id'] == offer_id
        assert 'access' in resp_json
        assert 'token' in resp_json['access']

        test_offer_map[offer_id] = resp_json['data']['dateModified']

    resp = await api.get('/api/offers?reverse=1')
    assert resp.status == 200
    resp_json = await resp.json()
    assert len(resp_json['data']) > 10
    prev = resp_json['data'][0]
    assert test_offer_map[prev['id']] == prev['dateModified']
    for item in resp_json['data'][1:]:
        assert prev['dateModified'] > item['dateModified']
        assert test_offer_map[item['id']] == item['dateModified']

    offset = ''
    while True:
        resp = await api.get('/api/offers?limit=5&offset=' + quote(offset))
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
        assert test_offer_map.pop(prev['id']) == prev['dateModified']
        for item in resp_json['data'][1:]:
            assert prev['dateModified'] < item['dateModified']
            assert test_offer_map.pop(item['id']) == item['dateModified']

    assert len(test_offer_map) == 0
