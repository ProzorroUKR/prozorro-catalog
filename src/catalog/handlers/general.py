import logging
from aiohttp.web import Response
from aiohttp_swagger import swagger_path

from catalog import version as api_version
from catalog.serialization import json_response
logger = logging.getLogger(__name__)


@swagger_path('/swagger/ping.yaml')
async def ping_handler(request):
    return Response(text="pong")


@swagger_path('/swagger/version.yaml')
async def get_version(request):
    return json_response({'api_version': api_version})

