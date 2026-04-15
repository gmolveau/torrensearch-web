set shell := ["bash", "-euo", "pipefail", "-c"]
set dotenv-load := true

default:
    @just --list

build:
    docker build -t torrensearch-web:dev .

ruff:
    uv run ruff format .
    uv run ruff check . --fix

ruff-check:
    uv run ruff check src
    uv run ruff format --check src

checks: ruff-check

format: ruff

upgrade:
    uv sync --upgrade

bump-version bump:
    uv version --bump {{ bump }}

clean:
    rm -rf .venv dist
    find . -type f -name '*.pyc' -delete
    find . -type d -name '__pycache__' -delete
    find . -type d -name '.ty_cache ' -delete
    find . -type d -name '.pytest_cache ' -delete
    find . -type d -name '.ruff_cache' -delete
    rm -f coverage coverage.xml
    rm -rf .report
