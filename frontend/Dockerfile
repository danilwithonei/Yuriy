# Use an official Node runtime as a parent image
FROM node:20-alpine

# Set the working directory in the container
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application code
COPY . .

# Build the application
# RUN npm run build

# Expose the port the app runs on
EXPOSE 3000

# Run the application in development mode (as currently configured in the project)
CMD ["npm", "run", "dev"]
