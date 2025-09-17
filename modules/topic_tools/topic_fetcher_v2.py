"""
话题获取器 V2 - 基于新数据源架构
使用统一的数据源管理器获取话题数据
"""

import os
import sys
import yaml
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path

# 导入编码处理器
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
try:
    from modules.utils.encoding_handler import safe_print
except ImportError:
    def safe_print(text, **kwargs):
        print(text, **kwargs)

# 导入新的数据源架构
from modules.data_sources.factory import register_all_sources
from modules.data_sources.base import DataSourceManager, DataSourceRegistry
from modules.cache import CacheManager


class TopicFetcherV2:
    """
    话题获取器 V2
    基于新的数据源架构，通过统一接口获取话题
    """

    def __init__(self, config_path: Optional[str] = None, cache_manager: Optional[CacheManager] = None):
        """
        初始化话题获取器

        Args:
            config_path: 配置文件路径
            cache_manager: 缓存管理器
        """
        self.logger = logging.getLogger(__name__)

        # 注册所有数据源
        register_all_sources()

        # 加载配置
        self.config = self._load_config(config_path)

        # 初始化缓存管理器
        self.cache_manager = cache_manager or CacheManager(cache_dir="data/topic_cache")

        # 初始化数据源管理器
        try:
            self.ds_manager = DataSourceManager(self.config, self.cache_manager)
            self.logger.info("话题获取器V2初始化成功")
        except Exception as e:
            self.logger.error(f"数据源管理器初始化失败: {e}")
            raise

        # 智能家居分类定义
        self.categories = [
            'smart_plugs', 'security_cameras', 'robot_vacuums',
            'smart_speakers', 'smart_lighting', 'smart_thermostats',
            'smart_locks', 'general'
        ]

        # 话题分析权重配置
        self.topic_weights = {
            'trending_score': 0.4,      # 趋势得分
            'engagement': 0.3,          # 互动量
            'freshness': 0.2,           # 时间新鲜度
            'relevance': 0.1           # 相关性
        }

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """加载配置文件"""
        if config_path is None:
            # 尝试多个默认配置文件位置
            possible_paths = [
                "config/data_sources.yml",
                "config/data_sources_test.yml",
                "keyword_engine.yml"
            ]

            for path in possible_paths:
                if os.path.exists(path):
                    config_path = path
                    break
            else:
                self.logger.warning("未找到配置文件，使用默认配置")
                return self._get_default_config()

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            self.logger.info(f"配置文件加载成功: {config_path}")
            return config
        except Exception as e:
            self.logger.error(f"配置文件加载失败: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'data_sources': {
                'rss': {
                    'enabled': True,
                    'max_age_hours': 24,
                    'min_relevance': 0.3,
                    'request_timeout': 10,
                    'request_delay': 1,
                    'feeds': {
                        'techcrunch': {
                            'url': 'https://techcrunch.com/feed/',
                            'name': 'TechCrunch',
                            'smart_home_keywords': ['smart home', 'iot', 'smart tech']
                        }
                    }
                },
                'google_trends': {
                    'enabled': False,
                    'request_delay': 3,
                    'region': 'US'
                },
                'reddit': {
                    'enabled': False,
                    'client_id': '',
                    'client_secret': '',
                    'user_agent': 'TopicAnalyzer/1.0'
                }
            }
        }

    def fetch_topics_by_category(self, category: str, limit: int = 10,
                                 sources: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        按分类获取话题

        Args:
            category: 分类名称 ('smart_plugs', 'all', etc.)
            limit: 数量限制
            sources: 指定数据源列表

        Returns:
            话题数据列表
        """
        try:
            # 使用数据源管理器获取话题
            topic_data = self.ds_manager.get_topics(
                category=category,
                limit=limit,
                sources=sources
            )

            # 转换为传统格式以保持兼容性
            topics = []
            for topic_data_item in topic_data:
                topic_dict = {
                    'title': topic_data_item.title,
                    'content': topic_data_item.content,
                    'url': topic_data_item.url,
                    'category': topic_data_item.category,
                    'source': topic_data_item.source,
                    'trending_score': topic_data_item.trending_score,
                    'engagement': topic_data_item.engagement,
                    'keywords': topic_data_item.keywords or [],
                    'timestamp': topic_data_item.timestamp,
                    'metadata': topic_data_item.metadata or {}
                }
                topics.append(topic_dict)

            self.logger.info(f"获取到 {len(topics)} 个话题 (分类: {category})")
            return topics

        except Exception as e:
            self.logger.error(f"获取话题失败: {e}")
            return []

    def fetch_trending_topics(self, limit: int = 10, min_trending_score: float = 0.5) -> List[Dict[str, Any]]:
        """
        获取趋势话题

        Args:
            limit: 数量限制
            min_trending_score: 最小趋势得分

        Returns:
            趋势话题列表
        """
        try:
            # 获取所有话题
            all_topics = self.fetch_topics_by_category('all', limit * 2)

            # 过滤和排序
            trending_topics = [
                topic for topic in all_topics
                if topic.get('trending_score', 0) >= min_trending_score
            ]

            # 按综合得分排序
            trending_topics.sort(key=lambda x: self._calculate_composite_score(x), reverse=True)

            # 添加趋势分析
            for topic in trending_topics[:limit]:
                topic['trend_analysis'] = self._analyze_topic_trend(topic)

            self.logger.info(f"获取到 {len(trending_topics[:limit])} 个趋势话题")
            return trending_topics[:limit]

        except Exception as e:
            self.logger.error(f"获取趋势话题失败: {e}")
            return []

    def fetch_topics_multi_category(self, categories: List[str],
                                    limit_per_category: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取多个分类的话题

        Args:
            categories: 分类列表
            limit_per_category: 每个分类的数量限制

        Returns:
            按分类组织的话题数据
        """
        results = {}

        for category in categories:
            try:
                topics = self.fetch_topics_by_category(category, limit_per_category)
                results[category] = topics
                self.logger.info(f"分类 {category}: {len(topics)} 个话题")
            except Exception as e:
                self.logger.error(f"获取分类话题失败 {category}: {e}")
                results[category] = []

        return results

    def analyze_topic_keywords(self, topics: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        分析话题中的关键词频率

        Args:
            topics: 话题列表

        Returns:
            关键词频率统计
        """
        keyword_count = {}

        for topic in topics:
            keywords = topic.get('keywords', [])
            for keyword in keywords:
                if isinstance(keyword, str):
                    keyword_count[keyword] = keyword_count.get(keyword, 0) + 1

        # 按频率排序
        sorted_keywords = dict(sorted(keyword_count.items(), key=lambda x: x[1], reverse=True))

        self.logger.info(f"分析了 {len(topics)} 个话题，发现 {len(sorted_keywords)} 个关键词")
        return sorted_keywords

    def get_topic_insights(self, topics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取话题洞察

        Args:
            topics: 话题列表

        Returns:
            话题洞察数据
        """
        if not topics:
            return {}

        insights = {
            'total_topics': len(topics),
            'avg_trending_score': sum(t.get('trending_score', 0) for t in topics) / len(topics),
            'avg_engagement': sum(t.get('engagement', 0) for t in topics) / len(topics),
            'source_distribution': {},
            'category_distribution': {},
            'top_keywords': {},
            'trend_patterns': {}
        }

        # 数据源分布
        for topic in topics:
            source = topic.get('source', 'unknown')
            insights['source_distribution'][source] = insights['source_distribution'].get(source, 0) + 1

        # 分类分布
        for topic in topics:
            category = topic.get('category', 'unknown')
            insights['category_distribution'][category] = insights['category_distribution'].get(category, 0) + 1

        # 关键词分析
        insights['top_keywords'] = dict(list(self.analyze_topic_keywords(topics).items())[:10])

        # 趋势模式分析
        insights['trend_patterns'] = self._analyze_trend_patterns(topics)

        self.logger.info("话题洞察分析完成")
        return insights

    def export_topics(self, topics: List[Dict[str, Any]], output_file: str) -> str:
        """
        导出话题到文件

        Args:
            topics: 话题列表
            output_file: 输出文件路径

        Returns:
            实际输出文件路径
        """
        try:
            # 确保输出目录存在
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # 如果没有扩展名，添加.json
            if not output_path.suffix:
                output_path = output_path.with_suffix('.json')

            # 导出为JSON格式
            import json
            export_data = {
                'export_time': datetime.now().isoformat(),
                'total_topics': len(topics),
                'insights': self.get_topic_insights(topics),
                'topics': topics
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

            self.logger.info(f"话题已导出到: {output_path}")
            return str(output_path)

        except Exception as e:
            self.logger.error(f"导出话题失败: {e}")
            raise

    def get_source_status(self) -> Dict[str, Dict[str, Any]]:
        """获取数据源状态"""
        try:
            return self.ds_manager.get_source_status()
        except Exception as e:
            self.logger.error(f"获取数据源状态失败: {e}")
            return {}

    def get_available_categories(self) -> List[str]:
        """获取可用的分类列表"""
        return self.categories.copy()

    def get_available_sources(self) -> List[str]:
        """获取可用的数据源列表"""
        return DataSourceRegistry.list_sources()

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            return self.cache_manager.get_stats()
        except Exception as e:
            self.logger.error(f"获取缓存统计失败: {e}")
            return {}

    def clear_cache(self) -> bool:
        """清空缓存"""
        try:
            self.cache_manager.clear()
            self.logger.info("缓存已清空")
            return True
        except Exception as e:
            self.logger.error(f"清空缓存失败: {e}")
            return False

    def _calculate_composite_score(self, topic: Dict[str, Any]) -> float:
        """计算话题综合得分"""
        trending_score = topic.get('trending_score', 0)
        engagement = min(1.0, topic.get('engagement', 0) / 100.0)  # 归一化互动量

        # 计算时间新鲜度
        timestamp = topic.get('timestamp')
        if timestamp:
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            hours_old = (datetime.now() - timestamp.replace(tzinfo=None)).total_seconds() / 3600
            freshness = max(0, 1 - (hours_old / 168))  # 一周内的内容
        else:
            freshness = 0.5

        # 相关性基于关键词数量
        relevance = min(1.0, len(topic.get('keywords', [])) / 5.0)

        # 加权计算综合得分
        composite_score = (
                trending_score * self.topic_weights['trending_score'] +
                engagement * self.topic_weights['engagement'] +
                freshness * self.topic_weights['freshness'] +
                relevance * self.topic_weights['relevance']
        )

        return composite_score

    def _analyze_topic_trend(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        """分析话题趋势"""
        analysis = {
            'trend_direction': 'stable',
            'confidence': 'medium',
            'factors': []
        }

        trending_score = topic.get('trending_score', 0)
        engagement = topic.get('engagement', 0)

        # 趋势方向判断
        if trending_score > 0.7:
            analysis['trend_direction'] = 'rising'
            analysis['confidence'] = 'high'
            analysis['factors'].append('高趋势得分')
        elif trending_score < 0.3:
            analysis['trend_direction'] = 'declining'
            analysis['factors'].append('低趋势得分')

        # 互动量影响
        if engagement > 50:
            analysis['factors'].append('高互动量')
            if analysis['trend_direction'] == 'stable':
                analysis['trend_direction'] = 'rising'
        elif engagement < 10:
            analysis['factors'].append('低互动量')

        # 关键词相关性
        keywords = topic.get('keywords', [])
        if len(keywords) >= 3:
            analysis['factors'].append('丰富关键词')

        return analysis

    def _analyze_trend_patterns(self, topics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析趋势模式"""
        patterns = {
            'rising_count': 0,
            'stable_count': 0,
            'declining_count': 0,
            'high_engagement_topics': 0,
            'recent_topics': 0
        }

        now = datetime.now()

        for topic in topics:
            # 趋势方向统计
            trending_score = topic.get('trending_score', 0)
            if trending_score > 0.6:
                patterns['rising_count'] += 1
            elif trending_score < 0.4:
                patterns['declining_count'] += 1
            else:
                patterns['stable_count'] += 1

            # 高互动话题
            if topic.get('engagement', 0) > 50:
                patterns['high_engagement_topics'] += 1

            # 最近话题
            timestamp = topic.get('timestamp')
            if timestamp:
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                hours_old = (now - timestamp.replace(tzinfo=None)).total_seconds() / 3600
                if hours_old < 24:
                    patterns['recent_topics'] += 1

        return patterns


# 向后兼容性: 提供旧接口
class TopicFetcher(TopicFetcherV2):
    """向后兼容的话题获取器"""
    pass


# 示例使用
if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    safe_print("=== 话题获取器V2测试 ===\n")

    try:
        # 创建话题获取器
        fetcher = TopicFetcherV2()

        # 检查数据源状态
        safe_print("--- 数据源状态 ---")
        status = fetcher.get_source_status()
        for source_name, info in status.items():
            safe_print(f"{source_name}: {'✅ 可用' if info['healthy'] else '❌ 不可用'}")

        safe_print()

        # 获取一般智能家居话题
        safe_print("--- 智能家居话题 ---")
        topics = fetcher.fetch_topics_by_category('general', limit=3)

        for i, topic in enumerate(topics, 1):
            safe_print(f"{i}. {topic['title']}")
            safe_print(f"   来源: {topic['source']}")
            safe_print(f"   趋势得分: {topic.get('trending_score', 0):.2f}")
            safe_print(f"   互动量: {topic.get('engagement', 0)}")
            if topic.get('keywords'):
                safe_print(f"   关键词: {', '.join(topic['keywords'][:3])}")
            safe_print()

        # 获取趋势话题
        safe_print("--- 趋势话题 ---")
        trending = fetcher.fetch_trending_topics(limit=2)

        for i, topic in enumerate(trending, 1):
            safe_print(f"{i}. {topic['title']}")
            trend_analysis = topic.get('trend_analysis', {})
            safe_print(f"   趋势: {trend_analysis.get('trend_direction', 'unknown')}")
            safe_print(f"   置信度: {trend_analysis.get('confidence', 'unknown')}")
            safe_print()

        # 话题洞察
        if topics:
            safe_print("--- 话题洞察 ---")
            insights = fetcher.get_topic_insights(topics)
            safe_print(f"平均趋势得分: {insights.get('avg_trending_score', 0):.2f}")
            safe_print(f"平均互动量: {insights.get('avg_engagement', 0):.0f}")

            top_keywords = insights.get('top_keywords', {})
            if top_keywords:
                safe_print("热门关键词:")
                for keyword, count in list(top_keywords.items())[:3]:
                    safe_print(f"  - {keyword}: {count}次")

        safe_print("\n✅ 话题获取器V2测试完成！")

    except Exception as e:
        safe_print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()