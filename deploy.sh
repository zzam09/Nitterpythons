#!/bin/bash

# Tweet Tracker VPS Deployment Script
# One-command deployment for VPS

set -e

echo "=== Tweet Tracker VPS Deployment ==="
echo "Starting deployment..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "Docker installed. Please log out and log back in, then run this script again."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose not found. Installing..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Create data directory
mkdir -p data

# Stop existing container if running
echo "Stopping existing container (if any)..."
docker-compose down 2>/dev/null || true

# Build and start the application
echo "Building and starting Tweet Tracker..."
docker-compose up --build -d

# Wait for container to start
echo "Waiting for application to start..."
sleep 10

# Check if application is running
if curl -f http://localhost:5000/api/stats &> /dev/null; then
    echo "=== Deployment Successful! ==="
    echo "Tweet Tracker is now running on: http://$(curl -s ifconfig.me):5000"
    echo ""
    echo "Quick Test Commands:"
    echo "  curl http://$(curl -s ifconfig.me):5000/api/stats"
    echo "  curl http://$(curl -s ifconfig.me):5000/api/users"
    echo ""
    echo "Management Commands:"
    echo "  View logs: docker-compose logs -f"
    echo "  Stop: docker-compose down"
    echo "  Restart: docker-compose restart"
    echo "  Update: docker-compose pull && docker-compose up -d"
    echo ""
    echo "Data Location: ./data/"
    echo "Settings File: ./settings.json"
    echo "Environment: .env"
else
    echo "=== Deployment Failed ==="
    echo "Check logs with: docker-compose logs"
    exit 1
fi
