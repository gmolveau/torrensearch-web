set shell := ["bash", "-euo", "pipefail", "-c"]
set dotenv-load := true

default:
    @just --list

build:
    docker build -t torrensearch-web:dev .
