# Use the official image from the creators of uv (astral-sh)
# We use Python 3.11 as discussed for maximum compatibility
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

# Set the working directory inside the container
WORKDIR /app

# 1. Copy dependency files first
# This allows Docker to cache the installation step so re-builds are fast
COPY pyproject.toml uv.lock ./

# 2. Install dependencies
# --frozen: ensures we use exactly the versions in uv.lock
# --no-dev: we don't need dev tools unless you plan to run tests inside docker often
RUN uv sync --frozen --no-dev

# 3. Copy the rest of your code
COPY . .

# 4. Install your project in editable mode
RUN uv pip install --system -e .

# 5. Default command: Launch Jupyter Lab
# --ip=0.0.0.0 allows you to access it from your browser outside the container
CMD ["uv", "run", "jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]
