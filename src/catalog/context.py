from contextvars import ContextVar
from catalog.settings import TIMEZONE
from datetime import datetime

request_var = ContextVar('request_var')
now_var = ContextVar('now_var')


def get_request():
    return request_var.get()


def get_request_scheme():
    request = get_request()
    return request.headers.get('X-Forwarded-Proto', request.scheme)


def set_request(request):
    request_var.set(request)


def set_now():
    now_var.set(datetime.now(tz=TIMEZONE))


def get_now() -> datetime:
    return now_var.get()
