from catalog.db import (
    init_mongo,
    get_category_collection,
    get_profiles_collection,
    get_products_collection,
    get_offers_collection,
)
import asyncio


renames = (
    # ("zakupki.prom.ua",	"prom.ua"),
    # ("smarttender.biz",	"it.ua"),
    # ("dzo.com.ua",	"netcast.com.ua"),
    # ("bid.e-tender.biz", "e-tender.biz"),
    # ("tender-oline.com.ua",	"tender-online.com.ua"),
    ("test.prozorro.ua",	"kill_me"),
)


async def main():
    collections = (
        get_category_collection(),
        get_profiles_collection(),
        get_products_collection(),
        get_offers_collection(),
    )
    for name, rename in renames:
        r = await asyncio.gather(*(
            collection.update_many(
                {"access.owner": name},
                {"$set": {"access.owner": rename}}
            )
            for collection in collections
        ))
        print(
            f"Updated: {r[0].modified_count} categories; {r[1].modified_count} profiles; "
            f"{r[2].modified_count} products; {r[3].modified_count} offers"
        )


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo(None))
    loop.run_until_complete(main())

