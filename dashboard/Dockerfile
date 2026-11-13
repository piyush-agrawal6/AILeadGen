FROM node:24.22.2-bookworm-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Compile with nonsecret fixtures only. All real auth/gateway values are supplied
# by Secret Manager to the final runtime, never Docker build arguments or layers.
RUN PLANEBYTE_STANDALONE=true APP_ENV=test NEXT_TELEMETRY_DISABLED=1 \
    AUTH_SECRET=build-only-placeholder-at-least-32-characters \
    AUTH_GOOGLE_ID=build-only AUTH_GOOGLE_SECRET=build-only \
    ALLOWED_USER_EMAILS=build-only@example.invalid \
    LEADENGINE_API_URL=https://backend.example.invalid \
    LEADENGINE_API_SIGNING_SECRET=build-only-placeholder-at-least-32-characters npm run build

FROM node:24.22.2-bookworm-slim AS runtime
ENV NODE_ENV=production APP_ENV=production NEXT_TELEMETRY_DISABLED=1 \
    PORT=8080 HOSTNAME=0.0.0.0
WORKDIR /app
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
COPY --from=build --chown=node:node /app/public ./public
USER node
EXPOSE 8080
CMD ["node", "server.js"]
