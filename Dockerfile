# Neev backend on Cloud Run.
#
# The image mirrors the repo layout on purpose. `app/fixtures/loader.py` and
# `app/db/seed.py` both resolve the repo root as `parents[4]` and read
# `<root>/fixtures/draw_schedule.csv` from it, so flattening the tree into
# /app would break the seed at container start. Hence /app/src/backend plus
# /app/fixtures, exactly as in git.
#
# This lives at the REPO ROOT rather than in src/backend/ for two reasons that
# both point the same way: the build context must include fixtures/ (see above),
# and `gcloud run deploy --source .` only picks up a Dockerfile at the root of
# the context it is given. The frontend has its own at src/frontend/Dockerfile.
#
#   docker build -t neev-backend .
FROM python:3.11-slim

# uvicorn's --reload and pip's cache are dev conveniences; neither belongs here.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app/src/backend

# Dependencies first, so a code change does not reinstall them.
COPY src/backend/pyproject.toml ./
RUN pip install --no-cache-dir \
      "fastapi>=0.115" "uvicorn[standard]>=0.32" "pydantic>=2.9" \
      "pydantic-settings>=2.6" "sqlalchemy>=2.0" "python-multipart>=0.0.12" \
      "pillow>=11.0"

COPY src/backend/app ./app
# The seed's other input, read via the repo-root path described above.
COPY fixtures /app/fixtures

# Fixture mode is the default, and NEEV_ALLOW_BILLED_CALLS is deliberately
# absent: an image that reached live mode by accident would spend credits. Set
# both explicitly at deploy time if and when live analysis is wanted.
ENV NEEV_MODE=fixture \
    PORT=8080

# SQLite lives on the container's own filesystem, which Cloud Run discards when
# the instance recycles. That is why the database is seeded at start rather than
# baked in: every cold start gets a coherent book, and any decision written
# during a session lasts as long as the instance. Deploy with
# --min-instances=1 --max-instances=1 so there is exactly one of them.
COPY src/backend/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
