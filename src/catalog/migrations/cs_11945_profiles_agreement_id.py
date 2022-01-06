import asyncio
import logging
import os
import re
from dataclasses import dataclass
from typing import List

import aiohttp

from catalog.db import get_profiles_collection, update_profile, rename_id


OPENPROCUREMENT_API_URL = os.environ.get("OPENPROCUREMENT_API_URL", "http://127.0.0.1:8000/api/0")


logger = logging.getLogger(__name__)

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
            profile.get('additionalClassifications', "") == agreement.get('additionalClassifications', "")
    )

    return (
        additionalClassifications_matches and
        agreement['agreementType'] == 'electronicCatalogue' and
        profile['access']['owner'] == agreement['procuringEntity']['identifier']['id']
    )


async def migrate_profiles():
    logger.info("Start migration.")
    # profiles = await load_profiles()

    counters = Counters()

    async for profile in load_profiles():
        profile = rename_id(profile)
        new_counter = await migrate_profile(profile)
        counters += new_counter
        if counters.total_profiles % 100 == 0:
            logger.info(f"Migration in progress. {counters}")
    logger.info(f"Migration finished. {counters}")
    return counters


async def migrate_profile(profile) -> Counters:
    if profile.get('agreementID'):
        logger.debug(f'skipping profile {profile["id"]}. agreementID already exists.')
        return Counters(skipped_profiles=1)

    classification_id = profile["classification"]["id"]
    additional_classifications_ids = [c['id'] for c in profile.get('additionalClassifications', "")]
    for next_classification_id in modified_classification_ids(classification_id):
        agreements = await load_agreements_by_classification(next_classification_id, additional_classifications_ids)
        agreements_for_profile = [
            a for a in agreements
            if agreement_matches_profile(a, profile)
        ]
        if len(agreements_for_profile) > 1:
            logger.debug(f"too many agreements for {profile['id']}")
            return Counters(too_many_agreement_profiles=1)
        if not agreements_for_profile:
            continue

        agreement = agreements_for_profile[0]
        profile['agreementID'] = agreement['id']
        await update_profile(profile)
        logger.debug(f"found agreement_id for profile "
                    f"profile_id={profile['id']}, "
                    f"agreement_id={agreement['id']}, "
                    f"classification_id={agreement['classification']['id']}")
        return Counters(succeeded_profiles=1)
    else:
        logger.debug(f"not found agreements for {profile['id']}")
        return Counters(no_agreement_profiles=1)


def load_profiles():
    return get_profiles_collection().find(
        {
            "status": {"$ne": "general"},
        }
    )


async def load_agreements_by_classification(classification_id: str, additional_classifications_ids: List[str]):
    classification_id_cleaned = classification_id.split('-')[0]
    additional_classifications_query_string = ",".join(additional_classifications_ids) or 'none'
    async with aiohttp.ClientSession() as session:
        response = await session.get(
            f"{OPENPROCUREMENT_API_URL}/agreements_by_classification/{classification_id_cleaned}?additional_classifications={additional_classifications_query_string}"
        )
        response_data = await response.json()

        agreements = await asyncio.gather(*[
            load_agreement_by_id(session, agreement['id'])
            for agreement in response_data['data']
        ])
    return agreements


async def load_agreement_by_id(session, agreement_id):
    response = await session.get(
        f"{OPENPROCUREMENT_API_URL}/agreements/{agreement_id}"
    )
    response_data = await response.json()
    return response_data['data']


c_id_re = re.compile(r'(\d{2,})[1-9](.*)')


def modified_classification_ids(classification_id):
    while True:
        yield classification_id
        match = c_id_re.match(classification_id)
        if not match:
            return
        classification_id = f"{match[1]}0{match[2]}"
