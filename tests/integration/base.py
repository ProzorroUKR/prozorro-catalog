from aiohttp.helpers import BasicAuth


TEST_AUTH = BasicAuth("test.prozorro.ua", "")
TEST_AUTH_ANOTHER = BasicAuth("zakupki.prom.ua", "")
TEST_AUTH_NO_PERMISSION = BasicAuth("booking.uz.gov.ua", "")
