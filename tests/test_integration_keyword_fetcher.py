#!/usr/bin/env python3
"""
KeywordFetcherV2 集成测试
测试关键词获取器的完整功能和数据源集成
"""

import os
import sys
import yaml
import logging
import time
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置编码处理
try:
    from modules.utils.encoding_handler import safe_print
except ImportError:
    def safe_print(text, **kwargs):
        print(text, **kwargs)

# 导入测试模块
from modules.keyword_tools.keyword_fetcher_v2 import KeywordFetcherV2
from modules.data_sources.factory import register_all_sources
from modules.data_sources.base import DataSourceRegistry
from modules.cache import CacheManager


class KeywordFetcherV2IntegrationTest:
    """KeywordFetcherV2集成测试类"""

    def __init__(self, config_path: str = "tests/config/test_config.yml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.test_results = {}
        self.start_time = datetime.now()

        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def _load_config(self) -> Dict[str, Any]:
        """加载测试配置"""
        if not os.path.exists(self.config_path):
            safe_print(f"❌ 配置文件不存在: {self.config_path}")
            return {}

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            safe_print(f"✅ 已加载配置文件: {self.config_path}")
            return config
        except Exception as e:
            safe_print(f"❌ 加载配置文件失败: {e}")
            return {}

    def setup_test_environment(self):
        """设置测试环境"""
        safe_print("🔧 设置测试环境...")

        # 创建测试目录
        test_dirs = [
            self.config.get('test_environment', {}).get('cache_dir', 'data/test_cache'),
            self.config.get('reporting', {}).get('results_dir', 'tests/results')
        ]

        for test_dir in test_dirs:
            os.makedirs(test_dir, exist_ok=True)
            safe_print(f"   📁 创建目录: {test_dir}")

        # 注册数据源
        register_all_sources()
        available_sources = DataSourceRegistry.list_sources()
        safe_print(f"   🔌 已注册数据源: {available_sources}")

        return True

    def test_keyword_fetcher_initialization(self) -> bool:
        """测试KeywordFetcherV2初始化"""
        safe_print("\n🔍 测试KeywordFetcherV2初始化...")

        try:
            # 测试默认初始化
            fetcher = KeywordFetcherV2()
            safe_print("   ✅ 默认初始化成功")

            # 测试带配置初始化
            fetcher_with_config = KeywordFetcherV2(config_path=self.config_path)
            safe_print("   ✅ 带配置初始化成功")

            # 测试带缓存管理器初始化
            cache_manager = CacheManager(cache_dir="data/test_cache")
            fetcher_with_cache = KeywordFetcherV2(cache_manager=cache_manager)
            safe_print("   ✅ 带缓存管理器初始化成功")

            return True

        except Exception as e:
            safe_print(f"   ❌ 初始化失败: {e}")
            return False

    def test_single_category_fetch(self) -> bool:
        """测试单分类关键词获取"""
        safe_print("\n📋 测试单分类关键词获取...")

        try:
            fetcher = KeywordFetcherV2(config_path=self.config_path)

            # 测试不同分类
            test_categories = ['smart_plugs', 'smart_lighting', 'general']
            results = {}

            for category in test_categories:
                safe_print(f"   🔍 测试分类: {category}")

                start_time = time.time()
                keywords = fetcher.fetch_keywords_by_category(
                    category=category,
                    limit=5
                )
                fetch_time = time.time() - start_time

                results[category] = {
                    'keywords_count': len(keywords),
                    'fetch_time': fetch_time,
                    'sample_keywords': [kw['keyword'] for kw in keywords[:3]]
                }

                safe_print(f"      获取到 {len(keywords)} 个关键词 (耗时: {fetch_time:.2f}s)")

            # 验证结果质量
            total_keywords = sum(r['keywords_count'] for r in results.values())
            safe_print(f"   📊 总关键词数: {total_keywords}")

            if total_keywords > 0:
                safe_print("   ✅ 单分类获取测试通过")
                return True
            else:
                safe_print("   ⚠️  未获取到关键词，可能是数据源配置问题")
                return False

        except Exception as e:
            safe_print(f"   ❌ 单分类获取失败: {e}")
            return False

    def test_multi_category_fetch(self) -> bool:
        """测试多分类关键词获取"""
        safe_print("\n📋 测试多分类关键词获取...")

        try:
            fetcher = KeywordFetcherV2(config_path=self.config_path)

            categories = ['smart_plugs', 'smart_lighting']
            limit_per_category = 3

            safe_print(f"   🔍 测试分类: {categories}")
            safe_print(f"   📏 每分类限制: {limit_per_category}")

            start_time = time.time()
            results = fetcher.fetch_keywords_multi_category(
                categories=categories,
                limit_per_category=limit_per_category
            )
            fetch_time = time.time() - start_time

            safe_print(f"   ⏱️  总耗时: {fetch_time:.2f}s")

            # 验证结果结构
            if not isinstance(results, dict):
                safe_print("   ❌ 返回结果格式错误")
                return False

            total_keywords = 0
            for category, keywords in results.items():
                keyword_count = len(keywords)
                total_keywords += keyword_count
                safe_print(f"      {category}: {keyword_count} 个关键词")

            safe_print(f"   📊 总关键词数: {total_keywords}")

            if total_keywords > 0:
                safe_print("   ✅ 多分类获取测试通过")
                return True
            else:
                safe_print("   ⚠️  未获取到关键词")
                return False

        except Exception as e:
            safe_print(f"   ❌ 多分类获取失败: {e}")
            return False

    def test_source_specific_fetch(self) -> bool:
        """测试指定数据源获取"""
        safe_print("\n🎯 测试指定数据源获取...")

        try:
            fetcher = KeywordFetcherV2(config_path=self.config_path)

            # 获取可用数据源
            available_sources = DataSourceRegistry.list_sources()
            safe_print(f"   🔌 可用数据源: {available_sources}")

            results = {}

            for source in available_sources:
                safe_print(f"   🔍 测试数据源: {source}")

                try:
                    start_time = time.time()
                    keywords = fetcher.fetch_keywords_by_category(
                        category='smart_plugs',
                        limit=3,
                        sources=[source]
                    )
                    fetch_time = time.time() - start_time

                    results[source] = {
                        'success': True,
                        'keywords_count': len(keywords),
                        'fetch_time': fetch_time
                    }

                    safe_print(f"      ✅ {source}: {len(keywords)} 个关键词 ({fetch_time:.2f}s)")

                except Exception as e:
                    results[source] = {
                        'success': False,
                        'error': str(e)
                    }
                    safe_print(f"      ❌ {source}: 获取失败 - {str(e)[:50]}...")

            # 统计成功率
            successful_sources = sum(1 for r in results.values() if r['success'])
            success_rate = successful_sources / len(available_sources) if available_sources else 0

            safe_print(f"   📊 数据源成功率: {success_rate:.1%} ({successful_sources}/{len(available_sources)})")

            if success_rate >= 0.5:  # 至少50%成功
                safe_print("   ✅ 指定数据源获取测试通过")
                return True
            else:
                safe_print("   ⚠️  数据源成功率偏低")
                return False

        except Exception as e:
            safe_print(f"   ❌ 指定数据源测试失败: {e}")
            return False

    def test_all_sources_fetch(self) -> bool:
        """测试所有数据源聚合获取"""
        safe_print("\n🌐 测试所有数据源聚合获取...")

        try:
            fetcher = KeywordFetcherV2(config_path=self.config_path)

            safe_print("   🔍 从所有可用数据源获取关键词")

            start_time = time.time()
            keywords = fetcher.fetch_all_sources(
                category='smart_plugs',
                limit=10
            )
            fetch_time = time.time() - start_time

            safe_print(f"   📊 获取结果: {len(keywords)} 个关键词")
            safe_print(f"   ⏱️  总耗时: {fetch_time:.2f}s")

            if keywords:
                # 分析数据源分布
                source_distribution = {}
                for kw in keywords:
                    source = kw.get('source', 'unknown')
                    source_distribution[source] = source_distribution.get(source, 0) + 1

                safe_print("   📈 数据源分布:")
                for source, count in source_distribution.items():
                    safe_print(f"      {source}: {count} 个关键词")

                # 显示样例关键词
                safe_print("   📋 关键词样例:")
                for i, kw in enumerate(keywords[:5], 1):
                    safe_print(f"      {i}. {kw['keyword']} (来源: {kw.get('source', 'unknown')})")

                safe_print("   ✅ 聚合获取测试通过")
                return True
            else:
                safe_print("   ⚠️  未获取到关键词")
                return False

        except Exception as e:
            safe_print(f"   ❌ 聚合获取失败: {e}")
            return False

    def test_caching_mechanism(self) -> bool:
        """测试缓存机制"""
        safe_print("\n💾 测试缓存机制...")

        try:
            # 创建带缓存的获取器
            cache_manager = CacheManager(cache_dir="data/test_cache")
            fetcher = KeywordFetcherV2(
                config_path=self.config_path,
                cache_manager=cache_manager
            )

            category = 'smart_plugs'
            limit = 5

            # 第一次获取 (应该从源获取)
            safe_print("   🔄 第一次获取 (从数据源)...")
            start_time = time.time()
            keywords_1 = fetcher.fetch_keywords_by_category(category, limit)
            first_fetch_time = time.time() - start_time

            safe_print(f"      获取 {len(keywords_1)} 个关键词 (耗时: {first_fetch_time:.2f}s)")

            # 第二次获取 (应该从缓存获取)
            safe_print("   ⚡ 第二次获取 (从缓存)...")
            start_time = time.time()
            keywords_2 = fetcher.fetch_keywords_by_category(category, limit)
            second_fetch_time = time.time() - start_time

            safe_print(f"      获取 {len(keywords_2)} 个关键词 (耗时: {second_fetch_time:.2f}s)")

            # 检查缓存效果
            if second_fetch_time < first_fetch_time * 0.8:  # 至少20%的性能提升
                improvement = (1 - second_fetch_time / first_fetch_time) * 100
                safe_print(f"   ✅ 缓存生效: 性能提升 {improvement:.1f}%")

                # 检查缓存统计
                cache_stats = cache_manager.get_stats()
                safe_print(f"   📊 缓存统计:")
                safe_print(f"      内存缓存条目: {cache_stats['memory_cache_count']}")
                safe_print(f"      文件缓存条目: {cache_stats['file_cache_count']}")

                return True
            else:
                safe_print(f"   ⚠️  缓存效果不明显")
                return False

        except Exception as e:
            safe_print(f"   ❌ 缓存测试失败: {e}")
            return False

    def test_error_handling(self) -> bool:
        """测试错误处理"""
        safe_print("\n🛡️  测试错误处理...")

        try:
            fetcher = KeywordFetcherV2(config_path=self.config_path)

            # 测试无效分类
            safe_print("   🔍 测试无效分类处理...")
            invalid_keywords = fetcher.fetch_keywords_by_category(
                category='invalid_category_that_does_not_exist',
                limit=5
            )
            safe_print(f"      无效分类返回 {len(invalid_keywords)} 个关键词")

            # 测试无效数据源
            safe_print("   🔍 测试无效数据源处理...")
            invalid_source_keywords = fetcher.fetch_keywords_by_category(
                category='smart_plugs',
                limit=5,
                sources=['invalid_source_that_does_not_exist']
            )
            safe_print(f"      无效数据源返回 {len(invalid_source_keywords)} 个关键词")

            # 测试极限参数
            safe_print("   🔍 测试极限参数处理...")
            zero_limit_keywords = fetcher.fetch_keywords_by_category(
                category='smart_plugs',
                limit=0
            )
            safe_print(f"      零限制返回 {len(zero_limit_keywords)} 个关键词")

            # 如果没有抛出异常，说明错误处理正常
            safe_print("   ✅ 错误处理测试通过")
            return True

        except Exception as e:
            safe_print(f"   ❌ 错误处理测试失败: {e}")
            return False

    def run_all_tests(self) -> bool:
        """运行所有集成测试"""
        safe_print("╔══════════════════════════════════════════════════════════════╗")
        safe_print("║              KeywordFetcherV2 集成测试                      ║")
        safe_print("╚══════════════════════════════════════════════════════════════╝\n")

        if not self.config:
            safe_print("❌ 无法加载配置，测试终止")
            return False

        # 设置测试环境
        if not self.setup_test_environment():
            safe_print("❌ 测试环境设置失败")
            return False

        # 定义测试序列
        tests = [
            ("初始化测试", self.test_keyword_fetcher_initialization),
            ("单分类获取", self.test_single_category_fetch),
            ("多分类获取", self.test_multi_category_fetch),
            ("指定数据源", self.test_source_specific_fetch),
            ("聚合获取", self.test_all_sources_fetch),
            ("缓存机制", self.test_caching_mechanism),
            ("错误处理", self.test_error_handling),
        ]

        safe_print("📋 测试计划:")
        for i, (test_name, _) in enumerate(tests, 1):
            safe_print(f"   {i}. {test_name}")

        safe_print("\n" + "="*60)

        # 执行测试
        overall_success = True
        for test_name, test_method in tests:
            safe_print(f"\n🔄 执行 {test_name}...")

            try:
                success = test_method()
                self.test_results[test_name] = success

                if not success:
                    overall_success = False

                result_icon = "✅" if success else "❌"
                safe_print(f"{result_icon} {test_name} {'通过' if success else '失败'}")

            except Exception as e:
                self.test_results[test_name] = False
                overall_success = False
                safe_print(f"❌ {test_name} 执行异常: {e}")

        # 生成测试报告
        self._generate_test_report(overall_success)

        return overall_success

    def _generate_test_report(self, overall_success: bool):
        """生成测试报告"""
        safe_print("\n" + "="*60)
        safe_print("📊 集成测试结果摘要:")

        passed = sum(1 for success in self.test_results.values() if success)
        total = len(self.test_results)

        for test_name, success in self.test_results.items():
            icon = "✅" if success else "❌"
            safe_print(f"   {icon} {test_name}")

        safe_print(f"\n总计: {passed}/{total} 通过 ({passed/total*100:.1f}%)")

        total_time = (datetime.now() - self.start_time).total_seconds()
        safe_print(f"总耗时: {total_time:.2f}s")

        # 保存详细报告
        if self.config.get('reporting', {}).get('save_results', False):
            self._save_detailed_report(overall_success, total_time)

    def _save_detailed_report(self, overall_success: bool, total_time: float):
        """保存详细测试报告"""
        try:
            results_dir = self.config.get('reporting', {}).get('results_dir', 'tests/results')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_file = os.path.join(results_dir, f'integration_test_report_{timestamp}.json')

            report_data = {
                'test_type': 'KeywordFetcherV2_Integration',
                'timestamp': timestamp,
                'overall_success': overall_success,
                'total_time_seconds': total_time,
                'test_results': self.test_results,
                'config_file': self.config_path,
                'environment': {
                    'available_sources': DataSourceRegistry.list_sources(),
                    'python_version': sys.version,
                }
            }

            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)

            safe_print(f"\n📄 详细报告已保存: {report_file}")

        except Exception as e:
            safe_print(f"❌ 保存报告失败: {e}")


def main():
    """主函数"""
    safe_print("🚀 启动KeywordFetcherV2集成测试...\n")

    tester = KeywordFetcherV2IntegrationTest()
    success = tester.run_all_tests()

    if success:
        safe_print("\n🎉 所有集成测试通过！KeywordFetcherV2工作正常。")
        exit(0)
    else:
        safe_print("\n❌ 部分集成测试失败，请检查配置和数据源连接。")
        exit(1)


if __name__ == "__main__":
    main()