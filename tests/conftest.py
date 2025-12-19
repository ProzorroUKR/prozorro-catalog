import asyncio
import pytest
from catalog.db import flush_database, init_mongo, get_database


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db(event_loop):
    try:
        await init_mongo()
        yield get_database()
    except Exception:
        await flush_database()
