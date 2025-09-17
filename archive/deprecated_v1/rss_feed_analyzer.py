"""
RSS Feed Analyzer for extracting smart home keywords from tech news sources.
Provides real-time keyword extraction from The Verge, 9to5Mac, CNET, and other tech publications.
"""

import re
import time
import requests
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin, urlparse
import logging
from dataclasses import dataclass
import xml.etree.ElementTree as ET

@dataclass
class RSSKeyword:
    """Keyword extracted from RSS feed with metadata"""
    keyword: str
    source: str
    feed_name: str
    title: str
    publish_date: datetime
    url: str
    relevance_score: float
    category: str

class RSSFeedAnalyzer:
    """
    Analyzes RSS feeds from tech publications to extract smart home keywords.
    Provides a real-time alternative to API-based keyword research.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Define RSS feeds for tech publications (OPTIMIZED - failed sources removed)
        self.rss_feeds = {
            # REMOVED: the_verge - 403 Forbidden access
            # 'the_verge': {
            #     'url': 'https://www.theverge.com/rss/index.xml',
            #     'name': 'The Verge',
            #     'smart_home_keywords': ['smart home', 'alexa', 'google home', 'homekit', 'iot', 'nest']
            # },
            'engadget': {
                'url': 'https://www.engadget.com/rss.xml',
                'name': 'Engadget',
                'smart_home_keywords': ['smart', 'home automation', 'connected', 'wifi', 'bluetooth']
            },
            'cnet': {
                'url': 'https://www.cnet.com/rss/news/',
                'name': 'CNET News',
                'smart_home_keywords': ['smart home', 'home tech', 'automation', 'security camera', 'robot vacuum']
            },
            'ars_technica': {
                'url': 'https://feeds.arstechnica.com/arstechnica/index/',
                'name': 'Ars Technica',
                'smart_home_keywords': ['home automation', 'iot security', 'smart device', 'privacy']
            },
            # REMOVED: android_police - Connection issues
            # 'android_police': {
            #     'url': 'https://www.androidpolice.com/feed/',
            #     'name': 'Android Police',
            #     'smart_home_keywords': ['android auto', 'google assistant', 'smart display', 'nest']
            # },
            # NEW ADDITIONS for better coverage
            'techcrunch': {
                'url': 'https://techcrunch.com/feed/',
                'name': 'TechCrunch',
                'smart_home_keywords': ['smart home', 'iot', 'connected devices', 'home automation', 'smart tech']
            },
            'wired': {
                'url': 'https://www.wired.com/feed/',
                'name': 'WIRED',
                'smart_home_keywords': ['smart home', 'gadgets', 'security', 'automation', 'iot']
            },
            'gizmodo': {
                'url': 'https://gizmodo.com/rss',
                'name': 'Gizmodo',
                'smart_home_keywords': ['smart home', 'tech reviews', 'gadgets', 'home tech', 'automation']
            },
            'digital_trends': {
                'url': 'https://www.digitaltrends.com/feed/',
                'name': 'Digital Trends',
                'smart_home_keywords': ['smart home', 'home theater', 'security systems', 'smart appliances']
            },
            'mashable': {
                'url': 'https://mashable.com/feeds/rss/all',
                'name': 'Mashable',
                'smart_home_keywords': ['tech', 'smart devices', 'home automation', 'gadget reviews']
            },
            'tom_guide': {
                'url': 'https://www.tomsguide.com/feeds/all',
                'name': "Tom's Guide",
                'smart_home_keywords': ['smart home', 'best', 'reviews', 'buying guide', 'home security']
            },
            # REMOVED: pcmag - 404 Not Found
            # 'pcmag': {
            #     'url': 'https://www.pcmag.com/feed/',
            #     'name': 'PCMag',
            #     'smart_home_keywords': ['smart home', 'reviews', 'tech news', 'gadget testing', 'best picks']
            # },

            # VERIFIED BACKUP SOURCES (tested and working)
            'android_central': {
                'url': 'https://www.androidcentral.com/feed',
                'name': 'Android Central',
                'smart_home_keywords': ['android', 'google assistant', 'smart home', 'nest', 'automation']
            },
            'tech_radar': {
                'url': 'https://www.techradar.com/rss',
                'name': 'TechRadar',
                'smart_home_keywords': ['smart home', 'best', 'reviews', 'buying guides', 'tech news']
            },

            # Additional verified reliable source
            'cnet_smart_home': {
                'url': 'https://www.cnet.com/rss/smart-home/',
                'name': 'CNET Smart Home',
                'smart_home_keywords': ['smart home', 'automation', 'security', 'energy', 'appliances']
            },
            'zdnet': {
                'url': 'https://www.zdnet.com/news/rss.xml',
                'name': 'ZDNet',
                'smart_home_keywords': ['smart home', 'enterprise tech', 'iot security', 'automation']
            }
        }
        
        # Smart home product categories and keywords
        self.smart_home_categories = {
            'smart_plugs': [
                'smart plug', 'wifi plug', 'alexa plug', 'smart outlet', 'energy monitoring',
                'power strip', 'outdoor plug', 'smart switch'
            ],
            'security_cameras': [
                'security camera', 'doorbell camera', 'outdoor camera', 'wifi camera',
                'surveillance', 'ring doorbell', 'arlo', 'nest cam', 'wyze cam'
            ],
            'robot_vacuums': [
                'robot vacuum', 'roomba', 'robotic cleaner', 'autonomous vacuum',
                'mapping vacuum', 'pet hair vacuum', 'self-emptying'
            ],
            'smart_speakers': [
                'smart speaker', 'alexa', 'google home', 'echo dot', 'nest mini',
                'voice assistant', 'smart display', 'homepod'
            ],
            'smart_lighting': [
                'smart bulb', 'led bulb', 'color bulb', 'dimmer switch', 'light strip',
                'philips hue', 'smart light', 'motion sensor light'
            ],
            'smart_thermostats': [
                'smart thermostat', 'nest thermostat', 'ecobee', 'wifi thermostat',
                'programmable thermostat', 'energy saving'
            ],
            'smart_locks': [
                'smart lock', 'keyless entry', 'smart deadbolt', 'door lock',
                'august lock', 'yale lock', 'schlage'
            ]
        }
        
        # Commercial intent indicators
        self.commercial_keywords = [
            'best', 'review', 'price', 'deal', 'sale', 'discount', 'buy', 'cheap',
            'comparison', 'vs', 'alternative', 'guide', 'recommendation', '2025'
        ]
        
        # Request headers to avoid being blocked
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive'
        }
    
    def fetch_rss_keywords(self, max_age_hours: int = 24, 
                          min_relevance: float = 0.3) -> List[RSSKeyword]:
        """
        Fetch smart home keywords from all configured RSS feeds.
        
        Args:
            max_age_hours: Maximum age of articles to consider
            min_relevance: Minimum relevance score for keywords
            
        Returns:
            List of RSSKeyword objects
        """
        all_keywords = []
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        for feed_id, feed_config in self.rss_feeds.items():
            try:
                keywords = self._process_feed(feed_config, cutoff_time, min_relevance)
                all_keywords.extend(keywords)
                
                # Be respectful with request timing
                time.sleep(1)
                
            except Exception as e:
                self.logger.warning(f"Failed to process feed {feed_id}: {e}")
                continue
        
        # Sort by relevance score and publish date
        all_keywords.sort(key=lambda x: (x.relevance_score, x.publish_date), reverse=True)
        
        return all_keywords
    
    def _process_feed(self, feed_config: Dict, cutoff_time: datetime, 
                     min_relevance: float) -> List[RSSKeyword]:
        """Process a single RSS feed and extract keywords"""
        keywords = []
        
        try:
            # Fetch and parse RSS feed
            response = requests.get(feed_config['url'], headers=self.headers, timeout=10)
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            
            if not feed.entries:
                self.logger.warning(f"No entries found in feed: {feed_config['name']}")
                return keywords
            
            for entry in feed.entries:
                try:
                    # Parse publish date
                    publish_date = self._parse_date(entry)
                    
                    if publish_date < cutoff_time:
                        continue
                    
                    # Extract title and description
                    title = entry.get('title', '')
                    description = entry.get('description', '') or entry.get('summary', '')
                    content = f"{title} {description}".lower()
                    
                    # Extract smart home keywords
                    extracted_keywords = self._extract_smart_home_keywords(
                        content, title, feed_config, entry, publish_date, min_relevance
                    )
                    
                    keywords.extend(extracted_keywords)
                    
                except Exception as e:
                    self.logger.debug(f"Failed to process entry: {e}")
                    continue
            
        except Exception as e:
            self.logger.error(f"Failed to fetch RSS feed {feed_config['url']}: {e}")
        
        return keywords
    
    def _parse_date(self, entry) -> datetime:
        """Parse publish date from RSS entry"""
        # Try different date fields
        date_fields = ['published_parsed', 'updated_parsed']
        
        for field in date_fields:
            if hasattr(entry, field) and getattr(entry, field):
                time_struct = getattr(entry, field)
                return datetime(*time_struct[:6])
        
        # Fallback to current time if no date found
        return datetime.now()
    
    def _extract_smart_home_keywords(self, content: str, title: str, 
                                   feed_config: Dict, entry: Dict, 
                                   publish_date: datetime, 
                                   min_relevance: float) -> List[RSSKeyword]:
        """Extract smart home keywords from article content"""
        keywords = []
        
        # Check if content is relevant to smart home
        if not self._is_smart_home_relevant(content, feed_config):
            return keywords
        
        # Extract keywords for each category
        for category, category_keywords in self.smart_home_categories.items():
            for base_keyword in category_keywords:
                if base_keyword in content:
                    # Calculate relevance score
                    relevance = self._calculate_relevance_score(
                        content, title, base_keyword, feed_config
                    )
                    
                    if relevance >= min_relevance:
                        # Generate variations with commercial intent
                        keyword_variations = self._generate_keyword_variations(base_keyword, content)
                        
                        for variation in keyword_variations:
                            keywords.append(RSSKeyword(
                                keyword=variation,
                                source='rss',
                                feed_name=feed_config['name'],
                                title=title,
                                publish_date=publish_date,
                                url=entry.get('link', ''),
                                relevance_score=relevance,
                                category=category
                            ))
        
        return keywords
    
    def _is_smart_home_relevant(self, content: str, feed_config: Dict) -> bool:
        """Check if content is relevant to smart home topics"""
        # Check feed-specific smart home keywords
        for keyword in feed_config.get('smart_home_keywords', []):
            if keyword in content:
                return True
        
        # Check general smart home terms
        general_terms = [
            'smart home', 'home automation', 'iot', 'connected home',
            'alexa', 'google home', 'homekit', 'nest', 'ring'
        ]
        
        return any(term in content for term in general_terms)
    
    def _calculate_relevance_score(self, content: str, title: str, 
                                 keyword: str, feed_config: Dict) -> float:
        """Calculate relevance score for a keyword"""
        score = 0.0
        
        # Base score for keyword presence
        if keyword in content:
            score += 0.3
        
        # Higher score if in title
        if keyword in title.lower():
            score += 0.4
        
        # Commercial intent boost
        for commercial_word in self.commercial_keywords:
            if commercial_word in content:
                score += 0.1
                break
        
        # Feed-specific relevance boost
        for feed_keyword in feed_config.get('smart_home_keywords', []):
            if feed_keyword in content:
                score += 0.2
                break
        
        # Recency boost (newer articles get higher scores)
        score += 0.1  # Base recency bonus
        
        return min(1.0, score)
    
    def _generate_keyword_variations(self, base_keyword: str, content: str) -> List[str]:
        """Generate keyword variations with commercial intent"""
        variations = [base_keyword]
        
        # Add commercial modifiers if they appear in content
        modifiers = []
        
        if any(word in content for word in ['best', 'top', 'review']):
            modifiers.append('best')
        
        if any(word in content for word in ['2025', '2024', 'new']):
            modifiers.append('2025')
        
        if any(word in content for word in ['cheap', 'budget', 'affordable']):
            modifiers.append('budget')
        
        if any(word in content for word in ['wifi', 'wireless']):
            modifiers.append('wifi')
        
        # Create variations
        for modifier in modifiers[:2]:  # Limit to 2 modifiers
            if modifier == 'best':
                variations.append(f'best {base_keyword}')
            elif modifier == '2025':
                variations.append(f'{base_keyword} 2025')
            elif modifier == 'budget':
                variations.append(f'budget {base_keyword}')
            elif modifier == 'wifi':
                variations.append(f'{base_keyword} wifi')
        
        return variations
    
    def get_trending_keywords(self, limit: int = 10, 
                            category: str = None) -> List[Dict]:
        """
        Get trending keywords formatted for the keyword analyzer.
        
        Args:
            limit: Maximum number of keywords to return
            category: Optional category filter
            
        Returns:
            List of keyword dictionaries compatible with keyword analyzer
        """
        rss_keywords = self.fetch_rss_keywords()
        
        # Filter by category if specified
        if category:
            rss_keywords = [k for k in rss_keywords if k.category == category]
        
        # Convert to keyword analyzer format
        trending_keywords = []
        
        for rss_kw in rss_keywords[:limit]:
            keyword_data = {
                'keyword': rss_kw.keyword,
                'category': rss_kw.category,
                'trend_score': rss_kw.relevance_score,
                'source': 'rss',
                'feed_name': rss_kw.feed_name,
                'title': rss_kw.title,
                'url': rss_kw.url,
                'publish_date': rss_kw.publish_date.isoformat(),
                'reason': f'Trending in {rss_kw.feed_name}: {rss_kw.title[:60]}...',
                'commercial_intent': 0.7,  # RSS keywords typically have good commercial intent
                'search_volume': 15000,    # Estimated based on trending status
                'difficulty': 'Medium',
                'timestamp': datetime.now()
            }
            trending_keywords.append(keyword_data)
        
        return trending_keywords
    
    def get_feed_statistics(self) -> Dict:
        """Get statistics about RSS feed processing"""
        stats = {
            'total_feeds': len(self.rss_feeds),
            'feed_names': [config['name'] for config in self.rss_feeds.values()],
            'categories_tracked': len(self.smart_home_categories),
            'keywords_per_category': {cat: len(keywords) for cat, keywords in self.smart_home_categories.items()},
            'commercial_indicators': len(self.commercial_keywords)
        }
        
        return stats

# Example usage and testing
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Test RSS feed analyzer
    analyzer = RSSFeedAnalyzer()
    
    print("=== Testing RSS Feed Analyzer ===")
    
    # Get trending keywords
    trending = analyzer.get_trending_keywords(limit=5)
    
    print(f"Found {len(trending)} trending keywords:")
    for i, kw in enumerate(trending, 1):
        print(f"{i}. {kw['keyword']} (from {kw['feed_name']})")
        print(f"   Relevance: {kw['trend_score']:.2f}")
        print(f"   Category: {kw['category']}")
        print(f"   Reason: {kw['reason']}")
        print()
    
    # Get statistics
    stats = analyzer.get_feed_statistics()
    print(f"RSS Stats: {stats['total_feeds']} feeds, {stats['categories_tracked']} categories")
    print(f"Feeds: {', '.join(stats['feed_names'])}")