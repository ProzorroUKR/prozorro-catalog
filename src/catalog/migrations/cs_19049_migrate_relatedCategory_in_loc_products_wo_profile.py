import asyncio

import logging
import sentry_sdk

from pymongo import UpdateOne

from catalog.db import (
    init_mongo,
    transaction_context_manager,
    get_category_collection,
    get_products_collection,
)
from catalog.migrations.cs_16303_requirement_iso_migration import bulk_update
from catalog.utils import get_now
from catalog.logging import setup_logging
from catalog.settings import SENTRY_DSN

logger = logging.getLogger(__name__)

OLD_LOCALIZATION_CATEGORY_ID = "99999999-919912-02426097"

CLASSIFICATION_CATEGORY_MAPPING = {
    "31121100-1": "b480d6e458d04c69a632354d3c9a3903",
    "31121200-2": "575884a53d0248f88c892c6c97c43bec",
    "31124100-2": "36ff2eced4f74199b2873c1935237b5e",
    "31170000-8": "282e73acf44f4442b857da74b4c58505",
    "31171000-5": "282e73acf44f4442b857da74b4c58505",
    "31172000-2": "282e73acf44f4442b857da74b4c58505",
    "31173000-9": "282e73acf44f4442b857da74b4c58505",
    "31174000-6": "282e73acf44f4442b857da74b4c58505",
    "31711150-9": "c09b9eadfd534dfc861d0c2869e55078",
    "31711151-6": "c09b9eadfd534dfc861d0c2869e55078",
    "31711152-3": "c09b9eadfd534dfc861d0c2869e55078",
    "34114121-3": "34114121-810289-425746299",
    "34120000-4": "844d9c5ba1044274ae7c2b3c59356098",
    "34121400-5": "0129fe4d71744095a2165729589867ed",
    "34130000-7": "7f7600cea92a43f7b32b07e72586e8e0",
    "34140000-0": "0064cd5a22474a8fadd893c569c881d5",
    "34142000-4": "0064cd5a22474a8fadd893c569c881d5",
    "34142100-5": "0064cd5a22474a8fadd893c569c881d5",
    "34144000-8": "0064cd5a22474a8fadd893c569c881d5",
    "34144212-7": "0064cd5a22474a8fadd893c569c881d5",
    "34144213-4": "0064cd5a22474a8fadd893c569c881d5",
    "34144430-1": "0064cd5a22474a8fadd893c569c881d5",
    "34144510-6": "0064cd5a22474a8fadd893c569c881d5",
    "34144910-0": "0064cd5a22474a8fadd893c569c881d5",
    "34210000-2": "8c2aef73e3284c90bb3e0e91b8e2cf63",
    "34220000-5": "4095cf3784a34ffd88d208804fe9dc44",
    "34223000-6": "4095cf3784a34ffd88d208804fe9dc44",
    "34223100-7": "4095cf3784a34ffd88d208804fe9dc44",
    "34223300-9": "4095cf3784a34ffd88d208804fe9dc44",
    "34620000-9": "bb68010d9050423fa66f3ef998d4a6b8",
    "34622100-4": "bb68010d9050423fa66f3ef998d4a6b8",
    "34622300-6": "bb68010d9050423fa66f3ef998d4a6b8",
    "34710000-7": "cc64d8c7893344b597130ad5942e96fc",
    "42110000-3": "48fb55d5d8904741a14224c918ef7eb0",
    "42120000-6": "4fb5a54e95ab4b2e88ea547eba9b1a48",
    "42122000-0": "4fb5a54e95ab4b2e88ea547eba9b1a48",
    "42122100-1": "4fb5a54e95ab4b2e88ea547eba9b1a48",
    "42122400-4": "4fb5a54e95ab4b2e88ea547eba9b1a48",
    "42122430-3": "4fb5a54e95ab4b2e88ea547eba9b1a48",
    "42123000-7": "0c334641b4a14238bc823b972b5bea6d",
    "42123100-8": "0c334641b4a14238bc823b972b5bea6d",
    "42123200-9": "0c334641b4a14238bc823b972b5bea6d",
    "42123400-1": "0c334641b4a14238bc823b972b5bea6d",
    "42123500-2": "0c334641b4a14238bc823b972b5bea6d",
    "42990000-2": "95b8b4a0dbbd489c831a5af251502bfc",
    "43210000-8": "8bf6f6edfd584e809bec2c94e343218e",
    "43251000-7": "c51bd072fd174bf9af4830cb2a44dd06",
    "43260000-3": "4be279025a6c4337832943cc7e1d2314",
    "43261000-0": "4be279025a6c4337832943cc7e1d2314",
    "43412000-4": "45b12d7b54614bbe96c671c03fe26c64",
}

UNIQUE_LOCALIZATION_PRODUCTS_MAPPING = {
    "ad64eca10c45464a86d1bf3f846586ae": "4fb5a54e95ab4b2e88ea547eba9b1a48",
    "378037a67fe043f09d672d394c21b331": "4fb5a54e95ab4b2e88ea547eba9b1a48",
    "ea54f6da09e44b26876ea305c7d91b7a": "4fb5a54e95ab4b2e88ea547eba9b1a48",
    "8068a0d621cf4f8aa569bbf5836e856c": "4fb5a54e95ab4b2e88ea547eba9b1a48",
    "a04d58e8ebb3419c8ee7f90bbc7723fb": "4be279025a6c4337832943cc7e1d2314",
    "d8f78a3a4e8b42debc2ca01854fd44bf": "4be279025a6c4337832943cc7e1d2314",
    "7006ad1d1bdf4c4394d221cc75e3d79e": "4fb5a54e95ab4b2e88ea547eba9b1a48",
    "8fd01ccf84434d0ab50cb5d598a4b918": "4095cf3784a34ffd88d208804fe9dc44",
    "2d2bed3752fd46b9bbb6a9b08e2d3006": "95b8b4a0dbbd489c831a5af251502bfc",
    "da7dbad5e5da42ab814ba5ff41591772": "b480d6e458d04c69a632354d3c9a3903",
    "790d0458fc6f4e7e9e591d58a6e97a8a": "31120000-730722-40996564",
    "9832308f705e4804a0f9ce862e688473": "31120000-730722-40996564",
    "dff24046bf9444b68ab47d4bdd3ccbe6": "4be279025a6c4337832943cc7e1d2314",
    "829864d04e7c49cb99715af2dc597d12": "4be279025a6c4337832943cc7e1d2314",
    "3c151ce938334df8a348456d4726624e": "31120000-730722-40996564",
    "8e58d28a05264caea61ba8c9840119c6": "95b8b4a0dbbd489c831a5af251502bfc",
    "74b1d6b5142246e1aec47d82d5790be6": "0064cd5a22474a8fadd893c569c881d5",
    "f882109385674ee9a6361efac989a949": "95b8b4a0dbbd489c831a5af251502bfc",
    "af302b57f9a1467fa60c8c4ded3f1d76": "95b8b4a0dbbd489c831a5af251502bfc",
    "185b90b4c42847e294a3af00cad0eceb": "95b8b4a0dbbd489c831a5af251502bfc",
    "afe6b7c2818a4e47a21d2c61c104d437": "95b8b4a0dbbd489c831a5af251502bfc",
    "1882ed246de743609d09c9f367675385": "282e73acf44f4442b857da74b4c58505",
    "5e96b521a9ed488d9685e4a986f1b17d": "282e73acf44f4442b857da74b4c58505",
    "fc6869bbc2ae4c02bbff01a49e8c934f": "282e73acf44f4442b857da74b4c58505",
    "93845a04e3d44693bd029152492d82aa": "282e73acf44f4442b857da74b4c58505",
    "dd57d26fe121463f839c7dff046d5d1a": "b480d6e458d04c69a632354d3c9a3903",
}


async def migrate():
    logger.info("Start localized products migration of set relatedCategory matched by classification.id")
    counter = 0
    bulk = []
    products_collection = get_products_collection()
    async for product in products_collection.find(
        {
            "relatedCategory": OLD_LOCALIZATION_CATEGORY_ID,
            "status": "active",
        },
        {"classification": 1},
    ):
        if special_category_id := UNIQUE_LOCALIZATION_PRODUCTS_MAPPING.get(product["_id"]):
            category = await get_category_collection().find_one(
                filter={"_id": special_category_id},
                projection={"classification": 1},
            )

            if category:
                bulk.append(
                    UpdateOne(
                        filter={"_id": product["_id"]},
                        update={
                            "$set": {
                                "relatedCategory": UNIQUE_LOCALIZATION_PRODUCTS_MAPPING[product["_id"]],
                                "classification": category["classification"],
                                "dateModified": get_now().isoformat(),
                            }}
                    )
                )
                counter += 1
        else:
            try:
                bulk.append(
                    UpdateOne(
                        filter={"_id": product["_id"]},
                        update={
                            "$set": {
                                "relatedCategory": CLASSIFICATION_CATEGORY_MAPPING[product["classification"]["id"]],
                                "dateModified": get_now().isoformat(),
                            }}
                    )
                )
                counter += 1
            except Exception as e:
                logger.error(f"Profile {product['_id']} with classification {product['classification']['id']} not updated, cause error: {e}")
                raise e

        if bulk and len(bulk) % 500 == 0:
            async with transaction_context_manager() as session:
                await bulk_update(products_collection, bulk, session, counter, migrated_obj="products")
            bulk = []

    if bulk:
        async with transaction_context_manager() as session:
            await bulk_update(products_collection, bulk, session, counter, migrated_obj="products")

    logger.info(f"Finished. Processed {counter} updated products")
    logger.info("Successfully migrated")


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate())


if __name__ == '__main__':
    main()
