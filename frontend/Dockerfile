# Use an official Node runtime as a parent image
FROM node:20-alpine

# Install libc6-compat for compatibility with some native modules (like lightningcss)
RUN apk add --no-cache libc6-compat

# Set the working directory in the container
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Clean install to ensure correct platform binaries are downloaded
RUN npm ci

# Copy the rest of the application code
COPY . .

# Build the application
# RUN npm run build

# Expose the port the app runs on
EXPOSE 3000

# Run the application in development mode
CMD ["npm", "run", "dev"]
