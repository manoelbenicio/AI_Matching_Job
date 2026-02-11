# AI Job Matcher — Next.js Frontend
FROM node:20-alpine

WORKDIR /app

# Install deps
COPY package.json package-lock.json* ./
RUN npm ci

# Copy source
COPY . .

EXPOSE 3000

# Dev mode with hot reload
CMD ["npm", "run", "dev"]
