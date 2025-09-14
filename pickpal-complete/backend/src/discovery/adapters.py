import asyncio
import aiohttp
import json
import re
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from urllib.parse import quote_plus, urljoin
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

class BaseAdapter:
    """Base class for all discovery adapters."""
    
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    async def fetch(self, url: str, timeout: int = 10) -> Optional[str]:
        """Fetch content from URL with error handling."""
        try:
            async with self.session.get(url, headers=self.headers, timeout=timeout) as response:
                if response.status == 200:
                    return await response.text()
                return None
        except Exception:
            return None

class AmazonAdapter(BaseAdapter):
    """Adapter for Amazon Product Advertising API and web scraping."""
    
    def __init__(self, session: aiohttp.ClientSession, api_key: Optional[str] = None):
        super().__init__(session)
        self.api_key = api_key
        self.base_url = "https://webservices.amazon.com/paapi5"
        
    async def search_products(self, queries: List[str], category: str, max_results: int = 20) -> List[Dict]:
        """Search for products using Amazon API or web scraping fallback."""
        candidates = []
        
        if self.api_key:
            # Use official API if available
            candidates = await self._search_via_api(queries, category, max_results)
        else:
            # Fallback to web scraping (for demonstration - requires careful implementation)
            candidates = await self._search_via_scraping(queries, category, max_results)
        
        return candidates
    
    async def _search_via_api(self, queries: List[str], category: str, max_results: int) -> List[Dict]:
        """Search using official Amazon Product Advertising API."""
        # Note: This requires proper AWS credentials and PAAPI setup
        # For now, returning simulated API response structure
        
        candidates = []
        for query in queries[:3]:  # Limit API calls
            # Simulate API call structure
            search_payload = {
                "Keywords": query,
                "SearchIndex": self._map_category_to_search_index(category),
                "ItemCount": min(max_results // len(queries), 10),
                "Resources": [
                    "ItemInfo.Title",
                    "ItemInfo.Features",
                    "Offers.Listings.Price",
                    "CustomerReviews.StarRating",
                    "CustomerReviews.Count"
                ]
            }
            
            # In real implementation, make actual API call here
            # For demonstration, simulate response
            mock_response = await self._simulate_amazon_api_response(query, category)
            candidates.extend(mock_response)
        
        return candidates[:max_results]
    
    async def _search_via_scraping(self, queries: List[str], category: str, max_results: int) -> List[Dict]:
        """Fallback web scraping for Amazon search results."""
        candidates = []
        
        for query in queries[:2]:  # Limit scraping requests
            search_url = f"https://www.amazon.com/s?k={quote_plus(query)}"
            
            content = await self.fetch(search_url)
            if content:
                scraped_products = self._parse_amazon_search_results(content, query)
                candidates.extend(scraped_products)
                
                # Rate limiting
                await asyncio.sleep(1)
        
        return candidates[:max_results]
    
    def _parse_amazon_search_results(self, html_content: str, query: str) -> List[Dict]:
        """Parse Amazon search results HTML."""
        candidates = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find product containers (Amazon's structure changes frequently)
            products = soup.find_all('div', {'data-component-type': 's-search-result'})
            
            for product in products[:10]:  # Limit results per query
                try:
                    # Extract product name
                    title_elem = product.find('h2', class_='a-size-mini')
                    if not title_elem:
                        continue
                    
                    name = title_elem.get_text(strip=True)
                    
                    # Extract price
                    price_elem = product.find('span', class_='a-price-whole')
                    price = 0.0
                    if price_elem:
                        price_text = price_elem.get_text(strip=True).replace(',', '')
                        try:
                            price = float(price_text)
                        except:
                            pass
                    
                    # Extract rating
                    rating_elem = product.find('span', class_='a-icon-alt')
                    stars = 0.0
                    if rating_elem:
                        rating_text = rating_elem.get_text()
                        match = re.search(r'(\d+\.?\d*)', rating_text)
                        if match:
                            stars = float(match.group(1))
                    
                    # Extract product URL
                    link_elem = product.find('h2').find('a') if product.find('h2') else None
                    url = ""
                    if link_elem and link_elem.get('href'):
                        url = urljoin("https://www.amazon.com", link_elem['href'])
                    
                    # Extract review count
                    review_elem = product.find('a', class_='a-link-normal')
                    reviews_count = 0
                    if review_elem:
                        review_text = review_elem.get_text()
                        match = re.search(r'(\d+)', review_text.replace(',', ''))
                        if match:
                            reviews_count = int(match.group(1))
                    
                    candidate = {
                        "name": name,
                        "price": price,
                        "stars": stars,
                        "url": url,
                        "source": "amazon",
                        "reviews_count": reviews_count,
                        "category": self._infer_category_from_name(name),
                        "last_updated": datetime.now().isoformat(),
                        "reviews": []  # Would need separate API call to get actual reviews
                    }
                    
                    candidates.append(candidate)
                    
                except Exception:
                    continue
                    
        except Exception:
            pass
        
        return candidates
    
    def _map_category_to_search_index(self, category: str) -> str:
        """Map internal category to Amazon search index."""
        mapping = {
            "wireless_earbuds": "Electronics",
            "standing_desk": "OfficeProducts",
            "laptop": "Computers",
            "smartphone": "Electronics",
            "headphones": "Electronics"
        }
        return mapping.get(category, "All")
    
    def _infer_category_from_name(self, name: str) -> str:
        """Infer product category from name."""
        name_lower = name.lower()
        if any(term in name_lower for term in ["earbud", "airpod", "wireless"]):
            return "wireless_earbuds"
        elif any(term in name_lower for term in ["desk", "standing", "sit-stand"]):
            return "standing_desk"
        elif any(term in name_lower for term in ["laptop", "notebook"]):
            return "laptop"
        return "general"
    
    async def _simulate_amazon_api_response(self, query: str, category: str) -> List[Dict]:
        """Simulate Amazon API response for demonstration."""
        # This would be replaced with actual API calls
        mock_products = [
            {
                "name": f"Premium {query.title()} Pro",
                "price": 149.99,
                "stars": 4.3,
                "url": f"https://amazon.com/dp/MOCK123",
                "source": "amazon",
                "reviews_count": 1247,
                "category": category,
                "last_updated": datetime.now().isoformat(),
                "reviews": [
                    "Great product, highly recommended!",
                    "Good value for money",
                    "Works as expected"
                ]
            }
        ]
        return mock_products

class RedditAdapter(BaseAdapter):
    """Adapter for Reddit API to find product discussions."""
    
    def __init__(self, session: aiohttp.ClientSession, client_id: Optional[str] = None, 
                 client_secret: Optional[str] = None):
        super().__init__(session)
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.base_url = "https://oauth.reddit.com"
    
    async def search_products(self, queries: List[str], category: str, max_results: int = 15) -> List[Dict]:
        """Search Reddit for product discussions and recommendations."""
        candidates = []
        
        if self.client_id and self.client_secret:
            # Use official Reddit API
            await self._authenticate()
            candidates = await self._search_via_api(queries, category, max_results)
        else:
            # Fallback to web scraping Reddit
            candidates = await self._search_via_scraping(queries, category, max_results)
        
        return candidates
    
    async def _authenticate(self):
        """Authenticate with Reddit API."""
        auth_url = "https://www.reddit.com/api/v1/access_token"
        auth_data = {
            'grant_type': 'client_credentials'
        }
        
        auth = aiohttp.BasicAuth(self.client_id, self.client_secret)
        
        try:
            async with self.session.post(auth_url, data=auth_data, auth=auth) as response:
                if response.status == 200:
                    data = await response.json()
                    self.access_token = data.get('access_token')
        except Exception:
            pass
    
    async def _search_via_api(self, queries: List[str], category: str, max_results: int) -> List[Dict]:
        """Search using official Reddit API."""
        candidates = []
        
        if not self.access_token:
            return candidates
        
        # Search relevant subreddits
        subreddits = self._get_relevant_subreddits(category)
        
        headers = {**self.headers, 'Authorization': f'Bearer {self.access_token}'}
        
        for query in queries[:3]:
            for subreddit in subreddits[:2]:  # Limit subreddit searches
                search_url = f"{self.base_url}/r/{subreddit}/search"
                params = {
                    'q': query,
                    'sort': 'relevance',
                    'limit': 10,
                    'restrict_sr': 'true'
                }
                
                try:
                    async with self.session.get(search_url, headers=headers, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            posts = self._parse_reddit_api_response(data, query, subreddit)
                            candidates.extend(posts)
                            
                    await asyncio.sleep(0.5)  # Rate limiting
                    
                except Exception:
                    continue
        
        return candidates[:max_results]
    
    async def _search_via_scraping(self, queries: List[str], category: str, max_results: int) -> List[Dict]:
        """Fallback web scraping for Reddit."""
        candidates = []
        subreddits = self._get_relevant_subreddits(category)
        
        for query in queries[:2]:
            for subreddit in subreddits[:2]:
                search_url = f"https://www.reddit.com/r/{subreddit}/search/?q={quote_plus(query)}&restrict_sr=1"
                
                content = await self.fetch(search_url)
                if content:
                    scraped_posts = self._parse_reddit_search_results(content, query, subreddit)
                    candidates.extend(scraped_posts)
                    
                await asyncio.sleep(1)  # Rate limiting
        
        return candidates[:max_results]
    
    def _get_relevant_subreddits(self, category: str) -> List[str]:
        """Get relevant subreddits for product category."""
        subreddit_mapping = {
            "wireless_earbuds": ["headphones", "audiophile", "BuyItForLife"],
            "standing_desk": ["battlestations", "HomeOffice", "BuyItForLife"],
            "laptop": ["laptops", "SuggestALaptop", "BuyItForLife"],
            "smartphone": ["Android", "iphone", "PickAnAndroidForMe"]
        }
        
        general_subreddits = ["BuyItForLife", "ProductPorn", "reviews"]
        return subreddit_mapping.get(category, general_subreddits)
    
    def _parse_reddit_api_response(self, data: Dict, query: str, subreddit: str) -> List[Dict]:
        """Parse Reddit API response."""
        candidates = []
        
        try:
            posts = data.get('data', {}).get('children', [])
            
            for post in posts:
                post_data = post.get('data', {})
                
                # Extract product mentions from title and text
                title = post_data.get('title', '')
                selftext = post_data.get('selftext', '')
                
                # Simple product extraction (would need more sophisticated NLP)
                products = self._extract_products_from_text(f"{title} {selftext}", query)
                
                for product in products:
                    candidate = {
                        "name": product,
                        "price": 0.0,  # Reddit doesn't have price info
                        "stars": 0.0,   # No direct rating
                        "url": f"https://reddit.com{post_data.get('permalink', '')}",
                        "source": "reddit",
                        "upvotes": post_data.get('ups', 0),
                        "mentions": 1,
                        "subreddit": subreddit,
                        "category": self._infer_category_from_text(title),
                        "last_updated": datetime.fromtimestamp(post_data.get('created_utc', 0)).isoformat(),
                        "reviews": [title, selftext[:200]]  # Use post content as "review"
                    }
                    candidates.append(candidate)
                    
        except Exception:
            pass
        
        return candidates
    
    def _parse_reddit_search_results(self, html_content: str, query: str, subreddit: str) -> List[Dict]:
        """Parse Reddit search results HTML."""
        # Similar to API parsing but for scraped HTML
        # Implementation would parse Reddit's HTML structure
        return []  # Simplified for demonstration
    
    def _extract_products_from_text(self, text: str, query: str) -> List[str]:
        """Extract product names from Reddit text."""
        # Simple implementation - would need more sophisticated NLP
        products = []
        
        # Look for brand names and model numbers
        patterns = [
            r'([A-Z][a-z]+ [A-Z0-9-]+)',  # Brand ModelNumber
            r'([A-Z][a-z]+ [A-Z][a-z]+ [A-Z0-9-]+)',  # Brand Product ModelNumber
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            products.extend(matches)
        
        # Filter to relevant products
        query_words = query.lower().split()
        relevant_products = []
        
        for product in products:
            if any(word in product.lower() for word in query_words):
                relevant_products.append(product)
        
        return relevant_products[:3]  # Limit products per post
    
    def _infer_category_from_text(self, text: str) -> str:
        """Infer category from Reddit post text."""
        text_lower = text.lower()
        if any(term in text_lower for term in ["earbud", "headphone", "audio"]):
            return "wireless_earbuds"
        elif any(term in text_lower for term in ["desk", "standing", "office"]):
            return "standing_desk"
        return "general"

class ReviewBlogAdapter(BaseAdapter):
    """Adapter for scraping review blogs and tech sites."""
    
    def __init__(self, session: aiohttp.ClientSession):
        super().__init__(session)
        self.review_sites = [
            "wirecutter.nytimes.com",
            "rtings.com",
            "techradar.com",
            "pcmag.com",
            "consumerreports.org"
        ]
    
    async def search_products(self, queries: List[str], category: str, max_results: int = 10) -> List[Dict]:
        """Search review blogs for product recommendations."""
        candidates = []
        
        for query in queries[:2]:  # Limit queries
            for site in self.review_sites[:3]:  # Limit sites
                try:
                    site_candidates = await self._search_site(site, query, category)
                    candidates.extend(site_candidates)
                    
                    await asyncio.sleep(1)  # Rate limiting
                    
                except Exception:
                    continue
        
        return candidates[:max_results]
    
    async def _search_site(self, site: str, query: str, category: str) -> List[Dict]:
        """Search a specific review site."""
        # Use Google site search
        search_url = f"https://www.google.com/search?q=site:{site} {quote_plus(query)}"
        
        content = await self.fetch(search_url)
        if not content:
            return []
        
        # Parse Google search results for the site
        return self._parse_google_results(content, site, query, category)
    
    def _parse_google_results(self, html_content: str, site: str, query: str, category: str) -> List[Dict]:
        """Parse Google search results for review site links."""
        candidates = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find search result links
            result_links = soup.find_all('a', href=True)
            
            for link in result_links[:5]:  # Limit results per site
                href = link.get('href', '')
                
                # Extract actual URL from Google result
                if '/url?q=' in href:
                    actual_url = href.split('/url?q=')[1].split('&')[0]
                    
                    if site in actual_url:
                        # Extract title from link text
                        title = link.get_text(strip=True)
                        
                        if title and len(title) > 10:  # Filter out short/empty titles
                            candidate = {
                                "name": self._extract_product_name_from_title(title, query),
                                "price": 0.0,  # Review sites don't always have prices
                                "stars": 0.0,   # Would need to scrape individual pages
                                "url": actual_url,
                                "source": f"review_blog_{site.split('.')[0]}",
                                "category": category,
                                "last_updated": datetime.now().isoformat(),
                                "reviews": [title]  # Use title as review snippet
                            }
                            candidates.append(candidate)
                            
        except Exception:
            pass
        
        return candidates
    
    def _extract_product_name_from_title(self, title: str, query: str) -> str:
        """Extract product name from review article title."""
        # Remove common review site phrases
        clean_title = title
        
        remove_phrases = [
            "Review:", "Best", "Top", "Our pick:", "The", "- PCMag",
            "- TechRadar", "- Wirecutter", "| RTINGS.com"
        ]
        
        for phrase in remove_phrases:
            clean_title = clean_title.replace(phrase, "")
        
        # Extract the most relevant part
        clean_title = clean_title.strip()
        
        # If title is too long, try to extract the product name
        if len(clean_title) > 50:
            words = clean_title.split()
            # Look for capitalized words that might be product names
            product_words = [word for word in words if word[0].isupper() and len(word) > 2]
            if product_words:
                clean_title = " ".join(product_words[:4])  # Take first 4 capitalized words
        
        return clean_title or query
