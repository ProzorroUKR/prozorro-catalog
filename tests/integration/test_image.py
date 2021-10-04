from .base import TEST_AUTH
from aiohttp import FormData
from unittest.mock import patch, Mock


file_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00'+\
        b'\x00\x00\x01\x01\x03\x00\x00\x00%\xdbV\xca\x00\x00\x00' +\
        b'\x03PLTE\x00\x00\x00\xa7z=\xda\x00\x00\x00\x01tRNS\x00' +\
        b'@\xe6\xd8f\x00\x00\x00\nIDAT\x08\xd7c`\x00\x00\x00\x02' +\
        b'\x00\x01\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82'


async def test_600_image_create(api):
    data = {'sizes': '10x10', 'title': 'Test image title'}
    resp = await api.post('/api/images', data=data, auth=TEST_AUTH)
    assert resp.status == 400
    assert {'errors': ['multipart/* content type expected']} == await resp.json()

    data = FormData()
    data.add_field('file',
                   file_data,
                   filename='report.xls',
                   content_type='application/vnd.ms-excel')

    uuid_mock = Mock()
    uuid_mock.return_value.hex = "a" * 32
    with patch("catalog.handlers.image.uuid4", uuid_mock):
        resp = await api.post('/api/images', data=data, auth=TEST_AUTH)
    assert resp.status == 201, await resp.json()
    assert {"url": "/static/images/aa/aa/aa/aaaaaaaaaaaaaaaaaaaaaaaaaa.png",
            "hash": "md5:71a50dbba44c78128b221b7df7bb51f1",
            "size": 95} == await resp.json()

    data = FormData()
    data.add_field('file',
                   b"000000000",
                   filename='report.xls',
                   content_type='application/vnd.ms-excel')
    with patch("catalog.handlers.image.uuid4", uuid_mock):
        resp = await api.post('/api/images', data=data, auth=TEST_AUTH)
    assert resp.status == 400
    assert {'errors': ["Not allowed img type: 'None'"]} == await resp.json()
