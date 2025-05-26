import logging
from aiohttp_pydantic.oas.typing import r200
from aiohttp_pydantic.decorator import inject_params
from pydantic import BaseModel

from catalog import version as api_version
from catalog.serialization import json_response
logger = logging.getLogger(__name__)


class PingResponse(BaseModel):
    text: str


class VersionResponse(BaseModel):
    version: str


@inject_params.and_request
async def ping_handler(request) -> r200[PingResponse]:
    """
    This end-point allow to test that service is up.
    Successful operation returns "pong" text

    Tags: Helpers
    """
    return json_response({"text": "pong"})


@inject_params.and_request
async def get_version(request) -> r200[VersionResponse]:
    """
    Get api version

    Tags: Helpers
    """
    return json_response({'api_version': api_version})

