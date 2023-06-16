from copy import deepcopy
from urllib.parse import quote
from uuid import uuid4
from catalog.db import get_offers_collection, insert_object
from catalog.utils import get_now
from .base import TEST_AUTH


async def test_540_offer_limit_offset(api, product):
    test_offer = api.get_fixture_json('offer')
    test_offer['relatedProduct'] = product["data"]["id"]

    test_offer_map = {}
    for i in range(11):
        test_offer_copy = deepcopy(test_offer)
        test_offer_copy['suppliers'][0]['identifier']['id'] = "32490244"
        test_offer_copy['comment'] += " copy {}".format(i + 1)
        test_offer_copy['id'] = offer_id = uuid4().hex
        test_offer_copy['dateModified'] = get_now().isoformat()

        await insert_object(get_offers_collection(), test_offer_copy)

        resp = await api.get(f'/api/offers/{offer_id }')
        assert resp.status == 200
        resp_json = await resp.json()
        assert resp_json['data']['id'] == offer_id

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
    prev_resp_next = None
    while True:
        resp = await api.get('/api/offers?limit=5&offset=' + quote(offset))
        assert resp.status == 200
        resp_json = await resp.json()
        if len(resp_json['data']) == 0:
            assert prev_resp_next == resp_json["next_page"]
            break
        assert 'next_page' in resp_json
        prev_resp_next = resp_json["next_page"]
        assert 'offset' in resp_json['next_page']
        offset = resp_json['next_page']['offset']

        assert len(resp_json['data']) <= 5
        prev = resp_json['data'][0]
        assert test_offer_map.pop(prev['id']) == prev['dateModified']
        for item in resp_json['data'][1:]:
            assert prev['dateModified'] < item['dateModified']
            assert test_offer_map.pop(item['id']) == item['dateModified']

    assert len(test_offer_map) == 0
