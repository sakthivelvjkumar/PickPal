import { useState, useEffect } from 'react'
import { Send, Sparkles, Star, DollarSign, MessageSquare, History, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface ProductRecommendation {
  name: string
  price: number
  rating: number
  overall_score: number
  pros: string[]
  cons: string[]
  summary: string
  review_count: number
  image_url?: string
}

interface SearchResponse {
  query: string
  recommendations: ProductRecommendation[]
  total_found: number
}

interface SearchHistoryItem {
  id: string
  query: string
  timestamp: Date
  results_count: number
}

function App() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [searchHistory, setSearchHistory] = useState<SearchHistoryItem[]>([])
  const [showHistory, setShowHistory] = useState(false)

  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  useEffect(() => {
    loadSearchHistory()
  }, [])

  const loadSearchHistory = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/search-history`)
      if (response.ok) {
        const data = await response.json()
        setSearchHistory(data.map((item: any) => ({
          ...item,
          timestamp: new Date(item.timestamp)
        })))
      } else {
        const savedHistory = localStorage.getItem('pickpal-search-history')
        if (savedHistory) {
          const parsed = JSON.parse(savedHistory)
          setSearchHistory(parsed.map((item: any) => ({
            ...item,
            timestamp: new Date(item.timestamp)
          })))
        }
      }
    } catch (error) {
      console.error('Failed to load search history:', error)
      const savedHistory = localStorage.getItem('pickpal-search-history')
      if (savedHistory) {
        try {
          const parsed = JSON.parse(savedHistory)
          setSearchHistory(parsed.map((item: any) => ({
            ...item,
            timestamp: new Date(item.timestamp)
          })))
        } catch (e) {
          console.error('Failed to parse search history:', e)
        }
      }
    }
  }

  const addToHistory = async (query: string, resultsCount: number) => {
    try {
      const response = await fetch(`${API_BASE_URL}/search-history`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query,
          results_count: resultsCount
        })
      })
      
      if (response.ok) {
        const newItem = await response.json()
        setSearchHistory(prev => [
          { ...newItem, timestamp: new Date(newItem.timestamp) },
          ...prev.slice(0, 19)
        ])
      } else {
        const newItem: SearchHistoryItem = {
          id: Date.now().toString(),
          query,
          timestamp: new Date(),
          results_count: resultsCount
        }
        setSearchHistory(prev => [newItem, ...prev.slice(0, 19)])
        localStorage.setItem('pickpal-search-history', JSON.stringify([newItem, ...searchHistory.slice(0, 19)]))
      }
    } catch (error) {
      console.error('Failed to save search history:', error)
      const newItem: SearchHistoryItem = {
        id: Date.now().toString(),
        query,
        timestamp: new Date(),
        results_count: resultsCount
      }
      setSearchHistory(prev => [newItem, ...prev.slice(0, 19)])
      localStorage.setItem('pickpal-search-history', JSON.stringify([newItem, ...searchHistory.slice(0, 19)]))
    }
  }

  const clearHistory = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/search-history`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        setSearchHistory([])
      } else {
        setSearchHistory([])
        localStorage.removeItem('pickpal-search-history')
      }
    } catch (error) {
      console.error('Failed to clear search history:', error)
      setSearchHistory([])
      localStorage.removeItem('pickpal-search-history')
    }
  }

  const selectFromHistory = (historyQuery: string) => {
    setQuery(historyQuery)
    setShowHistory(false)
  }

  const handleSearch = async () => {
    if (!query.trim()) return
    
    setLoading(true)
    setError('')
    
    try {
      const searchData = { query: query.trim() }

      const response = await fetch(`${API_BASE_URL}/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(searchData),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data: SearchResponse = await response.json()
      setResults(data)
      addToHistory(query.trim(), data.recommendations.length)
    } catch (err) {
      setError('Failed to search products. Please try again.')
      console.error('Search error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSearch()
    }
  }

  const suggestions = [
    "Best wireless earbuds under $200",
    "Standing desk for small spaces", 
    "Gaming laptop with good battery life",
    "Noise-canceling headphones for travel",
    "Ergonomic office chair under $500",
    "Smart home security camera"
  ]

  return (
    <div className="min-h-screen bg-white flex">
      {/* Search History Sidebar */}
      <div className={`${showHistory ? 'w-80' : 'w-0'} transition-all duration-500 ease-out overflow-hidden border-r border-gray-100 bg-gray-50/80 backdrop-blur-sm`}>
        <div className="p-4 h-full flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-medium text-gray-900">Search History</h2>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearHistory}
              className="h-8 w-8 p-0 text-gray-500 hover:text-gray-700"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
          <div className="flex-1 overflow-y-auto space-y-2">
            {searchHistory.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-8">No search history yet</p>
            ) : (
              searchHistory.map((item) => (
                <button
                  key={item.id}
                  onClick={() => selectFromHistory(item.query)}
                  className="w-full text-left p-3 rounded-lg hover:bg-white transition-all duration-300 ease-out border border-transparent hover:border-gray-200 hover:shadow-sm hover:scale-[1.02] transform"
                >
                  <div className="text-sm text-gray-900 font-medium truncate mb-1">
                    {item.query}
                  </div>
                  <div className="text-xs text-gray-500">
                    {item.results_count} results • {item.timestamp.toLocaleDateString()}
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="border-b border-gray-100">
          <div className="max-w-4xl mx-auto px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-gradient-to-br from-orange-400 to-red-500 rounded-lg flex items-center justify-center">
                  <Sparkles className="h-5 w-5 text-white" />
                </div>
                <h1 className="text-xl font-medium text-gray-900">PickPal</h1>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowHistory(!showHistory)}
                className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-all duration-200 hover:scale-105"
              >
                <History className="h-4 w-4" />
                History
              </Button>
            </div>
          </div>
        </div>

        <div className="max-w-4xl mx-auto px-6 flex-1">
          {/* Main Content Area */}
          <div className="flex flex-col h-[calc(100vh-80px)]">
            {/* Content */}
            <div className="flex-1 overflow-y-auto py-8">
            {!results && !loading && (
              <div className="flex flex-col items-center justify-center h-full text-center max-w-2xl mx-auto animate-in fade-in duration-700 ease-out">
                <div className="w-20 h-20 bg-gradient-to-br from-orange-400 to-red-500 rounded-3xl flex items-center justify-center mb-8 animate-in zoom-in duration-1000 delay-300 ease-out shadow-lg">
                  <Sparkles className="h-10 w-10 text-white animate-pulse" />
                </div>
                <h2 className="text-3xl font-medium text-gray-900 mb-4 animate-in slide-in-from-bottom duration-700 delay-500 ease-out">
                  What do you want to buy?
                </h2>
                <p className="text-lg text-gray-600 mb-12 leading-relaxed animate-in slide-in-from-bottom duration-700 delay-700 ease-out">
                  I'll analyze thousands of reviews to find the best products for you, 
                  complete with pros, cons, and honest recommendations.
                </p>
                
                <div className="w-full space-y-3 animate-in slide-in-from-bottom duration-700 delay-900 ease-out">
                  <p className="text-sm text-gray-500 mb-4">Try asking about:</p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {suggestions.map((suggestion, index) => (
                      <button
                        key={index}
                        onClick={() => setQuery(suggestion)}
                        className="p-4 text-left border border-gray-200 rounded-xl hover:border-orange-200 hover:bg-orange-50/50 transition-all duration-400 ease-out hover:scale-[1.03] hover:shadow-md text-sm text-gray-700 animate-in slide-in-from-bottom duration-600 ease-out transform hover:-translate-y-1"
                        style={{ animationDelay: `${1100 + index * 150}ms` }}
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {loading && (
              <div className="flex flex-col items-center justify-center h-full animate-in fade-in duration-500 ease-out">
                <div className="relative mb-6">
                  <div className="w-12 h-12 border-3 border-orange-100 border-t-orange-500 rounded-full animate-spin"></div>
                  <div className="absolute inset-0 w-12 h-12 border-3 border-transparent border-r-orange-300 rounded-full animate-spin animation-delay-150"></div>
                </div>
                <p className="text-gray-600 animate-pulse text-lg font-medium">Analyzing products with AI...</p>
                <div className="flex space-x-1 mt-4">
                  <div className="w-2 h-2 bg-orange-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-orange-400 rounded-full animate-bounce animation-delay-100"></div>
                  <div className="w-2 h-2 bg-orange-400 rounded-full animate-bounce animation-delay-200"></div>
                </div>
              </div>
            )}

            {error && (
              <div className="flex items-center justify-center h-full">
                <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-red-700 max-w-md text-center">
                  {error}
                </div>
              </div>
            )}

            {results && !loading && (
              <div className="space-y-8 animate-in slide-in-from-bottom duration-700 ease-out">
                <div className="text-center animate-in fade-in duration-600 delay-200 ease-out">
                  <h2 className="text-2xl font-medium text-gray-900 mb-2">
                    Best products for "{results.query}"
                  </h2>
                  <p className="text-gray-600">
                    I analyzed {results.total_found} products and found these top recommendations
                  </p>
                </div>

                <div className="space-y-6">
                  {results.recommendations.map((product, index) => (
                    <Card 
                      key={index} 
                      className="border border-gray-200 hover:border-orange-200 transition-all duration-500 ease-out hover:shadow-xl hover:scale-[1.02] animate-in slide-in-from-bottom duration-700 transform hover:-translate-y-2 bg-white/80 backdrop-blur-sm"
                      style={{ animationDelay: `${400 + index * 200}ms` }}
                    >
                      <CardContent className="p-8">
                        <div className="flex gap-6">
                          <div className="flex-shrink-0">
                            {product.image_url && (
                              <img
                                src={product.image_url}
                                alt={product.name}
                                className="w-24 h-24 object-cover rounded-xl"
                              />
                            )}
                          </div>
                          
                          <div className="flex-1">
                            <div className="flex items-start justify-between mb-4">
                              <div>
                                <div className="flex items-center gap-3 mb-2">
                                  <Badge variant="secondary" className="text-sm px-2 py-1 font-medium">
                                    #{index + 1}
                                  </Badge>
                                  <h3 className="text-xl font-medium text-gray-900">
                                    {product.name}
                                  </h3>
                                </div>
                                <p className="text-gray-600 mb-3">{product.summary}</p>
                                <div className="flex items-center gap-6 text-sm text-gray-600">
                                  <div className="flex items-center gap-1">
                                    <DollarSign className="h-4 w-4" />
                                    <span className="font-medium">${product.price}</span>
                                  </div>
                                  <div className="flex items-center gap-1">
                                    <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                                    <span>{product.rating}/5</span>
                                  </div>
                                  <div className="flex items-center gap-1">
                                    <MessageSquare className="h-4 w-4" />
                                    <span>{product.review_count} reviews</span>
                                  </div>
                                </div>
                              </div>
                              <Badge 
                                variant="secondary" 
                                className={`text-base px-3 py-1 font-medium ${
                                  product.overall_score >= 8.5 ? 'bg-green-100 text-green-800' :
                                  product.overall_score >= 7.5 ? 'bg-yellow-100 text-yellow-800' :
                                  'bg-red-100 text-red-800'
                                }`}
                              >
                                {product.overall_score}/10
                              </Badge>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                              <div>
                                <h4 className="font-medium text-green-700 mb-3">
                                  ✓ What's great
                                </h4>
                                <ul className="space-y-2">
                                  {product.pros.map((pro, i) => (
                                    <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                                      <span className="text-green-600 mt-1 flex-shrink-0">•</span>
                                      <span>{pro}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                              
                              <div>
                                <h4 className="font-medium text-red-700 mb-3">
                                  ✗ Watch out for
                                </h4>
                                <ul className="space-y-2">
                                  {product.cons.map((con, i) => (
                                    <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                                      <span className="text-red-600 mt-1 flex-shrink-0">•</span>
                                      <span>{con}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            )}
            </div>

            {/* Input Area - Fixed at bottom */}
            <div className="border-t border-gray-100 py-6">
              <div className="relative">
                <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="What do you want to buy?"
                className="w-full resize-none border border-gray-300 rounded-2xl px-6 py-4 pr-14 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent text-gray-900 placeholder-gray-500 text-lg leading-relaxed transition-all duration-300 ease-out focus:shadow-xl focus:scale-[1.01] bg-white/90 backdrop-blur-sm"
                rows={1}
                style={{
                  minHeight: '60px',
                  maxHeight: '160px',
                  height: 'auto'
                }}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = 'auto';
                  target.style.height = Math.min(target.scrollHeight, 160) + 'px';
                }}
              />
              <Button
                onClick={handleSearch}
                disabled={loading || !query.trim()}
                className="absolute right-3 top-3 h-10 w-10 p-0 bg-orange-500 hover:bg-orange-600 disabled:bg-gray-300 rounded-xl transition-all duration-300 ease-out hover:scale-110 active:scale-95 hover:shadow-lg hover:rotate-12 disabled:hover:scale-100 disabled:hover:rotate-0"
              >
                <Send className={`h-5 w-5 transition-transform duration-300 ease-out ${loading ? 'animate-pulse scale-90' : 'group-hover:translate-x-0.5'}`} />
              </Button>
              </div>
              <p className="text-xs text-gray-500 mt-3 text-center">
                Press Enter to search • Shift + Enter for new line
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
