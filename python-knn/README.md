[![CHUV](https://img.shields.io/badge/CHUV-LREN-AF4C64.svg)](https://www.unil.ch/lren/en/home.html) [![DockerHub](https://img.shields.io/badge/docker-hbpmip%2Fpython--sgd-regression-008bb8.svg)](https://hub.docker.com/r/hbpmip/python-knn/)
[![ImageVersion](https://images.microbadger.com/badges/version/hbpmip/python-knn.svg)](https://hub.docker.com/r/hbpmip/python-knn/tags "hbpmip/python-knn image tags")
[![ImageLayers](https://images.microbadger.com/badges/image/hbpmip/python-knn.svg)](https://microbadger.com/#/images/hbpmip/python-knn "hbpmip/python-knn on microbadger")

# Python k-nearest neighbors

Implementation of [k-nearest neighbors algorithm](https://en.wikipedia.org/wiki/K-nearest_neighbors_algorithm) in Python.

Number of neighbors is parametrized using env `MODEL_PARAM_k`.


## Usage

It has two modes

1. `compute --mode intermediate`
2. `compute --mode aggregate --job-ids 1 2 3`

Intermediate mode calculates knn from a single node, while aggregate mode is used after intermediate to
combine knn from multiple jobs. Intermediate mode can be also used to calculate knn from single node.


## Build (for contributors)

Run: `./build.sh`


## Integration Test (for contributors)

Run: `captain test`


## Publish (for contributors)

Run: `./publish.sh`


## Unit tests (for contributors)

WARNING: unit tests can fail nondeterministically on `AttributeError: can't set attribute` because of some error
in Titus port to Python 3

Run unit tests
```
find . -name \*.pyc -delete
(cd tests; docker-compose run test_suite -x --ff --capture=no)
```
