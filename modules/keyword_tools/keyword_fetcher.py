"""
Keyword Fetcher - 专门负责从多数据源获取关键词
从原 keyword_analyzer.py 中提取的关键词获取功能
"""

import os
import sys
import time
import random
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import json
import asyncio
import aiohttp
from urllib.parse import quote
import logging

# 导入配置管理器和工具模块
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from modules.config import ConfigManager
try:
    from modules.utils import (
        safe_print, NetworkClient, retry_with_backoff,
        safe_request, check_internet_connection
    )
except ImportError:
    def safe_print(text, **kwargs):
        print(text, **kwargs)

    # 简单的fallback实现
    def safe_request(url, **kwargs):
        return requests.get(url, **kwargs)

    def check_internet_connection():
        return True

    def retry_with_backoff(func):
        return func

# Import data sources
try:
    from ..data_sources.rss_feed_analyzer import RSSFeedAnalyzer
    RSS_AVAILABLE = True
except ImportError:
    RSS_AVAILABLE = False

try:
    from ..data_sources.amazon_scraper import AmazonBestSellersScraper
    AMAZON_AVAILABLE = True
except ImportError:
    AMAZON_AVAILABLE = False

# Optional dependencies
try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False

try:
    import praw
    REDDIT_AVAILABLE = True
except ImportError:
    REDDIT_AVAILABLE = False

try:
    from googleapiclient.discovery import build
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False


class KeywordFetcher:
    """
    关键词获取器 - 专门负责从多个数据源获取关键词数据
    不包含分析逻辑，只负责数据获取和格式化
    """

    def __init__(self, config: Optional[Dict] = None):
        self.logger = logging.getLogger(__name__)

        # 加载配置管理器
        self.config_manager = ConfigManager()

        # 使用传入配置或默认配置
        self.config = config or self._get_default_config()

        # 初始化各种数据源
        self.pytrends = None
        self.reddit = None
        self.youtube = None
        self.rss_analyzer = None
        self.amazon_scraper = None

        # 智能家居关键词分类
        self.smart_home_categories = {
            'smart_plugs': [
                'smart plug', 'wifi outlet', 'alexa plug', 'google home plug',
                'smart outlet', 'energy monitoring plug', 'outdoor smart plug'
            ],
            'smart_speakers': [
                'alexa echo', 'google home', 'smart speaker', 'voice assistant',
                'echo dot', 'google nest', 'homepod', 'smart display'
            ],
            'security_cameras': [
                'security camera', 'wifi camera', 'outdoor camera', 'doorbell camera',
                'surveillance camera', 'ip camera', 'wireless camera', 'night vision camera'
            ],
            'robot_vacuums': [
                'robot vacuum', 'robotic cleaner', 'automatic vacuum', 'smart vacuum',
                'roomba', 'mapping vacuum', 'self emptying vacuum', 'pet hair vacuum'
            ],
            'smart_thermostats': [
                'smart thermostat', 'wifi thermostat', 'programmable thermostat',
                'nest thermostat', 'ecobee', 'learning thermostat', 'energy saving thermostat'
            ],
            'smart_lighting': [
                'smart bulb', 'led smart light', 'color changing bulb', 'dimmer switch',
                'smart light strip', 'outdoor smart lights', 'motion sensor lights'
            ]
        }

        self._initialize_data_sources()

    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            'max_keywords_per_batch': 5,
            'request_delay': 1.0,
            'cache_enabled': True,
            'enable_reddit_trends': True,
            'enable_youtube_trends': True,
            'enable_amazon_trends': True,
            'enable_rss_trends': True,
            'reddit_subreddits': [
                'smarthome', 'homeautomation', 'amazonecho', 'googlehome',
                'homekit', 'homesecurity', 'amazonalexa', 'internetofthings',
                'gadgets', 'technology', 'buyitforlife', 'reviews'
            ],
            'youtube_search_regions': ['US', 'GB', 'CA', 'AU'],
            'max_reddit_posts': 50,
            'max_youtube_videos': 25
        }

    def _initialize_data_sources(self):
        """初始化各个数据源"""
        # 初始化Google Trends
        if PYTRENDS_AVAILABLE:
            try:
                self.pytrends = TrendReq(hl='en-US', tz=360)
                self.logger.info("Google Trends initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize pytrends: {e}")

        # 初始化Reddit
        if REDDIT_AVAILABLE:
            self._initialize_reddit()

        # 初始化YouTube
        if YOUTUBE_AVAILABLE:
            self._initialize_youtube()

        # 初始化RSS分析器
        if RSS_AVAILABLE:
            try:
                self.rss_analyzer = RSSFeedAnalyzer()
                self.logger.info("RSS analyzer initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize RSS analyzer: {e}")

        # 初始化Amazon爬虫
        if AMAZON_AVAILABLE:
            try:
                self.amazon_scraper = AmazonBestSellersScraper()
                self.logger.info("Amazon scraper initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Amazon scraper: {e}")

    def _initialize_reddit(self):
        """初始化Reddit API客户端"""
        try:
            # 从配置管理器获取凭据
            credentials = self.config_manager.get_api_credentials()
            client_id = credentials.get('reddit_client_id', '')
            client_secret = credentials.get('reddit_client_secret', '')

            if not client_id or not client_secret:
                self.logger.warning("Reddit API凭据未配置，跳过Reddit数据源")
                self.reddit = None
                return

            # 只读模式认证
            user_agent = self.config_manager.get('data_sources.user_agents.reddit', 'KeywordTool-Reddit/1.0')
            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent
            )

            # 测试连接
            test_subreddit = self.reddit.subreddit('test')
            _ = test_subreddit.display_name

            self.logger.info("Reddit API initialized successfully")

        except Exception as e:
            self.logger.warning(f"Reddit API initialization failed: {e}")
            self.reddit = None

    def _initialize_youtube(self):
        """初始化YouTube API客户端"""
        try:
            # 从配置管理器获取凭据
            credentials = self.config_manager.get_api_credentials()
            api_key = credentials.get('youtube_api_key', '')

            if not api_key:
                self.logger.warning("YouTube API密钥未配置，跳过YouTube数据源")
                self.youtube = None
                return

            self.youtube = build('youtube', 'v3', developerKey=api_key, cache_discovery=False)
            self.logger.info("YouTube API initialized successfully")

        except Exception as e:
            self.logger.warning(f"YouTube API initialization failed: {e}")
            self.youtube = None

    def fetch_google_trends(self, category: str = None, geo: str = 'US') -> List[Dict]:
        """
        从Google Trends获取热门关键词

        Args:
            category: 智能家居类别
            geo: 地理区域

        Returns:
            关键词列表
        """
        if not PYTRENDS_AVAILABLE or not self.pytrends:
            return self._get_fallback_google_trends(category)

        trending_keywords = []
        categories = [category] if category else list(self.smart_home_categories.keys())

        for cat in categories:
            try:
                seed_keywords = self.smart_home_categories[cat][:self.config['max_keywords_per_batch']]

                # 构建Google Trends请求
                self.pytrends.build_payload(
                    seed_keywords,
                    cat=0,
                    timeframe='today 3-m',
                    geo=geo,
                    gprop=''
                )

                # 获取兴趣趋势
                interest_df = self.pytrends.interest_over_time()

                if not interest_df.empty:
                    for keyword in seed_keywords:
                        if keyword in interest_df.columns:
                            trend_data = interest_df[keyword]

                            keyword_data = {
                                'keyword': keyword,
                                'category': cat,
                                'source': 'google_trends',
                                'avg_interest': trend_data.mean(),
                                'peak_interest': trend_data.max(),
                                'current_interest': trend_data.iloc[-1] if len(trend_data) > 0 else 0,
                                'timestamp': datetime.now(),
                                'geo': geo
                            }
                            trending_keywords.append(keyword_data)

                # 获取相关查询
                related_queries = self.pytrends.related_queries()
                for keyword, queries in related_queries.items():
                    if queries is not None and 'top' in queries and queries['top'] is not None:
                        for _, row in queries['top'].head(3).iterrows():
                            related_keyword = row['query']
                            if self._is_relevant_keyword(related_keyword, cat):
                                keyword_data = {
                                    'keyword': related_keyword,
                                    'category': cat,
                                    'source': 'google_trends_related',
                                    'parent_keyword': keyword,
                                    'query_type': 'related_top',
                                    'timestamp': datetime.now(),
                                    'geo': geo
                                }
                                trending_keywords.append(keyword_data)

                # 延迟请求
                time.sleep(self.config['request_delay'])

            except Exception as e:
                self.logger.error(f"Error fetching Google Trends for category {cat}: {e}")
                continue

        return trending_keywords

    def fetch_reddit_trends(self, category: str = None) -> List[Dict]:
        """
        从Reddit获取热门关键词

        Args:
            category: 智能家居类别

        Returns:
            关键词列表
        """
        if not REDDIT_AVAILABLE or not self.reddit:
            return self._get_fallback_reddit_trends(category)

        reddit_keywords = []
        subreddits = self.config.get('reddit_subreddits', ['smarthome', 'homeautomation'])
        limit = int(self.config.get('max_reddit_posts', 50))
        per_sub_limit = max(3, int(limit / len(subreddits)))

        for sub in subreddits:
            try:
                sr = self.reddit.subreddit(sub)
                for post in sr.hot(limit=per_sub_limit):
                    title = str(post.title)
                    keyword = self._extract_keyword_from_text(title)

                    if keyword and self._is_relevant_keyword(keyword, category):
                        keyword_data = {
                            'keyword': keyword,
                            'category': self._infer_category(keyword),
                            'source': 'reddit',
                            'subreddit': sub,
                            'title': title,
                            'score': int(post.score or 0),
                            'comments': int(post.num_comments or 0),
                            'url': f"https://reddit.com{post.permalink}",
                            'timestamp': datetime.now()
                        }
                        reddit_keywords.append(keyword_data)

            except Exception as e:
                self.logger.debug(f"Subreddit {sub} fetch failed: {e}")
                continue

        return reddit_keywords

    def fetch_youtube_trends(self, category: str = None, geo: str = 'US') -> List[Dict]:
        """
        从YouTube获取热门关键词

        Args:
            category: 智能家居类别
            geo: 地理区域

        Returns:
            关键词列表
        """
        if not YOUTUBE_AVAILABLE or not self.youtube:
            return self._get_fallback_youtube_trends(category)

        youtube_keywords = []

        # 构建搜索种子
        if category and category in self.smart_home_categories:
            seeds = self.smart_home_categories[category][:5]
        else:
            seeds = []
            for cat_keywords in self.smart_home_categories.values():
                seeds.extend(cat_keywords[:1])
            seeds = seeds[:8]

        # 查询最近7天的视频
        published_after = (datetime.utcnow() - timedelta(days=7)).isoformat("T") + "Z"

        for query in seeds:
            try:
                search_response = self.youtube.search().list(
                    q=query,
                    part='id',
                    type='video',
                    order='viewCount',
                    maxResults=10,
                    publishedAfter=published_after
                ).execute()

                video_ids = [item['id']['videoId'] for item in search_response.get('items', [])
                           if 'id' in item and 'videoId' in item['id']]

                if video_ids:
                    videos_response = self.youtube.videos().list(
                        id=','.join(video_ids),
                        part='snippet,statistics'
                    ).execute()

                    for item in videos_response.get('items', []):
                        snippet = item.get('snippet', {})
                        stats = item.get('statistics', {})
                        title = snippet.get('title', '')
                        keyword = self._extract_keyword_from_text(title)

                        if keyword and self._is_relevant_keyword(keyword, category):
                            keyword_data = {
                                'keyword': keyword,
                                'category': self._infer_category(keyword),
                                'source': 'youtube',
                                'video_title': title,
                                'channel': snippet.get('channelTitle', ''),
                                'views': int(stats.get('viewCount', 0)),
                                'likes': int(stats.get('likeCount', 0)),
                                'search_query': query,
                                'timestamp': datetime.now()
                            }
                            youtube_keywords.append(keyword_data)

            except Exception as e:
                self.logger.warning(f"YouTube query failed for '{query}': {e}")
                continue

        return youtube_keywords

    def fetch_amazon_trends(self, category: str = None) -> List[Dict]:
        """
        从Amazon获取热门产品关键词

        Args:
            category: 智能家居类别

        Returns:
            关键词列表
        """
        if not AMAZON_AVAILABLE or not self.amazon_scraper:
            return self._get_fallback_amazon_trends(category)

        try:
            amazon_products = self.amazon_scraper.get_trending_products(category=category, limit=10)
            return amazon_products
        except Exception as e:
            self.logger.warning(f"Amazon scraping failed: {e}")
            return self._get_fallback_amazon_trends(category)

    def fetch_rss_trends(self, category: str = None) -> List[Dict]:
        """
        从RSS feeds获取热门关键词

        Args:
            category: 智能家居类别

        Returns:
            关键词列表
        """
        if not RSS_AVAILABLE or not self.rss_analyzer:
            return []

        try:
            return self.rss_analyzer.get_trending_keywords(limit=10, category=category)
        except Exception as e:
            self.logger.warning(f"RSS trends failed: {e}")
            return []

    def fetch_all_sources(self, category: str = None, geo: str = 'US') -> Dict[str, List[Dict]]:
        """
        从所有数据源获取关键词

        Args:
            category: 智能家居类别
            geo: 地理区域

        Returns:
            按数据源分组的关键词字典
        """
        all_keywords = {}

        # Google Trends
        if PYTRENDS_AVAILABLE:
            try:
                google_keywords = self.fetch_google_trends(category, geo)
                all_keywords['google_trends'] = google_keywords
                self.logger.info(f"Fetched {len(google_keywords)} keywords from Google Trends")
            except Exception as e:
                self.logger.error(f"Google Trends fetch failed: {e}")
                all_keywords['google_trends'] = []

        # Reddit
        if self.config.get('enable_reddit_trends', True):
            try:
                reddit_keywords = self.fetch_reddit_trends(category)
                all_keywords['reddit'] = reddit_keywords
                self.logger.info(f"Fetched {len(reddit_keywords)} keywords from Reddit")
            except Exception as e:
                self.logger.error(f"Reddit fetch failed: {e}")
                all_keywords['reddit'] = []

        # YouTube
        if self.config.get('enable_youtube_trends', True):
            try:
                youtube_keywords = self.fetch_youtube_trends(category, geo)
                all_keywords['youtube'] = youtube_keywords
                self.logger.info(f"Fetched {len(youtube_keywords)} keywords from YouTube")
            except Exception as e:
                self.logger.error(f"YouTube fetch failed: {e}")
                all_keywords['youtube'] = []

        # Amazon
        if self.config.get('enable_amazon_trends', True):
            try:
                amazon_keywords = self.fetch_amazon_trends(category)
                all_keywords['amazon'] = amazon_keywords
                self.logger.info(f"Fetched {len(amazon_keywords)} keywords from Amazon")
            except Exception as e:
                self.logger.error(f"Amazon fetch failed: {e}")
                all_keywords['amazon'] = []

        # RSS
        if self.config.get('enable_rss_trends', True):
            try:
                rss_keywords = self.fetch_rss_trends(category)
                all_keywords['rss'] = rss_keywords
                self.logger.info(f"Fetched {len(rss_keywords)} keywords from RSS")
            except Exception as e:
                self.logger.error(f"RSS fetch failed: {e}")
                all_keywords['rss'] = []

        return all_keywords

    def aggregate_keywords(self, keyword_sources: Dict[str, List[Dict]]) -> List[Dict]:
        """
        聚合多个数据源的关键词，去重和排序

        Args:
            keyword_sources: 按数据源分组的关键词

        Returns:
            聚合后的关键词列表
        """
        all_keywords = []
        for source, keywords in keyword_sources.items():
            all_keywords.extend(keywords)

        # 按关键词去重
        unique_keywords = {}
        for kw in all_keywords:
            keyword = kw.get('keyword', '').strip().lower()
            if keyword and keyword not in unique_keywords:
                unique_keywords[keyword] = kw
            else:
                # 如果已存在，合并数据源信息
                existing = unique_keywords.get(keyword, {})
                sources = existing.get('sources', [])
                if isinstance(sources, list):
                    sources.append(kw.get('source', 'unknown'))
                else:
                    sources = [sources, kw.get('source', 'unknown')]
                existing['sources'] = list(set(sources))  # 去重
                unique_keywords[keyword] = existing

        # 按来源数量和时间戳排序
        sorted_keywords = sorted(
            unique_keywords.values(),
            key=lambda x: (
                len(x.get('sources', [])) if isinstance(x.get('sources'), list) else 1,
                x.get('timestamp', datetime.now())
            ),
            reverse=True
        )

        return sorted_keywords

    def _extract_keyword_from_text(self, text: str) -> str:
        """从文本中提取关键词"""
        lowered = (text or '').lower()

        # 尝试匹配已知的智能家居关键词
        for cat, seeds in self.smart_home_categories.items():
            for seed in seeds:
                if seed in lowered:
                    return seed

        # fallback: 提取前几个有意义的词
        tokens = [t for t in lowered.split() if t.isalnum() and len(t) > 2]
        return ' '.join(tokens[:3]) if tokens else ''

    def _infer_category(self, keyword: str) -> str:
        """推断关键词类别"""
        kw = (keyword or '').lower()
        for cat, seeds in self.smart_home_categories.items():
            if any(seed in kw for seed in seeds):
                return cat
        return 'general'

    def _is_relevant_keyword(self, keyword: str, category: str = None) -> bool:
        """检查关键词是否与智能家居相关"""
        if not keyword:
            return False

        keyword_lower = keyword.lower()

        # 检查是否匹配指定类别
        if category and category in self.smart_home_categories:
            category_terms = self.smart_home_categories[category]
            for term in category_terms:
                if any(word in keyword_lower for word in term.lower().split()):
                    return True

        # 通用智能家居术语
        smart_home_terms = [
            'smart', 'wifi', 'bluetooth', 'alexa', 'google', 'home', 'automation',
            'iot', 'connected', 'wireless', 'app', 'control', 'remote'
        ]

        # 具体产品术语
        product_terms = [
            'plug', 'outlet', 'switch', 'dimmer', 'bulb', 'light', 'lamp',
            'camera', 'doorbell', 'lock', 'thermostat', 'sensor', 'detector',
            'hub', 'bridge', 'gateway', 'router', 'speaker', 'display',
            'vacuum', 'robot', 'cleaner', 'security', 'alarm', 'monitor'
        ]

        # 检查所有术语
        all_terms = smart_home_terms + product_terms
        return any(term in keyword_lower for term in all_terms)

    # Fallback methods for when APIs are unavailable
    def _get_fallback_google_trends(self, category: str = None) -> List[Dict]:
        """Google Trends fallback data"""
        fallback_trends = [
            {'keyword': 'smart home automation', 'category': 'general', 'source': 'google_trends_fallback'},
            {'keyword': 'alexa smart plug', 'category': 'smart_plugs', 'source': 'google_trends_fallback'},
            {'keyword': 'robot vacuum pet hair', 'category': 'robot_vacuums', 'source': 'google_trends_fallback'},
            {'keyword': 'outdoor security camera', 'category': 'security_cameras', 'source': 'google_trends_fallback'},
            {'keyword': 'color changing smart bulb', 'category': 'smart_lighting', 'source': 'google_trends_fallback'}
        ]

        for trend in fallback_trends:
            trend['timestamp'] = datetime.now()
            trend['avg_interest'] = random.randint(20, 80)

        if category:
            return [t for t in fallback_trends if t.get('category') == category]
        return fallback_trends

    def _get_fallback_reddit_trends(self, category: str = None) -> List[Dict]:
        """Reddit fallback data"""
        fallback_data = [
            {
                'keyword': 'smart plug energy monitoring',
                'category': 'smart_plugs',
                'source': 'reddit_fallback',
                'subreddit': 'smarthome',
                'score': random.randint(100, 500),
                'comments': random.randint(20, 100),
                'timestamp': datetime.now()
            }
        ]

        if category:
            return [d for d in fallback_data if d.get('category') == category]
        return fallback_data

    def _get_fallback_youtube_trends(self, category: str = None) -> List[Dict]:
        """YouTube fallback data"""
        fallback_data = [
            {
                'keyword': 'smart speaker setup guide',
                'category': 'smart_speakers',
                'source': 'youtube_fallback',
                'views': random.randint(50000, 200000),
                'timestamp': datetime.now()
            }
        ]

        if category:
            return [d for d in fallback_data if d.get('category') == category]
        return fallback_data

    def _get_fallback_amazon_trends(self, category: str = None) -> List[Dict]:
        """Amazon fallback data"""
        fallback_data = [
            {
                'keyword': 'best smart doorbell camera',
                'category': 'security_cameras',
                'source': 'amazon_fallback',
                'timestamp': datetime.now()
            }
        ]

        if category:
            return [d for d in fallback_data if d.get('category') == category]
        return fallback_data


# 示例使用
if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.INFO)

    # 创建关键词获取器
    fetcher = KeywordFetcher()

    safe_print("=== 关键词获取器测试 ===")

    # 获取智能插座类别的关键词
    safe_print("\n获取智能插座关键词...")
    smart_plug_keywords = fetcher.fetch_all_sources(category='smart_plugs')

    for source, keywords in smart_plug_keywords.items():
        safe_print(f"\n{source}: {len(keywords)} 个关键词")
        for kw in keywords[:3]:  # 显示前3个
            safe_print(f"  - {kw.get('keyword', 'N/A')}")

    # 聚合所有关键词
    safe_print("\n聚合关键词...")
    aggregated = fetcher.aggregate_keywords(smart_plug_keywords)
    safe_print(f"聚合后总共 {len(aggregated)} 个关键词")

    for kw in aggregated[:5]:  # 显示前5个
        sources = kw.get('sources', [])
        if isinstance(sources, list):
            sources_str = ', '.join(sources)
        else:
            sources_str = str(sources)
        safe_print(f"  - {kw.get('keyword', 'N/A')} (来源: {sources_str})")