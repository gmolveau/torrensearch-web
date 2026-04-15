FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim@sha256:82f018bb3bd8b1d12c376c3e87da186ec1932cbf91bc8e73089feea6428fec00

WORKDIR /app

# install dependencies first (cached layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# copy source and install project
COPY src src
RUN uv sync --frozen --no-dev

# put jackett.json (and future configs) in a mountable volume
ENV XDG_CONFIG_HOME=/config
VOLUME /config

ENV TORRENSEARCH_WEB_HOST=0.0.0.0
ENV TORRENSEARCH_WEB_PORT=8000
EXPOSE 8000

CMD ["uv", "run", "torrensearch-web"]
