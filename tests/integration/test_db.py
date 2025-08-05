from unittest.mock import AsyncMock, MagicMock

from bson.timestamp import Timestamp

from catalog.db import wait_until_cluster_time_reached


class IncrementingClusterTimeSession:
    def __init__(self, start_time, target_time):
        self._time = start_time
        self._target = target_time
        self.client = MagicMock()
        self._ping_count = 0

        # підставляємо ping, який змінює cluster_time
        async def ping(*args, **kwargs):
            self._ping_count += 1
            if self._time.time < self._target.time:
                self._time = Timestamp(self._time.time + 1, self._time.inc)
            return {"ok": 1}

        self.client.admin.command = AsyncMock(side_effect=ping)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    @property
    def cluster_time(self):
        return {"clusterTime": self._time}

    def advance_cluster_time(self, val):
        pass

    def advance_operation_time(self, val):
        pass

    @property
    def ping_count(self):
        return self._ping_count


async def test_wait_until_cluster_time_reached_retries():
    start_time = Timestamp(1754313847, 1)
    target_time = Timestamp(1754313850, 1)

    session = IncrementingClusterTimeSession(start_time, target_time)

    await wait_until_cluster_time_reached(session, {"clusterTime": target_time})

    assert session.ping_count >= 3  # перевіряємо, що було щонайменше 3 ping'и
