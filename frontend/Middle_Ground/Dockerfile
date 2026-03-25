# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the React app
RUN npm run build

# Production stage - Serve with Node
FROM node:20-alpine

WORKDIR /app

# Copy built files from builder
COPY --from=builder /app/dist ./dist

# Install serve to run the app
RUN npm install -g serve

EXPOSE 3000

# Serve the built app
CMD ["serve", "-s", "dist", "-l", "3000"]