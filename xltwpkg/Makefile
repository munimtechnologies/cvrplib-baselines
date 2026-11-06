# xltw-solver. MV2 of Munim, Inc. Apache-2.0. `make` builds ./solver (see build.sh).
.PHONY: all offline test clean
all:
	bash build.sh
offline:
	bash build.sh --offline
test:
	python3 -m unittest -v test_pkg
clean:
	rm -rf lib solver
