import webview
import threading
import uvicorn
import sys
import os
import subprocess
import time
import socket

# Add the backend folder to sys.path so we can import the FastAPI app
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.append(backend_dir)

from server_cloud import app

# Keep track of subprocesses to kill them cleanly
processes = []

def start_api_server():
    """Starts the FastAPI web server via subprocess."""
    print("Starting ChargeOps API Server...")
    server_path = os.path.join(backend_dir, "server_cloud.py")
    # We can run uvicorn as a module
    p = subprocess.Popen([sys.executable, "-m", "uvicorn", "server_cloud:app", "--host", "127.0.0.1", "--port", "8000"], cwd=backend_dir)
    processes.append(p)

def start_simulation():
    """Starts the edge node simulation that feeds the database."""
    print("Starting Edge Node Simulation...")
    edge_node_path = os.path.join(backend_dir, "edge_node.py")
    p = subprocess.Popen([sys.executable, edge_node_path], cwd=backend_dir)
    processes.append(p)

def check_port_in_use(port):
    """Utility to check if the server actually started."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def on_closed():
    """Callback when the main window is closed by the user."""
    print("Window closed. Shutting down all services...")
    for p in processes:
        p.terminate()
    os._exit(0)

def force_window_refresh(window):
    """Ensure the webview reloads correctly after server boots."""
    time.sleep(2)
    # wait until port 8000 is listening
    while not check_port_in_use(8000):
        time.sleep(0.5)
    print("Server is active. Loading UI...")
    # Optional reload; usually the initial URL is enough, but this ensures no white screen
    window.load_url('http://127.0.0.1:8000/dashboard/')

if __name__ == '__main__':
    # 1. Start the API Server as a subprocess
    start_api_server()

    # 2. Wait a moment then start simulation script
    start_simulation()

    # 3. Create the Native Desktop Window via PyWebView
    window = webview.create_window(
        'ChargeOps AI - Native Dashboard', 
        url='http://127.0.0.1:8000/dashboard/',
        width=1280, 
        height=850,
        min_size=(900, 600),
        background_color='#f8fafc' # Slate-50 background like light mode
    )
    
    # Register close event
    window.events.closed += on_closed
    
    # Optional: trigger a clean reload once the server binds port 8000
    threading.Thread(target=force_window_refresh, args=(window,), daemon=True).start()

    # Launch PyWebView (must be in the main thread)
    print("Launching Desktop UI...")
    webview.start(private_mode=False)

