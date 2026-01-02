FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

# 1) Copy dependency metadata first (cache-friendly)
COPY pyproject.toml uv.lock README.md ./

# 2) Install third-party deps only (do not install the project yet)
RUN uv sync --frozen --no-dev --no-install-project

# 3) Copy your source/config
COPY src/ ./src/
COPY config/ ./config/

# 4) Now install the project into the same environment
RUN uv sync --frozen --no-dev

# 5) JupyterLab
CMD ["uv", "run", "jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]
