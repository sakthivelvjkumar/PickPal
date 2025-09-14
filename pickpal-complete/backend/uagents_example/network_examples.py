"""
Complete examples of connecting MyPickPal uAgents to Fetch.ai network
Includes testnet, mainnet, and local development configurations
"""

import os
import asyncio
from uagents import Agent, Context, Protocol, Bureau
from uagents.setup import fund_agent_if_low
from uagents.network import get_faucet, wait_for_tx_to_complete

# Environment-based configuration
def get_network_config():
    """Get network configuration based on environment"""
    env = os.getenv("FETCH_NETWORK", "local")  # local, testnet, mainnet
    
    if env == "testnet":
        return {
            "network": "dorado-1",
            "endpoint_base": os.getenv("PUBLIC_ENDPOINT", "http://localhost"),
            "faucet_url": "https://faucet-dorado.fetch.ai"
        }
    elif env == "mainnet":
        return {
            "network": "fetchhub-4", 
            "endpoint_base": os.getenv("PUBLIC_ENDPOINT", "https://agents.mypickpal.com"),
            "faucet_url": None  # No faucet on mainnet
        }
    else:  # local development
        return {
            "network": None,  # Local network
            "endpoint_base": "http://localhost",
            "faucet_url": None
        }

# Get configuration
config = get_network_config()

# Create agents with network configuration
discovery_agent = Agent(
    name="myPickPal_discovery",
    seed=os.getenv("DISCOVERY_SEED", "discovery_seed_phrase_12345"),
    port=8000,
    endpoint=[f"{config['endpoint_base']}:8000/submit"] if config['endpoint_base'] else None,
    network=config.get("network")
)

planner_agent = Agent(
    name="myPickPal_planner", 
    seed=os.getenv("PLANNER_SEED", "planner_seed_phrase_67890"),
    port=8001,
    endpoint=[f"{config['endpoint_base']}:8001/submit"] if config['endpoint_base'] else None,
    network=config.get("network")
)

client_agent = Agent(
    name="myPickPal_client",
    seed=os.getenv("CLIENT_SEED", "client_seed_phrase_abcde"),
    port=8002,
    endpoint=[f"{config['endpoint_base']}:8002/submit"] if config['endpoint_base'] else None,
    network=config.get("network")
)

@discovery_agent.on_event("startup")
async def setup_discovery_agent(ctx: Context):
    """Setup discovery agent for network"""
    ctx.logger.info(f"Discovery Agent starting on network: {config.get('network', 'local')}")
    ctx.logger.info(f"Agent address: {discovery_agent.address}")
    ctx.logger.info(f"Wallet address: {discovery_agent.wallet.address()}")
    
    # Fund agent if on testnet
    if config.get("network") == "dorado-1":
        try:
            await fund_agent_if_low(discovery_agent.wallet.address())
            ctx.logger.info("Agent funded on testnet")
        except Exception as e:
            ctx.logger.error(f"Failed to fund agent: {e}")
            ctx.logger.info(f"Manual funding: Visit {config['faucet_url']} with address {discovery_agent.wallet.address()}")

@planner_agent.on_event("startup") 
async def setup_planner_agent(ctx: Context):
    """Setup planner agent for network"""
    ctx.logger.info(f"Planner Agent starting on network: {config.get('network', 'local')}")
    ctx.logger.info(f"Agent address: {planner_agent.address}")
    ctx.logger.info(f"Wallet address: {planner_agent.wallet.address()}")
    
    # Fund agent if on testnet
    if config.get("network") == "dorado-1":
        try:
            await fund_agent_if_low(planner_agent.wallet.address())
            ctx.logger.info("Agent funded on testnet")
        except Exception as e:
            ctx.logger.error(f"Failed to fund agent: {e}")

@client_agent.on_event("startup")
async def setup_client_agent(ctx: Context):
    """Setup client agent for network"""
    ctx.logger.info(f"Client Agent starting on network: {config.get('network', 'local')}")
    ctx.logger.info(f"Agent address: {client_agent.address}")
    
    # Fund agent if on testnet
    if config.get("network") == "dorado-1":
        try:
            await fund_agent_if_low(client_agent.wallet.address())
            ctx.logger.info("Agent funded on testnet")
        except Exception as e:
            ctx.logger.error(f"Failed to fund agent: {e}")
    
    # Wait for other agents to be ready
    await asyncio.sleep(3)
    
    # In network mode, discover other agents
    if config.get("network"):
        await discover_and_test_network(ctx)
    else:
        await test_local_communication(ctx)

async def discover_and_test_network(ctx: Context):
    """Discover agents on the network and test communication"""
    ctx.logger.info("Discovering agents on Fetch.ai network...")
    
    # In a real implementation, you would query the network for agents
    # For now, we'll use known addresses (would be discovered dynamically)
    
    # These would be the actual addresses of your deployed agents
    known_agents = {
        "discovery": discovery_agent.address,
        "planner": planner_agent.address
    }
    
    ctx.logger.info(f"Known agents: {known_agents}")
    
    # Test communication with planner
    from planner_uagent import ShoppingRequest
    import uuid
    
    test_request = ShoppingRequest(
        request_id=f"network_test_{uuid.uuid4().hex[:8]}",
        query="wireless earbuds under $100",
        constraints={"max_price": 100.0},
        user_address=client_agent.address
    )
    
    try:
        await ctx.send(known_agents["planner"], test_request)
        ctx.logger.info("Successfully sent test request over network")
    except Exception as e:
        ctx.logger.error(f"Failed to send network message: {e}")

async def test_local_communication(ctx: Context):
    """Test local agent communication"""
    ctx.logger.info("Testing local agent communication...")
    
    # Local testing logic here
    from planner_uagent import ShoppingRequest
    import uuid
    
    test_request = ShoppingRequest(
        request_id=f"local_test_{uuid.uuid4().hex[:8]}",
        query="gaming laptop under $1000",
        constraints={"max_price": 1000.0},
        user_address=client_agent.address
    )
    
    try:
        # In local mode, use direct addresses
        await ctx.send(planner_agent.address, test_request)
        ctx.logger.info("Successfully sent test request locally")
    except Exception as e:
        ctx.logger.error(f"Failed to send local message: {e}")

# Bureau for running all agents together (development mode)
bureau = Bureau(port=8080)
bureau.add(discovery_agent)
bureau.add(planner_agent) 
bureau.add(client_agent)

def run_single_agent(agent_name):
    """Run a single agent (for production deployment)"""
    agents = {
        "discovery": discovery_agent,
        "planner": planner_agent,
        "client": client_agent
    }
    
    if agent_name in agents:
        print(f"Starting {agent_name} agent...")
        print(f"Network: {config.get('network', 'local')}")
        print(f"Address: {agents[agent_name].address}")
        agents[agent_name].run()
    else:
        print(f"Unknown agent: {agent_name}")
        print(f"Available agents: {list(agents.keys())}")

if __name__ == "__main__":
    import sys
    
    print("MyPickPal uAgents Network Setup")
    print(f"Network: {config.get('network', 'local')}")
    print(f"Endpoint base: {config.get('endpoint_base', 'localhost')}")
    
    if len(sys.argv) > 1:
        # Run specific agent
        agent_name = sys.argv[1]
        run_single_agent(agent_name)
    else:
        # Run all agents via bureau (development mode)
        print("Running all agents via Bureau...")
        print("Agent addresses:")
        print(f"  Discovery: {discovery_agent.address}")
        print(f"  Planner: {planner_agent.address}")
        print(f"  Client: {client_agent.address}")
        bureau.run()
