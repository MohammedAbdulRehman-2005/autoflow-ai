FROM node:20-alpine

WORKDIR /app

# Install dependencies first for caching
COPY package*.json ./
RUN npm install

# Copy source code
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Run the dev server with host flag so Docker binds to 0.0.0.0
CMD ["npm", "run", "dev", "--", "--host"]
