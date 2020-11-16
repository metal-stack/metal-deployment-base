DOCKER_TAG := $(or ${GITHUB_TAG_NAME}, latest)

.PHONY: dockerimage
dockerimage:
	docker build -t ghcr.io/metal-stack/metal-deployment-base:${DOCKER_TAG} .

.PHONY: dockerpush
dockerpush:
	docker push ghcr.io/metal-stack/metal-deployment-base:${DOCKER_TAG}
