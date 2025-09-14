"""
Fetch.ai Network Configuration for MyPickPal uAgents
Shows how to connect your uAgents to the Fetch.ai testnet/mainnet
"""

import asyncio
from uagents import Agent, Context, Protocol
from uagents.setup import fund_agent_if_low
from uagents.network import get_faucet, wait_for_tx_to_complete

# Network Configuration
TESTNET_CONFIG = {
    "network": "dorado-1",  # Fetch.ai testnet
    "chain_id": "dorado-1",
    "faucet_url": "https://faucet-dorado.fetch.ai",
    "rest_endpoint": "https://rest-dorado.fetch.ai",
    "rpc_endpoint": "https://rpc-dorado.fetch.ai:443"
}

MAINNET_CONFIG = {
    "network": "fetchhub-4",  # Fetch.ai mainnet
    "chain_id": "fetchhub-4",
    "rest_endpoint": "https://rest-fetchhub.fetch.ai",
    "rpc_endpoint": "https://rpc-fetchhub.fetch.ai:443"
}

# Create agent with network configuration
discovery_agent = Agent(
    name="myPickPal_discovery",
    seed="your_unique_seed_phrase_here_discovery_agent_12345",
    port=8000,
    endpoint=["http://localhost:8000/submit"],
    # Connect to testnet
    network=TESTNET_CONFIG["network"]
)

@discovery_agent.on_event("startup")
async def setup_network_connection(ctx: Context):
    """Setup network connection and fund agent if needed"""
    ctx.logger.info(f"Agent address: {discovery_agent.address}")
    ctx.logger.info(f"Agent wallet address: {discovery_agent.wallet.address()}")
    
    # Fund agent on testnet (for testing)
    try:
        await fund_agent_if_low(discovery_agent.wallet.address())
        ctx.logger.info("Agent funded successfully")
    except Exception as e:
        ctx.logger.error(f"Failed to fund agent: {e}")
    
    # Register agent services (optional)
    await register_agent_services(ctx)

async def register_agent_services(ctx: Context):
    """Register agent capabilities with the network"""
    # This would register your agent's services in the Fetch.ai service registry
    # For now, just log the registration intent
    ctx.logger.info("Registering discovery services...")
    ctx.logger.info("Services: product_discovery, amazon_search, reddit_search")

# Example of how to deploy to different networks
def create_agent_for_network(network_type="testnet"):
    """Create agent configured for specific network"""
    
    config = TESTNET_CONFIG if network_type == "testnet" else MAINNET_CONFIG
    
    agent = Agent(
        name="myPickPal_discovery",
        seed="your_unique_seed_phrase_here",
        port=8000,
        endpoint=["http://localhost:8000/submit"],
        network=config["network"]
    )
    
    return agent

if __name__ == "__main__":
    print("Starting MyPickPal Discovery Agent on Fetch.ai Network...")
    print(f"Network: {TESTNET_CONFIG['network']}")
    print(f"Agent Address: {discovery_agent.address}")
    discovery_agent.run()
