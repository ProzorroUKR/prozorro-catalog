from base64 import b64decode
from bson.json_util import loads
from catalog.db import wait_until_cluster_time_reached, get_database
from catalog.serialization import json_response, json_dumps
from aiohttp.web import (
    HTTPInternalServerError,
    HTTPBadRequest
)
from catalog.logging import request_id_var
from catalog.auth import login_user
from catalog.context import set_now, set_request, set_db_session
from aiohttp.web import middleware, HTTPException
from pydantic import ValidationError
from uuid import uuid4
import logging

from catalog.utils import get_session_time

logger = logging.getLogger(__name__)


def json_dumps_validation_error(exc: ValidationError) -> str:
    """Format ValidationError into JSON string with detailed error messages."""
    formatted_errors = []

    for error in exc.errors():
        msg = error["msg"]
        loc = error.get("loc", ())

        if loc:
            field_path = ".".join(str(part) for part in loc if not str(part).startswith(('function-after', 'list')))
            formatted_error = f"{msg}: {field_path}"
        else:
            formatted_error = msg

        formatted_errors.append(formatted_error)

    return json_dumps({"errors": formatted_errors})


@middleware
async def error_middleware(request, handler):
    try:
        response = await handler(request)
    except ValidationError as exc:
        raise HTTPBadRequest(
            content_type="application/json",
            text=json_dumps_validation_error(exc),
        )
    except HTTPException as exc:
        if exc.content_type == "text/plain":
             exc.content_type = "application/json"
             exc.text = json_dumps({"errors": [exc.text]})
        raise exc
    except Exception as exc:
        logger.exception(exc)
        raise HTTPInternalServerError(
            content_type="application/json",
            text=json_dumps({"errors": [str(exc)]}),
        )
    return response


@middleware
async def convert_response_to_json(request, handler):
    """
    convert dicts into valid json responses
    """
    response = await handler(request)
    if isinstance(response, dict):
        status_code = 201 if request.method in ("POST", "PUT") else 200
        response = json_response(response, status=status_code)
    return response


@middleware
async def request_id_middleware(request, handler):
    """
    Sets request_id contextvar and request['request_id']
    :param request:
    :param handler:
    :return:
    """
    value = request.headers.get('X-Request-ID', str(uuid4()))
    request_id_var.set(value)  # for loggers inside context
    response = await handler(request)
    response.headers['X-Request-ID'] = value  # for AccessLogger
    return response


@middleware
async def login_middleware(request, handler):
    request.user = login_user(
        request,
        allow_anonymous=request.method in ("GET", "HEAD") or request.path == "/api/search"
    )
    response = await handler(request)
    return response


@middleware
async def context_middleware(request, handler):
    set_request(request)
    set_now()
    response = await handler(request)
    return response


@middleware
async def db_session_middleware(request, handler):
    """
    Sets db session contextvar
    :param request:
    :param handler:
    :return:
    """
    cookie_name = 'SESSION'
    warning = None
    db = get_database()
    async with await db.client.start_session(causal_consistency=True) as session:
        cookie = request.cookies.get(cookie_name)
        if cookie:
            try:
                values = loads(b64decode(cookie))
                session.advance_cluster_time(values["cluster_time"])  # global time in cluster level
                session.advance_operation_time(values["operation_time"])  # last successful operation time in session

                # adds retry if current cluster time less than cluster time from cookie
                await wait_until_cluster_time_reached(session, values["cluster_time"])
            except Exception as exc:
                warning = f"Error on {cookie_name} cookie parsing: {exc}"
                logger.debug(warning)

        set_db_session(session)
        try:
            response = await handler(request)  # processing request
        finally:
            set_db_session(None)

    if warning:
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Warning
        response.headers["X-Warning"] = f'199 - "{warning}"'

    response.set_cookie(cookie_name, get_session_time(session))
    return response
