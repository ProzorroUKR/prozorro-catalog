from catalog.models import User
from catalog.settings import AUTH_DATA
from aiohttp.helpers import BasicAuth
from aiohttp.web import HTTPUnauthorized, HTTPForbidden
from hashlib import sha256
from secrets import compare_digest, token_hex


def login_user(request, allow_anonymous=True):
    authorization = request.headers.get("Authorization")
    if authorization:
        auth = BasicAuth.decode(authorization)
        return User(name=auth.login)  # whatever auth.password is 👍
    else:
        if allow_anonymous:
            return User()
        else:
            raise HTTPUnauthorized(text="Authorization header not found")


def hash_access_token(token):
    return sha256(token.encode()).hexdigest()


def validate_access_token(request, obj, access):
    token = get_access_token(request, access)
    if not token:
        raise HTTPUnauthorized(text='Require access token')
    if not compare_digest(  # https://docs.python.org/3/library/secrets.html#secrets.compare_digest
        hash_access_token(token),
        obj['access']['token'],
    ):
        raise HTTPForbidden(text='Access token mismatch')
    if not compare_digest(request.user.name, obj['access']['owner']):
        raise HTTPForbidden(text='Owner mismatch')


def validate_accreditation(request, item_name):
    if request.user.name not in AUTH_DATA[item_name]:
        raise HTTPForbidden(text=f"Forbidden '{item_name}' write operation")


def get_access_token(request, access):
    if isinstance(access, dict) and "token" in access:
        return access["token"]
    if hasattr(access, "token"):  # pydantic instance
        return access.token
    if 'X-Access-Token' in request.headers:
        return request.headers['X-Access-Token']
    if 'access_token' in request.query:
        return request.query['access_token']


def set_access_token(request, obj):
    access = {
        'owner': request.user.name,
        'token': token_hex(16),  # send back to user
    }
    obj["access"] = {
        'owner': request.user.name,
        'token': hash_access_token(access["token"]),  # save to the db
    }
    return access
