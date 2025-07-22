.PHONY: run
run:
# 	docker build -t metal-deployment-base .
	docker build -t metal-deployment-base-test -f Dockerfile.test .
	docker run --rm -it metal-deployment-base-test bash -c 'ansible -m metal_stack_release_vector localhost -v && find ~/.ansible/roles -type d -ls'
