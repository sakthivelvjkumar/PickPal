import asyncio
import random
from typing import Dict, Any, List
from datetime import datetime, timedelta
from .base_agent import BaseAgent, EventType
from models.schemas import Product, Review
from pydantic_settings import BaseSettings

class DiscoveryAgent(BaseAgent):
    def __init__(self, event_bus):
        super().__init__("discovery_agent", event_bus)
        self.discovered_urls = set()  # URL deduplication
        
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        await self.emit_event(EventType.TASK_STARTED, {
            'task': 'product_discovery',
            'category': task.get('inputs', {}).get('category', 'general')
        })
        
        try:
            # For demo, use comprehensive mock data
            products, reviews = await self._discover_mock_data(task.get('inputs', {}))
            
            result = {
                'products': products,
                'reviews': reviews,
                'total_products': len(products),
                'total_reviews': len(reviews),
                'status': 'success'
            }
            
            await self.emit_event(EventType.DATA_DISCOVERED, {
                'products_found': len(products),
                'reviews_found': len(reviews)
            })
            
            return result
            
        except Exception as e:
            await self.emit_event(EventType.TASK_FAILED, {
                'task': 'product_discovery',
                'error': str(e)
            })
            raise

    async def _discover_mock_data(self, inputs: Dict[str, Any]) -> tuple[List[Product], List[Review]]:
        """Generate comprehensive mock product and review data"""
        
        category = inputs.get('category', 'general')
        budget_max = inputs.get('budget_max', 1000)
        
        # Mock product data with realistic variety
        mock_products_data = {
            'earbuds': [
                {'name': 'AirPods Pro (2nd Gen)', 'brand': 'Apple', 'price': 249, 'rating': 4.4},
                {'name': 'WF-1000XM4', 'brand': 'Sony', 'price': 199, 'rating': 4.2},
                {'name': 'QuietComfort Earbuds', 'brand': 'Bose', 'price': 279, 'rating': 4.1},
                {'name': 'Soundcore Life P3', 'brand': 'Anker', 'price': 79, 'rating': 4.3},
                {'name': 'Galaxy Buds2 Pro', 'brand': 'Samsung', 'price': 229, 'rating': 4.0},
            ],
            'headphones': [
                {'name': 'WH-1000XM5', 'brand': 'Sony', 'price': 399, 'rating': 4.5},
                {'name': 'QuietComfort 45', 'brand': 'Bose', 'price': 329, 'rating': 4.3},
                {'name': 'AirPods Max', 'brand': 'Apple', 'price': 549, 'rating': 4.2},
                {'name': 'HD 450BT', 'brand': 'Sennheiser', 'price': 149, 'rating': 4.1},
                {'name': 'Space Q45', 'brand': 'Anker', 'price': 149, 'rating': 4.4},
            ],
            'gaming': [
                {'name': 'HyperX Cloud II', 'brand': 'HyperX', 'price': 99, 'rating': 4.5},
                {'name': 'Arctis 7P', 'brand': 'SteelSeries', 'price': 179, 'rating': 4.3},
                {'name': 'G PRO X', 'brand': 'Logitech', 'price': 129, 'rating': 4.2},
                {'name': 'Barracuda X', 'brand': 'Razer', 'price': 99, 'rating': 4.0},
            ]
        }
        
        # Get products for category
        products_data = mock_products_data.get(category, mock_products_data['earbuds'])
        
        # Filter by budget
        if budget_max:
            products_data = [p for p in products_data if p['price'] <= budget_max]
        
        products = []
        reviews = []
        
        for i, prod_data in enumerate(products_data[:10]):  # Limit to 10 products
            product = Product(
                product_id=f"prod_{i+1}",
                name=prod_data['name'],
                brand=prod_data['brand'],
                price=prod_data['price'],
                rating=prod_data['rating'],
                review_count=random.randint(50, 500),
                url=f"https://example.com/product/{i+1}",
                image_url=f"https://example.com/images/product_{i+1}.jpg",
                sku=f"SKU{i+1:03d}",
                in_stock=random.choice([True, True, True, False])  # 75% in stock
            )
            products.append(product)
            
            # Generate reviews for each product
            product_reviews = await self._generate_reviews(product.product_id, category)
            reviews.extend(product_reviews)
        
        return products, reviews

    async def _generate_reviews(self, product_id: str, category: str) -> List[Review]:
        """Generate realistic review data with sentiment variation"""
        
        review_templates = {
            'earbuds': [
                {'text': 'Great battery life, lasts all day. Sound quality is excellent for the price.', 'rating': 5, 'aspects': ['battery', 'sound_quality']},
                {'text': 'Comfortable fit but the case is a bit bulky. Good for workouts.', 'rating': 4, 'aspects': ['comfort', 'build']},
                {'text': 'Amazing noise cancellation! Perfect for commuting and travel.', 'rating': 5, 'aspects': ['noise_cancellation']},
                {'text': 'Decent sound but they fall out during running. Not ideal for sports.', 'rating': 3, 'aspects': ['fit', 'sports']},
                {'text': 'Good value for money. Build quality could be better but works well.', 'rating': 4, 'aspects': ['price', 'build']},
            ],
            'headphones': [
                {'text': 'Exceptional comfort for long listening sessions. Premium build quality.', 'rating': 5, 'aspects': ['comfort', 'build']},
                {'text': 'Outstanding noise cancellation and sound quality. Worth the price.', 'rating': 5, 'aspects': ['noise_cancellation', 'sound_quality']},
                {'text': 'Good headphones but heavy for extended wear. Great for home use.', 'rating': 4, 'aspects': ['comfort', 'sound_quality']},
                {'text': 'Battery life is impressive. Charges quickly and lasts forever.', 'rating': 5, 'aspects': ['battery']},
                {'text': 'Too expensive for what you get. Sound is good but not amazing.', 'rating': 3, 'aspects': ['price', 'sound_quality']},
            ]
        }
        
        templates = review_templates.get(category, review_templates['earbuds'])
        reviews = []
        
        for i in range(random.randint(5, 10)):  # 5-10 reviews per product
            template = random.choice(templates)
            review = Review(
                review_id=f"rev_{product_id}_{i+1}",
                product_id=product_id,
                rating=template['rating'] + random.randint(-1, 1),  # Add some variation
                text=template['text'],
                title=f"Review {i+1}",
                author=f"User_{random.randint(1000, 9999)}",
                date=datetime.now() - timedelta(days=random.randint(1, 365)),
                helpful_votes=random.randint(0, 50),
                verified_purchase=random.choice([True, False]),
                source=random.choice(["amazon", "reddit", "blog"])
            )
            # Clamp rating to 1-5
            review.rating = max(1, min(5, review.rating))
            reviews.append(review)
        
        return reviews
