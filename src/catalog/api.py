from aiohttp import web
from aiohttp_swagger import setup_swagger
from catalog import version
from catalog.settings import SWAGGER_DOC_AVAILABLE
from catalog.swagger import get_definitions
from catalog.middleware import (
    request_unpack_params,
    convert_response_to_json,
    error_middleware,
    request_id_middleware,
    login_middleware,
)
from catalog.db import init_mongo, cleanup_db_client
from catalog.logging import AccessLogger, setup_logging
from catalog.handlers.general import get_version, ping_handler
from catalog.handlers.profile import ProfileView
from catalog.handlers.category import CategoryView
from catalog.handlers.product import ProductView
from catalog.handlers.offer import OfferView
from catalog.handlers.image import ImageView
from catalog.handlers.search import SearchView
from catalog.settings import SENTRY_DSN, IMG_PATH, IMG_DIR, CLIENT_MAX_SIZE
from catalog.migration import import_data_job
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
import sentry_sdk
import logging

logger = logging.getLogger(__name__)


def create_application(on_cleanup=None):
    app = web.Application(
        middlewares=(
            request_id_middleware,
            error_middleware,
            convert_response_to_json,
            login_middleware,
            request_unpack_params,
        ),
        client_max_size=CLIENT_MAX_SIZE
    )
    app.router.add_get("/api/ping", ping_handler, allow_head=False)
    app.router.add_get("/api/version", get_version, allow_head=False)

    # categories
    app.router.add_get(
        "/api/categories",
        CategoryView.collection_get,
        name="read_category_registry",
        allow_head=False
    )
    app.router.add_get(
        r"/api/categories/{category_id:[\w-]+}",
        CategoryView.get,
        name="read_category",
        allow_head=False
    )
    app.router.add_put(
        r"/api/categories/{category_id:[\w-]+}",
        CategoryView.put,
        name="create_category"
    )
    app.router.add_patch(
        r"/api/categories/{category_id:[\w-]+}",
        CategoryView.patch,
        name="update_category"
    )

    # risk profiles
    app.router.add_get(
        "/api/profiles",
        ProfileView.collection_get,
        name="read_profile_registry",
        allow_head=False
    )
    app.router.add_get(
        r"/api/profiles/{profile_id:[\w-]+}",
        ProfileView.get,
        name="read_profile",
        allow_head=False
    )
    app.router.add_put(
        r"/api/profiles/{profile_id:[\w-]+}",
        ProfileView.put,
        name="create_profile"
    )
    app.router.add_patch(
        r"/api/profiles/{profile_id:[\w-]+}",
        ProfileView.patch,
        name="update_profile"
    )

    # products
    app.router.add_get(
        "/api/products",
        ProductView.collection_get,
        name="read_product_registry",
        allow_head=False
    )
    app.router.add_get(
        r"/api/products/{product_id:[\w-]+}",
        ProductView.get,
        name="read_product",
        allow_head=False
    )
    app.router.add_put(
        r"/api/products/{product_id:[\w-]+}",
        ProductView.put,
        name="create_product"
    )
    app.router.add_patch(
        r"/api/products/{product_id:[\w-]+}",
        ProductView.patch,
        name="update_product"
    )

    # offers
    app.router.add_get(
        "/api/offers",
        OfferView.collection_get,
        name="read_offer_registry",
        allow_head=False
    )
    app.router.add_get(
        r"/api/offers/{offer_id:[\w-]+}",
        OfferView.get,
        name="read_offer",
        allow_head=False
    )
    app.router.add_put(
        r"/api/offers/{offer_id:[\w-]+}",
        OfferView.put,
        name="create_offer"
    )
    app.router.add_patch(
        r"/api/offers/{offer_id:[\w-]+}",
        OfferView.patch,
        name="update_offer"
    )
    # search
    app.router.add_post(
        r"/api/search",
        SearchView.post,
        name="search_resources"
    )
    # images
    app.router.add_post(
        r"/api/images",
        ImageView.post,
        name="upload_image"
    )
    # server images for dev env
    app.router.add_static(IMG_PATH, IMG_DIR)

    app.on_startup.append(init_mongo)
    app.on_startup.append(import_data_job)
    if on_cleanup:
        app.on_cleanup.append(on_cleanup)
    app.on_cleanup.append(cleanup_db_client)
    return app


if __name__ == "__main__":
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[AioHttpIntegration()]
        )
    logger.info("Starting app on 0.0.0.0:8000")
    application = create_application()

    if SWAGGER_DOC_AVAILABLE:
        setup_swagger(
            application,
            title='Prozorro Catalog API',
            description='Prozorro Catalog API description',
            api_version=version,
            ui_version=3,
            definitions=get_definitions(),
        )
    web.run_app(
        application,
        host="0.0.0.0",
        port=8000,
        access_log_class=AccessLogger,
        print=None
    )
