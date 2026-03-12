FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.5.18 /uv /usr/local/bin/uv

WORKDIR /app

ENV UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY bot/ ./bot/
COPY budget_goals.json ./

CMD ["uv", "run", "python", "-m", "bot.main"]
