#!/bin/bash

# Configuration - Update these with your details
DOCKER_USERNAME="yogeshabnave"  # Replace with your Docker Hub username
IMAGE_NAME="my-html-app"
IMAGE_TAG="v1.0"
FULL_IMAGE_NAME="$DOCKER_USERNAME/$IMAGE_NAME:$IMAGE_TAG"

echo "🐳 Starting Docker build and push process..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Build the Docker image
echo "🔨 Building Docker image: $FULL_IMAGE_NAME"
docker build -t $FULL_IMAGE_NAME .

if [ $? -eq 0 ]; then
    echo "✅ Docker image built successfully!"
else
    echo "❌ Failed to build Docker image"
    exit 1
fi

# Tag image as latest as well
docker tag $FULL_IMAGE_NAME $DOCKER_USERNAME/$IMAGE_NAME:latest

# Test the image locally (optional)
echo "🧪 Testing the image locally..."
docker run -d -p 8080:80 --name test-container $FULL_IMAGE_NAME

# Wait a moment for container to start
sleep 3

# Check if container is running
if docker ps | grep -q test-container; then
    echo "✅ Container is running successfully on http://localhost:8080"
    echo "🛑 Stopping test container..."
    docker stop test-container
    docker rm test-container
else
    echo "❌ Container failed to start"
    exit 1
fi

# Login to Docker Hub (you'll be prompted for credentials)
echo "🔑 Please login to Docker Hub:"
docker login

if [ $? -eq 0 ]; then
    echo "✅ Successfully logged in to Docker Hub"
else
    echo "❌ Failed to login to Docker Hub"
    exit 1
fi

# Push the image to Docker Hub
echo "📤 Pushing image to Docker Hub..."
docker push $FULL_IMAGE_NAME
docker push $DOCKER_USERNAME/$IMAGE_NAME:latest

if [ $? -eq 0 ]; then
    echo "🎉 Successfully pushed image to Docker Hub!"
    echo "📋 Image details:"
    echo "   - Repository: https://hub.docker.com/r/$DOCKER_USERNAME/$IMAGE_NAME"
    echo "   - Pull command: docker pull $FULL_IMAGE_NAME"
    echo "   - Run command: docker run -p 8080:80 $FULL_IMAGE_NAME"
else
    echo "❌ Failed to push image to Docker Hub"
    exit 1
fi

echo "🏁 Process completed successfully!"