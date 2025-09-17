"""
数据源基类定义
所有数据源都需要继承此基类并实现抽象方法
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging


@dataclass
class KeywordData:
    """关键词数据标准格式"""
    keyword: str
    source: str
    category: str
    confidence: float  # 0-1, 关键词相关性置信度
    search_volume: Optional[int] = None
    trend_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class TopicData:
    """话题数据标准格式"""
    title: str
    source: str
    category: str
    content: str
    url: Optional[str] = None
    engagement: Optional[int] = None  # 点赞、评论等互动数据
    trending_score: Optional[float] = None
    keywords: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class DataSourceError(Exception):
    """数据源异常基类"""
    pass


class DataSourceConfigError(DataSourceError):
    """数据源配置错误"""
    pass


class DataSourceConnectionError(DataSourceError):
    """数据源连接错误"""
    pass


class DataSourceRateLimitError(DataSourceError):
    """数据源频率限制错误"""
    pass


class DataSource(ABC):
    """
    数据源抽象基类
    所有数据源都需要继承此类并实现抽象方法
    """

    def __init__(self, config: Dict[str, Any], cache_manager=None):
        """
        初始化数据源

        Args:
            config: 数据源配置
            cache_manager: 缓存管理器
        """
        self.config = config
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(self.__class__.__name__)
        self.source_name = self.__class__.__name__.lower().replace('source', '')

        # 验证配置
        self._validate_config()

        # 初始化数据源
        self._initialize()

    @abstractmethod
    def _validate_config(self) -> None:
        """验证配置是否正确"""
        pass

    @abstractmethod
    def _initialize(self) -> None:
        """初始化数据源连接"""
        pass

    @abstractmethod
    def get_keywords(self, category: str, limit: int = 20, **kwargs) -> List[KeywordData]:
        """
        获取关键词数据

        Args:
            category: 分类（如 smart_plugs, smart_speakers）
            limit: 数量限制
            **kwargs: 其他参数

        Returns:
            关键词数据列表
        """
        pass

    @abstractmethod
    def get_topics(self, category: str, limit: int = 10, **kwargs) -> List[TopicData]:
        """
        获取话题数据

        Args:
            category: 分类
            limit: 数量限制
            **kwargs: 其他参数

        Returns:
            话题数据列表
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        健康检查

        Returns:
            True 如果数据源正常工作
        """
        pass

    def get_source_info(self) -> Dict[str, Any]:
        """获取数据源信息"""
        return {
            'name': self.source_name,
            'class': self.__class__.__name__,
            'config_keys': list(self.config.keys()),
            'healthy': self.health_check()
        }

    def _get_cache_key(self, method: str, category: str, **kwargs) -> str:
        """生成缓存键"""
        import hashlib
        key_parts = [self.source_name, method, category]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
        key_str = "|".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """从缓存获取数据"""
        if self.cache_manager:
            return self.cache_manager.get(cache_key)
        return None

    def _save_to_cache(self, cache_key: str, data: Any, ttl: int = 3600) -> None:
        """保存数据到缓存"""
        if self.cache_manager:
            self.cache_manager.set(cache_key, data, ttl)

    def get_keywords_cached(self, category: str, limit: int = 20, cache_ttl: int = 3600, **kwargs) -> List[KeywordData]:
        """带缓存的关键词获取"""
        cache_key = self._get_cache_key('keywords', category, limit=limit, **kwargs)

        # 尝试从缓存获取
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            self.logger.debug(f"从缓存获取关键词数据: {cache_key}")
            return cached_data

        # 获取新数据
        try:
            data = self.get_keywords(category, limit, **kwargs)
            self._save_to_cache(cache_key, data, cache_ttl)
            return data
        except Exception as e:
            self.logger.error(f"获取关键词失败: {e}")
            raise

    def get_topics_cached(self, category: str, limit: int = 10, cache_ttl: int = 3600, **kwargs) -> List[TopicData]:
        """带缓存的话题获取"""
        cache_key = self._get_cache_key('topics', category, limit=limit, **kwargs)

        # 尝试从缓存获取
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            self.logger.debug(f"从缓存获取话题数据: {cache_key}")
            return cached_data

        # 获取新数据
        try:
            data = self.get_topics(category, limit, **kwargs)
            self._save_to_cache(cache_key, data, cache_ttl)
            return data
        except Exception as e:
            self.logger.error(f"获取话题失败: {e}")
            raise