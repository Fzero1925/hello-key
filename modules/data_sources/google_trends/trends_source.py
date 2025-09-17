"""
Google Trends数据源模块
基于Google Trends获取智能家居相关的关键词趋势数据
"""

import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import logging

# 导入基类
from ..base.data_source import (
    DataSource, KeywordData, TopicData,
    DataSourceError, DataSourceConfigError,
    DataSourceConnectionError, DataSourceRateLimitError
)

# 可选的pytrends依赖
try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False


class GoogleTrendsSource(DataSource):
    """Google Trends数据源实现"""

    def _validate_config(self) -> None:
        """验证Google Trends配置"""
        if not PYTRENDS_AVAILABLE:
            raise DataSourceConfigError("pytrends库未安装，请运行: pip install pytrends")

        required_fields = ['enabled']
        for field in required_fields:
            if field not in self.config:
                raise DataSourceConfigError(f"Google Trends配置缺少必需字段: {field}")

    def _initialize(self) -> None:
        """初始化Google Trends数据源"""
        # 设置默认配置
        self.request_delay = self.config.get('request_delay', 3)  # Google Trends需要更长延迟
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay = self.config.get('retry_delay', 5)
        self.region = self.config.get('region', 'US')
        self.language = self.config.get('language', 'en-US')
        self.timezone = self.config.get('timezone', 360)

        # 初始化pytrends
        try:
            self.pytrends = TrendReq(
                hl=self.language,
                tz=self.timezone,
                timeout=(10, 25),
                retries=2,
                backoff_factor=0.1
            )
            self.logger.info("Google Trends API初始化成功")
        except Exception as e:
            raise DataSourceConnectionError(f"Google Trends API初始化失败: {e}")

        # 智能家居关键词分类
        self.smart_home_categories = {
            'smart_plugs': [
                'smart plug', 'wifi outlet', 'alexa plug', 'smart outlet',
                'energy monitoring plug', 'outdoor smart plug'
            ],
            'security_cameras': [
                'security camera', 'doorbell camera', 'outdoor camera',
                'wifi camera', 'ring doorbell', 'nest cam', 'wyze cam'
            ],
            'robot_vacuums': [
                'robot vacuum', 'roomba', 'robotic cleaner',
                'mapping vacuum', 'pet hair vacuum'
            ],
            'smart_speakers': [
                'smart speaker', 'alexa', 'google home', 'echo dot',
                'nest mini', 'voice assistant', 'smart display'
            ],
            'smart_lighting': [
                'smart bulb', 'led smart bulb', 'philips hue',
                'smart light switch', 'smart dimmer'
            ],
            'smart_thermostats': [
                'smart thermostat', 'nest thermostat', 'ecobee',
                'wifi thermostat', 'programmable thermostat'
            ],
            'smart_locks': [
                'smart lock', 'smart deadbolt', 'keyless entry',
                'august lock', 'yale lock'
            ],
            'general': [
                'smart home', 'home automation', 'iot device',
                'connected home', 'smart device'
            ]
        }

        # 趋势评分权重
        self.trend_weights = {
            'interest_over_time': 0.4,
            'rising_related': 0.3,
            'top_related': 0.2,
            'regional_interest': 0.1
        }

        self.logger.info(f"Google Trends数据源初始化完成")

    def get_keywords(self, category: str, limit: int = 20, **kwargs) -> List[KeywordData]:
        """
        从Google Trends获取关键词

        Args:
            category: 分类
            limit: 数量限制
            **kwargs: 其他参数

        Returns:
            关键词数据列表
        """
        try:
            # 获取分类关键词
            if category == 'all':
                base_keywords = []
                for cat_keywords in self.smart_home_categories.values():
                    base_keywords.extend(cat_keywords[:2])  # 每个分类取2个
            else:
                base_keywords = self.smart_home_categories.get(category, [])

            if not base_keywords:
                self.logger.warning(f"未找到分类的关键词: {category}")
                return []

            # 获取趋势数据
            all_keywords = self._fetch_trending_keywords(base_keywords, category)

            # 限制数量
            result = all_keywords[:limit]

            self.logger.info(f"从Google Trends获取到{len(result)}个关键词")
            return result

        except DataSourceRateLimitError:
            self.logger.warning("Google Trends请求频率限制，返回缓存数据")
            return self._get_fallback_keywords(category, limit)
        except Exception as e:
            self.logger.error(f"获取Google Trends关键词失败: {e}")
            return self._get_fallback_keywords(category, limit)

    def get_topics(self, category: str, limit: int = 10, **kwargs) -> List[TopicData]:
        """
        从Google Trends获取话题

        Args:
            category: 分类
            limit: 数量限制
            **kwargs: 其他参数

        Returns:
            话题数据列表
        """
        try:
            # 获取分类关键词
            if category == 'all':
                base_keywords = ['smart home', 'home automation', 'iot device']
            else:
                base_keywords = self.smart_home_categories.get(category, [])[:3]

            if not base_keywords:
                return []

            # 获取相关话题
            all_topics = self._fetch_trending_topics(base_keywords, category)

            # 限制数量
            result = all_topics[:limit]

            self.logger.info(f"从Google Trends获取到{len(result)}个话题")
            return result

        except Exception as e:
            self.logger.error(f"获取Google Trends话题失败: {e}")
            return []

    def health_check(self) -> bool:
        """健康检查 - 测试Google Trends API是否可用"""
        try:
            # 尝试简单的趋势查询
            self.pytrends.build_payload(['smart home'], timeframe='now 7-d', geo=self.region)

            # 获取兴趣时间线数据
            interest_data = self.pytrends.interest_over_time()

            # 如果有数据返回则说明API正常
            is_healthy = not interest_data.empty if hasattr(interest_data, 'empty') else False

            self.logger.debug(f"Google Trends健康检查: {'通过' if is_healthy else '失败'}")
            return is_healthy

        except Exception as e:
            self.logger.warning(f"Google Trends健康检查失败: {e}")
            return False

    def _fetch_trending_keywords(self, base_keywords: List[str], category: str) -> List[KeywordData]:
        """获取趋势关键词"""
        all_keywords = []

        # 分批处理关键词（Google Trends限制每次5个关键词）
        batch_size = 5
        for i in range(0, len(base_keywords), batch_size):
            batch = base_keywords[i:i + batch_size]

            try:
                # 获取这批关键词的趋势数据
                batch_keywords = self._process_keyword_batch(batch, category)
                all_keywords.extend(batch_keywords)

                # 请求间隔
                self._wait_for_rate_limit()

            except DataSourceRateLimitError:
                self.logger.warning("遇到频率限制，停止后续请求")
                break
            except Exception as e:
                self.logger.warning(f"处理关键词批次失败: {e}")
                continue

        # 按趋势评分排序
        all_keywords.sort(key=lambda x: x.trend_score or 0, reverse=True)
        return all_keywords

    def _process_keyword_batch(self, keywords: List[str], category: str) -> List[KeywordData]:
        """处理一批关键词"""
        try:
            # 构建查询
            self.pytrends.build_payload(
                keywords,
                timeframe='now 7-d',  # 最近7天
                geo=self.region
            )

            # 获取兴趣时间线
            interest_data = self.pytrends.interest_over_time()

            # 获取相关查询
            try:
                related_queries = self.pytrends.related_queries()
            except:
                related_queries = {}

            batch_keywords = []

            for keyword in keywords:
                try:
                    # 计算趋势评分
                    trend_score = self._calculate_trend_score(keyword, interest_data, related_queries)

                    # 生成关键词变体
                    variations = self._generate_keyword_variations(keyword, related_queries.get(keyword, {}))

                    for variation in variations:
                        keyword_data = KeywordData(
                            keyword=variation,
                            source=self.source_name,
                            category=category,
                            confidence=trend_score,
                            search_volume=self._estimate_search_volume(variation, trend_score),
                            trend_score=trend_score,
                            metadata={
                                'base_keyword': keyword,
                                'trend_region': self.region,
                                'timeframe': 'now 7-d',
                                'timestamp': datetime.now()
                            }
                        )
                        batch_keywords.append(keyword_data)

                except Exception as e:
                    self.logger.debug(f"处理关键词失败 {keyword}: {e}")
                    continue

            return batch_keywords

        except Exception as e:
            if '429' in str(e) or 'quota' in str(e).lower():
                raise DataSourceRateLimitError(f"Google Trends频率限制: {e}")
            else:
                raise DataSourceConnectionError(f"Google Trends查询失败: {e}")

    def _calculate_trend_score(self, keyword: str, interest_data, related_queries: Dict) -> float:
        """计算趋势评分"""
        score = 0.0

        try:
            # 兴趣时间线评分
            if not interest_data.empty and keyword in interest_data.columns:
                values = interest_data[keyword].dropna()
                if len(values) >= 2:
                    # 计算增长趋势
                    recent_avg = values.tail(3).mean()
                    overall_avg = values.mean()

                    if overall_avg > 0:
                        growth_rate = (recent_avg - overall_avg) / overall_avg
                        score += min(0.4, max(0, 0.2 + growth_rate * 0.2))

                    # 绝对兴趣值
                    max_interest = values.max()
                    score += min(0.3, max_interest / 100.0 * 0.3)

            # 相关查询评分
            if related_queries:
                rising_queries = related_queries.get('rising')
                top_queries = related_queries.get('top')

                if rising_queries is not None and not rising_queries.empty:
                    score += 0.2  # 有rising查询说明趋势上升

                if top_queries is not None and not top_queries.empty:
                    score += 0.1  # 有top查询说明搜索热度高

        except Exception as e:
            self.logger.debug(f"计算趋势评分失败 {keyword}: {e}")

        return min(1.0, max(0.0, score))

    def _generate_keyword_variations(self, base_keyword: str, related_data: Dict) -> List[str]:
        """生成关键词变体"""
        variations = [base_keyword]

        try:
            # 从相关查询中提取变体
            top_queries = related_data.get('top')
            if top_queries is not None and not top_queries.empty:
                # 取前3个相关查询
                for query in top_queries['query'].head(3):
                    if isinstance(query, str) and query.lower() != base_keyword.lower():
                        variations.append(query)

            # 添加常见商业修饰词
            commercial_modifiers = ['best', '2025', 'review', 'buy']
            for modifier in commercial_modifiers[:2]:
                variations.append(f"{modifier} {base_keyword}")

        except Exception as e:
            self.logger.debug(f"生成关键词变体失败 {base_keyword}: {e}")

        return variations[:5]  # 限制变体数量

    def _fetch_trending_topics(self, base_keywords: List[str], category: str) -> List[TopicData]:
        """获取趋势话题"""
        all_topics = []

        for keyword in base_keywords[:3]:  # 限制关键词数量
            try:
                # 获取相关话题
                self.pytrends.build_payload([keyword], timeframe='now 7-d', geo=self.region)

                try:
                    related_topics = self.pytrends.related_topics()

                    if keyword in related_topics:
                        topics_data = related_topics[keyword]

                        # 处理top topics
                        top_topics = topics_data.get('top')
                        if top_topics is not None and not top_topics.empty:
                            for _, topic_row in top_topics.head(3).iterrows():
                                topic_data = TopicData(
                                    title=topic_row.get('topic_title', ''),
                                    source=self.source_name,
                                    category=category,
                                    content=f"Google Trends话题: {topic_row.get('topic_title', '')}",
                                    trending_score=topic_row.get('value', 0) / 100.0,
                                    keywords=[keyword],
                                    metadata={
                                        'topic_mid': topic_row.get('topic_mid', ''),
                                        'topic_type': topic_row.get('topic_type', ''),
                                        'base_keyword': keyword,
                                        'region': self.region
                                    }
                                )
                                all_topics.append(topic_data)

                except Exception as e:
                    self.logger.debug(f"获取相关话题失败 {keyword}: {e}")

                # 请求间隔
                self._wait_for_rate_limit()

            except Exception as e:
                self.logger.warning(f"处理话题关键词失败 {keyword}: {e}")
                continue

        return all_topics

    def _estimate_search_volume(self, keyword: str, trend_score: float) -> int:
        """基于趋势评分估算搜索量"""
        # 基础搜索量
        base_volume = 1000

        # 根据趋势评分调整
        volume_multiplier = 1 + (trend_score * 2)  # 趋势评分越高，搜索量越大

        # 根据关键词长度调整
        word_count = len(keyword.split())
        if word_count == 1:
            volume_multiplier *= 1.5
        elif word_count > 3:
            volume_multiplier *= 0.7

        estimated_volume = int(base_volume * volume_multiplier)
        return max(100, estimated_volume)

    def _wait_for_rate_limit(self):
        """等待以避免频率限制"""
        delay = self.request_delay + random.uniform(0, 2)  # 添加随机延迟
        time.sleep(delay)

    def _get_fallback_keywords(self, category: str, limit: int) -> List[KeywordData]:
        """获取备用关键词（当API失败时）"""
        fallback_keywords = []

        # 获取分类的基础关键词
        base_keywords = self.smart_home_categories.get(category, [])
        if category == 'all':
            base_keywords = ['smart home', 'home automation', 'iot device', 'smart device']

        for keyword in base_keywords[:limit]:
            keyword_data = KeywordData(
                keyword=keyword,
                source=self.source_name,
                category=category,
                confidence=0.5,  # 默认置信度
                search_volume=1000,  # 默认搜索量
                trend_score=0.5,  # 默认趋势评分
                metadata={
                    'fallback': True,
                    'reason': 'API_UNAVAILABLE'
                }
            )
            fallback_keywords.append(keyword_data)

        return fallback_keywords