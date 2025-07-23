ifeq ($(CI),true)
  DOCKER_RUN_ARG=
else
  DOCKER_RUN_ARG=t
endif

.PHONY: test
test:
	docker build -t metal-deployment-base .
	docker build -t metal-deployment-base-test -f Dockerfile.test .
	docker run --rm -i$(DOCKER_RUN_ARG) metal-deployment-base-test bash -c \
		'ansible -m metalstack.base.metal_stack_release_vector localhost && find ~/.ansible/roles -maxdepth 1 -type d -ls'
