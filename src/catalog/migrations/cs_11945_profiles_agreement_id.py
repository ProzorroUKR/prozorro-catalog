import asyncio
import logging
import os
import re
from typing import List

import aiohttp

from catalog.db import get_profiles_collection


OPENPROCUREMENT_API_URL = os.environ.get("OPENPROCUREMENT_API_URL", "127.0.0.1")


logger = logging.getLogger(__name__)


def save(profile):
    logger.info(f'saving profile {profile["id"]}')


def agreement_matches_profile(agreement, profile):
    additionalClassifications_matches = (
            {(c['id'], c['scheme']) for c in profile.get('additionalClassifications', "")}
            == {(c['id'], c['scheme']) for c in agreement.get('additionalClassifications', "")}
    )

    return (
        additionalClassifications_matches and
        agreement['agreementType'] == 'electronicCatalogue' and
        profile['access']['owner'] == agreement['procuringEntity']['identifier']['id']
    )


async def migrate_profiles():
    collection = await load_profiles()

    for profile in collection:
        classification_id = profile["classification"]["id"]
        additional_classifications_ids = [c['id'] for c in profile.get('additionalClassifications', "")]

        for next_classification_id in modified_classification_ids(classification_id):
            agreements = await load_agreements_by_classification(next_classification_id, additional_classifications_ids)
            agreements_for_profile = [
                a for a in agreements
                if agreement_matches_profile(a, profile)
            ]
            if len(agreements_for_profile) > 1:
                logger.info(f"too many agreements for {profile['_id']}")
                break
            if not agreements_for_profile:
                continue

            agreement = agreements_for_profile[0]
            profile['agreementId'] = agreement['id']
            save(profile)
            logger.info(f"found agreement_id for profile "
                  f"profile_id={profile['_id']}, "
                  f"agreement_id={agreement['id']}, "
                  f"classification_id={agreement['classification']['id']}")
            break
        else:
            logger.info(f"not found agreements for {profile['_id']}")


async def load_profiles():
    collection = await get_profiles_collection().find(
        {
            "status": {"$ne": "general"},
        }
    ).to_list(None)
    return collection


async def load_agreements_by_classification(classification_id: str, additional_classifications_ids: List[str]):
    classification_id_cleaned = classification_id.split('-')[0]
    additional_classifications_query_string = ",".join(additional_classifications_ids) or 'none'
    async with aiohttp.ClientSession() as session:
        response = await session.get(
            f"https://{OPENPROCUREMENT_API_URL}/api/0/agreements_by_classification/{classification_id_cleaned}?additional_classifications={additional_classifications_query_string}"
        )
        response_data = await response.json()

        agreements = await asyncio.gather(*[
            load_agreement_by_id(session, agreement['id'])
            for agreement in response_data['data']
        ])
    return agreements


async def load_agreement_by_id(session, agreement_id):
    response = await session.get(
        f"https://{OPENPROCUREMENT_API_URL}/api/0/agreements/{agreement_id}"
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
