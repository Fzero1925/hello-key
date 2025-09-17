"""
关键词获取器 V2 - 基于新数据源架构
使用统一的数据源管理器获取关键词数据
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


class KeywordFetcherV2:
    """
    关键词获取器 V2
    基于新的数据源架构，通过统一接口获取关键词
    """

    def __init__(self, config_path: Optional[str] = None, cache_manager: Optional[CacheManager] = None):
        """
        初始化关键词获取器

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
        self.cache_manager = cache_manager or CacheManager(cache_dir="data/keyword_cache")

        # 初始化数据源管理器
        try:
            self.ds_manager = DataSourceManager(self.config, self.cache_manager)
            self.logger.info("关键词获取器V2初始化成功")
        except Exception as e:
            self.logger.error(f"数据源管理器初始化失败: {e}")
            raise

        # 智能家居分类定义
        self.categories = [
            'smart_plugs', 'security_cameras', 'robot_vacuums',
            'smart_speakers', 'smart_lighting', 'smart_thermostats',
            'smart_locks', 'general'
        ]

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
                    'enabled': False,  # 默认禁用，避免频率限制
                    'request_delay': 3,
                    'region': 'US'
                },
                'reddit': {
                    'enabled': False,  # 需要API配置
                    'client_id': '',
                    'client_secret': '',
                    'user_agent': 'KeywordAnalyzer/1.0'
                }
            }
        }

    def fetch_keywords_by_category(self, category: str, limit: int = 20,
                                   sources: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        按分类获取关键词

        Args:
            category: 分类名称 ('smart_plugs', 'all', etc.)
            limit: 数量限制
            sources: 指定数据源列表

        Returns:
            关键词数据列表
        """
        try:
            # 使用数据源管理器获取关键词
            keyword_data = self.ds_manager.get_keywords(
                category=category,
                limit=limit,
                sources=sources
            )

            # 转换为传统格式以保持兼容性
            keywords = []
            for kw_data in keyword_data:
                keyword_dict = {
                    'keyword': kw_data.keyword,
                    'category': kw_data.category,
                    'source': kw_data.source,
                    'confidence': kw_data.confidence,
                    'search_volume': kw_data.search_volume,
                    'trend_score': kw_data.trend_score,
                    'timestamp': kw_data.timestamp,
                    'metadata': kw_data.metadata or {}
                }
                keywords.append(keyword_dict)

            self.logger.info(f"获取到 {len(keywords)} 个关键词 (分类: {category})")
            return keywords

        except Exception as e:
            self.logger.error(f"获取关键词失败: {e}")
            return []

    def fetch_all_sources(self, category: str = 'all', limit: int = 50) -> List[Dict[str, Any]]:
        """
        从所有可用数据源获取关键词

        Args:
            category: 分类名称
            limit: 总数量限制

        Returns:
            关键词数据列表
        """
        return self.fetch_keywords_by_category(category, limit)

    def fetch_keywords_multi_category(self, categories: List[str],
                                      limit_per_category: int = 10) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取多个分类的关键词

        Args:
            categories: 分类列表
            limit_per_category: 每个分类的数量限制

        Returns:
            按分类组织的关键词数据
        """
        results = {}

        for category in categories:
            try:
                keywords = self.fetch_keywords_by_category(category, limit_per_category)
                results[category] = keywords
                self.logger.info(f"分类 {category}: {len(keywords)} 个关键词")
            except Exception as e:
                self.logger.error(f"获取分类关键词失败 {category}: {e}")
                results[category] = []

        return results

    def get_trending_keywords(self, limit: int = 20,
                              timeframe: str = '24h') -> List[Dict[str, Any]]:
        """
        获取趋势关键词

        Args:
            limit: 数量限制
            timeframe: 时间范围

        Returns:
            趋势关键词列表
        """
        try:
            # 获取所有关键词并按趋势得分排序
            all_keywords = self.fetch_keywords_by_category('all', limit * 2)

            # 按趋势得分排序
            trending_keywords = sorted(
                all_keywords,
                key=lambda x: x.get('trend_score', 0),
                reverse=True
            )

            # 添加趋势相关信息
            for kw in trending_keywords[:limit]:
                kw['trending_reason'] = self._generate_trending_reason(kw)

            self.logger.info(f"获取到 {len(trending_keywords[:limit])} 个趋势关键词")
            return trending_keywords[:limit]

        except Exception as e:
            self.logger.error(f"获取趋势关键词失败: {e}")
            return []

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

    def export_keywords(self, keywords: List[Dict[str, Any]],
                        output_file: str) -> str:
        """
        导出关键词到文件

        Args:
            keywords: 关键词列表
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
                'total_keywords': len(keywords),
                'keywords': keywords
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

            self.logger.info(f"关键词已导出到: {output_path}")
            return str(output_path)

        except Exception as e:
            self.logger.error(f"导出关键词失败: {e}")
            raise

    def _generate_trending_reason(self, keyword_data: Dict[str, Any]) -> str:
        """生成趋势原因说明"""
        source = keyword_data.get('source', 'unknown')
        trend_score = keyword_data.get('trend_score', 0)
        metadata = keyword_data.get('metadata', {})

        if source == 'rss':
            feed_name = metadata.get('feed_name', '新闻源')
            return f"在{feed_name}中热度上升 (趋势得分: {trend_score:.2f})"
        elif source == 'reddit':
            subreddit = metadata.get('subreddit', 'Reddit')
            score = metadata.get('score', 0)
            return f"Reddit r/{subreddit} 热门讨论 (得分: {score})"
        elif source == 'google_trends':
            return f"Google搜索趋势上升 (趋势得分: {trend_score:.2f})"
        else:
            return f"多源数据显示热度上升 (得分: {trend_score:.2f})"


# 向后兼容性: 提供旧接口
class KeywordFetcher(KeywordFetcherV2):
    """向后兼容的关键词获取器"""
    pass


# 示例使用
if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    safe_print("=== 关键词获取器V2测试 ===\n")

    try:
        # 创建关键词获取器
        fetcher = KeywordFetcherV2()

        # 检查数据源状态
        safe_print("--- 数据源状态 ---")
        status = fetcher.get_source_status()
        for source_name, info in status.items():
            safe_print(f"{source_name}: {'✅ 可用' if info['healthy'] else '❌ 不可用'}")

        safe_print()

        # 获取智能插座关键词
        safe_print("--- 智能插座关键词 ---")
        smart_plug_keywords = fetcher.fetch_keywords_by_category('smart_plugs', limit=5)

        for i, kw in enumerate(smart_plug_keywords, 1):
            safe_print(f"{i}. {kw['keyword']}")
            safe_print(f"   来源: {kw['source']}")
            safe_print(f"   置信度: {kw['confidence']:.2f}")
            safe_print(f"   搜索量: {kw.get('search_volume', 'N/A')}")
            safe_print()

        # 获取趋势关键词
        safe_print("--- 趋势关键词 ---")
        trending = fetcher.get_trending_keywords(limit=3)

        for i, kw in enumerate(trending, 1):
            safe_print(f"{i}. {kw['keyword']}")
            safe_print(f"   原因: {kw['trending_reason']}")
            safe_print()

        # 缓存统计
        cache_stats = fetcher.get_cache_stats()
        safe_print(f"--- 缓存统计 ---")
        safe_print(f"内存缓存: {cache_stats.get('memory_cache_count', 0)} 条目")
        safe_print(f"文件缓存: {cache_stats.get('file_cache_count', 0)} 条目")

        safe_print("\n✅ 关键词获取器V2测试完成！")

    except Exception as e:
        safe_print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()