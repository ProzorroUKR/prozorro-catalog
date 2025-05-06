import asyncio
import csv
import hashlib
import io
import logging
from uuid import uuid4

from jsonpatch import make_patch
from jsonpointer import resolve_pointer
from hashlib import sha256
from json import dumps
from unittest.mock import ANY
from urllib.parse import quote
from aiocache import cached as aiocache_cached
from aiohttp.hdrs import CONTENT_DISPOSITION, CONTENT_TYPE
from aiohttp.web import Response, HTTPBadRequest, HTTPNotFound
from catalog.settings import IS_TEST, TIMEZONE
from datetime import datetime

logger = logging.getLogger(__name__)


def get_now(tz=TIMEZONE):
    return datetime.now(tz=tz)


def get_int_from_query(request, key, default=0):
    value = request.query.get(key, default)
    try:
        value = int(value)
    except ValueError as e:
        logger.exception(e)
        raise HTTPBadRequest(text=f"Can't parse {key} from value: '{value}'")
    else:
        return value


def pagination_params(request, default_limit=100):
    q = request.query
    offset = q.get("offset", "")
    limit = get_int_from_query(request, "limit", default=default_limit)
    reverse = bool(q.get('reverse') or get_int_from_query(request, "descending"))
    return offset, limit, reverse


def requests_params(request, *args):
    params = {}
    for param in args:
        params[param] = request.query.get(param)
    return params


def requests_sequence_params(request, *args, separator=None):
    params = {}
    for param in args:
        value = request.query.get(param)
        if value:
            params[param] = value.split("," if not separator else separator)
    return params


def remove_keys(obj, keys):
    return {key: value for key, value in obj.items() if key not in keys}


def build_content_disposition_name(file_name):
    try:
        file_name.encode('ascii')
        file_expr = 'filename="{}"'.format(file_name)
    except UnicodeEncodeError:
        file_expr = "filename*=utf-8''{}".format(quote(file_name))
    return f'attachment; {file_expr}'


def csv_response(name, fieldnames, rows):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(convert_lists(row))
    buffer.seek(0)

    response = Response(body=buffer)
    if not name.endswith(".csv"):
        name += ".csv"
    response.headers[CONTENT_DISPOSITION] = build_content_disposition_name(name)
    response.headers[CONTENT_TYPE] = "text/csv"
    return response


def convert_lists(row):
    return {k: ", ".join(v) if isinstance(v, list) else v for k, v in row.items()}


def cached(*args, **kwargs):
    if IS_TEST:
        return lambda f: f  # disable cache
    return aiocache_cached(*args, **kwargs)


def async_retry(tries=-1, exceptions=Exception,
                delay=0, max_delay=None, backoff=1, fail_exception=None):
    def func_wrapper(f):
        async def wrapper(*args, **kwargs):
            _tries, _delay = tries, delay
            if callable(_delay):
                _delay = _delay()
            while True:
                try:
                    result = await f(*args, **kwargs)
                except exceptions as exc:
                    _tries -= 1
                    if not _tries:
                        logger.exception(exc)
                        raise fail_exception or exc
                    else:
                        logger.warning(
                            f"Retry {f} in {_delay}s because of {exc}")
                        await asyncio.sleep(_delay)

                        _delay *= backoff
                        if max_delay is not None:
                            _delay = min(_delay, max_delay)
                else:
                    return result
        return wrapper
    return func_wrapper


def create_md5_hash(string):
    result = hashlib.md5(string.encode())
    return result.hexdigest()


def find_item_by_id(items, item_id, item_name):
    for item in items:
        if item["id"] == item_id:
            return item
    raise HTTPNotFound(text=f"{item_name} with id {item_id} not found")


def delete_sent_none_values(data, json):
    for key in json:
        if key in data and json[key] is None:
            del data[key]


def find_contributor_ban(contributor, ban_id):
    for ban in contributor.get("bans", ""):
        if ban["id"] == ban_id:
            return ban
    else:
        raise HTTPNotFound(text="Ban not found")


def generate_revision(obj, patch, author, date=None):
    return {
        "author": author,
        "changes": patch,
        "rev": obj.get("rev"),
        "date": (date or get_now()).isoformat(),
    }


def append_revision(request, obj, patch, date=None):
    author = request.user.name
    revision_data = generate_revision(obj, patch, author, date)
    if "revisions" not in obj:
        obj["revisions"] = []
    obj["revisions"].append(revision_data)
    return obj["revisions"]


def append_obj_revision(request, obj, patch, date):
    status_changes = [p for p in patch if all([p["path"].endswith("/status"), p["op"] == "replace"])]
    changed_obj = obj
    for change in status_changes:
        changed_obj = resolve_pointer(obj, change["path"].replace("/status", ""))
        if changed_obj and hasattr(changed_obj, "date") and hasattr(changed_obj, "revisions"):
            date_path = change["path"].replace("/status", "/date")
            if changed_obj.date and not any(p for p in patch if date_path == p["path"]):
                patch.append(
                    {
                        "op": "replace",
                        "path": date_path,
                        "value": changed_obj.date.isoformat(),
                    }
                )
            elif not changed_obj.date:
                patch.append({"op": "remove", "path": date_path})
            changed_obj.date = date
        else:
            changed_obj = obj
    return append_revision(request, changed_obj, patch)


def get_revision_changes(request, new_obj, old_obj=None):
    if old_obj is None:
        old_obj = dict()
    patch = make_patch(new_obj, old_obj).patch
    if patch:
        now = get_now()
        append_obj_revision(request, new_obj, patch, now)


def get_next_rev(current_rev=None):
    """
    This mimics couchdb _rev field
    that prevents concurrent updates
    :param current_rev:
    :return:
    """
    if current_rev:
        version, _ = current_rev.split("-")
        version = int(version)
    else:
        version = 1
    next_rev = f"{version + 1}-{uuid4().hex}"
    return next_rev
