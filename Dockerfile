# Base image
FROM node:22-alpine

# Set working directory
WORKDIR /app

# Set environment to production
ENV NODE_ENV=production

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy app files
COPY . .

# Expose the app port
EXPOSE 3001

# Command to run the app
CMD ["node", "src/index.js"]