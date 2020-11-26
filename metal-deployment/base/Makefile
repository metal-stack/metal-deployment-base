DOCKER_TAG := $(or ${GITHUB_TAG_NAME}, latest)

.PHONY: dockerimage
dockerimage:
	docker build -t ghcr.io/metal-stack/metal-deployment-base:${DOCKER_TAG} .
	docker build --build-arg BASE_VERSION=${DOCKER_TAG} -t ghcr.io/metal-stack/metal-deployment-base:${DOCKER_TAG}-vagrant . -f Dockerfile.withvagrant

.PHONY: dockerpush
dockerpush:
	docker tag ghcr.io/metal-stack/metal-deployment-base:${DOCKER_TAG} metalstack/metal-deployment-base:${DOCKER_TAG}
	docker tag ghcr.io/metal-stack/metal-deployment-base:${DOCKER_TAG}-vagrant metalstack/metal-deployment-base:${DOCKER_TAG}-vagrant

	docker push ghcr.io/metal-stack/metal-deployment-base:${DOCKER_TAG}
	docker push ghcr.io/metal-stack/metal-deployment-base:${DOCKER_TAG}-vagrant

	docker push metalstack/metal-deployment-base:${DOCKER_TAG}
	docker push metalstack/metal-deployment-base:${DOCKER_TAG}-vagrant
