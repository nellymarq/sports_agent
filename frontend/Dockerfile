FROM node:20-alpine

WORKDIR /app

# Install dependencies first for layer caching
COPY package.json package-lock.json* ./
RUN npm ci --production=false

COPY . .

# Build for production
RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start"]
