"""
Topic Fetcher - 专门负责话题获取
从多个数据源获取热门话题和趋势信息
"""

import os
import sys
import time
import json
import requests
import asyncio
import aiohttp
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple, Optional, Any
import logging
import pytz
import random
import yaml

# 导入配置管理器和编码处理器
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from modules.config import ConfigManager
try:
    from modules.utils.encoding_handler import safe_print, get_encoding_handler
except ImportError:
    def safe_print(text, **kwargs):
        print(text, **kwargs)

# 时区配置
US_EASTERN = pytz.timezone('US/Eastern')
US_PACIFIC = pytz.timezone('US/Pacific')
UK_LONDON = pytz.timezone('Europe/London')
CHINA_TIMEZONE = pytz.timezone('Asia/Shanghai')

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


class TopicFetcher:
    """
    话题获取器 - 专门负责从多个数据源获取热门话题
    不包含分析逻辑，只负责数据获取和格式化
    """

    def __init__(self, config: Optional[Dict] = None):
        self.logger = logging.getLogger(__name__)

        # 加载配置管理器
        self.config_manager = ConfigManager()

        # 使用传入配置或默认配置
        self.config = config or self._get_default_config()
        self.data_dir = "data/realtime_trends"
        self.cache_dir = "data/trend_cache"

        # 创建必要的目录
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)

        # 智能家居相关的种子关键词
        self.smart_home_seeds = {
            'smart_plugs': [
                'smart plug', 'wifi outlet', 'alexa plug', 'smart switch',
                'energy monitoring plug', 'outdoor smart plug', 'voice control outlet'
            ],
            'security_devices': [
                'security camera', 'video doorbell', 'smart lock', 'doorbell cam',
                'wireless camera', 'outdoor camera', 'home security system'
            ],
            'cleaning_devices': [
                'robot vacuum', 'robotic cleaner', 'smart mop', 'pet hair vacuum',
                'self emptying vacuum', 'mapping vacuum', 'quiet robot vacuum'
            ],
            'climate_control': [
                'smart thermostat', 'wifi thermostat', 'nest thermostat',
                'programmable thermostat', 'energy saving thermostat'
            ],
            'lighting': [
                'smart bulb', 'color changing bulb', 'wifi light', 'smart dimmer',
                'led smart bulb', 'outdoor smart lights', 'motion sensor lights'
            ],
            'speakers_displays': [
                'smart speaker', 'alexa echo', 'google nest', 'smart display',
                'voice assistant', 'smart home hub', 'wifi speaker'
            ],
            'emerging_categories': [
                'smart mirror', 'smart doorbell', 'smart garage door', 'smart garden',
                'smart pet feeder', 'smart air purifier', 'smart blinds'
            ]
        }

        # 初始化数据源
        self.pytrends = None
        self.reddit = None
        self.youtube = None
        self._initialize_data_sources()

    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            'google_trends_enabled': True,
            'reddit_enabled': True,
            'youtube_enabled': True,
            'social_signals_enabled': True,
            'max_topics_per_source': 20,
            'cache_expiry_hours': 2,
            'request_delay': 1.0,
            'reddit_subreddits': [
                'smarthome', 'homeautomation', 'amazonecho', 'googlehome',
                'homekit', 'homesecurity', 'amazonalexa', 'internetofthings'
            ]
        }

    def _initialize_data_sources(self):
        """初始化各个数据源"""
        # 初始化Google Trends
        if PYTRENDS_AVAILABLE and self.config.get('google_trends_enabled', True):
            try:
                self.pytrends = TrendReq(hl='en-US', tz=360)
                self.logger.info("Google Trends initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Google Trends: {e}")

        # 初始化Reddit
        if REDDIT_AVAILABLE and self.config.get('reddit_enabled', True):
            self._initialize_reddit()

        # 初始化YouTube
        if YOUTUBE_AVAILABLE and self.config.get('youtube_enabled', True):
            self._initialize_youtube()

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

    async def fetch_google_trends_topics(self, geo: str = 'US', timeframe: str = 'now 1-d') -> List[Dict]:
        """
        从Google Trends获取实时热门话题

        Args:
            geo: 地理区域
            timeframe: 时间范围

        Returns:
            话题列表
        """
        if not self.pytrends:
            return self._get_fallback_google_trends()

        trending_topics = []

        try:
            # 获取各个智能家居类别的趋势
            for category, seeds in self.smart_home_seeds.items():
                try:
                    # 使用前3个种子关键词
                    keywords = seeds[:3]

                    self.pytrends.build_payload(
                        keywords,
                        cat=0,
                        timeframe=timeframe,
                        geo=geo,
                        gprop=''
                    )

                    # 获取兴趣趋势
                    interest_df = self.pytrends.interest_over_time()

                    if not interest_df.empty:
                        for keyword in keywords:
                            if keyword in interest_df.columns:
                                trend_data = interest_df[keyword]

                                topic_data = {
                                    'keyword': keyword,
                                    'category': category,
                                    'source': 'google_trends',
                                    'interest_data': trend_data.to_dict(),
                                    'avg_interest': trend_data.mean(),
                                    'peak_interest': trend_data.max(),
                                    'current_interest': trend_data.iloc[-1] if len(trend_data) > 0 else 0,
                                    'trend_direction': self._calculate_trend_direction(trend_data),
                                    'timestamp': datetime.now(timezone.utc),
                                    'geo': geo,
                                    'timeframe': timeframe
                                }
                                trending_topics.append(topic_data)

                    # 获取相关查询
                    try:
                        related_queries = self.pytrends.related_queries()
                        for kw, queries in related_queries.items():
                            if queries and 'top' in queries and queries['top'] is not None:
                                for _, row in queries['top'].head(3).iterrows():
                                    related_topic = {
                                        'keyword': row['query'],
                                        'category': category,
                                        'source': 'google_trends_related',
                                        'parent_keyword': kw,
                                        'query_type': 'related_top',
                                        'value': row.get('value', 0),
                                        'timestamp': datetime.now(timezone.utc),
                                        'geo': geo
                                    }
                                    trending_topics.append(related_topic)
                    except Exception as e:
                        self.logger.debug(f"Failed to get related queries for {category}: {e}")

                    # 延迟请求
                    await asyncio.sleep(self.config['request_delay'])

                except Exception as e:
                    self.logger.warning(f"Error processing Google Trends for {category}: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Google Trends fetch failed: {e}")

        return trending_topics

    async def fetch_reddit_topics(self, time_filter: str = 'day', limit: int = 50) -> List[Dict]:
        """
        从Reddit获取热门话题

        Args:
            time_filter: 时间过滤器 ('day', 'week', 'month')
            limit: 获取数量限制

        Returns:
            话题列表
        """
        if not self.reddit:
            return self._get_fallback_reddit_topics()

        reddit_topics = []
        subreddits = self.config.get('reddit_subreddits', ['smarthome', 'homeautomation'])
        per_sub_limit = max(5, limit // len(subreddits))

        for sub in subreddits:
            try:
                sr = self.reddit.subreddit(sub)

                # 获取热门帖子
                for post in sr.top(time_filter=time_filter, limit=per_sub_limit):
                    topic_data = {
                        'keyword': post.title,
                        'category': self._infer_category_from_text(post.title),
                        'source': 'reddit',
                        'subreddit': sub,
                        'title': post.title,
                        'score': post.score,
                        'comments': post.num_comments,
                        'url': f"https://reddit.com{post.permalink}",
                        'created_utc': datetime.fromtimestamp(post.created_utc, tz=timezone.utc),
                        'author': str(post.author) if post.author else 'deleted',
                        'upvote_ratio': getattr(post, 'upvote_ratio', 0),
                        'timestamp': datetime.now(timezone.utc),
                        'time_filter': time_filter
                    }
                    reddit_topics.append(topic_data)

                await asyncio.sleep(0.5)  # 短暂延迟

            except Exception as e:
                self.logger.warning(f"Failed to fetch from r/{sub}: {e}")
                continue

        return reddit_topics

    async def fetch_youtube_topics(self, published_within_days: int = 7, max_results: int = 30) -> List[Dict]:
        """
        从YouTube获取热门视频话题

        Args:
            published_within_days: 发布时间范围（天）
            max_results: 最大结果数量

        Returns:
            话题列表
        """
        if not self.youtube:
            return self._get_fallback_youtube_topics()

        youtube_topics = []
        published_after = (datetime.utcnow() - timedelta(days=published_within_days)).isoformat("T") + "Z"

        # 使用智能家居关键词搜索
        search_terms = []
        for seeds in self.smart_home_seeds.values():
            search_terms.extend(seeds[:2])  # 每个类别取前2个
        search_terms = search_terms[:8]  # 总共不超过8个

        for term in search_terms:
            try:
                search_response = self.youtube.search().list(
                    q=term,
                    part='id,snippet',
                    type='video',
                    order='viewCount',
                    maxResults=max_results // len(search_terms),
                    publishedAfter=published_after
                ).execute()

                video_ids = []
                for item in search_response.get('items', []):
                    if 'id' in item and 'videoId' in item['id']:
                        video_ids.append(item['id']['videoId'])

                if video_ids:
                    # 获取视频统计信息
                    videos_response = self.youtube.videos().list(
                        id=','.join(video_ids),
                        part='snippet,statistics'
                    ).execute()

                    for item in videos_response.get('items', []):
                        snippet = item.get('snippet', {})
                        stats = item.get('statistics', {})

                        topic_data = {
                            'keyword': snippet.get('title', ''),
                            'category': self._infer_category_from_text(snippet.get('title', '')),
                            'source': 'youtube',
                            'video_id': item['id'],
                            'title': snippet.get('title', ''),
                            'channel': snippet.get('channelTitle', ''),
                            'description': snippet.get('description', '')[:200],
                            'published_at': snippet.get('publishedAt', ''),
                            'views': int(stats.get('viewCount', 0)),
                            'likes': int(stats.get('likeCount', 0)),
                            'comments': int(stats.get('commentCount', 0)),
                            'search_term': term,
                            'timestamp': datetime.now(timezone.utc)
                        }
                        youtube_topics.append(topic_data)

                await asyncio.sleep(1)  # API限制延迟

            except Exception as e:
                self.logger.warning(f"YouTube search failed for '{term}': {e}")
                continue

        return youtube_topics

    async def fetch_social_signals(self) -> List[Dict]:
        """
        获取社交媒体信号（简化版）

        Returns:
            社交信号话题列表
        """
        social_topics = []

        # 这里可以集成Twitter API、Facebook API等
        # 目前提供模拟数据
        try:
            # 模拟社交媒体热门话题
            simulated_topics = [
                {
                    'keyword': 'smart home automation trends',
                    'category': 'general',
                    'source': 'social_signals',
                    'platform': 'twitter',
                    'mentions': random.randint(100, 1000),
                    'sentiment': random.choice(['positive', 'neutral', 'negative']),
                    'engagement_rate': random.uniform(0.02, 0.08),
                    'timestamp': datetime.now(timezone.utc)
                },
                {
                    'keyword': 'best robot vacuum 2025',
                    'category': 'cleaning_devices',
                    'source': 'social_signals',
                    'platform': 'facebook',
                    'mentions': random.randint(50, 500),
                    'sentiment': 'positive',
                    'engagement_rate': random.uniform(0.03, 0.09),
                    'timestamp': datetime.now(timezone.utc)
                }
            ]

            social_topics.extend(simulated_topics)

        except Exception as e:
            self.logger.warning(f"Social signals fetch failed: {e}")

        return social_topics

    async def fetch_search_volume_spikes(self) -> List[Dict]:
        """
        检测搜索量激增的话题

        Returns:
            搜索量激增话题列表
        """
        spike_topics = []

        try:
            if self.pytrends:
                # 检测过去24小时的搜索量变化
                timeframe = 'now 1-H'  # 过去1小时

                for category, seeds in self.smart_home_seeds.items():
                    for keyword in seeds[:2]:  # 每个类别检查前2个关键词
                        try:
                            self.pytrends.build_payload(
                                [keyword],
                                cat=0,
                                timeframe=timeframe,
                                geo='US',
                                gprop=''
                            )

                            interest_df = self.pytrends.interest_over_time()

                            if not interest_df.empty and keyword in interest_df.columns:
                                trend_data = interest_df[keyword]

                                # 检测是否有激增
                                if len(trend_data) >= 2:
                                    recent_avg = trend_data.tail(3).mean()
                                    overall_avg = trend_data.mean()

                                    if recent_avg > overall_avg * 1.5:  # 50%以上增长
                                        spike_data = {
                                            'keyword': keyword,
                                            'category': category,
                                            'source': 'search_volume_spike',
                                            'spike_ratio': recent_avg / overall_avg if overall_avg > 0 else 1,
                                            'current_interest': trend_data.iloc[-1],
                                            'avg_interest': overall_avg,
                                            'peak_interest': trend_data.max(),
                                            'detection_time': datetime.now(timezone.utc),
                                            'timeframe': timeframe
                                        }
                                        spike_topics.append(spike_data)

                            await asyncio.sleep(0.5)

                        except Exception as e:
                            self.logger.debug(f"Spike detection failed for {keyword}: {e}")
                            continue

        except Exception as e:
            self.logger.warning(f"Search volume spike detection failed: {e}")

        return spike_topics

    async def fetch_seasonal_opportunities(self) -> List[Dict]:
        """
        获取季节性机会话题

        Returns:
            季节性话题列表
        """
        seasonal_topics = []

        try:
            current_month = datetime.now().month
            current_season = self._get_current_season(current_month)

            # 季节性关键词映射
            seasonal_keywords = {
                'winter': [
                    'smart thermostat winter savings',
                    'indoor air purifier winter',
                    'smart heater wifi control',
                    'winter home security camera'
                ],
                'spring': [
                    'smart garden irrigation',
                    'outdoor security camera spring',
                    'smart air quality monitor',
                    'spring cleaning robot vacuum'
                ],
                'summer': [
                    'smart air conditioner wifi',
                    'outdoor smart plug summer',
                    'smart pool monitor',
                    'solar powered security camera'
                ],
                'fall': [
                    'smart doorbell holiday season',
                    'automated christmas lights',
                    'smart door lock security',
                    'holiday smart home bundle'
                ]
            }

            if current_season in seasonal_keywords:
                for keyword in seasonal_keywords[current_season]:
                    seasonal_data = {
                        'keyword': keyword,
                        'category': self._infer_category_from_text(keyword),
                        'source': 'seasonal_opportunity',
                        'season': current_season,
                        'month': current_month,
                        'seasonality_score': random.uniform(0.7, 1.0),
                        'estimated_interest': random.randint(1000, 5000),
                        'timestamp': datetime.now(timezone.utc)
                    }
                    seasonal_topics.append(seasonal_data)

        except Exception as e:
            self.logger.warning(f"Seasonal opportunities fetch failed: {e}")

        return seasonal_topics

    async def fetch_all_topics(self, force_refresh: bool = False) -> Dict[str, List[Dict]]:
        """
        从所有数据源获取话题

        Args:
            force_refresh: 强制刷新缓存

        Returns:
            按数据源分组的话题字典
        """
        all_topics = {}

        # 检查缓存
        if not force_refresh:
            cached_data = self._load_cached_topics()
            if cached_data:
                self.logger.info("Using cached topic data")
                return cached_data

        try:
            # 并发获取各个数据源的话题
            tasks = []

            if self.config.get('google_trends_enabled', True):
                tasks.append(('google_trends', self.fetch_google_trends_topics()))

            if self.config.get('reddit_enabled', True):
                tasks.append(('reddit', self.fetch_reddit_topics()))

            if self.config.get('youtube_enabled', True):
                tasks.append(('youtube', self.fetch_youtube_topics()))

            if self.config.get('social_signals_enabled', True):
                tasks.append(('social_signals', self.fetch_social_signals()))

            tasks.append(('search_spikes', self.fetch_search_volume_spikes()))
            tasks.append(('seasonal', self.fetch_seasonal_opportunities()))

            # 执行所有任务
            results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)

            # 组织结果
            for i, (source_name, _) in enumerate(tasks):
                result = results[i]
                if isinstance(result, Exception):
                    self.logger.error(f"Failed to fetch {source_name} topics: {result}")
                    all_topics[source_name] = []
                else:
                    all_topics[source_name] = result
                    self.logger.info(f"Fetched {len(result)} topics from {source_name}")

            # 缓存结果
            self._cache_topics(all_topics)

        except Exception as e:
            self.logger.error(f"Failed to fetch all topics: {e}")

        return all_topics

    def aggregate_topics(self, topic_sources: Dict[str, List[Dict]]) -> List[Dict]:
        """
        聚合多个数据源的话题，去重和初步排序

        Args:
            topic_sources: 按数据源分组的话题

        Returns:
            聚合后的话题列表
        """
        all_topics = []
        for source, topics in topic_sources.items():
            all_topics.extend(topics)

        # 按关键词去重
        unique_topics = {}
        for topic in all_topics:
            keyword = topic.get('keyword', '').strip().lower()
            if keyword and keyword not in unique_topics:
                unique_topics[keyword] = topic
            else:
                # 如果已存在，合并数据源信息
                existing = unique_topics.get(keyword, {})
                sources = existing.get('sources', [])
                if isinstance(sources, list):
                    sources.append(topic.get('source', 'unknown'))
                else:
                    sources = [sources, topic.get('source', 'unknown')]
                existing['sources'] = list(set(sources))  # 去重
                unique_topics[keyword] = existing

        # 按时间戳排序（最新的在前）
        sorted_topics = sorted(
            unique_topics.values(),
            key=lambda x: x.get('timestamp', datetime.now(timezone.utc)),
            reverse=True
        )

        return sorted_topics

    # Helper methods
    def _calculate_trend_direction(self, trend_data) -> str:
        """计算趋势方向"""
        if len(trend_data) < 2:
            return 'stable'

        recent_avg = trend_data.tail(3).mean()
        early_avg = trend_data.head(3).mean()

        if recent_avg > early_avg * 1.2:
            return 'rising'
        elif recent_avg < early_avg * 0.8:
            return 'falling'
        else:
            return 'stable'

    def _infer_category_from_text(self, text: str) -> str:
        """从文本推断类别"""
        text_lower = text.lower()

        for category, keywords in self.smart_home_seeds.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return category

        return 'general'

    def _get_current_season(self, month: int) -> str:
        """获取当前季节"""
        if month in [12, 1, 2]:
            return 'winter'
        elif month in [3, 4, 5]:
            return 'spring'
        elif month in [6, 7, 8]:
            return 'summer'
        else:
            return 'fall'

    def _load_cached_topics(self) -> Optional[Dict[str, List[Dict]]]:
        """加载缓存的话题数据"""
        cache_file = os.path.join(self.cache_dir, "topics_cache.json")

        if not os.path.exists(cache_file):
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)

            # 检查缓存是否过期
            cache_time = datetime.fromisoformat(cached_data.get('cached_at', ''))
            expiry_hours = self.config.get('cache_expiry_hours', 2)

            if datetime.now(timezone.utc) - cache_time < timedelta(hours=expiry_hours):
                return cached_data.get('topics', {})

        except Exception as e:
            self.logger.warning(f"Failed to load cached topics: {e}")

        return None

    def _cache_topics(self, topics: Dict[str, List[Dict]]):
        """缓存话题数据"""
        cache_file = os.path.join(self.cache_dir, "topics_cache.json")

        try:
            cache_data = {
                'topics': topics,
                'cached_at': datetime.now(timezone.utc).isoformat()
            }

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False, default=str)

        except Exception as e:
            self.logger.warning(f"Failed to cache topics: {e}")

    # Fallback methods
    def _get_fallback_google_trends(self) -> List[Dict]:
        """Google Trends fallback data"""
        return [
            {
                'keyword': 'smart home automation',
                'category': 'general',
                'source': 'google_trends_fallback',
                'avg_interest': random.randint(20, 80),
                'timestamp': datetime.now(timezone.utc)
            }
        ]

    def _get_fallback_reddit_topics(self) -> List[Dict]:
        """Reddit fallback data"""
        return [
            {
                'keyword': 'best smart plug 2025',
                'category': 'smart_plugs',
                'source': 'reddit_fallback',
                'score': random.randint(100, 500),
                'timestamp': datetime.now(timezone.utc)
            }
        ]

    def _get_fallback_youtube_topics(self) -> List[Dict]:
        """YouTube fallback data"""
        return [
            {
                'keyword': 'smart speaker setup guide',
                'category': 'speakers_displays',
                'source': 'youtube_fallback',
                'views': random.randint(50000, 200000),
                'timestamp': datetime.now(timezone.utc)
            }
        ]


# 示例使用
if __name__ == "__main__":
    import asyncio

    # 设置日志
    logging.basicConfig(level=logging.INFO)

    async def main():
        # 创建话题获取器
        fetcher = TopicFetcher()

        safe_print("=== 话题获取器测试 ===")

        # 获取Google Trends话题
        safe_print("\n获取Google Trends话题...")
        google_topics = await fetcher.fetch_google_trends_topics()
        safe_print(f"获取到 {len(google_topics)} 个Google Trends话题")

        # 获取Reddit话题
        safe_print("\n获取Reddit话题...")
        reddit_topics = await fetcher.fetch_reddit_topics(limit=10)
        safe_print(f"获取到 {len(reddit_topics)} 个Reddit话题")

        # 获取所有话题
        safe_print("\n获取所有数据源话题...")
        all_topics = await fetcher.fetch_all_topics()

        for source, topics in all_topics.items():
            safe_print(f"{source}: {len(topics)} 个话题")
            for topic in topics[:2]:  # 显示前2个
                safe_print(f"  - {topic.get('keyword', 'N/A')}")

        # 聚合话题
        safe_print("\n聚合话题...")
        aggregated = fetcher.aggregate_topics(all_topics)
        safe_print(f"聚合后总共 {len(aggregated)} 个话题")

        for topic in aggregated[:5]:  # 显示前5个
            safe_print(f"  - {topic.get('keyword', 'N/A')} (来源: {topic.get('source', 'N/A')})")

    asyncio.run(main())