#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_message() {
    echo -e "${2}${1}${NC}"
}

# Function to check if a command exists
check_command() {
    if ! command -v $1 &> /dev/null; then
        print_message "Error: $1 is not installed" "$RED"
        exit 1
    fi
}

# Function to check if Docker daemon is running
check_docker_daemon() {
    if ! docker info > /dev/null 2>&1; then
        print_message "Error: Docker daemon is not running" "$RED"
        print_message "Please start Docker Desktop and try again" "$YELLOW"
        print_message "On macOS, you can start Docker Desktop by:" "$YELLOW"
        print_message "1. Opening Docker Desktop application" "$YELLOW"
        print_message "2. Waiting for it to fully start (whale icon in menu bar should stop animating)" "$YELLOW"
        exit 1
    fi
}

# Function to check if a port is in use
check_port() {
    if lsof -i :$1 > /dev/null; then
        print_message "Error: Port $1 is already in use" "$RED"
        exit 1
    fi
}

# Function to determine docker compose command
get_docker_compose_cmd() {
    if docker compose version > /dev/null 2>&1; then
        echo "docker compose"
    else
        echo "docker-compose"
    fi
}

# Check required commands
print_message "Checking required commands..." "$YELLOW"
check_command "docker"

# Check if Docker daemon is running
print_message "Checking Docker daemon..." "$YELLOW"
check_docker_daemon

# Determine docker compose command
DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
print_message "Using Docker Compose command: $DOCKER_COMPOSE_CMD" "$YELLOW"

# Check for .env file and load it if exists
if [ -f .env ]; then
    print_message "Loading environment variables from .env file..." "$YELLOW"
    set -a
    source .env
    set +a
fi

# Check required ports
print_message "Checking required ports..." "$YELLOW"
check_port "8080"  # Airflow webserver
check_port "8000"  # API
check_port "5432"  # PostgreSQL

# Check required environment variables
print_message "Checking environment variables..." "$YELLOW"
required_vars=("AWS_ACCESS_KEY_ID" "AWS_SECRET_ACCESS_KEY" "AWS_DEFAULT_REGION")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    print_message "Error: The following environment variables are not set:" "$RED"
    printf '%s\n' "${missing_vars[@]}"
    print_message "Please set these variables in your environment or in the .env file" "$RED"
    print_message "Example .env file contents:" "$YELLOW"
    print_message "AWS_ACCESS_KEY_ID=your_access_key" "$YELLOW"
    print_message "AWS_SECRET_ACCESS_KEY=your_secret_key" "$YELLOW"
    print_message "AWS_DEFAULT_REGION=your_region" "$YELLOW"
    exit 1
fi

# Create necessary directories if they don't exist
print_message "Creating necessary directories..." "$YELLOW"
mkdir -p ./airflow/dags
mkdir -p ./terraform/aws
mkdir -p ./terraform/oci

# Stop any existing containers
print_message "Stopping any existing containers..." "$YELLOW"
$DOCKER_COMPOSE_CMD down -v

# Start PostgreSQL first
print_message "Starting PostgreSQL..." "$YELLOW"
$DOCKER_COMPOSE_CMD up -d postgres

# Function to wait for a service to be healthy
wait_for_service() {
    local service=$1
    local max_attempts=30  # Increased from 3 to 30
    local attempt=1
    
    print_message "Waiting for $service to be healthy..." "$YELLOW"
    
    while [ $attempt -le $max_attempts ]; do
        if $DOCKER_COMPOSE_CMD ps $service | grep -q "healthy"; then
            print_message "$service is healthy!" "$GREEN"
            return 0
        fi
        print_message "Attempt $attempt/$max_attempts: Waiting for $service..." "$YELLOW"
        sleep 5
        attempt=$((attempt + 1))
    done
    
    print_message "Error: $service failed to become healthy" "$RED"
    print_message "Checking logs for $service..." "$YELLOW"
    $DOCKER_COMPOSE_CMD logs $service --tail=50
    return 1
}

# Wait for PostgreSQL to be healthy
wait_for_service "postgres"

# Initialize Airflow database
print_message "Initializing Airflow database..." "$YELLOW"
$DOCKER_COMPOSE_CMD run --rm airflow-init airflow db init

# Create admin user
print_message "Creating admin user..." "$YELLOW"
$DOCKER_COMPOSE_CMD run --rm airflow-init airflow users create \
    --username admin \
    --firstname admin \
    --lastname admin \
    --role Admin \
    --email admin@example.com \
    --password admin

# Start the remaining services
print_message "Starting remaining services..." "$YELLOW"
$DOCKER_COMPOSE_CMD up -d

# Wait for services to be healthy
wait_for_service "airflow-webserver"

# Check if services are running
print_message "Checking service status..." "$YELLOW"
if $DOCKER_COMPOSE_CMD ps | grep -q "Up"; then
    print_message "All services are running!" "$GREEN"
    print_message "\nAccess points:" "$GREEN"
    print_message "Airflow UI: http://localhost:8080" "$GREEN"
    print_message "API: http://localhost:8000" "$GREEN"
    print_message "\nDefault credentials:" "$GREEN"
    print_message "Username: admin" "$GREEN"
    print_message "Password: admin" "$GREEN"
else
    print_message "Error: Some services failed to start" "$RED"
    $DOCKER_COMPOSE_CMD ps
    print_message "\nChecking logs for all services..." "$YELLOW"
    $DOCKER_COMPOSE_CMD logs --tail=50
    exit 1
fi

# Print container logs
print_message "\nContainer logs:" "$YELLOW"
$DOCKER_COMPOSE_CMD logs --tail=50 