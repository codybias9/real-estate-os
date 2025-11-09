# ===========================================================================
# Next.js Frontend Dockerfile
# ===========================================================================
# Multi-stage build for Next.js 14 application
#
# Stages:
#   - base: Node.js base image
#   - dependencies: Install npm packages
#   - development: Hot-reload development server
#   - build: Production build
#   - production: Optimized production server
# ===========================================================================

# ---------------------------------------------------------------------------
# Base Stage
# ---------------------------------------------------------------------------
FROM node:20-alpine AS base

WORKDIR /app

# Install dependencies only when needed
FROM base AS dependencies
COPY package.json package-lock.json* ./
RUN npm install

# ---------------------------------------------------------------------------
# Development Stage (with hot reload)
# ---------------------------------------------------------------------------
FROM base AS development

WORKDIR /app

# Copy dependencies from dependencies stage
COPY --from=dependencies /app/node_modules ./node_modules

# Copy source
COPY . .

# Expose port
EXPOSE 3000

# Set environment to development
ENV NODE_ENV=development
ENV NEXT_TELEMETRY_DISABLED=1

# Start development server
CMD ["npm", "run", "dev"]

# ---------------------------------------------------------------------------
# Build Stage
# ---------------------------------------------------------------------------
FROM base AS build

WORKDIR /app

# Copy dependencies
COPY --from=dependencies /app/node_modules ./node_modules

# Copy source
COPY . .

# Build application
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# ---------------------------------------------------------------------------
# Production Stage
# ---------------------------------------------------------------------------
FROM base AS production

WORKDIR /app

# Set to production
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Copy built application
COPY --from=build /app/public ./public
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static

# Expose port
EXPOSE 3000

# Start production server
CMD ["node", "server.js"]
