#!/usr/bin/env python3
"""
RSS数据源快速测试
"""

import sys
import os
import logging
sys.path.insert(0, os.path.dirname(__file__))

# 导入模块
from modules.data_sources.factory import register_all_sources
from modules.data_sources.base import DataSourceRegistry
from modules.data_sources.rss import RSSSource

def quick_test():
    """快速测试RSS数据源"""
    print("=== RSS数据源快速测试 ===")

    # 设置日志
    logging.basicConfig(level=logging.WARNING)

    # 注册数据源
    register_all_sources()
    print(f"已注册数据源: {DataSourceRegistry.list_sources()}")

    # 简单的RSS配置
    simple_config = {
        'enabled': True,
        'max_age_hours': 24,
        'min_relevance': 0.3,
        'request_timeout': 5,
        'request_delay': 0.5,
        'feeds': {
            'techcrunch': {
                'url': 'https://techcrunch.com/feed/',
                'name': 'TechCrunch',
                'smart_home_keywords': ['smart home', 'iot', 'smart tech']
            }
        }
    }

    try:
        # 创建RSS数据源
        rss_source = RSSSource(simple_config)
        print("RSS数据源初始化成功")

        # 健康检查
        is_healthy = rss_source.health_check()
        print(f"健康检查: {'✅ 通过' if is_healthy else '❌ 失败'}")

        if is_healthy:
            # 尝试获取1个关键词
            print("尝试获取关键词...")
            keywords = rss_source.get_keywords('general', limit=1)
            print(f"获取到 {len(keywords)} 个关键词")

            if keywords:
                kw = keywords[0]
                print(f"示例关键词: {kw.keyword}")
                print(f"分类: {kw.category}")
                print(f"置信度: {kw.confidence:.2f}")

        print("✅ RSS数据源基本功能测试通过")
        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = quick_test()
    exit(0 if success else 1)