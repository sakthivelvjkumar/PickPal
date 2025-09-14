"""
Quick ngrok setup for MyPickPal uAgents
Automatically configures agents with ngrok public endpoints
"""

import subprocess
import time
import json
import requests
from typing import Optional

def get_ngrok_url(port: int) -> Optional[str]:
    """Get the public ngrok URL for a given port"""
    try:
        # Query ngrok API for tunnels
        response = requests.get("http://localhost:4040/api/tunnels")
        tunnels = response.json()["tunnels"]
        
        for tunnel in tunnels:
            if tunnel["config"]["addr"] == f"localhost:{port}":
                return tunnel["public_url"]
        
        return None
    except Exception as e:
        print(f"Error getting ngrok URL: {e}")
        return None

def start_ngrok_tunnel(port: int) -> str:
    """Start ngrok tunnel and return public URL"""
    print(f"Starting ngrok tunnel for port {port}...")
    
    # Start ngrok in background
    process = subprocess.Popen(
        ["ngrok", "http", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for ngrok to start
    time.sleep(3)
    
    # Get the public URL
    public_url = get_ngrok_url(port)
    
    if public_url:
        print(f"✅ ngrok tunnel active: {public_url}")
        return public_url
    else:
        print("❌ Failed to get ngrok URL")
        return None

def setup_agents_with_ngrok():
    """Setup both agents with ngrok endpoints"""
    print("🚀 Setting up MyPickPal agents with ngrok...")
    
    # Start tunnels for both agents
    discovery_url = start_ngrok_tunnel(8000)
    planner_url = start_ngrok_tunnel(8001)
    
    if discovery_url and planner_url:
        print("\n📝 Agent Configuration:")
        print(f"Discovery Agent: {discovery_url}")
        print(f"Planner Agent: {planner_url}")
        
        # Save configuration
        config = {
            "discovery_endpoint": discovery_url,
            "planner_endpoint": planner_url,
            "timestamp": time.time()
        }
        
        with open("ngrok_config.json", "w") as f:
            json.dump(config, f, indent=2)
        
        print("\n💾 Configuration saved to ngrok_config.json")
        print("\n🔗 Next steps:")
        print("1. Update your agent code with these endpoints")
        print("2. Start your agents: python agentverse_discovery.py")
        print("3. Test connectivity: curl {discovery_url}/health")
        
        return config
    else:
        print("❌ Failed to setup ngrok tunnels")
        return None

if __name__ == "__main__":
    setup_agents_with_ngrok()
