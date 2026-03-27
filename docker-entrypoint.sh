#!/bin/bash

echo "Starting Backend Database & AI FastAPI..."
# Navigate to backend since the code heavily relies on backend directory paths
cd /app/backend
uvicorn server_cloud:app --host 0.0.0.0 --port 8000 &

echo "Waiting for server to start..."
sleep 3

echo "Starting Edge Node IoT Simulation..."
python edge_node.py &

# Wait for any process to exit (meaning if one fails, docker doesn't instantly die but keeps running the other)
wait -n

# Exit with status of process that exited first
exit $?
