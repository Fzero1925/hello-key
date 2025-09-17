"""
Reddit数据源模块
基于Reddit API获取智能家居相关的关键词和话题
"""

import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Set
import logging

# 导入基类
from ..base.data_source import (
    DataSource, KeywordData, TopicData,
    DataSourceError, DataSourceConfigError,
    DataSourceConnectionError, DataSourceRateLimitError
)

# 可选的praw依赖
try:
    import praw
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False


class RedditSource(DataSource):
    """Reddit数据源实现"""

    def _validate_config(self) -> None:
        """验证Reddit配置"""
        if not PRAW_AVAILABLE:
            raise DataSourceConfigError("praw库未安装，请运行: pip install praw")

        required_fields = ['client_id', 'client_secret', 'user_agent', 'enabled']
        for field in required_fields:
            if field not in self.config:
                raise DataSourceConfigError(f"Reddit配置缺少必需字段: {field}")

    def _initialize(self) -> None:
        """初始化Reddit数据源"""
        # 设置默认配置
        self.request_delay = self.config.get('request_delay', 2)
        self.max_posts = self.config.get('max_posts', 50)
        self.max_comments = self.config.get('max_comments', 20)
        self.score_threshold = self.config.get('score_threshold', 5)

        # Reddit API配置
        self.client_id = self.config['client_id']
        self.client_secret = self.config['client_secret']
        self.user_agent = self.config['user_agent']

        # 智能家居相关subreddit
        self.subreddits = self.config.get('subreddits', [
            'smarthome', 'homeautomation', 'amazonecho', 'googlehome',
            'homekit', 'homesecurity', 'internetofthings', 'gadgets',
            'technology', 'buyitforlife', 'reviews'
        ])

        # 初始化Reddit客户端
        try:
            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent,
                read_only=True
            )
            # 测试连接
            self.reddit.auth.limits
            self.logger.info("Reddit API初始化成功")
        except Exception as e:
            raise DataSourceConnectionError(f"Reddit API初始化失败: {e}")

        # 智能家居关键词分类
        self.smart_home_categories = {
            'smart_plugs': [
                'smart plug', 'wifi outlet', 'alexa plug', 'smart outlet',
                'energy monitoring plug', 'tp-link kasa', 'wyze plug'
            ],
            'security_cameras': [
                'security camera', 'doorbell camera', 'outdoor camera',
                'wifi camera', 'ring doorbell', 'nest cam', 'wyze cam',
                'arlo camera', 'surveillance system'
            ],
            'robot_vacuums': [
                'robot vacuum', 'roomba', 'robotic cleaner',
                'mapping vacuum', 'pet hair vacuum', 'shark robot',
                'eufy vacuum', 'roborock'
            ],
            'smart_speakers': [
                'smart speaker', 'alexa', 'google home', 'echo dot',
                'nest mini', 'voice assistant', 'smart display',
                'echo show', 'nest hub'
            ],
            'smart_lighting': [
                'smart bulb', 'led smart bulb', 'philips hue',
                'smart light switch', 'smart dimmer', 'wyze bulb',
                'lifx', 'kasa switch'
            ],
            'smart_thermostats': [
                'smart thermostat', 'nest thermostat', 'ecobee',
                'wifi thermostat', 'programmable thermostat',
                'honeywell thermostat'
            ],
            'smart_locks': [
                'smart lock', 'smart deadbolt', 'keyless entry',
                'august lock', 'yale lock', 'schlage lock',
                'door lock', 'electronic lock'
            ],
            'general': [
                'smart home', 'home automation', 'iot device',
                'connected home', 'smart device', 'home tech',
                'automation system', 'smart appliance'
            ]
        }

        # 商业意图关键词
        self.commercial_keywords = [
            'best', 'recommend', 'review', 'buy', 'purchase',
            'worth it', 'budget', 'cheap', 'expensive', 'price',
            'comparison', 'vs', 'alternative', 'upgrade'
        ]

        self.logger.info(f"Reddit数据源初始化完成，监控{len(self.subreddits)}个subreddit")

    def get_keywords(self, category: str, limit: int = 20, **kwargs) -> List[KeywordData]:
        """
        从Reddit获取关键词

        Args:
            category: 分类
            limit: 数量限制
            **kwargs: 其他参数

        Returns:
            关键词数据列表
        """
        try:
            # 获取Reddit关键词
            all_keywords = self._fetch_reddit_keywords(category)

            # 按分类过滤
            if category != 'all':
                all_keywords = [kw for kw in all_keywords if kw['category'] == category]

            # 转换为标准格式并限制数量
            result = []
            for reddit_kw in all_keywords[:limit]:
                keyword_data = KeywordData(
                    keyword=reddit_kw['keyword'],
                    source=self.source_name,
                    category=reddit_kw['category'],
                    confidence=reddit_kw['confidence'],
                    search_volume=self._estimate_search_volume(reddit_kw['keyword'], reddit_kw['score']),
                    trend_score=reddit_kw['trend_score'],
                    metadata={
                        'subreddit': reddit_kw['subreddit'],
                        'post_title': reddit_kw['post_title'],
                        'post_url': reddit_kw['post_url'],
                        'score': reddit_kw['score'],
                        'comment_count': reddit_kw['comment_count'],
                        'created_time': reddit_kw['created_time']
                    }
                )
                result.append(keyword_data)

            self.logger.info(f"从Reddit获取到{len(result)}个关键词")
            return result

        except Exception as e:
            self.logger.error(f"获取Reddit关键词失败: {e}")
            raise DataSourceConnectionError(f"Reddit关键词获取失败: {e}")

    def get_topics(self, category: str, limit: int = 10, **kwargs) -> List[TopicData]:
        """
        从Reddit获取话题

        Args:
            category: 分类
            limit: 数量限制
            **kwargs: 其他参数

        Returns:
            话题数据列表
        """
        try:
            # 获取Reddit话题
            all_topics = self._fetch_reddit_topics(category)

            # 按分类过滤
            if category != 'all':
                all_topics = [topic for topic in all_topics if topic['category'] == category]

            # 转换为标准格式并限制数量
            result = []
            for reddit_topic in all_topics[:limit]:
                topic_data = TopicData(
                    title=reddit_topic['title'],
                    source=self.source_name,
                    category=reddit_topic['category'],
                    content=reddit_topic['content'],
                    url=reddit_topic['url'],
                    engagement=reddit_topic['score'] + reddit_topic['comment_count'],
                    trending_score=reddit_topic['trending_score'],
                    keywords=reddit_topic['keywords'],
                    metadata={
                        'subreddit': reddit_topic['subreddit'],
                        'score': reddit_topic['score'],
                        'comment_count': reddit_topic['comment_count'],
                        'created_time': reddit_topic['created_time'],
                        'author': reddit_topic.get('author', 'Unknown')
                    }
                )
                result.append(topic_data)

            self.logger.info(f"从Reddit获取到{len(result)}个话题")
            return result

        except Exception as e:
            self.logger.error(f"获取Reddit话题失败: {e}")
            raise DataSourceConnectionError(f"Reddit话题获取失败: {e}")

    def health_check(self) -> bool:
        """健康检查 - 测试Reddit API是否可用"""
        try:
            # 测试API连接
            limits = self.reddit.auth.limits

            # 尝试获取一个简单的subreddit信息
            test_subreddit = self.reddit.subreddit('smarthome')
            test_subreddit.display_name

            self.logger.debug("Reddit API健康检查通过")
            return True

        except Exception as e:
            self.logger.warning(f"Reddit健康检查失败: {e}")
            return False

    def _fetch_reddit_keywords(self, category: str) -> List[Dict]:
        """从Reddit获取关键词"""
        all_keywords = []
        processed_posts = set()

        # 获取目标关键词
        if category == 'all':
            target_keywords = []
            for cat_keywords in self.smart_home_categories.values():
                target_keywords.extend(cat_keywords)
        else:
            target_keywords = self.smart_home_categories.get(category, [])

        # 遍历相关subreddit
        for subreddit_name in self.subreddits:
            try:
                keywords = self._process_subreddit_for_keywords(
                    subreddit_name, target_keywords, processed_posts
                )
                all_keywords.extend(keywords)

                # 请求间隔
                time.sleep(self.request_delay)

            except Exception as e:
                self.logger.warning(f"处理subreddit失败 {subreddit_name}: {e}")
                continue

        # 按得分和置信度排序
        all_keywords.sort(key=lambda x: (x['confidence'], x['score']), reverse=True)
        return all_keywords

    def _fetch_reddit_topics(self, category: str) -> List[Dict]:
        """从Reddit获取话题"""
        all_topics = []
        processed_posts = set()

        # 遍历相关subreddit
        for subreddit_name in self.subreddits:
            try:
                topics = self._process_subreddit_for_topics(
                    subreddit_name, category, processed_posts
                )
                all_topics.extend(topics)

                # 请求间隔
                time.sleep(self.request_delay)

            except Exception as e:
                self.logger.warning(f"处理subreddit话题失败 {subreddit_name}: {e}")
                continue

        # 按趋势得分排序
        all_topics.sort(key=lambda x: x['trending_score'], reverse=True)
        return all_topics

    def _process_subreddit_for_keywords(self, subreddit_name: str, target_keywords: List[str],
                                        processed_posts: Set[str]) -> List[Dict]:
        """处理单个subreddit获取关键词"""
        keywords = []

        try:
            subreddit = self.reddit.subreddit(subreddit_name)

            # 获取热门帖子
            hot_posts = list(subreddit.hot(limit=self.max_posts))

            for post in hot_posts:
                # 避免重复处理
                if post.id in processed_posts:
                    continue
                processed_posts.add(post.id)

                # 检查帖子得分
                if post.score < self.score_threshold:
                    continue

                # 提取帖子文本
                post_text = f"{post.title} {getattr(post, 'selftext', '')}".lower()

                # 提取关键词
                extracted_keywords = self._extract_keywords_from_post(
                    post, post_text, target_keywords, subreddit_name
                )
                keywords.extend(extracted_keywords)

        except Exception as e:
            self.logger.warning(f"处理subreddit关键词失败 {subreddit_name}: {e}")

        return keywords

    def _process_subreddit_for_topics(self, subreddit_name: str, category: str,
                                      processed_posts: Set[str]) -> List[Dict]:
        """处理单个subreddit获取话题"""
        topics = []

        try:
            subreddit = self.reddit.subreddit(subreddit_name)

            # 获取热门帖子
            hot_posts = list(subreddit.hot(limit=min(self.max_posts, 20)))

            for post in hot_posts:
                # 避免重复处理
                if post.id in processed_posts:
                    continue
                processed_posts.add(post.id)

                # 检查帖子得分
                if post.score < self.score_threshold:
                    continue

                # 提取帖子文本
                post_text = f"{post.title} {getattr(post, 'selftext', '')}".lower()

                # 检查是否与智能家居相关
                if not self._is_smart_home_relevant(post_text):
                    continue

                # 确定分类
                topic_category = self._determine_category(post_text)
                if category != 'all' and topic_category != category:
                    continue

                # 计算趋势得分
                trending_score = self._calculate_trending_score(post)

                # 提取关键词
                keywords = self._extract_keywords_from_text(post_text)

                topics.append({
                    'title': post.title,
                    'content': getattr(post, 'selftext', post.title)[:500],
                    'url': f"https://reddit.com{post.permalink}",
                    'category': topic_category,
                    'trending_score': trending_score,
                    'score': post.score,
                    'comment_count': post.num_comments,
                    'created_time': datetime.fromtimestamp(post.created_utc),
                    'subreddit': subreddit_name,
                    'keywords': keywords[:5],
                    'author': str(post.author) if post.author else 'Unknown'
                })

        except Exception as e:
            self.logger.warning(f"处理subreddit话题失败 {subreddit_name}: {e}")

        return topics

    def _extract_keywords_from_post(self, post, post_text: str, target_keywords: List[str],
                                    subreddit_name: str) -> List[Dict]:
        """从帖子中提取关键词"""
        keywords = []

        for keyword in target_keywords:
            if keyword in post_text:
                # 计算关键词置信度
                confidence = self._calculate_keyword_confidence(
                    keyword, post_text, post.score, post.num_comments
                )

                # 确定分类
                category = self._determine_keyword_category(keyword)

                # 计算趋势得分
                trend_score = self._calculate_trending_score(post)

                keywords.append({
                    'keyword': keyword,
                    'category': category,
                    'confidence': confidence,
                    'trend_score': trend_score,
                    'score': post.score,
                    'comment_count': post.num_comments,
                    'subreddit': subreddit_name,
                    'post_title': post.title,
                    'post_url': f"https://reddit.com{post.permalink}",
                    'created_time': datetime.fromtimestamp(post.created_utc)
                })

        return keywords

    def _is_smart_home_relevant(self, text: str) -> bool:
        """检查文本是否与智能家居相关"""
        # 检查基础智能家居术语
        basic_terms = [
            'smart home', 'home automation', 'iot', 'connected home',
            'smart device', 'alexa', 'google home', 'homekit',
            'automation', 'smart', 'wifi', 'app control'
        ]

        return any(term in text for term in basic_terms)

    def _determine_category(self, text: str) -> str:
        """确定文本的分类"""
        for category, keywords in self.smart_home_categories.items():
            for keyword in keywords:
                if keyword in text:
                    return category
        return 'general'

    def _determine_keyword_category(self, keyword: str) -> str:
        """确定关键词的分类"""
        for category, keywords in self.smart_home_categories.items():
            if keyword in keywords:
                return category
        return 'general'

    def _calculate_keyword_confidence(self, keyword: str, text: str, score: int,
                                      comment_count: int) -> float:
        """计算关键词置信度"""
        confidence = 0.0

        # 基础出现得分
        keyword_count = text.count(keyword)
        confidence += min(0.3, keyword_count * 0.1)

        # Reddit得分影响
        normalized_score = min(1.0, score / 100.0)
        confidence += normalized_score * 0.3

        # 评论数影响
        normalized_comments = min(1.0, comment_count / 50.0)
        confidence += normalized_comments * 0.2

        # 商业意图加分
        for commercial_word in self.commercial_keywords:
            if commercial_word in text:
                confidence += 0.2
                break

        return min(1.0, confidence)

    def _calculate_trending_score(self, post) -> float:
        """计算趋势得分"""
        # 基于帖子得分、评论数和时间的综合评分
        score = 0.0

        # 帖子得分归一化
        normalized_score = min(1.0, post.score / 200.0)
        score += normalized_score * 0.4

        # 评论数归一化
        normalized_comments = min(1.0, post.num_comments / 100.0)
        score += normalized_comments * 0.3

        # 时间新鲜度（越新得分越高）
        post_age_hours = (datetime.now() - datetime.fromtimestamp(post.created_utc)).total_seconds() / 3600
        freshness = max(0, 1 - (post_age_hours / 168))  # 一周内的帖子
        score += freshness * 0.3

        return min(1.0, score)

    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        keywords = []

        for category_keywords in self.smart_home_categories.values():
            for keyword in category_keywords:
                if keyword in text and keyword not in keywords:
                    keywords.append(keyword)

        return keywords

    def _estimate_search_volume(self, keyword: str, reddit_score: int) -> int:
        """基于Reddit数据估算搜索量"""
        # 基础搜索量
        base_volume = 1000

        # 根据Reddit得分调整
        score_multiplier = 1 + (reddit_score / 100.0)

        # 根据关键词长度调整
        word_count = len(keyword.split())
        if word_count == 1:
            score_multiplier *= 1.3
        elif word_count > 3:
            score_multiplier *= 0.8

        estimated_volume = int(base_volume * score_multiplier)
        return max(100, estimated_volume)