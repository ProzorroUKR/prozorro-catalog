import asyncio
import logging
import re
import traceback
from dataclasses import dataclass
from typing import List

import aiohttp
import sentry_sdk

from catalog.db import get_profiles_collection, update_profile, rename_id, init_mongo
from catalog.logging import setup_logging
from catalog.settings import OPENPROCUREMENT_API_URL, SENTRY_DSN

logger = logging.getLogger(__name__)
CLASSIFICATION_ID_RE = re.compile(r"(\d{2,})[1-9](.*)")


@dataclass
class Counters:
    total_profiles: int = 0
    succeeded_profiles: int = 0
    skipped_profiles: int = 0
    no_agreement_profiles: int = 0
    too_many_agreement_profiles: int = 0

    def __post_init__(self):
        self.total_profiles = self.total_profiles or (
            self.succeeded_profiles +
            self.skipped_profiles +
            self.no_agreement_profiles +
            self.too_many_agreement_profiles
        )

    def __add__(self, other):
        return Counters(
            self.total_profiles + other.total_profiles,
            self.succeeded_profiles + other.succeeded_profiles,
            self.skipped_profiles + other.skipped_profiles,
            self.no_agreement_profiles + other.no_agreement_profiles,
            self.too_many_agreement_profiles + other.too_many_agreement_profiles,
        )


def agreement_matches_profile(agreement, profile):
    additionalClassifications_matches = (
        profile.get("additionalClassifications", []) == agreement.get("additionalClassifications", [])
    )

    return (
        additionalClassifications_matches and
        agreement["agreementType"] == "electronicCatalogue" and
        agreement["status"] == "active" and
        profile["access"]["owner"] == agreement["procuringEntity"]["identifier"]["id"]
    )


async def migrate_profiles():
    logger.info("Start migration.")
    counters = Counters()

    async for profile in load_profiles():
        profile = rename_id(profile)
        try:
            new_counter = await migrate_profile(profile)
        except Exception as e:
            logger.debug(f"Failed {profile['id']}. Caught {type(e).__name__}.")
            traceback.print_exc()
            new_counter = Counters(skipped_profiles=1)
        counters += new_counter
        if counters.total_profiles % 100 == 0:
            logger.info(f"Migration in progress. {counters}")
    logger.info(f"Migration finished. {counters}")
    return counters


async def migrate_profile(profile) -> Counters:
    if profile.get("agreementID"):
        logger.debug(f"Skipped {profile['id']}. agreementID already exists.")
        return Counters(skipped_profiles=1)

    classification_id = profile["classification"]["id"]
    additional_classifications_ids = [c["id"] for c in profile.get("additionalClassifications", "")]
    for next_classification_id in modified_classification_ids(classification_id):
        logger.debug(f"Trying {next_classification_id} for {profile['id']}.")
        agreements = await load_agreements_by_classification(next_classification_id, additional_classifications_ids)
        agreements_for_profile = [
            a for a in agreements
            if agreement_matches_profile(a, profile)
        ]
        if len(agreements_for_profile) > 1:
            logger.debug(f"Failed {profile['id']}. Too many agreements for {profile['id']} at {next_classification_id}.")
            return Counters(too_many_agreement_profiles=1)
        elif not agreements_for_profile:
            logger.debug(f"Round failed. Found no agreements with {next_classification_id} for {profile['id']}.")
            continue

        agreement = agreements_for_profile[0]
        profile["agreementID"] = agreement["id"]
        await update_profile(profile)
        logger.debug(f"Resolved {profile['id']}. Found agreement_id for profile "
                    f"agreement_id={agreement['id']}, "
                    f"classification_id={agreement['classification']['id']}")
        return Counters(succeeded_profiles=1)
    logger.debug(f"Failed {profile['id']}. Not found agreements for {profile['id']}.")
    return Counters(no_agreement_profiles=1)


def load_profiles():
    return get_profiles_collection().find(
        {
            "status": {"$ne": "general"},
        }
    )


async def load_agreements_by_classification(classification_id: str, additional_classifications_ids: List[str]):
    classification_id_cleaned = classification_id.split("-")[0]
    additional_classifications_query_string = ",".join(additional_classifications_ids) or "none"
    async with aiohttp.ClientSession() as session:
        response = await session.get(
            f"{OPENPROCUREMENT_API_URL}/agreements_by_classification/{classification_id_cleaned}"
            f"?additional_classifications={additional_classifications_query_string}"
        )
        if response.status != 200:
            logger.info(f"Received {response.status} on {response.url}")
            return []
        response_data = await response.json()

        agreements = await asyncio.gather(*[
            load_agreement_by_id(session, agreement["id"])
            for agreement in response_data["data"]
        ])
    return [a for a in agreements if a]


async def load_agreement_by_id(session, agreement_id):
    response = await session.get(
        f"{OPENPROCUREMENT_API_URL}/agreements/{agreement_id}"
    )
    if response.status != 200:
        logger.info(f"Received {response.status} on {response.url}")
        return None
    response_data = await response.json()
    return response_data["data"]


async def ensure_api_accessibility():
    async with aiohttp.ClientSession() as session:
        response = await session.get(
            f"{OPENPROCUREMENT_API_URL}/agreements"
        )
        if response.status != 200:
            return False
        response_data = (await response.json()) or {}
        if not response_data or "data" not in response_data:
            return False
    return True


def modified_classification_ids(classification_id):
    while True:
        yield classification_id
        match = CLASSIFICATION_ID_RE.match(classification_id)
        if not match:
            return
        classification_id = f"{match[1]}0{match[2]}"


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    is_api_accessible = loop.run_until_complete(ensure_api_accessibility())
    if not is_api_accessible:
        logger.warning(f"Cannot retrieve any agreements from {OPENPROCUREMENT_API_URL}.")
    else:
        logger.info(f"Api {OPENPROCUREMENT_API_URL} accessible.")

    loop.run_until_complete(migrate_profiles())


if __name__ == '__main__':
    main()
