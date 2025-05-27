RELEASE_VECTOR_REF := "ghcr.io/metal-stack/releases:develop"

.PHONY: run
run:
	docker build -t metal-deployment-base .
	docker run --rm -it metal-deployment-base bash -c 'ansible localhost -m metal_stack_release_vector -a ref=$(RELEASE_VECTOR_REF) && find ~/.ansible/roles -type d -ls'
