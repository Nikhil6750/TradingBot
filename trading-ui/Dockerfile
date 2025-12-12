# Base image
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Expose Vite default port
EXPOSE 5173

# Run dev server with --host to expose to network
CMD ["npm", "run", "dev", "--", "--host"]
