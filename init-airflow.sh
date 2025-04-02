#!/bin/bash

# Wait for postgres to be ready
echo "Waiting for postgres to be ready..."
sleep 10

# Initialize the database
echo "Initializing Airflow database..."
docker-compose exec airflow-webserver airflow db init

# Create admin user
echo "Creating admin user..."
docker-compose exec airflow-webserver airflow users create \
    --username admin \
    --password admin \
    --firstname admin \
    --lastname admin \
    --role Admin \
    --email admin@example.com

# Start all services
echo "Starting all services..."
docker-compose up -d

echo "Airflow initialization complete!" 