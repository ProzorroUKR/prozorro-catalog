import logging

import sentry_sdk
from aiohttp import web
from aiohttp_pydantic import oas
from sentry_sdk.integrations.aiohttp import AioHttpIntegration

from catalog import version
from catalog.db import cleanup_db_client, init_mongo
from catalog.handlers.category import (
    CategoryCriteriaItemView,
    CategoryCriteriaRGItemView,
    CategoryCriteriaRGRequirementItemView,
    CategoryCriteriaRGRequirementView,
    CategoryCriteriaRGView,
    CategoryCriteriaView,
    CategoryItemView,
    CategoryView,
)
from catalog.handlers.crowd_sourcing.contributor import ContributorItemView, ContributorView
from catalog.handlers.crowd_sourcing.contributor_ban import ContributorBanItemView, ContributorBanView
from catalog.handlers.crowd_sourcing.contributor_ban_document import (
    ContributorBanDocumentItemView,
    ContributorBanDocumentView,
)
from catalog.handlers.crowd_sourcing.contributor_document import ContributorDocumentItemView, ContributorDocumentView
from catalog.handlers.crowd_sourcing.product_request import (
    ContributorProductRequestView,
    ProductRequestAcceptionView,
    ProductRequestItemView,
    ProductRequestRejectionView,
    ProductRequestView,
)
from catalog.handlers.crowd_sourcing.product_request_document import (
    ProductRequestDocumentItemView,
    ProductRequestDocumentView,
)
from catalog.handlers.general import get_version, ping_handler
from catalog.handlers.image import ImageView
from catalog.handlers.offer import OfferItemView, OfferView
from catalog.handlers.product import ProductItemView, ProductView
from catalog.handlers.product_document import ProductDocumentItemView, ProductDocumentView
from catalog.handlers.profile import (
    ProfileCriteriaItemView,
    ProfileCriteriaRGItemView,
    ProfileCriteriaRGRequirementItemView,
    ProfileCriteriaRGRequirementView,
    ProfileCriteriaRGView,
    ProfileCriteriaView,
    ProfileItemView,
    ProfileView,
)
from catalog.handlers.search import SearchView
from catalog.handlers.tags import TagItemView, TagView
from catalog.handlers.vendor import VendorItemView, VendorSignItemView, VendorView
from catalog.handlers.vendor_ban import VendorBanItemView, VendorBanView
from catalog.handlers.vendor_ban_document import VendorBanDocumentItemView, VendorBanDocumentView
from catalog.handlers.vendor_document import VendorDocumentItemView, VendorDocumentView
from catalog.handlers.vendor_product import VendorProductView
from catalog.handlers.vendor_product_document import VendorProductDocumentItemView, VendorProductDocumentView
from catalog.logging import AccessLogger, setup_logging
from catalog.middleware import (
    context_middleware,
    convert_response_to_json,
    db_session_middleware,
    error_middleware,
    login_middleware,
    request_id_middleware,
)
from catalog.migration import import_data_job
from catalog.settings import CLIENT_MAX_SIZE, IMG_DIR, IMG_PATH, SENTRY_DSN

logger = logging.getLogger(__name__)


def apply_custom_validation_error_handler():
    from aiohttp_pydantic import PydanticView

    async def custom_validation_error_handler(self, exception, context):
        raise exception

    # Monkey patch PydanticView to use our custom validation error handler
    PydanticView.on_validation_error = custom_validation_error_handler


def create_application(on_cleanup=None):
    app = web.Application(
        middlewares=(
            request_id_middleware,
            db_session_middleware,
            context_middleware,
            error_middleware,
            convert_response_to_json,
            login_middleware,
        ),
        client_max_size=CLIENT_MAX_SIZE,
    )
    oas.setup(
        app,
        title_spec="Prozorro Catalog API",
        version_spec=version,
        url_prefix="/api/doc",
        security={"Basic": {"type": "http", "scheme": "basic", "in": "header", "name": "Authorization"}},
    )

    apply_custom_validation_error_handler()

    app.router.add_get("/api/ping", ping_handler, allow_head=False)
    app.router.add_get("/api/version", get_version, allow_head=False)

    # categories
    app.router.add_view(
        "/api/categories",
        CategoryView,
    )
    app.router.add_view(
        "/api/categories/{category_id}",
        CategoryItemView,
    )

    # category criteria

    app.router.add_view(
        r"/api/categories/{obj_id:[\w-]+}/criteria",
        CategoryCriteriaView,
    )
    app.router.add_view(
        r"/api/categories/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}",
        CategoryCriteriaItemView,
    )

    # profile criteria RG
    app.router.add_view(
        r"/api/categories/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups",
        CategoryCriteriaRGView,
    )
    app.router.add_view(
        r"/api/categories/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups/{rg_id:[\w-]+}",
        CategoryCriteriaRGItemView,
    )

    # profile criteria RG requirements
    app.router.add_view(
        r"/api/categories/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups/{rg_id:[\w-]+}/requirements",
        CategoryCriteriaRGRequirementView,
    )
    app.router.add_view(
        r"/api/categories/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups/{rg_id:[\w-]+}/requirements/{requirement_id:[\w-]+}",
        CategoryCriteriaRGRequirementItemView,
    )

    # profiles
    app.router.add_view(
        "/api/profiles",
        ProfileView,
    )
    app.router.add_view(
        r"/api/profiles/{profile_id:[\w-]+}",
        ProfileItemView,
    )

    # profile criteria
    app.router.add_view(
        r"/api/profiles/{obj_id:[\w-]+}/criteria",
        ProfileCriteriaView,
    )
    app.router.add_view(
        r"/api/profiles/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}",
        ProfileCriteriaItemView,
    )

    # profile criteria RG
    app.router.add_view(
        r"/api/profiles/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups",
        ProfileCriteriaRGView,
    )
    app.router.add_view(
        r"/api/profiles/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups/{rg_id:[\w-]+}",
        ProfileCriteriaRGItemView,
    )

    # profile criteria RG requirements
    app.router.add_view(
        r"/api/profiles/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups/{rg_id:[\w-]+}/requirements",
        ProfileCriteriaRGRequirementView,
    )
    app.router.add_view(
        r"/api/profiles/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups/{rg_id:[\w-]+}/requirements/{requirement_id:[\w-]+}",
        ProfileCriteriaRGRequirementItemView,
    )

    # products
    app.router.add_view("/api/products", ProductView)
    app.router.add_view(r"/api/products/{product_id:[\w-]+}", ProductItemView)

    # product docs
    app.router.add_view(
        r"/api/products/{product_id:[\w-]+}/documents",
        ProductDocumentView,
    )
    app.router.add_view(
        r"/api/products/{product_id:[\w-]+}/documents/{doc_id:[\w]{32}}",
        ProductDocumentItemView,
    )

    # offers
    app.router.add_view(
        "/api/offers",
        OfferView,
    )
    app.router.add_view(
        r"/api/offers/{offer_id:[\w-]+}",
        OfferItemView,
    )

    # vendors
    app.router.add_view(
        "/api/vendors",
        VendorView,
    )
    app.router.add_view(
        r"/api/vendors/{vendor_id:[\w]{32}}",
        VendorItemView,
    )
    app.router.add_view(
        r"/api/sign/vendors/{vendor_id:[\w]{32}}",
        VendorSignItemView,
    )

    # vendor docs
    app.router.add_view(
        r"/api/vendors/{vendor_id:[\w]{32}}/documents",
        VendorDocumentView,
    )
    app.router.add_view(
        r"/api/vendors/{vendor_id:[\w]{32}}/documents/{doc_id:[\w]{32}}",
        VendorDocumentItemView,
    )

    # vendor product
    app.router.add_view(
        r"/api/vendors/{vendor_id:[\w]{32}}/products",
        VendorProductView,
    )

    # vendor product docs
    app.router.add_view(
        r"/api/vendors/{vendor_id:[\w]{32}}/products/{product_id:[\w]{32}}/documents",
        VendorProductDocumentView,
    )
    app.router.add_view(
        r"/api/vendors/{vendor_id:[\w]{32}}/products/{product_id:[\w]{32}}/documents/{doc_id:[\w]{32}}",
        VendorProductDocumentItemView,
    )

    # vendor ban
    app.router.add_view(
        r"/api/vendors/{vendor_id:[\w]{32}}/bans",
        VendorBanView,
    )
    app.router.add_view(
        r"/api/vendors/{vendor_id:[\w]{32}}/bans/{ban_id:[\w]{32}}",
        VendorBanItemView,
    )

    # vendor ban docs
    app.router.add_view(
        r"/api/vendors/{vendor_id:[\w]{32}}/bans/{ban_id:[\w]{32}}/documents",
        VendorBanDocumentView,
    )
    app.router.add_view(
        r"/api/vendors/{vendor_id:[\w]{32}}/bans/{ban_id:[\w]{32}}" r"/documents/{doc_id:[\w]{32}}",
        VendorBanDocumentItemView,
    )

    # contributors
    app.router.add_view(
        "/api/crowd-sourcing/contributors",
        ContributorView,
    )
    app.router.add_view(
        r"/api/crowd-sourcing/contributors/{contributor_id:[\w]{32}}",
        ContributorItemView,
    )

    # contributor ban
    app.router.add_view(
        r"/api/crowd-sourcing/contributors/{contributor_id:[\w]{32}}/bans",
        ContributorBanView,
    )
    app.router.add_view(
        r"/api/crowd-sourcing/contributors/{contributor_id:[\w]{32}}/bans/{ban_id:[\w]{32}}",
        ContributorBanItemView,
    )

    # contributor docs
    app.router.add_view(
        r"/api/crowd-sourcing/contributors/{contributor_id:[\w]{32}}/documents",
        ContributorDocumentView,
    )
    app.router.add_view(
        r"/api/crowd-sourcing/contributors/{contributor_id:[\w]{32}}/documents/{doc_id:[\w]{32}}",
        ContributorDocumentItemView,
    )

    # contributor ban docs
    app.router.add_view(
        r"/api/crowd-sourcing/contributors/{contributor_id:[\w]{32}}/bans/{ban_id:[\w]{32}}/documents",
        ContributorBanDocumentView,
    )
    app.router.add_view(
        r"/api/crowd-sourcing/contributors/{contributor_id:[\w]{32}}/bans/{ban_id:[\w]{32}}"
        r"/documents/{doc_id:[\w]{32}}",
        ContributorBanDocumentItemView,
    )

    # product request
    app.router.add_view(
        r"/api/crowd-sourcing/contributors/{contributor_id:[\w]{32}}/requests",
        ContributorProductRequestView,
    )
    app.router.add_view(
        r"/api/crowd-sourcing/requests",
        ProductRequestView,
    )
    app.router.add_view(
        r"/api/crowd-sourcing/requests/{request_id:[\w]{32}}",
        ProductRequestItemView,
    )
    app.router.add_view(
        r"/api/crowd-sourcing/requests/{request_id:[\w]{32}}/accept",
        ProductRequestAcceptionView,
    )
    app.router.add_view(
        r"/api/crowd-sourcing/requests/{request_id:[\w]{32}}/reject",
        ProductRequestRejectionView,
    )

    # # product request docs
    app.router.add_view(
        r"/api/crowd-sourcing/requests/{request_id:[\w]{32}}/documents",
        ProductRequestDocumentView,
    )
    app.router.add_view(
        r"/api/crowd-sourcing/requests/{request_id:[\w]{32}}/documents/{doc_id:[\w]{32}}",
        ProductRequestDocumentItemView,
    )

    # tags
    app.router.add_view(
        "/api/tags",
        TagView,
    )
    app.router.add_view(
        "/api/tags/{tag_id}",
        TagItemView,
    )

    # search
    app.router.add_view(
        r"/api/search",
        SearchView,
    )
    # images
    app.router.add_post(r"/api/images", ImageView.post, name="upload_image")
    # server images for dev env
    app.router.add_static(IMG_PATH, IMG_DIR)

    app.on_startup.append(init_mongo)
    app.on_startup.append(import_data_job)
    if on_cleanup:
        app.on_cleanup.append(on_cleanup)
    app.on_cleanup.append(cleanup_db_client)
    return app


def setup_sentry():
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN, integrations=[AioHttpIntegration()])


async def application():
    setup_logging()
    setup_sentry()
    application = create_application()
    return application


if __name__ == "__main__":
    logger.info("Starting app on 0.0.0.0:8000")
    web.run_app(application(), host="0.0.0.0", port=8000, access_log_class=AccessLogger, print=None)
