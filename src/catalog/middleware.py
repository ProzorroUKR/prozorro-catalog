from catalog.serialization import json_response, json_dumps
from aiohttp.web import (
    HTTPUnprocessableEntity,
    HTTPInternalServerError,
    HTTPBadRequest
)
from catalog.logging import request_id_var
from catalog.auth import login_user
from json import JSONDecodeError
from aiohttp.web import middleware, HTTPException
from pydantic import ValidationError
from uuid import uuid4
import logging


logger = logging.getLogger(__name__)


@middleware
async def error_middleware(request, handler):
    try:
        response = await handler(request)
    except ValidationError as exc:
        text = json_dumps(dict(errors=[
            f"{e['msg']}: {'.'.join(str(part) for part in e['loc'])}"
            for e in exc.errors()
        ]))
        return HTTPBadRequest(
            text=text,
            content_type="application/json",
        )
    except Exception as exc:
        if isinstance(exc, HTTPException) and exc.content_type == "text/plain":
             exc.content_type = "application/json"
             exc.text = json_dumps({"errors": [exc.text]})
             raise exc
        elif isinstance(exc, JSONDecodeError):
            return HTTPBadRequest(
                content_type="application/json",
                text=json_dumps({"errors": [f"Bad request: required valid json body. {exc}"]})
            )
        logger.exception(exc)
        return HTTPInternalServerError(
            text=json_dumps({"errors": [str(exc)]}),
            content_type="application/json",
        )
    else:
        return response


@middleware
async def request_unpack_params(request, handler):
    """
    middleware for the func views
    to pass variables from url
    as kwargs
    """
    if 'swagger' in request.path or '/static/' in request.path:
        return await handler(request)
    return await handler(request, **request.match_info)


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
    request.user = login_user(request, allow_anonymous=request.method in ("GET", "HEAD"))
    response = await handler(request)
    return response
