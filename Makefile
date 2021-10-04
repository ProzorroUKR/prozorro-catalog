CI_COMMIT_SHORT_SHA ?= $(shell git rev-parse --short HEAD)
IMAGE ?= catalog:latest
IMAGE_TEST ?= catalog:test
GIT_STAMP ?= $(shell git describe)
HELM ?= helm3

.EXPORT_ALL_VARIABLES:

ifdef CI
  REBUILD_IMAGES_FOR_TESTS =
else
  REBUILD_IMAGES_FOR_TESTS = docker-build
endif


run: docker-build
	docker-compose --file=docker-compose.yml up -d

stop:
	docker-compose --file=docker-compose.yml stop

docker-build:
	docker build --build-arg version=$(GIT_STAMP) -t $(IMAGE) .
	docker build --target=test --build-arg version=$(GIT_STAMP) -t $(IMAGE_TEST) .

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

test-unit: $(REBUILD_IMAGES_FOR_TESTS)
	docker rm -f unit-$(CI_COMMIT_SHORT_SHA) || true
	docker build --target=test -t $(IMAGE_TEST) .
	docker run \
		--name unit-$(CI_COMMIT_SHORT_SHA) \
		--env AUTH_KS_DIR=tests/auth_keys \
	   	$(IMAGE_TEST) \
	   	nosetests -v tests/unit

test-integration: COMPOSE ?= docker-compose -f docker-compose-integration.yml
test-integration: $(REBUILD_IMAGES_FOR_TESTS)
	docker rm -f integration-$(CI_COMMIT_SHORT_SHA) || true
	IMAGE_TEST=$(IMAGE_TEST) $(COMPOSE) run \
	    --name integration-$(CI_COMMIT_SHORT_SHA) api \
		nosetests -v tests/integration --with-coverage --cover-package=customs --cover-xml
	docker cp integration-$(CI_COMMIT_SHORT_SHA):/asur_rms/coverage.xml coverage.xml		
	cat coverage.xml | sed "s/\/asur_rms\/customs/\/builds\/asur\/rms\/src\/customs/" > coverage.xml.tmp && mv coverage.xml.tmp coverage.xml

remove-compose: COMPOSE ?= docker-compose -f docker-compose-integration.yml
remove-compose:
	$(COMPOSE) down
