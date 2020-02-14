DOCKER_TAG := $(or ${GITHUB_TAG_NAME}, latest)

.PHONY: dockerimage
dockerimage:
	docker build -t metalstack/metal-deployment-base:${DOCKER_TAG} .

.PHONY: dockerpush
dockerpush:
	docker push metalstack/meta-deployment-base:${DOCKER_TAG}
