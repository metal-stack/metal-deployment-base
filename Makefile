RELEASE_VECTOR_REF := "ghcr.io/metal-stack/releases:develop"

.PHONY: run
run:
# 	docker build -t metal-deployment-base .
	docker build -t metal-deployment-base-test -f Dockerfile.test .
	docker run --rm -it metal-deployment-base-test bash -c 'ansible-playbook example-playbook.yaml -v && find ~/.ansible/roles -type d -ls'
