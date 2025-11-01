# Multi-stage Dockerfile for React/Vite frontend
# Production-ready with Nginx serving

# ============================================================================
# Stage 1: Build the React application
# ============================================================================
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY web/package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY web/ ./

# Build the application
RUN npm run build

# ============================================================================
# Stage 2: Production image with Nginx
# ============================================================================
FROM nginx:1.25-alpine AS runtime

# Copy custom nginx config
COPY web/nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Add non-root user
RUN addgroup -g 1001 -S appuser && adduser -u 1001 -S appuser -G appuser

# Change ownership
RUN chown -R appuser:appuser /usr/share/nginx/html && \
    chown -R appuser:appuser /var/cache/nginx && \
    chown -R appuser:appuser /var/log/nginx && \
    chown -R appuser:appuser /etc/nginx/conf.d

# Create nginx pid directory
RUN touch /var/run/nginx.pid && \
    chown -R appuser:appuser /var/run/nginx.pid

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
