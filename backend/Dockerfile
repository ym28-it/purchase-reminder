# syntax=docker/dockerfile:1

FROM python:3.14-slim AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# ---------------------------------------------------------------------------
# dev: ソースはdocker-compose側のbind mountで供給される前提。
#      依存関係のみここでインストールしておく。
# ---------------------------------------------------------------------------
FROM base AS dev
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]

# ---------------------------------------------------------------------------
# prod-build: 本番イメージ用にソースを焼き込んでインストール
# ---------------------------------------------------------------------------
FROM base AS prod-build
COPY . .
RUN uv sync --frozen

# ---------------------------------------------------------------------------
# prod: Lambda Web Adapter を拡張機能として追加した本番ランタイム
#       ※ aws-lambda-adapter のバージョンは最新を確認の上、適宜更新してください
# ---------------------------------------------------------------------------
FROM python:3.14-slim AS prod
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 /lambda-adapter /opt/extensions/lambda-adapter

ENV PATH="/app/.venv/bin:$PATH" \
    AWS_LWA_PORT=8000 \
    PORT=8000

WORKDIR /app
COPY --from=prod-build /app /app

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
