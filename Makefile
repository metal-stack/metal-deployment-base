TAG := $(or $(TAG),metal-deployment-base)

ifeq ($(CI),true)
  DOCKER_RUN_ARG=
else
  DOCKER_RUN_ARG=t
endif

.PHONY: build
build:
	docker build -t $(TAG) .

.PHONY: test
test:
	docker build -t $(TAG)-test -f Dockerfile.test --build-arg=TAG=$(TAG) .
	docker run --rm -i$(DOCKER_RUN_ARG) $(TAG)-test bash -c \
		'ansible -m metalstack.base.metal_stack_release_vector localhost && find ~/.ansible/roles -maxdepth 1 -type d -ls'
