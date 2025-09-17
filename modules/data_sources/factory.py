"""
数据源工厂
管理所有数据源的注册和初始化
"""

from .base import DataSourceRegistry
from .rss import RSSSource
from .google_trends import GoogleTrendsSource
from .reddit import RedditSource


def register_all_sources():
    """注册所有可用的数据源"""
    # 注册RSS数据源
    DataSourceRegistry.register('rss', RSSSource)

    # 注册Google Trends数据源
    DataSourceRegistry.register('google_trends', GoogleTrendsSource)

    # 注册Reddit数据源
    DataSourceRegistry.register('reddit', RedditSource)

    # TODO: 注册其他数据源
    # DataSourceRegistry.register('youtube', YouTubeSource)
    # DataSourceRegistry.register('amazon', AmazonSource)


# 自动注册所有数据源
register_all_sources()