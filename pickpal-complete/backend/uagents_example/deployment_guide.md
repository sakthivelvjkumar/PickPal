# Connecting MyPickPal uAgents to Fetch.ai Network

## Quick Start - Testnet Deployment

### 1. Install Dependencies
```bash
pip install uagents==0.12.0
```

### 2. Get Testnet Tokens
Visit the Fetch.ai faucet: https://faucet-dorado.fetch.ai/
- Enter your agent's wallet address
- Request testnet FET tokens (needed for transactions)

### 3. Update Agent Configuration
```python
from uagents import Agent

# Connect to Fetch.ai testnet
agent = Agent(
    name="myPickPal_discovery",
    seed="your_unique_seed_phrase_here",
    port=8000,
    endpoint=["http://your-server.com:8000/submit"],  # Public endpoint
    network="dorado-1"  # Fetch.ai testnet
)
```

### 4. Deploy to Public Server
```bash
# Run on a server with public IP
python discovery_uagent.py
```

## Network Options

### Testnet (Recommended for Development)
```python
TESTNET_CONFIG = {
    "network": "dorado-1",
    "faucet": "https://faucet-dorado.fetch.ai",
    "explorer": "https://explore-dorado.fetch.ai"
}
```

### Mainnet (Production)
```python
MAINNET_CONFIG = {
    "network": "fetchhub-4",
    "explorer": "https://explore-fetchhub.fetch.ai"
}
```

## Step-by-Step Connection Process

### Step 1: Generate Agent Address
```python
from uagents import Agent

agent = Agent(seed="your_unique_seed")
print(f"Agent Address: {agent.address}")
print(f"Wallet Address: {agent.wallet.address()}")
```

### Step 2: Fund Your Agent (Testnet)
```bash
# Visit faucet with your wallet address
curl -X POST https://faucet-dorado.fetch.ai/api/v1/faucet \
  -H "Content-Type: application/json" \
  -d '{"address": "your_wallet_address"}'
```

### Step 3: Configure Public Endpoint
```python
agent = Agent(
    name="myPickPal_discovery",
    seed="your_seed",
    port=8000,
    endpoint=["http://YOUR_PUBLIC_IP:8000/submit"],  # Must be publicly accessible
    network="dorado-1"
)
```

### Step 4: Register Services (Optional)
```python
@agent.on_event("startup")
async def register_services(ctx: Context):
    # Register your agent's capabilities
    ctx.logger.info("Registering product discovery services")
    # Service registration logic here
```

## Agent Discovery & Communication

### Finding Other Agents
```python
# In production, you'd discover agents via the network
DISCOVERY_AGENT_ADDRESS = "agent1qw8s7d9k2j3h4g5f6d7s8a9z0x1c2v3b4n5m6"

# Send message to discovered agent
await ctx.send(DISCOVERY_AGENT_ADDRESS, shopping_request)
```

### Service Registry Integration
```python
from uagents.query import query

# Query for shopping agents
shopping_agents = await query(
    "shopping_recommendation", 
    network="dorado-1"
)
```

## Production Deployment Checklist

### Infrastructure
- [ ] Public server with static IP
- [ ] Domain name (optional but recommended)
- [ ] SSL certificate for HTTPS endpoints
- [ ] Firewall configured for agent ports

### Agent Configuration
- [ ] Unique seed phrases for each agent
- [ ] Public endpoints configured
- [ ] Network set to "fetchhub-4" for mainnet
- [ ] Sufficient FET tokens for transactions

### Monitoring
- [ ] Logging configured
- [ ] Health check endpoints
- [ ] Performance monitoring
- [ ] Error alerting

## Example Production Setup

### Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["python", "discovery_uagent.py"]
```

### Docker Compose
```yaml
version: '3.8'
services:
  discovery-agent:
    build: .
    ports:
      - "8000:8000"
    environment:
      - AGENT_SEED=${DISCOVERY_SEED}
      - NETWORK=fetchhub-4
      - ENDPOINT=https://discovery.mypickpal.com:8000/submit
    restart: unless-stopped

  planner-agent:
    build: .
    ports:
      - "8001:8001"
    environment:
      - AGENT_SEED=${PLANNER_SEED}
      - NETWORK=fetchhub-4
      - ENDPOINT=https://planner.mypickpal.com:8001/submit
    restart: unless-stopped
```

## Cost Considerations

### Testnet (Free)
- Free FET tokens from faucet
- No transaction costs
- Perfect for development/testing

### Mainnet (Production)
- Real FET tokens required
- Transaction fees for messages
- Typical costs: ~0.001 FET per message
- Monthly cost estimate: $10-50 for moderate usage

## Troubleshooting

### Common Issues
1. **Agent not reachable**: Ensure endpoint is publicly accessible
2. **Insufficient funds**: Check wallet balance and fund if needed
3. **Network connection**: Verify network configuration matches target
4. **Port conflicts**: Ensure agent ports are unique and available

### Debug Commands
```bash
# Check agent balance
uagents balance <wallet_address>

# Test network connectivity
curl http://your-agent-endpoint/health

# View agent logs
tail -f agent.log
```

## Security Best Practices

1. **Seed Management**: Store seed phrases securely (environment variables)
2. **Endpoint Security**: Use HTTPS for production endpoints
3. **Access Control**: Implement authentication for sensitive operations
4. **Rate Limiting**: Protect against spam/abuse
5. **Input Validation**: Sanitize all incoming messages

## Next Steps

1. Start with testnet deployment
2. Test agent communication
3. Monitor performance and costs
4. Gradually migrate to mainnet
5. Implement service discovery
6. Add economic incentives
