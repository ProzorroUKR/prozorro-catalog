import json

from aiohttp import web

from catalog.serialization import json_response, json_dumps
from aiohttp.web import (
    HTTPInternalServerError,
    HTTPBadRequest
)
from catalog.logging import request_id_var
from catalog.auth import login_user
from catalog.context import set_now, set_request
from json import JSONDecodeError
from aiohttp.web import middleware, HTTPException
from pydantic import ValidationError
from uuid import uuid4
import logging


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
    except JSONDecodeError as exc:
        raise HTTPBadRequest(
            content_type="application/json",
            text=json_dumps({"errors": [f"Bad request: required valid json body. {exc}"]}),
        )
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
