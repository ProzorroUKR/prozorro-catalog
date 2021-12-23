import os
import re

import aiohttp

from catalog.db import get_profiles_collection


OPENPROCUREMENT_API_URL = os.environ.get("OPENPROCUREMENT_API_URL", "http://127.0.0.1:8000")


def save(profile):
    print(f'saving profile {profile["id"]}')


def agreement_matches_profile(agreement, profile):
    additionalClassifications_matches = bool({c['id'] for c in agreement['additionalClassifications']}.intersection(
        {c['id'] for c in profile['additionalClassifications']}
    ))
    return (
            additionalClassifications_matches
            and agreement['scheme'] == profile['scheme']
            and agreement['agreementType'] == 'electronicCatalogue'
            and profile['owner'] == agreement['procuringEntity']['identifier']['id']
    )


async def migrate_profiles():
    collection = await load_profiles()

    for profile in collection:
        classification_id = profile["classification_id"]
        for next_classification_id in modified_classification_ids(classification_id):
            agreements = await load_agreements_by_id(next_classification_id)
            agreements_for_profile = [
                a for a in agreements
                if agreement_matches_profile(a, profile)
            ]
            if len(agreements_for_profile) > 1:
                print(f"too many agreements for {profile['id']}")
                break
            if not agreements_for_profile:
                continue

            agreement = agreements_for_profile[0]
            profile['agreementId'] = agreement['id']
            save(profile)
            print(f"found agreement_id for profile "
                  f"profile_id={profile['id']}, "
                  f"agreement_id={agreement['id']}, "
                  f"classification_id={agreement['classification_id']}")
            break
        else:
            print(f"not found agreements for {profile['id']}")



async def load_profiles():
    collection = await get_profiles_collection().find(
        {
            "status": {"ne": "general"},
        }
    )
    return collection


cache = {}

async def load_agreements_by_id(classification_id: str):
    if classification_id in cache:
        return cache[classification_id]

    async with aiohttp.ClientSession() as session:
        response = session.get(f"{OPENPROCUREMENT_API_URL}/api/v0/agreements_by_classification/{classification_id}")
        result = response.json()['data']
        cache[classification_id] = result
    return result



c_id_re = re.compile(r'(\d{2,})[1-9](.*)')

def modified_classification_ids(classification_id):
    while True:
        yield classification_id
        match = c_id_re.match(classification_id)
        if not match:
            return
        classification_id = f"{match[1]}0{match[2]}"


