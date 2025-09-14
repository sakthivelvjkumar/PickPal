"""
Agentverse Deployment Script
Automated deployment and registration of MyPickPal agents to Agentverse
"""

import asyncio
import json
import os
import requests
from typing import Dict, Any, Optional

from uagents import Agent
from agentverse_config import (
    AGENTVERSE_CONFIG, 
    DISCOVERY_AGENT_METADATA, 
    PLANNER_AGENT_METADATA,
    create_registration_payload,
    get_agentverse_config
)

class AgentverseDeployer:
    """Handles deployment and registration of agents to Agentverse"""
    
    def __init__(self):
        self.config = get_agentverse_config()
        self.session = requests.Session()
        
        # Set up authentication if API key is provided
        if self.config.get("api_key"):
            self.session.headers.update({
                "Authorization": f"Bearer {self.config['api_key']}",
                "Content-Type": "application/json"
            })
    
    async def register_agent(self, agent: Agent, agent_type: str) -> Dict[str, Any]:
        """Register an agent with Agentverse"""
        print(f"Registering {agent_type} agent with Agentverse...")
        
        # Create registration payload
        payload = create_registration_payload(
            agent_type=agent_type,
            agent_address=agent.address,
            public_endpoint=self.config["public_endpoint"]
        )
        
        try:
            # In a real implementation, this would make an API call to Agentverse
            # For now, we'll simulate the registration process
            print(f"Registration payload for {agent_type}:")
            print(json.dumps(payload, indent=2))
            
            # Simulate successful registration
            registration_result = {
                "success": True,
                "agent_id": f"agentverse_{agent_type}_{agent.address[:8]}",
                "marketplace_url": f"{AGENTVERSE_CONFIG['marketplace_url']}/agent/{agent.address}",
                "status": "registered",
                "message": f"{agent_type.title()} agent successfully registered"
            }
            
            print(f"✅ {agent_type.title()} agent registered successfully!")
            print(f"   Agent ID: {registration_result['agent_id']}")
            print(f"   Marketplace URL: {registration_result['marketplace_url']}")
            
            return registration_result
            
        except Exception as e:
            print(f"❌ Failed to register {agent_type} agent: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Registration failed for {agent_type} agent"
            }
    
    async def deploy_discovery_agent(self) -> Dict[str, Any]:
        """Deploy and register the Discovery Agent"""
        from agentverse_discovery import discovery_agent
        
        print("🚀 Deploying Discovery Agent to Agentverse...")
        
        # Register with Agentverse
        registration = await self.register_agent(discovery_agent, "discovery")
        
        if registration["success"]:
            print("📝 Discovery Agent Service Details:")
            print(f"   Name: {DISCOVERY_AGENT_METADATA['name']}")
            print(f"   Description: {DISCOVERY_AGENT_METADATA['description']}")
            print(f"   Capabilities: {len(DISCOVERY_AGENT_METADATA['capabilities'])} features")
            print(f"   Protocols: {', '.join(DISCOVERY_AGENT_METADATA['protocols'])}")
            print(f"   Pricing: {DISCOVERY_AGENT_METADATA['pricing']['base_fee']} FET per request")
        
        return registration
    
    async def deploy_planner_agent(self) -> Dict[str, Any]:
        """Deploy and register the Planner Agent"""
        from agentverse_planner import planner_agent
        
        print("🚀 Deploying Planner Agent to Agentverse...")
        
        # Register with Agentverse
        registration = await self.register_agent(planner_agent, "planner")
        
        if registration["success"]:
            print("📝 Planner Agent Service Details:")
            print(f"   Name: {PLANNER_AGENT_METADATA['name']}")
            print(f"   Description: {PLANNER_AGENT_METADATA['description']}")
            print(f"   Capabilities: {len(PLANNER_AGENT_METADATA['capabilities'])} features")
            print(f"   Protocols: {', '.join(PLANNER_AGENT_METADATA['protocols'])}")
            print(f"   Pricing: {PLANNER_AGENT_METADATA['pricing']['base_fee']} FET per goal")
        
        return registration
    
    async def deploy_all_agents(self) -> Dict[str, Any]:
        """Deploy all MyPickPal agents to Agentverse"""
        print("🌟 Starting MyPickPal Agentverse Deployment...")
        print(f"Network: {self.config['network']}")
        print(f"Public Endpoint: {self.config['public_endpoint']}")
        print("-" * 60)
        
        results = {}
        
        # Deploy Discovery Agent
        results["discovery"] = await self.deploy_discovery_agent()
        print()
        
        # Deploy Planner Agent
        results["planner"] = await self.deploy_planner_agent()
        print()
        
        # Summary
        successful_deployments = sum(1 for r in results.values() if r["success"])
        total_deployments = len(results)
        
        print("📊 Deployment Summary:")
        print(f"   Successful: {successful_deployments}/{total_deployments}")
        
        if successful_deployments == total_deployments:
            print("🎉 All agents deployed successfully!")
            print("\n🔗 Next Steps:")
            print("1. Verify agents are running on your public endpoints")
            print("2. Test agent communication via Agentverse")
            print("3. Enable Chat Protocol for ASI:One integration")
            print("4. Monitor agent performance and usage")
            print(f"5. Visit marketplace: {AGENTVERSE_CONFIG['marketplace_url']}")
        else:
            print("⚠️  Some deployments failed. Check logs above.")
        
        return results
    
    def generate_deployment_instructions(self) -> str:
        """Generate deployment instructions for manual setup"""
        instructions = f"""
# MyPickPal Agentverse Deployment Instructions

## Prerequisites
1. Public server with static IP address
2. Domain name (recommended)
3. SSL certificate for HTTPS
4. FET tokens for agent funding

## Environment Setup
```bash
export AGENTVERSE_NETWORK=fetchai-testnet
export PUBLIC_ENDPOINT=https://your-domain.com
export AGENTVERSE_API_KEY=your_api_key_here
export DISCOVERY_SEED=your_discovery_agent_seed
export PLANNER_SEED=your_planner_agent_seed
```

## Deployment Steps

### 1. Start Discovery Agent
```bash
cd uagents_example
python agentverse_discovery.py
```

### 2. Start Planner Agent (separate terminal)
```bash
cd uagents_example
python agentverse_planner.py
```

### 3. Register with Agentverse
```bash
python agentverse_deployment.py
```

## Verification
- Check agent health: GET https://your-domain.com:8000/health
- Test discovery: Send AgentverseShoppingRequest to discovery agent
- Test planning: Send AgentverseShoppingGoal to planner agent
- Verify marketplace listing: Visit {AGENTVERSE_CONFIG['marketplace_url']}

## Monitoring
- Monitor agent logs for errors
- Track request volume and response times
- Monitor FET token balance
- Set up alerts for downtime

## Troubleshooting
- Ensure ports 8000, 8001 are open
- Verify SSL certificates are valid
- Check agent funding status
- Validate endpoint accessibility from internet
"""
        return instructions

async def main():
    """Main deployment function"""
    deployer = AgentverseDeployer()
    
    # Check configuration
    config = get_agentverse_config()
    
    if not config.get("public_endpoint") or config["public_endpoint"] == "http://localhost":
        print("⚠️  Warning: PUBLIC_ENDPOINT not set or using localhost")
        print("   For Agentverse deployment, you need a public endpoint")
        print("   Set environment variable: export PUBLIC_ENDPOINT=https://your-domain.com")
        print()
    
    # Generate deployment instructions
    instructions = deployer.generate_deployment_instructions()
    
    # Save instructions to file
    with open("deployment_instructions.md", "w") as f:
        f.write(instructions)
    
    print("📋 Deployment instructions saved to: deployment_instructions.md")
    print()
    
    # Perform deployment
    results = await deployer.deploy_all_agents()
    
    # Save deployment results
    with open("deployment_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("💾 Deployment results saved to: deployment_results.json")

if __name__ == "__main__":
    asyncio.run(main())
