import argparse
import asyncio
import logging
from unittest.mock import Mock

import sentry_sdk
from catalog.context import set_request
from catalog.db import get_products_collection, init_mongo, transaction_context_manager
from catalog.logging import setup_logging
from catalog.migrations.cs_16303_requirement_iso_migration import bulk_update
from catalog.models.document import DocumentPostData
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now
from pymongo import UpdateOne

logger = logging.getLogger(__name__)


async def migrate_products(document):
    logger.info("Start products migration")
    counter = 0
    bulk = []
    products_collection = get_products_collection()
    async for product in products_collection.find(
        {
            "$and": [
                {"vendor": {"$exists": True}},
                {"status": "active"},
                {"dateCreated": {"$lt": "2025-12-12"}},
                {
                    "$or": [
                        {"documents": {"$exists": False}},
                        {
                            "$expr": {
                                "$lt": [
                                    {
                                        "$size": {
                                            "$filter": {
                                                "input": "$documents",
                                                "as": "file",
                                                "cond": {
                                                    "$ne": ["$$file.title", "sign.p7s"]
                                                },
                                            }
                                        }
                                    },
                                    6,
                                ]
                            }
                        },
                    ]
                },
            ]
        },
    ):
        now = get_now().isoformat()
        documents = product.get("documents", [])

        documents.append(
            {
                **document,
                "url": document["url"].format(product_id=product["_id"]),
                "dateModified": now,
                "datePublished": now,
            }
        )
        bulk.append(
            UpdateOne(
                filter={"_id": product["_id"]},
                update={
                    "$set": {
                        "status": "inactive",
                        "documents": documents,
                        "dateModified": now,
                        "expirationDate": now,
                    }
                },
            )
        )
        counter += 1

        if bulk and len(bulk) % 500 == 0:
            async with transaction_context_manager() as session:
                await bulk_update(
                    products_collection, bulk, session, counter, migrated_obj="products"
                )
            bulk = []

    if bulk:
        async with transaction_context_manager() as session:
            await bulk_update(
                products_collection, bulk, session, counter, migrated_obj="products"
            )

    logger.info(f"Finished. Processed {counter} updated products")
    logger.info("Successfully migrated")


async def migrate(args):
    document  = {
        "hash": args.doc_hash,
        "title": args.doc_title,
        "format": args.doc_format,
        "url": args.doc_url,
    }
    set_request(Mock(path="/api/products/{product_id}/documents"))
    document = DocumentPostData.process_url(document)
    await migrate_products(document)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--doc_hash",
        type=str,
        help="Document hash",
        required=True,
    )
    parser.add_argument(
        "--doc_title",
        type=str,
        help="Document title",
        required=True,
    )
    parser.add_argument(
        "--doc_format",
        type=str,
        help="Document format",
        required=True,
    )
    parser.add_argument(
        "--doc_url",
        type=str,
        help="Document url",
        required=True,
    )

    return parser.parse_args()


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate(parse_args()))


if __name__ == "__main__":
    main()
