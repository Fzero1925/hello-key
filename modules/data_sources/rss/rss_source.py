"""
RSS数据源模块
基于RSS feeds获取智能家居相关的关键词和话题
"""

import re
import time
import requests
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Any
from urllib.parse import urljoin, urlparse
import logging

# 导入基类
from ..base.data_source import (
    DataSource, KeywordData, TopicData,
    DataSourceError, DataSourceConfigError, DataSourceConnectionError
)


class RSSSource(DataSource):
    """RSS数据源实现"""

    def _validate_config(self) -> None:
        """验证RSS配置"""
        required_fields = ['feeds', 'enabled']
        for field in required_fields:
            if field not in self.config:
                raise DataSourceConfigError(f"RSS配置缺少必需字段: {field}")

        if not isinstance(self.config['feeds'], dict):
            raise DataSourceConfigError("feeds必须是字典格式")

    def _initialize(self) -> None:
        """初始化RSS数据源"""
        # 设置默认配置
        self.max_age_hours = self.config.get('max_age_hours', 24)
        self.min_relevance = self.config.get('min_relevance', 0.3)
        self.request_timeout = self.config.get('request_timeout', 10)
        self.request_delay = self.config.get('request_delay', 1)

        # RSS feeds配置
        self.rss_feeds = self.config.get('feeds', {})

        # 智能家居产品分类
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
            ],
            'general': [
                'smart home', 'home automation', 'iot', 'connected home', 'smart device',
                'home tech', 'automation system', 'smart appliance'
            ]
        }

        # 商业意图指示词
        self.commercial_keywords = [
            'best', 'review', 'price', 'deal', 'sale', 'discount', 'buy', 'cheap',
            'comparison', 'vs', 'alternative', 'guide', 'recommendation', '2025'
        ]

        # 请求头设置
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive'
        }

        self.logger.info(f"RSS数据源初始化完成，配置了{len(self.rss_feeds)}个RSS源")

    def get_keywords(self, category: str, limit: int = 20, **kwargs) -> List[KeywordData]:
        """
        从RSS feeds获取关键词

        Args:
            category: 分类
            limit: 数量限制
            **kwargs: 其他参数

        Returns:
            关键词数据列表
        """
        try:
            # 获取所有RSS关键词
            all_keywords = self._fetch_rss_keywords()

            # 按分类过滤
            if category != 'all':
                all_keywords = [kw for kw in all_keywords if kw['category'] == category]

            # 转换为标准格式并限制数量
            result = []
            for rss_kw in all_keywords[:limit]:
                keyword_data = KeywordData(
                    keyword=rss_kw['keyword'],
                    source=self.source_name,
                    category=rss_kw['category'],
                    confidence=rss_kw['relevance_score'],
                    search_volume=self._estimate_search_volume(rss_kw['keyword']),
                    trend_score=rss_kw['relevance_score'],
                    metadata={
                        'feed_name': rss_kw['feed_name'],
                        'title': rss_kw['title'],
                        'url': rss_kw['url'],
                        'publish_date': rss_kw['publish_date']
                    }
                )
                result.append(keyword_data)

            self.logger.info(f"从RSS获取到{len(result)}个关键词")
            return result

        except Exception as e:
            self.logger.error(f"获取RSS关键词失败: {e}")
            raise DataSourceConnectionError(f"RSS关键词获取失败: {e}")

    def get_topics(self, category: str, limit: int = 10, **kwargs) -> List[TopicData]:
        """
        从RSS feeds获取话题

        Args:
            category: 分类
            limit: 数量限制
            **kwargs: 其他参数

        Returns:
            话题数据列表
        """
        try:
            # 获取最新的RSS条目作为话题
            all_topics = self._fetch_rss_topics()

            # 按分类过滤
            if category != 'all':
                all_topics = [topic for topic in all_topics if topic['category'] == category]

            # 转换为标准格式并限制数量
            result = []
            for rss_topic in all_topics[:limit]:
                topic_data = TopicData(
                    title=rss_topic['title'],
                    source=self.source_name,
                    category=rss_topic['category'],
                    content=rss_topic['content'],
                    url=rss_topic['url'],
                    engagement=rss_topic.get('engagement', 0),
                    trending_score=rss_topic['relevance_score'],
                    keywords=rss_topic.get('keywords', []),
                    metadata={
                        'feed_name': rss_topic['feed_name'],
                        'publish_date': rss_topic['publish_date']
                    }
                )
                result.append(topic_data)

            self.logger.info(f"从RSS获取到{len(result)}个话题")
            return result

        except Exception as e:
            self.logger.error(f"获取RSS话题失败: {e}")
            raise DataSourceConnectionError(f"RSS话题获取失败: {e}")

    def health_check(self) -> bool:
        """健康检查 - 测试几个RSS源是否可用"""
        working_feeds = 0
        total_feeds = len(self.rss_feeds)

        if total_feeds == 0:
            return False

        # 测试前3个RSS源
        test_feeds = list(self.rss_feeds.items())[:3]

        for feed_id, feed_config in test_feeds:
            try:
                response = requests.get(
                    feed_config['url'],
                    headers=self.headers,
                    timeout=5
                )
                if response.status_code == 200:
                    working_feeds += 1
            except:
                continue

        # 如果至少有一半的测试源工作正常
        success_rate = working_feeds / len(test_feeds)
        is_healthy = success_rate >= 0.5

        self.logger.debug(f"RSS健康检查: {working_feeds}/{len(test_feeds)} 源正常工作")
        return is_healthy

    def _fetch_rss_keywords(self) -> List[Dict]:
        """获取RSS关键词"""
        all_keywords = []
        cutoff_time = datetime.now() - timedelta(hours=self.max_age_hours)

        for feed_id, feed_config in self.rss_feeds.items():
            try:
                keywords = self._process_feed_for_keywords(feed_config, cutoff_time)
                all_keywords.extend(keywords)

                # 请求间隔
                time.sleep(self.request_delay)

            except Exception as e:
                self.logger.warning(f"处理RSS源失败 {feed_id}: {e}")
                continue

        # 按相关性和发布时间排序
        all_keywords.sort(key=lambda x: (x['relevance_score'], x['publish_date']), reverse=True)
        return all_keywords

    def _fetch_rss_topics(self) -> List[Dict]:
        """获取RSS话题"""
        all_topics = []
        cutoff_time = datetime.now() - timedelta(hours=self.max_age_hours)

        for feed_id, feed_config in self.rss_feeds.items():
            try:
                topics = self._process_feed_for_topics(feed_config, cutoff_time)
                all_topics.extend(topics)

                # 请求间隔
                time.sleep(self.request_delay)

            except Exception as e:
                self.logger.warning(f"处理RSS源失败 {feed_id}: {e}")
                continue

        # 按相关性和发布时间排序
        all_topics.sort(key=lambda x: (x['relevance_score'], x['publish_date']), reverse=True)
        return all_topics

    def _process_feed_for_keywords(self, feed_config: Dict, cutoff_time: datetime) -> List[Dict]:
        """处理单个RSS源获取关键词"""
        keywords = []

        try:
            # 获取RSS内容
            response = requests.get(
                feed_config['url'],
                headers=self.headers,
                timeout=self.request_timeout
            )
            response.raise_for_status()

            feed = feedparser.parse(response.content)

            if not feed.entries:
                self.logger.warning(f"RSS源无条目: {feed_config['name']}")
                return keywords

            for entry in feed.entries:
                try:
                    # 解析发布时间
                    publish_date = self._parse_date(entry)

                    if publish_date < cutoff_time:
                        continue

                    # 提取标题和描述
                    title = entry.get('title', '')
                    description = entry.get('description', '') or entry.get('summary', '')
                    content = f"{title} {description}".lower()

                    # 检查是否与智能家居相关
                    if not self._is_smart_home_relevant(content, feed_config):
                        continue

                    # 提取关键词
                    extracted_keywords = self._extract_keywords_from_content(
                        content, title, feed_config, entry, publish_date
                    )

                    keywords.extend(extracted_keywords)

                except Exception as e:
                    self.logger.debug(f"处理RSS条目失败: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"获取RSS源失败 {feed_config['url']}: {e}")

        return keywords

    def _process_feed_for_topics(self, feed_config: Dict, cutoff_time: datetime) -> List[Dict]:
        """处理单个RSS源获取话题"""
        topics = []

        try:
            # 获取RSS内容
            response = requests.get(
                feed_config['url'],
                headers=self.headers,
                timeout=self.request_timeout
            )
            response.raise_for_status()

            feed = feedparser.parse(response.content)

            if not feed.entries:
                return topics

            for entry in feed.entries:
                try:
                    # 解析发布时间
                    publish_date = self._parse_date(entry)

                    if publish_date < cutoff_time:
                        continue

                    # 提取标题和描述
                    title = entry.get('title', '')
                    description = entry.get('description', '') or entry.get('summary', '')
                    content = f"{title} {description}".lower()

                    # 检查是否与智能家居相关
                    if not self._is_smart_home_relevant(content, feed_config):
                        continue

                    # 确定分类
                    category = self._determine_category(content)

                    # 计算相关性评分
                    relevance = self._calculate_relevance_score(content, title, feed_config)

                    if relevance >= self.min_relevance:
                        topics.append({
                            'title': title,
                            'content': description or title,
                            'url': entry.get('link', ''),
                            'category': category,
                            'relevance_score': relevance,
                            'feed_name': feed_config['name'],
                            'publish_date': publish_date,
                            'keywords': self._extract_topic_keywords(content)
                        })

                except Exception as e:
                    self.logger.debug(f"处理RSS话题失败: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"获取RSS话题失败 {feed_config['url']}: {e}")

        return topics

    def _parse_date(self, entry) -> datetime:
        """解析RSS条目的发布时间"""
        date_fields = ['published_parsed', 'updated_parsed']

        for field in date_fields:
            if hasattr(entry, field) and getattr(entry, field):
                time_struct = getattr(entry, field)
                return datetime(*time_struct[:6])

        # 如果没有找到日期，返回当前时间
        return datetime.now()

    def _is_smart_home_relevant(self, content: str, feed_config: Dict) -> bool:
        """检查内容是否与智能家居相关"""
        # 检查源特定关键词
        for keyword in feed_config.get('smart_home_keywords', []):
            if keyword in content:
                return True

        # 检查通用智能家居术语
        general_terms = [
            'smart home', 'home automation', 'iot', 'connected home',
            'alexa', 'google home', 'homekit', 'nest', 'ring', 'smart device'
        ]

        return any(term in content for term in general_terms)

    def _determine_category(self, content: str) -> str:
        """确定内容的分类"""
        for category, keywords in self.smart_home_categories.items():
            for keyword in keywords:
                if keyword in content:
                    return category
        return 'general'

    def _calculate_relevance_score(self, content: str, title: str, feed_config: Dict) -> float:
        """计算相关性评分"""
        score = 0.0

        # 智能家居关键词基础分
        smart_home_count = 0
        for category_keywords in self.smart_home_categories.values():
            for keyword in category_keywords:
                if keyword in content:
                    smart_home_count += 1

        score += min(0.4, smart_home_count * 0.1)

        # 标题中包含相关词加分
        if any(keyword in title.lower() for keywords in self.smart_home_categories.values() for keyword in keywords):
            score += 0.3

        # 商业意图加分
        for commercial_word in self.commercial_keywords:
            if commercial_word in content:
                score += 0.1
                break

        # RSS源特定关键词加分
        for feed_keyword in feed_config.get('smart_home_keywords', []):
            if feed_keyword in content:
                score += 0.2
                break

        return min(1.0, score)

    def _extract_keywords_from_content(self, content: str, title: str, feed_config: Dict,
                                       entry: Dict, publish_date: datetime) -> List[Dict]:
        """从内容中提取关键词"""
        keywords = []

        # 为每个分类提取关键词
        for category, category_keywords in self.smart_home_categories.items():
            for base_keyword in category_keywords:
                if base_keyword in content:
                    # 计算相关性评分
                    relevance = self._calculate_keyword_relevance(content, title, base_keyword, feed_config)

                    if relevance >= self.min_relevance:
                        # 生成关键词变体
                        variations = self._generate_keyword_variations(base_keyword, content)

                        for variation in variations:
                            keywords.append({
                                'keyword': variation,
                                'category': category,
                                'relevance_score': relevance,
                                'feed_name': feed_config['name'],
                                'title': title,
                                'url': entry.get('link', ''),
                                'publish_date': publish_date
                            })

        return keywords

    def _calculate_keyword_relevance(self, content: str, title: str, keyword: str, feed_config: Dict) -> float:
        """计算关键词相关性"""
        score = 0.0

        # 关键词出现基础分
        if keyword in content:
            score += 0.3

        # 标题中出现加分
        if keyword in title.lower():
            score += 0.4

        # 商业意图加分
        for commercial_word in self.commercial_keywords:
            if commercial_word in content:
                score += 0.1
                break

        # RSS源特定关键词加分
        for feed_keyword in feed_config.get('smart_home_keywords', []):
            if feed_keyword in content:
                score += 0.2
                break

        return min(1.0, score)

    def _generate_keyword_variations(self, base_keyword: str, content: str) -> List[str]:
        """生成关键词变体"""
        variations = [base_keyword]

        # 商业修饰词
        modifiers = []

        if any(word in content for word in ['best', 'top', 'review']):
            modifiers.append('best')

        if any(word in content for word in ['2025', '2024', 'new']):
            modifiers.append('2025')

        if any(word in content for word in ['cheap', 'budget', 'affordable']):
            modifiers.append('budget')

        if any(word in content for word in ['wifi', 'wireless']):
            modifiers.append('wifi')

        # 创建变体（最多2个修饰词）
        for modifier in modifiers[:2]:
            if modifier == 'best':
                variations.append(f'best {base_keyword}')
            elif modifier == '2025':
                variations.append(f'{base_keyword} 2025')
            elif modifier == 'budget':
                variations.append(f'budget {base_keyword}')
            elif modifier == 'wifi':
                variations.append(f'{base_keyword} wifi')

        return variations

    def _extract_topic_keywords(self, content: str) -> List[str]:
        """从话题内容中提取关键词"""
        keywords = []

        for category_keywords in self.smart_home_categories.values():
            for keyword in category_keywords:
                if keyword in content:
                    keywords.append(keyword)

        return keywords[:5]  # 限制关键词数量

    def _estimate_search_volume(self, keyword: str) -> int:
        """估算搜索量"""
        # 简单的搜索量估算逻辑
        base_volume = 1000

        # 根据关键词特征调整
        word_count = len(keyword.split())
        if word_count == 1:
            base_volume *= 2
        elif word_count > 3:
            base_volume *= 0.5

        # 商业意图关键词通常搜索量更高
        if any(word in keyword.lower() for word in self.commercial_keywords):
            base_volume *= 1.5

        return max(100, int(base_volume))