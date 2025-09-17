"""
数据源统一接口定义
定义了数据源管理器和工厂类
"""

from typing import List, Dict, Type, Optional, Any
from .data_source import DataSource, KeywordData, TopicData, DataSourceError
import logging


class DataSourceRegistry:
    """数据源注册表"""

    _sources: Dict[str, Type[DataSource]] = {}

    @classmethod
    def register(cls, name: str, source_class: Type[DataSource]):
        """注册数据源"""
        cls._sources[name] = source_class
        logging.getLogger(__name__).info(f"注册数据源: {name}")

    @classmethod
    def get_source_class(cls, name: str) -> Type[DataSource]:
        """获取数据源类"""
        if name not in cls._sources:
            raise DataSourceError(f"未知数据源: {name}")
        return cls._sources[name]

    @classmethod
    def list_sources(cls) -> List[str]:
        """列出所有已注册的数据源"""
        return list(cls._sources.keys())


class DataSourceManager:
    """数据源管理器"""

    def __init__(self, config: Dict[str, Any], cache_manager=None):
        """
        初始化数据源管理器

        Args:
            config: 全局配置
            cache_manager: 缓存管理器
        """
        self.config = config
        self.cache_manager = cache_manager
        self.sources: Dict[str, DataSource] = {}
        self.logger = logging.getLogger(__name__)

        # 初始化可用的数据源
        self._initialize_sources()

    def _initialize_sources(self):
        """初始化所有可用的数据源"""
        source_configs = self.config.get('data_sources', {})

        for source_name in DataSourceRegistry.list_sources():
            if source_name in source_configs and source_configs[source_name].get('enabled', False):
                try:
                    source_class = DataSourceRegistry.get_source_class(source_name)
                    source_config = source_configs[source_name]

                    source = source_class(source_config, self.cache_manager)

                    # 健康检查
                    if source.health_check():
                        self.sources[source_name] = source
                        self.logger.info(f"数据源初始化成功: {source_name}")
                    else:
                        self.logger.warning(f"数据源健康检查失败: {source_name}")

                except Exception as e:
                    self.logger.error(f"数据源初始化失败 {source_name}: {e}")

    def get_keywords(self, category: str, limit: int = 20, sources: Optional[List[str]] = None, **kwargs) -> List[KeywordData]:
        """
        从多个数据源获取关键词

        Args:
            category: 分类
            limit: 总数量限制
            sources: 指定数据源列表，如果为None则使用所有可用源
            **kwargs: 其他参数

        Returns:
            聚合的关键词数据
        """
        if sources is None:
            sources = list(self.sources.keys())

        # 按源分配数量限制
        per_source_limit = max(1, limit // len(sources))
        all_keywords = []

        for source_name in sources:
            if source_name not in self.sources:
                self.logger.warning(f"数据源不可用: {source_name}")
                continue

            try:
                source = self.sources[source_name]
                keywords = source.get_keywords_cached(
                    category=category,
                    limit=per_source_limit,
                    **kwargs
                )
                all_keywords.extend(keywords)

            except Exception as e:
                self.logger.error(f"从 {source_name} 获取关键词失败: {e}")

        # 去重并排序
        unique_keywords = self._deduplicate_keywords(all_keywords)
        return unique_keywords[:limit]

    def get_topics(self, category: str, limit: int = 10, sources: Optional[List[str]] = None, **kwargs) -> List[TopicData]:
        """
        从多个数据源获取话题

        Args:
            category: 分类
            limit: 总数量限制
            sources: 指定数据源列表
            **kwargs: 其他参数

        Returns:
            聚合的话题数据
        """
        if sources is None:
            sources = list(self.sources.keys())

        per_source_limit = max(1, limit // len(sources))
        all_topics = []

        for source_name in sources:
            if source_name not in self.sources:
                self.logger.warning(f"数据源不可用: {source_name}")
                continue

            try:
                source = self.sources[source_name]
                topics = source.get_topics_cached(
                    category=category,
                    limit=per_source_limit,
                    **kwargs
                )
                all_topics.extend(topics)

            except Exception as e:
                self.logger.error(f"从 {source_name} 获取话题失败: {e}")

        # 去重并排序
        unique_topics = self._deduplicate_topics(all_topics)
        return unique_topics[:limit]

    def _deduplicate_keywords(self, keywords: List[KeywordData]) -> List[KeywordData]:
        """关键词去重"""
        seen = set()
        unique = []

        for kw in keywords:
            kw_lower = kw.keyword.lower().strip()
            if kw_lower not in seen:
                seen.add(kw_lower)
                unique.append(kw)

        # 按置信度排序
        return sorted(unique, key=lambda x: x.confidence, reverse=True)

    def _deduplicate_topics(self, topics: List[TopicData]) -> List[TopicData]:
        """话题去重"""
        seen = set()
        unique = []

        for topic in topics:
            # 使用标题和URL作为去重标识
            identifier = f"{topic.title.lower().strip()}|{topic.url or ''}"
            if identifier not in seen:
                seen.add(identifier)
                unique.append(topic)

        # 按trending_score排序
        return sorted(unique, key=lambda x: x.trending_score or 0, reverse=True)

    def get_source_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有数据源状态"""
        status = {}

        for name, source in self.sources.items():
            status[name] = source.get_source_info()

        return status

    def reload_source(self, source_name: str) -> bool:
        """重新加载指定数据源"""
        try:
            if source_name in self.sources:
                del self.sources[source_name]

            source_config = self.config.get('data_sources', {}).get(source_name, {})
            if not source_config.get('enabled', False):
                return False

            source_class = DataSourceRegistry.get_source_class(source_name)
            source = source_class(source_config, self.cache_manager)

            if source.health_check():
                self.sources[source_name] = source
                self.logger.info(f"数据源重新加载成功: {source_name}")
                return True
            else:
                self.logger.warning(f"数据源健康检查失败: {source_name}")
                return False

        except Exception as e:
            self.logger.error(f"重新加载数据源失败 {source_name}: {e}")
            return False