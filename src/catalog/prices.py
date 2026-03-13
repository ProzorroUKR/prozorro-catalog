import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List
from uuid import uuid4

import sentry_sdk

from catalog import db
from catalog.db import init_mongo
from catalog.logging import setup_logging
from catalog.models.price import PriceCreateData
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now

logger = logging.getLogger(__name__)


async def calculate_price_for_product(product_id: str, days_back: int = 7) -> List[str]:
    last_price = await db.find_last_price_by_product(product_id)
    last_calculated_date = None

    if last_price and "date" in last_price:
        last_calculated_date = last_price["date"].date()

    start_date = None
    if last_calculated_date:
        start_date = datetime.combine(last_calculated_date - timedelta(days=days_back), datetime.min.time())

    product_bids = await db.find_product_bids_by_product(product_id, start_date=start_date)

    if not product_bids:
        return []

    parsed_bids = []
    for bid in product_bids:
        bid_date = bid["date"]
        parsed_bids.append((bid_date, bid))

    unique_days = sorted(list(set(bd.date() for bd, _ in parsed_bids)))

    if last_calculated_date:
        unique_days = [day for day in unique_days if day > last_calculated_date]

    if not unique_days:
        return []

    def get_quartile(k: int, n: int, sorted_data: list[Decimal]) -> Decimal:
        L = k * (n + 1) / 4.0
        if L <= 1:
            return sorted_data[0]
        if L >= n:
            return sorted_data[-1]

        idx = int(L) - 1
        fraction = Decimal(L - int(L))
        val = sorted_data[idx] + fraction * (sorted_data[idx + 1] - sorted_data[idx])
        return Decimal(str(round(val, 2)))

    inserted_ids = []

    for current_day in unique_days:
        start_day = current_day - timedelta(days=days_back - 1)

        window_bids = [bid for bd, bid in parsed_bids if start_day <= bd.date() <= current_day]

        if not window_bids:
            continue

        amounts = sorted([Decimal(bid["amount"]) for bid in window_bids])
        n = len(amounts)

        q1 = get_quartile(1, n, amounts)
        q2 = get_quartile(2, n, amounts)
        q3 = get_quartile(3, n, amounts)

        name = window_bids[0].get("name")
        code = window_bids[0].get("code")

        current_day_dates = [bd for bd, _ in parsed_bids if bd.date() == current_day]
        max_date_in_day = max(current_day_dates)

        price_data = PriceCreateData(
            id=uuid4().hex,
            productId=product_id,
            code=code,
            name=name,
            date=max_date_in_day,
            sampleSize=n,
            lowerQuartile=q1,
            medianQuartile=q2,
            upperQuartile=q3,
            dateCreated=get_now().isoformat(),
            dateModified=get_now().isoformat(),
        )

        data = price_data.model_dump(exclude_none=True)
        data["dateCreated"] = data["dateCreated"].isoformat()
        data["dateModified"] = data["dateModified"].isoformat()
        inserted_id = await db.insert_price(data)
        inserted_ids.append(inserted_id)

    logger.info(f"Calculated and inserted prices for product {product_id} in {len(inserted_ids)} rows")
    return inserted_ids


async def calculate_price(batch_size: int = 100) -> None:
    last_price = await db.find_last_calculated_price()
    last_calculated_date = None

    if last_price and "date" in last_price:
        last_calculated_date = last_price["dateCreated"]

    skip = 0
    while True:
        product_bids = await db.find_product_bids_group_products(
            limit=batch_size, skip=skip, start_date=last_calculated_date
        )
        count = 0
        async for product_bid in product_bids:
            await calculate_price_for_product(product_bid["_id"])
            count += 1

        if count < batch_size:
            break
        skip += batch_size
    return None


async def full_recalculation() -> None:
    logger.info("Clearing prices collection")
    await db.clear_prices_collection()
    await calculate_price()
    return None


async def run_task():
    logger.info("Starting full price recalculation")
    await full_recalculation()
    logger.info("Finished full price recalculation")

    return None


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(run_task())


if __name__ == "__main__":
    main()
