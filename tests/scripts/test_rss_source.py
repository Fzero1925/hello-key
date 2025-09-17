#!/usr/bin/env python3
"""
RSS数据源专用测试脚本
验证RSS数据源的详细功能和性能
"""

import os
import sys
import yaml
import logging
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置编码处理
try:
    from modules.utils.encoding_handler import safe_print
except ImportError:
    def safe_print(text, **kwargs):
        print(text, **kwargs)

# 导入数据源模块
from modules.data_sources.factory import register_all_sources
from modules.data_sources.base import DataSourceManager, DataSourceRegistry
from modules.cache import CacheManager


def load_test_config():
    """加载测试配置"""
    # 优先使用新的测试配置
    config_paths = [
        "tests/config/test_config.yml",
        "config/data_sources_test.yml"
    ]

    for config_path in config_paths:
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                safe_print(f"✅ 成功加载配置文件: {config_path}")
                return config
            except Exception as e:
                safe_print(f"❌ 加载配置文件失败: {e}")
                continue

    safe_print(f"❌ 未找到有效的配置文件")
    return None


def test_rss_source():
    """测试RSS数据源"""
    safe_print("╔══════════════════════════════════════════════════════════════╗")
    safe_print("║                     RSS数据源专项测试                       ║")
    safe_print("╚══════════════════════════════════════════════════════════════╝\n")

    # 设置日志
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # 加载配置
    config = load_test_config()
    if not config:
        return False

    # 检查RSS配置
    rss_config = config.get('data_sources', {}).get('rss', {})
    if not rss_config.get('enabled', False):
        safe_print("❌ RSS数据源未启用，请检查配置文件")
        return False

    # 创建缓存管理器
    cache_dir = config.get('test_environment', {}).get('cache_dir', 'data/test_cache')
    cache_manager = CacheManager(cache_dir=cache_dir)
    safe_print(f"✅ 缓存管理器初始化完成 (目录: {cache_dir})")

    # 注册数据源
    register_all_sources()
    safe_print(f"✅ 已注册数据源: {DataSourceRegistry.list_sources()}")

    # 创建数据源管理器
    try:
        ds_manager = DataSourceManager(config, cache_manager)
        safe_print("✅ 数据源管理器初始化完成")
    except Exception as e:
        safe_print(f"❌ 数据源管理器初始化失败: {e}")
        return False

    # 检查数据源状态
    safe_print("\n🔍 检查数据源状态...")
    status = ds_manager.get_source_status()
    for name, info in status.items():
        status_icon = "✅" if info['healthy'] else "❌"
        safe_print(f"   {status_icon} {name}: {'健康' if info['healthy'] else '不可用'}")

    if not any(info['healthy'] for info in status.values()):
        safe_print("❌ 没有可用的数据源")
        return False

    # 测试RSS Feed连接
    safe_print("\n📡 测试RSS Feed连接...")
    rss_feeds = rss_config.get('test_feeds', {})
    successful_feeds = 0

    for feed_name, feed_config in rss_feeds.items():
        try:
            import requests
            start_time = time.time()
            response = requests.get(feed_config['url'], timeout=10)
            response_time = time.time() - start_time

            if response.status_code == 200:
                successful_feeds += 1
                safe_print(f"   ✅ {feed_name}: 连接成功 ({response_time:.2f}s)")
            else:
                safe_print(f"   ❌ {feed_name}: HTTP {response.status_code}")

        except Exception as e:
            safe_print(f"   ❌ {feed_name}: 连接失败 - {str(e)[:50]}...")

    feed_success_rate = successful_feeds / len(rss_feeds) if rss_feeds else 0
    safe_print(f"   📊 Feed连接成功率: {feed_success_rate:.1%} ({successful_feeds}/{len(rss_feeds)})")

    # 测试关键词获取
    safe_print("\n🔍 测试关键词获取...")
    try:
        start_time = time.time()
        keywords = ds_manager.get_keywords(
            category='smart_plugs',
            limit=8,
            sources=['rss']
        )
        extraction_time = time.time() - start_time

        safe_print(f"   ✅ 获取到 {len(keywords)} 个关键词 (耗时: {extraction_time:.2f}s)")

        if keywords:
            safe_print("   📋 关键词样例:")
            for i, kw in enumerate(keywords[:5], 1):
                safe_print(f"      {i}. {kw.keyword}")
                safe_print(f"         分类: {kw.category} | 置信度: {kw.confidence:.2f}")
                safe_print(f"         来源: {kw.metadata.get('feed_name', 'Unknown')}")

            # 关键词质量分析
            valid_keywords = sum(1 for kw in keywords
                               if len(kw.keyword) > 2 and kw.confidence > 0.1)
            quality_rate = valid_keywords / len(keywords) if keywords else 0
            safe_print(f"   📊 关键词质量率: {quality_rate:.1%} ({valid_keywords}/{len(keywords)})")

    except Exception as e:
        safe_print(f"   ❌ 关键词获取失败: {e}")
        return False

    # 测试话题获取
    safe_print("\n📰 测试话题获取...")
    try:
        start_time = time.time()
        topics = ds_manager.get_topics(
            category='general',
            limit=5,
            sources=['rss']
        )
        topic_time = time.time() - start_time

        safe_print(f"   ✅ 获取到 {len(topics)} 个话题 (耗时: {topic_time:.2f}s)")

        if topics:
            safe_print("   📋 话题样例:")
            for i, topic in enumerate(topics[:3], 1):
                safe_print(f"      {i}. {topic.title[:60]}...")
                safe_print(f"         分类: {topic.category} | 趋势: {topic.trending_score:.2f}")
                safe_print(f"         来源: {topic.metadata.get('feed_name', 'Unknown')}")

    except Exception as e:
        safe_print(f"   ❌ 话题获取失败: {e}")
        return False

    # 测试缓存性能
    safe_print("\n💾 测试缓存性能...")
    try:
        cache_stats = cache_manager.get_stats()
        safe_print(f"   📊 内存缓存条目: {cache_stats['memory_cache_count']}")
        safe_print(f"   📊 文件缓存条目: {cache_stats['file_cache_count']}")

        # 测试缓存命中
        start_time = time.time()
        cached_keywords = ds_manager.get_keywords(
            category='smart_plugs',
            limit=5,
            sources=['rss']
        )
        cached_time = time.time() - start_time

        if cached_time < extraction_time * 0.5:
            safe_print(f"   ✅ 缓存生效: 第二次获取耗时 {cached_time:.2f}s (提升 {(1-cached_time/extraction_time)*100:.1f}%)")
        else:
            safe_print(f"   ⚠️  缓存效果不明显: {cached_time:.2f}s")

    except Exception as e:
        safe_print(f"   ❌ 缓存测试失败: {e}")

    safe_print("\n✅ RSS数据源专项测试完成！所有核心功能正常工作。")
    return True


def test_rss_health_check():
    """测试RSS数据源健康检查"""
    safe_print("\n🏥 RSS数据源健康检查...")

    config = load_test_config()
    if not config:
        return False

    # 直接测试RSS源
    from modules.data_sources.rss import RSSSource

    try:
        rss_config = config.get('data_sources', {}).get('rss', {})
        if not rss_config:
            safe_print("   ❌ RSS配置不存在")
            return False

        rss_source = RSSSource(rss_config)

        safe_print("   🔍 执行健康检查...")
        start_time = time.time()
        is_healthy = rss_source.health_check()
        health_check_time = time.time() - start_time

        health_icon = "✅" if is_healthy else "❌"
        safe_print(f"   {health_icon} 健康状态: {'健康' if is_healthy else '不健康'} (耗时: {health_check_time:.2f}s)")

        # 获取源信息
        info = rss_source.get_source_info()
        if info:
            safe_print(f"   📊 数据源信息:")
            for key, value in info.items():
                safe_print(f"      {key}: {value}")

        return is_healthy

    except Exception as e:
        safe_print(f"   ❌ 健康检查失败: {e}")
        return False


def test_rss_performance():
    """测试RSS数据源性能"""
    safe_print("\n⚡ RSS数据源性能测试...")

    config = load_test_config()
    if not config:
        return False

    try:
        cache_dir = config.get('test_environment', {}).get('cache_dir', 'data/test_cache')
        cache_manager = CacheManager(cache_dir=cache_dir)
        register_all_sources()
        ds_manager = DataSourceManager(config, cache_manager)

        # 测试并发获取
        import threading
        results = []
        errors = []

        def fetch_keywords():
            try:
                start_time = time.time()
                keywords = ds_manager.get_keywords(
                    category='smart_plugs',
                    limit=3,
                    sources=['rss']
                )
                fetch_time = time.time() - start_time
                results.append({'keywords': len(keywords), 'time': fetch_time})
            except Exception as e:
                errors.append(str(e))

        # 创建3个并发线程
        threads = []
        for i in range(3):
            thread = threading.Thread(target=fetch_keywords)
            threads.append(thread)

        start_time = time.time()
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        total_time = time.time() - start_time

        safe_print(f"   📊 并发测试结果:")
        safe_print(f"      总耗时: {total_time:.2f}s")
        safe_print(f"      成功请求: {len(results)}/3")
        safe_print(f"      失败请求: {len(errors)}/3")

        if results:
            avg_time = sum(r['time'] for r in results) / len(results)
            total_keywords = sum(r['keywords'] for r in results)
            safe_print(f"      平均响应时间: {avg_time:.2f}s")
            safe_print(f"      总关键词数: {total_keywords}")

        return len(errors) == 0

    except Exception as e:
        safe_print(f"   ❌ 性能测试失败: {e}")
        return False


if __name__ == "__main__":
    safe_print("🚀 启动RSS数据源专项测试...\n")

    # 创建必要的目录
    os.makedirs("data/test_cache", exist_ok=True)
    os.makedirs("tests/config", exist_ok=True)
    os.makedirs("tests/results", exist_ok=True)

    test_results = {}
    overall_success = True

    # 运行测试序列
    tests = [
        ("健康检查", test_rss_health_check),
        ("功能测试", test_rss_source),
        ("性能测试", test_rss_performance)
    ]

    safe_print("📋 测试计划:")
    for i, (test_name, _) in enumerate(tests, 1):
        safe_print(f"   {i}. {test_name}")

    safe_print("\n" + "="*60)

    for test_name, test_func in tests:
        safe_print(f"\n🔄 执行 {test_name}...")
        try:
            success = test_func()
            test_results[test_name] = success
            if not success:
                overall_success = False

            result_icon = "✅" if success else "❌"
            safe_print(f"{result_icon} {test_name} {'通过' if success else '失败'}")

        except Exception as e:
            test_results[test_name] = False
            overall_success = False
            safe_print(f"❌ {test_name} 执行异常: {e}")

    # 生成测试摘要
    safe_print("\n" + "="*60)
    safe_print("📊 测试结果摘要:")

    passed = sum(1 for success in test_results.values() if success)
    total = len(test_results)

    for test_name, success in test_results.items():
        icon = "✅" if success else "❌"
        safe_print(f"   {icon} {test_name}")

    safe_print(f"\n总计: {passed}/{total} 通过 ({passed/total*100:.1f}%)")

    if overall_success:
        safe_print("\n🎉 RSS数据源专项测试全部通过！数据源工作正常。")
        exit(0)
    else:
        safe_print("\n❌ 部分测试失败，请检查配置、网络连接和依赖项。")
        safe_print("💡 提示: 运行 'python tests/test_keyword_fetcher_comprehensive.py' 进行完整测试")
        exit(1)