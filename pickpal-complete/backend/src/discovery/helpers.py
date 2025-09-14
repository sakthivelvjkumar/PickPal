from typing import List, Dict, Set
import re
from urllib.parse import urlparse
from difflib import SequenceMatcher

def deduplicate_candidates(candidates: List[Dict], request_id: str) -> List[Dict]:
    """Remove duplicate candidates based on URL and name similarity."""
    from ..common.utils import logger, log_context
    
    if not candidates:
        return []
    
    unique_candidates = []
    seen_urls = set()
    seen_names = []
    
    with log_context(request_id):
        logger.info(f"Deduplicating {len(candidates)} candidates")
    
    for candidate in candidates:
        is_duplicate = False
        
        # Check URL duplicates
        url = candidate.get("url", "")
        if url:
            parsed_url = urlparse(url)
            # Normalize URL (remove query params, fragments)
            normalized_url = f"{parsed_url.netloc}{parsed_url.path}"
            
            if normalized_url in seen_urls:
                is_duplicate = True
                with log_context(request_id):
                    logger.info(f"Duplicate URL found: {candidate.get('name')} - {url}")
            else:
                seen_urls.add(normalized_url)
        
        # Check name similarity (fuzzy matching)
        if not is_duplicate:
            name = candidate.get("name", "").lower().strip()
            for seen_name in seen_names:
                similarity = SequenceMatcher(None, name, seen_name).ratio()
                if similarity > 0.85:  # 85% similarity threshold
                    is_duplicate = True
                    with log_context(request_id):
                        logger.info(f"Duplicate name found: {candidate.get('name')} similar to existing product")
                    break
        
        if not is_duplicate:
            unique_candidates.append(candidate)
            seen_names.append(name)
    
    with log_context(request_id):
        logger.info(f"After deduplication: {len(unique_candidates)} unique candidates")
    
    return unique_candidates

def gather_evidence_and_filter(candidates: List[Dict], brief, request_id: str) -> List[Dict]:
    """Filter candidates based on evidence quality and freshness."""
    from ..common.utils import logger, log_context
    from datetime import datetime, timedelta
    
    filtered_candidates = []
    min_reviews = brief.success.get("min_reviews", 10)
    
    with log_context(request_id):
        logger.info(f"Gathering evidence for {len(candidates)} candidates (min_reviews: {min_reviews})")
    
    for candidate in candidates:
        evidence_score = 0
        evidence_notes = []
        
        # Review count evidence
        reviews_count = candidate.get("reviews_count", len(candidate.get("reviews", [])))
        if reviews_count >= min_reviews:
            evidence_score += 2
            evidence_notes.append(f"{reviews_count} reviews")
        elif reviews_count > 0:
            evidence_score += 1
            evidence_notes.append(f"only {reviews_count} reviews")
        
        # Source credibility
        source = candidate.get("source", "")
        if source == "amazon":
            evidence_score += 2
            evidence_notes.append("Amazon verified")
        elif source == "reddit":
            upvotes = candidate.get("upvotes", 0)
            mentions = candidate.get("mentions", 0)
            if upvotes > 50 or mentions > 20:
                evidence_score += 2
                evidence_notes.append(f"Reddit: {upvotes} upvotes, {mentions} mentions")
            else:
                evidence_score += 1
        elif "review_blog" in source:
            evidence_score += 2
            evidence_notes.append("Professional review")
        
        # Freshness (prefer recent content)
        last_updated = candidate.get("last_updated", "")
        if last_updated:
            try:
                update_date = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                days_old = (datetime.now() - update_date.replace(tzinfo=None)).days
                if days_old < 30:
                    evidence_score += 1
                    evidence_notes.append("recent")
                elif days_old > 365:
                    evidence_score -= 1
                    evidence_notes.append("outdated")
            except:
                pass
        
        # Accept candidates with sufficient evidence
        if evidence_score >= 2:
            candidate["evidence_score"] = evidence_score
            candidate["evidence_notes"] = evidence_notes
            filtered_candidates.append(candidate)
            
            with log_context(request_id):
                logger.info(f"✓ {candidate.get('name')}: evidence score {evidence_score} ({', '.join(evidence_notes)})")
        else:
            with log_context(request_id):
                logger.info(f"✗ {candidate.get('name')}: insufficient evidence (score {evidence_score})")
    
    with log_context(request_id):
        logger.info(f"Evidence filtering: {len(filtered_candidates)} candidates have sufficient evidence")
    
    return filtered_candidates

def expand_search_queries(original_queries: List[str], category: str) -> List[str]:
    """Expand search queries by removing constraints and adding synonyms."""
    expanded = []
    
    # Remove price constraints for broader search
    for query in original_queries:
        # Remove price terms
        expanded_query = re.sub(r'\s*under\s*\$\d+', '', query, flags=re.IGNORECASE)
        expanded_query = re.sub(r'\s*below\s*\$\d+', '', expanded_query, flags=re.IGNORECASE)
        expanded_query = re.sub(r'\s*less\s*than\s*\$\d+', '', expanded_query, flags=re.IGNORECASE)
        
        if expanded_query.strip() != query.strip():
            expanded.append(expanded_query.strip())
    
    # Add category-specific broader terms
    if category == "wireless_earbuds":
        expanded.extend([
            "best wireless earbuds 2024",
            "top bluetooth earbuds",
            "wireless earbuds review"
        ])
    elif category == "standing_desk":
        expanded.extend([
            "best standing desk 2024",
            "adjustable height desk",
            "sit stand desk review"
        ])
    
    return list(set(expanded))  # Remove duplicates
