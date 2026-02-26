import asyncio
import json
import logging
from typing import Any
from uuid import uuid4

import sentry_sdk
from aiohttp import ClientSession
from prozorro_crawler.main import run_app
from prozorro_crawler.resource import process_resource
from prozorro_crawler.utils import get_resource_url

from catalog import db
from catalog.db import init_mongo
from catalog.logging import setup_logging
from catalog.models.common import BidUnit, BidUnitValue
from catalog.models.product_bid import ProductBidCreateData
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now

logger = logging.getLogger(__name__)


RESOURCE = "tenders"
TENDERS_URL = get_resource_url(RESOURCE)

async def process_tender(session: ClientSession, tender: dict[str, Any]) -> None:
    if tender is not None and "awardPeriod" in tender and tender["awardPeriod"].get("startDate") is not None and tender.get("procurementMethodType") == "priceQuotation":
        for n, bid in enumerate(tender.get("bids", []), start=1):
            
            if bid.get("status") == "active" and "items" in bid and type(bid["items"]) is list:
                for item in bid["items"]:

                    # Перевіряємо наявність необхідних полів та валідність даних
                    if "unit" in item and "product" in item and "value" in item["unit"] and item["unit"]["value"]["amount"] > 0:
                        product_bid_data = ProductBidCreateData(
                            id=uuid4().hex,
                            tenderId=tender["id"],
                            bidId=bid["id"],
                            itemId=item["id"],
                            productId=item["product"],
                            unit=BidUnit(
                                code=item["unit"]["code"],
                                name=item["unit"]["name"],
                                value=BidUnitValue(
                                    amount=item["unit"]["value"]["amount"],
                                    currency=item["unit"]["value"]["currency"],
                                    valueAddedTaxIncluded=item["unit"]["value"]["valueAddedTaxIncluded"],
                                ),
                                quantity=item["quantity"],
                            ),
                            date=tender["awardPeriod"]["startDate"],
                            lotValueStatus=tender.get("status", ""),
                            dateModified=get_now().isoformat(),
                            dateCreated=get_now().isoformat(),
                        )
                        try:
                            await db.insert_product_bid(product_bid_data.model_dump(exclude_none=True))
                            logger.info(f"Inserted product bid data for item in bid #{n} of tender {tender['id']}")
                        except Exception as e:
                            logger.exception(f"Error inserting product bid data for item in bid #{n}: {e}")

async def item_data_handler(session: ClientSession, items: list[dict[str, Any]]) -> None:
    if items is not None:
        logger.info(f"Processing {len(items)} tenders")
        for item in items:
            await process_resource(session, url=TENDERS_URL, resource_id=item["id"], process_function=process_tender)

async def run_task():
    logger.info("Starting tenders bid crawler")
    await run_app(
            data_handler=item_data_handler,
            json_loads=json.loads,
            opt_fields=["status"],
            resource=RESOURCE,
        )
    
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
