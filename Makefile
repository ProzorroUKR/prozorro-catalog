CI_COMMIT_SHORT_SHA ?= $(shell git rev-parse --short HEAD)
IMAGE ?= catalog:latest
IMAGE_TEST ?= catalog:test
GIT_STAMP ?= $(shell git describe)
HELM ?= helm3

.EXPORT_ALL_VARIABLES:


docker-build-test:
	docker build --target=test --build-arg version=$(GIT_STAMP) -t $(IMAGE_FULL_NAME):$(IMAGE_TAG) .
	docker push $(IMAGE_FULL_NAME):$(IMAGE_TAG)

docker-build:
	docker build --build-arg version=$(GIT_STAMP) -t $(IMAGE_FULL_NAME):$(IMAGE_TAG) .
	docker push $(IMAGE_FULL_NAME):$(IMAGE_TAG)


helm-lint:
	$(HELM) lint helm/prozorro-catalog

helm-build:
	$(HELM) package helm/prozorro-catalog --app-version=$(GIT_STAMP) --version=$(GIT_STAMP)

helm-install: docker-build
	$(HELM) install rms helm/prozorro-catalog

helm-uninstall:
	$(HELM) uninstall rms

version:
	$(eval GIT_TAG ?= $(shell git describe --abbrev=0))
	$(eval VERSION ?= $(shell read -p "Version: " VERSION; echo $$VERSION))
	echo "Tagged release $(VERSION)\n" > Changelog-$(VERSION).txt
	git log --oneline --no-decorate --no-merges $(GIT_TAG)..HEAD >> Changelog-$(VERSION).txt
	git tag -a -e -F Changelog-$(VERSION).txt $(VERSION)

pep8:
	@flake8 src/

test-integration:
	docker run $(CI_REGISTRY_IMAGE):$(CI_TAG) \
	    --mount source=tests,target=/app/tests \
	   	pip install -r tests/requirements && pytest --cov=catalog --cov-report xml tests/integration/

