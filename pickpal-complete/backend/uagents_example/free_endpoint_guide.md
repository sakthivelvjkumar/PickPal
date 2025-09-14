# Free Public Endpoint Setup Guide

## 🚀 Method 1: ngrok (Recommended - 2 minutes)

### Install
```bash
# macOS
brew install ngrok

# Windows/Linux - Download from https://ngrok.com/download
```

### Quick Setup
```bash
# Terminal 1: Start your agent
python agentverse_discovery.py

# Terminal 2: Expose publicly  
ngrok http 8000
# Copy the HTTPS URL: https://abc123.ngrok.io
```

### Update Agent Code
```python
discovery_agent = Agent(
    name="MyPickPal-Discovery",
    endpoint=["https://abc123.ngrok.io/submit"],  # Use ngrok URL
    port=8000
)
```

**Pros:** Instant setup, HTTPS included  
**Cons:** URL changes on restart

---

## ☁️ Method 2: Railway (Permanent Free)

### Setup
```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

### Get URL
- Visit Railway dashboard
- Copy your app URL: `https://yourapp.railway.app`

**Pros:** Permanent URL, Git integration  
**Cons:** 5-minute setup

---

## 🌐 Method 3: Render (Free Forever)

### Setup
1. Push code to GitHub
2. Connect to render.com
3. Deploy as Web Service
4. Get URL: `https://yourapp.onrender.com`

**Pros:** Always free, automatic deployments  
**Cons:** Sleeps after 15min (wakes on request)

---

## 🔧 Automated ngrok Setup

Run the setup script:
```bash
python ngrok_setup.py
```

This will:
1. Start ngrok tunnels for ports 8000 & 8001
2. Get public URLs automatically
3. Save configuration to `ngrok_config.json`

---

## 💡 Pro Tips

### For Development (ngrok)
- Free tier gives you random URLs
- Perfect for testing Agentverse integration
- Restart ngrok to get new URL if needed

### For Production (Railway/Render)
- Get permanent URLs
- Better for hackathon submissions
- Automatic HTTPS and scaling

### Quick Test
```bash
# Test your public endpoint
curl https://your-ngrok-url.ngrok.io/health
```

**Recommendation:** Start with ngrok for immediate testing, then move to Railway/Render for permanent deployment.
