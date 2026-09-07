# Neev frontend on Cloud Run. Multi-stage, so the served image carries the
# standalone server and its traced dependencies but no toolchain.
#
# Build from THIS directory (it needs no repo-root files):
#   docker build -t neev-frontend src/frontend
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
# `npm ci` not `install`: the lockfile is committed and the build must be
# reproducible rather than resolve fresh minors.
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# NEEV_API_BASE is deliberately NOT set here. It is read at runtime by
# lib/api.ts, which is `server-only` and therefore never inlined into a client
# bundle -- so this image can be built before the backend has a URL.
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    PORT=8080 \
    HOSTNAME=0.0.0.0

# Next's standalone output ships its own minimal server.js plus only the
# node_modules it actually traced. public/ and .next/static are not included in
# it and have to be copied alongside.
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Non-root, which Cloud Run does not require but costs nothing to do.
RUN addgroup -S neev && adduser -S neev -G neev && chown -R neev:neev /app
USER neev

EXPOSE 8080
CMD ["node", "server.js"]
