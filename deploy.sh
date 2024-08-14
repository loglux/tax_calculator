#!/bin/bash

# Stop script execution on error
set -e

# Image and container name
NAME="tax_calculator"
PORT=9000

# Build Docker image
echo "Building Docker image..."
docker build -t $NAME .

# Check if the container is running or exists
if [ "$(docker ps -a -q -f name=$NAME)" ]; then
    echo "Stopping and removing existing container..."
    docker stop $NAME
    docker rm $NAME
fi

# Run new container on the fixed port
echo "Running new container on port $PORT..."
docker run -d --name $NAME -p $PORT:8000 \
    -e DJANGO_SETTINGS_MODULE=tax_calculator.settings_docker \
    $NAME

# Check if the container started successfully
if [ "$(docker ps -q -f name=$NAME)" ]; then
    echo "Deployment completed successfully. Access the application on port $PORT."
else
    echo "Failed to start container. Here are the logs:"
    docker logs $NAME
    docker rm $NAME
fi
