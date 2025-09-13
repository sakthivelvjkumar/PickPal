# MyPickPal

🛍️ AI Shopping – Your Unbiased Product Research Assistant

🚀 Overview

Tired of opening 20 browser tabs just to buy one pair of earbuds? AI Shopping helps you find the best products in seconds, not hours.

Our tool scrapes reviews and discussions (Amazon, Reddit, blogs) and applies AI sentiment analysis + summarization to generate:
	•	✅ The top 3 products for your query
	•	⭐ A trustable overall score
	•	➕ 2–3 pros and cons per product, written in plain language

No affiliate links, no marketing fluff—just insights distilled from real user experiences.

⸻

💡 Problem Definition
	•	Pain Point: Shoppers waste hours reading reviews, blog posts, and forum threads.
	•	Target Users: Anyone buying tech gadgets, skincare, kitchen appliances, or more.
	•	Gap: Comparison sites push affiliate links, lack transparency, or overwhelm users with too many options.

⸻

🧠 Solution Concept

“An AI tool that scrapes reviews & discussions to recommend the top 3 products with pros/cons and a trustable overall score.”

Our AI-native edge: Instead of lists of raw reviews, we synthesize thousands of opinions into concise recommendations that actually save time.

⸻

✨ Core Features (MVP)
	•	🔎 Search input – e.g. “Best wireless earbuds under $150”
	•	📡 Scraper / Data fetcher – Amazon APIs, Reddit threads, or mock data for demo
	•	🤖 AI sentiment analysis + scoring – aggregate star ratings + opinion polarity
	•	🏆 Top 3 ranked recommendations – each with:
	•	Overall score
	•	Pros & cons (summarized from reviews)
	•	💻 Simple UI – input box + results cards

(Stretch goals: price filters, brand preferences, feature weighting.)

⸻

🛠️ Tech Stack
	•	Frontend: React (clean search & results UI)
	•	Backend: Flask / FastAPI (query handling, scraping, AI inference)
	•	AI/NLP:
	•	Sentiment analysis → HuggingFace (DistilBERT/BERT) or OpenAI API
	•	Summarization → GPT-4/5 or extractive summarizer
	•	Data:
	•	Live scraping (if stable)
	•	Pre-saved JSON reviews for hackathon demo reliability

⸻

🔄 User Journey (Demo Flow)
	1.	User enters query: “Best standing desk for small spaces.”
	2.	Backend fetches product reviews (real or mock).
	3.	AI runs sentiment + scoring model.
	4.	UI displays 3 product cards with:
	•	Score
	•	Pros & cons
	•	Short summary

⸻

🌟 Differentiation
	•	⏱ Cuts research time from hours → minutes
	•	🧑‍🤝‍🧑 Unlike affiliate blogs, results feel unbiased (based on real aggregated reviews)
	•	🗣 Pros & cons written in clear, human-like summaries
