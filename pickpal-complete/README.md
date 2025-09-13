# PickPal - AI Shopping Assistant

A modern AI-powered shopping assistant with Claude-like interface, built with React and FastAPI.

## 🚀 Features

- **AI-Powered Product Recommendations**: Analyzes thousands of reviews to recommend the top 3 products
- **Sentiment Analysis**: Uses TextBlob to analyze review sentiment and calculate overall scores
- **Claude-like Interface**: Fluid animations and smooth transitions
- **Search History**: Persistent search history with SQLite database storage
- **Responsive Design**: Beautiful UI with Tailwind CSS and shadcn/ui components

## 📁 Project Structure

```
pickpal-complete/
├── frontend/          # React frontend application
│   ├── src/
│   │   ├── App.tsx    # Main application component
│   │   ├── index.css  # Tailwind CSS styles with animations
│   │   └── main.tsx   # React entry point
│   ├── package.json   # Frontend dependencies
│   └── index.html     # HTML template
├── backend/           # FastAPI backend application
│   ├── app/
│   │   └── main.py    # FastAPI application with all endpoints
│   └── pyproject.toml # Backend dependencies
└── README.md          # This file
```

## 🛠️ Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Install Poetry (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. Install dependencies:
   ```bash
   poetry install
   ```

4. Run the backend server:
   ```bash
   poetry run fastapi dev app/main.py
   ```

The backend will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create a `.env` file:
   ```bash
   echo "VITE_API_URL=http://localhost:8000" > .env
   ```

4. Run the development server:
   ```bash
   npm run dev
   ```

The frontend will be available at `http://localhost:5173`

## 🎯 API Endpoints

- `GET /healthz` - Health check
- `POST /search` - Search for products
- `GET /categories` - Get available categories
- `GET /search-history` - Get search history
- `POST /search-history` - Create search history entry
- `DELETE /search-history/{id}` - Delete search history entry
- `DELETE /search-history` - Clear all search history

## 🎨 Key Features Implemented

### PickPal Branding
- Complete rebranding from "AI Shopping Assistant" to "PickPal"
- Updated throughout the interface and API responses

### Claude-like Animations
- Smooth transitions and hover effects
- Staggered animations for search results
- Micro-interactions on buttons and inputs

### Search History Sidebar
- Persistent search history with SQLite database
- Sidebar that slides in/out like Claude's interface
- Shows previous searches with timestamps and results counts

### AI-Powered Recommendations
- Sentiment analysis using TextBlob
- Overall scoring based on ratings and sentiment
- Pros and cons extraction from reviews
- Top 3 product recommendations

## 🚀 Deployment

The application is designed to be deployed with:
- Frontend: Static hosting (Vercel, Netlify, etc.)
- Backend: Cloud platforms (Fly.io, Railway, etc.)

Make sure to update the `VITE_API_URL` environment variable in the frontend to point to your deployed backend URL.

## 🛡️ Dependencies

### Frontend
- React 18 with TypeScript
- Vite for build tooling
- Tailwind CSS for styling
- shadcn/ui for components
- Lucide React for icons

### Backend
- FastAPI for the web framework
- TextBlob for sentiment analysis
- aiosqlite for database operations
- Pydantic for data validation

## 📝 License

This project is open source and available under the MIT License.
