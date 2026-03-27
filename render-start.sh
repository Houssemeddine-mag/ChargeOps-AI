#!/bin/bash

# Start the FastAPI backend server in the background
# We use the PORT environment variable provided by Render
cd backend
uvicorn server_cloud:app --host 0.0.0.0 --port $PORT &

# Go back to the root directory
cd ..

# Give the server 5 seconds to wake up and get ready
echo "Waiting for server to start..."
sleep 5

# Start the continuous simulator in the background
echo "Starting Edge Node Simulator..."
cd backend 
python edge_node.py &

# Wait for both background processes so the container doesn't exit
wait -n
