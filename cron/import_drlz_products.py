import asyncio
import csv
import logging
from collections import defaultdict

import aiohttp
import sentry_sdk
from catalog.db import get_category_collection, init_mongo
from catalog.logging import setup_logging
from catalog.settings import SENTRY_DSN
from catalog.validations import validate_req_response_values

logger = logging.getLogger(__name__)

DRLZ_RESOURCE_API = "https://drlz.info/api/prozorro/medical-product/"
LIMIT = 100
TOKEN = "mecHT-UYS1OjnOyhuguiq9nfgj4bMflrUJWt1SkQ8C4_E_ok9A61iHgkfWjORLvRl6NCn04WTdaDZjpnAEM7nwsw51bj5N4h9a96gicTj92jkvRjahzmN9zXU8b3wmeLUvQ_ddWv4Gwregaytc8IhOi0S6TrR2-4x-KiggkUHm4"
MNN_REQUIREMENT_TITLE = "Класифікація згідно МНН"


CATEGORIES_IDS = (
    "33620000-135646-42574629",
    "33630000-907202-42574629",
)

CSV_FIELD_NAMES = [
    "id",
    "title",
    "Класифікація згідно АТХ",
    "Класифікація згідно МНН",
    "Форма випуску",
    "Доза діючої речовини",
    "Кількість одиниць в упаковці",
    "Тип пакування",
]


async def get_categories_mnn():
    category_collection = get_category_collection()
    mnn_products_list = defaultdict(dict)

    async for category in category_collection.find(
        {"_id": {"$in": CATEGORIES_IDS}},
        no_cursor_timeout=True,
    ):
        for criterion in category.get("criteria", []):
            for req_group in criterion.get("requirementGroups", []):
                category_requirements = {}
                for req in req_group.get("requirements", []):
                    category_requirements[req["title"]] = req
                    if req["title"] == MNN_REQUIREMENT_TITLE:
                        # mnn_products_list.extend([value.lower() for value in req["expectedValues"]])
                        mnn_products_list[req["expectedValues"][0].split()[0]] = category_requirements
    return mnn_products_list


async def get_drlz_products():
    page = 0
    resp_page = None
    mnn_products_list = await get_categories_mnn()
    headers = {"Authorization": f"Bearer {TOKEN}"}  # GitHub actions bot user-agent is being blocked by API
    import os
    logger.info(os.getcwd())

    with open('drlz_products.csv', 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELD_NAMES, extrasaction="ignore")
        writer.writeheader()
        async with aiohttp.ClientSession(headers=headers) as session:
            # while page - 1 != resp_page:
            while page != 248:
                page += 1
                for attempt in range(3):
                    try:
                        logger.info(f"Reading {DRLZ_RESOURCE_API} with page {page} and limit {LIMIT}")
                        async with session.get(
                            DRLZ_RESOURCE_API,
                            params={"page": page, "limit": LIMIT},
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                resp_page = data["page"]

                                for product in data.get("items", []):
                                    responded_criteria = False
                                    requirements = dict()
                                    for req_response in product.get("requirementResponses", []):
                                        if (
                                            req_response.get("requirement") == MNN_REQUIREMENT_TITLE
                                            and req_response.get("values")
                                            and all(value.split()[0] in mnn_products_list.keys() for value in req_response["values"])
                                        ):
                                            logger.info(f"Product processing {product['identifier']['id']}")
                                            requirements = mnn_products_list[req_response["values"][0].split()[0]]
                                        else:
                                            continue
                                    if requirements:
                                        product_data = {
                                            "id": product["identifier"]["id"],
                                            "title": product["title"],
                                        }
                                        for req_response in product.get("requirementResponses", []):
                                            req_title = req_response.get("requirement")
                                            if requirement := requirements.get(req_title):
                                                try:
                                                    values = req_response.get("values", [])
                                                    if req_title == "Доза діючої речовини":
                                                        values = [value["strength"]["presentationRatio"] for value in req_response["values"]]
                                                    validate_req_response_values(requirement, values, req_title)
                                                    responded_criteria = True
                                                    product_data[req_title] = "+"
                                                except aiohttp.web.HTTPBadRequest as e:
                                                    product_data[req_title] = "-"
                                            else:
                                                logger.info(f"Product {product['identifier']['id']} have weird response {req_response.get("requirement")}")
                                    if responded_criteria:
                                        writer.writerow(product_data)
                                        logger.info(f"Product fits {product['identifier']['id']}")
                                break

                            else:
                                logger.error(
                                    f"Response from resource {DRLZ_RESOURCE_API}: {response.status} - {await response.text()}"
                                )
                                break

                    except aiohttp.ClientResponseError as e:
                        logger.error(f"HTTP error during importing products: {e.status}")
                        break
                    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                        logger.error(f"Network issue (attempt {attempt + 1}/3): {e}")
                        await asyncio.sleep(2)
                    except Exception as e:
                        logger.error(f"Another exception: {e}")
                        break
                if page == 248:
                    print(page)
                    print(resp_page)
                    print(page == resp_page)


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(get_drlz_products())


if __name__ == '__main__':
    main()
