FROM python:3.12-slim
WORKDIR /simulation-service
RUN pip install uv
COPY pyproject.toml uv.lock ./
RUN python --version && which python && uv --version
RUN uv sync --frozen --no-install-project
COPY . .
RUN uv sync --locked
CMD ["uv", "run", "fastapi", "run"]

