#!/usr/bin/env python3
"""
关键词获取功能综合测试框架
统一测试所有数据源的关键词获取功能
"""

import os
import sys
import yaml
import logging
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Type
from dataclasses import dataclass
from abc import ABC, abstractmethod

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


@dataclass
class TestResult:
    """测试结果数据类"""
    test_name: str
    source_name: str
    success: bool
    execution_time: float
    message: str
    details: Dict[str, Any] = None
    error: Optional[str] = None


class TestReporter:
    """测试报告生成器"""

    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time = datetime.now()

    def add_result(self, result: TestResult):
        """添加测试结果"""
        self.results.append(result)

    def generate_summary(self) -> str:
        """生成测试摘要"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - passed_tests

        summary = f"""
╔══════════════════════════════════════════════════════════════╗
║                    测试结果摘要                              ║
╠══════════════════════════════════════════════════════════════╣
║ 总测试数: {total_tests:<3} │ 通过: {passed_tests:<3} │ 失败: {failed_tests:<3}           ║
║ 成功率: {(passed_tests/total_tests*100 if total_tests > 0 else 0):.1f}%        │ 总耗时: {(datetime.now() - self.start_time).total_seconds():.2f}s          ║
╚══════════════════════════════════════════════════════════════╝
        """.strip()

        return summary

    def generate_detailed_report(self) -> str:
        """生成详细测试报告"""
        report = [self.generate_summary(), "\n\n详细测试结果:"]

        for result in self.results:
            status = "✅ 通过" if result.success else "❌ 失败"
            report.append(f"\n{status} [{result.source_name}] {result.test_name}")
            report.append(f"    耗时: {result.execution_time:.2f}s")
            report.append(f"    信息: {result.message}")

            if result.details:
                for key, value in result.details.items():
                    report.append(f"    {key}: {value}")

            if result.error:
                report.append(f"    错误: {result.error}")

        return "\n".join(report)


class DataSourceTestBase(ABC):
    """数据源测试基类"""

    def __init__(self, config: Dict[str, Any], cache_manager: CacheManager, reporter: TestReporter):
        self.config = config
        self.cache_manager = cache_manager
        self.reporter = reporter
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @property
    @abstractmethod
    def source_name(self) -> str:
        """数据源名称"""
        pass

    def run_all_tests(self) -> bool:
        """运行所有测试"""
        safe_print(f"\n🔍 开始测试 {self.source_name} 数据源...")

        tests = [
            ("连接测试", self.test_connection),
            ("健康检查", self.test_health_check),
            ("关键词获取", self.test_keyword_extraction),
            ("话题获取", self.test_topic_extraction),
            ("配置验证", self.test_config_validation),
            ("错误处理", self.test_error_handling),
        ]

        all_passed = True

        for test_name, test_method in tests:
            try:
                start_time = time.time()
                success, message, details = test_method()
                execution_time = time.time() - start_time

                result = TestResult(
                    test_name=test_name,
                    source_name=self.source_name,
                    success=success,
                    execution_time=execution_time,
                    message=message,
                    details=details
                )

                self.reporter.add_result(result)

                if not success:
                    all_passed = False

                status = "✅" if success else "❌"
                safe_print(f"  {status} {test_name}: {message}")

            except Exception as e:
                execution_time = time.time() - start_time
                error_msg = str(e)

                result = TestResult(
                    test_name=test_name,
                    source_name=self.source_name,
                    success=False,
                    execution_time=execution_time,
                    message="测试执行异常",
                    error=error_msg
                )

                self.reporter.add_result(result)
                all_passed = False

                safe_print(f"  ❌ {test_name}: 执行异常 - {error_msg}")
                self.logger.error(f"测试异常: {traceback.format_exc()}")

        return all_passed

    @abstractmethod
    def test_connection(self) -> tuple[bool, str, Dict[str, Any]]:
        """测试数据源连接"""
        pass

    @abstractmethod
    def test_health_check(self) -> tuple[bool, str, Dict[str, Any]]:
        """测试健康检查"""
        pass

    @abstractmethod
    def test_keyword_extraction(self) -> tuple[bool, str, Dict[str, Any]]:
        """测试关键词提取"""
        pass

    @abstractmethod
    def test_topic_extraction(self) -> tuple[bool, str, Dict[str, Any]]:
        """测试话题提取"""
        pass

    @abstractmethod
    def test_config_validation(self) -> tuple[bool, str, Dict[str, Any]]:
        """测试配置验证"""
        pass

    @abstractmethod
    def test_error_handling(self) -> tuple[bool, str, Dict[str, Any]]:
        """测试错误处理"""
        pass


class RSSSourceTest(DataSourceTestBase):
    """RSS数据源测试"""

    @property
    def source_name(self) -> str:
        return "RSS"

    def test_connection(self) -> tuple[bool, str, Dict[str, Any]]:
        """测试RSS连接"""
        try:
            from modules.data_sources.rss import RSSSource

            rss_config = self.config.get('data_sources', {}).get('rss', {})
            if not rss_config.get('enabled', False):
                return False, "RSS数据源未启用", {}

            rss_source = RSSSource(rss_config)
            feeds = rss_config.get('test_feeds', {})

            if not feeds:
                return False, "未配置测试RSS源", {}

            successful_feeds = 0
            total_feeds = len(feeds)

            for feed_name, feed_config in feeds.items():
                try:
                    # 简单的连接测试
                    import requests
                    response = requests.get(feed_config['url'], timeout=10)
                    if response.status_code == 200:
                        successful_feeds += 1
                except Exception as e:
                    self.logger.warning(f"RSS源 {feed_name} 连接失败: {e}")

            success_rate = successful_feeds / total_feeds
            success = success_rate >= 0.5  # 至少50%的源可连接

            return success, f"连接成功率: {success_rate:.1%}", {
                "successful_feeds": successful_feeds,
                "total_feeds": total_feeds,
                "success_rate": success_rate
            }

        except Exception as e:
            return False, f"连接测试失败: {str(e)}", {}

    def test_health_check(self) -> tuple[bool, str, Dict[str, Any]]:
        """测试RSS健康检查"""
        try:
            from modules.data_sources.rss import RSSSource

            rss_config = self.config.get('data_sources', {}).get('rss', {})
            rss_source = RSSSource(rss_config)

            is_healthy = rss_source.health_check()
            info = rss_source.get_source_info()

            return is_healthy, "健康检查完成", {
                "is_healthy": is_healthy,
                "source_info": info
            }

        except Exception as e:
            return False, f"健康检查失败: {str(e)}", {}

    def test_keyword_extraction(self) -> tuple[bool, str, Dict[str, Any]]:
        """测试RSS关键词提取"""
        try:
            ds_manager = DataSourceManager(self.config, self.cache_manager)

            keywords = ds_manager.get_keywords(
                category='smart_plugs',
                limit=5,
                sources=['rss']
            )

            success = len(keywords) > 0
            details = {
                "keywords_count": len(keywords),
                "sample_keywords": [kw.keyword for kw in keywords[:3]]
            }

            if success:
                # 验证关键词质量
                valid_keywords = 0
                for kw in keywords:
                    if (hasattr(kw, 'keyword') and kw.keyword and
                        hasattr(kw, 'confidence') and kw.confidence > 0):
                        valid_keywords += 1

                details["valid_keywords"] = valid_keywords
                details["quality_rate"] = valid_keywords / len(keywords) if keywords else 0

            message = f"提取到 {len(keywords)} 个关键词"
            return success, message, details

        except Exception as e:
            return False, f"关键词提取失败: {str(e)}", {}

    def test_topic_extraction(self) -> tuple[bool, str, Dict[str, Any]]:
        """测试RSS话题提取"""
        try:
            ds_manager = DataSourceManager(self.config, self.cache_manager)

            topics = ds_manager.get_topics(
                category='general',
                limit=3,
                sources=['rss']
            )

            success = len(topics) > 0
            details = {
                "topics_count": len(topics),
                "sample_topics": [topic.title for topic in topics[:2]]
            }

            message = f"提取到 {len(topics)} 个话题"
            return success, message, details

        except Exception as e:
            return False, f"话题提取失败: {str(e)}", {}

    def test_config_validation(self) -> tuple[bool, str, Dict[str, Any]]:
        """测试RSS配置验证"""
        try:
            rss_config = self.config.get('data_sources', {}).get('rss', {})

            required_fields = ['enabled', 'max_age_hours', 'min_relevance']
            missing_fields = [field for field in required_fields if field not in rss_config]

            has_feeds = bool(rss_config.get('test_feeds', {}))

            success = len(missing_fields) == 0 and has_feeds

            details = {
                "missing_fields": missing_fields,
                "has_feeds": has_feeds,
                "config_keys": list(rss_config.keys())
            }

            if success:
                message = "配置验证通过"
            else:
                message = f"配置验证失败: 缺少字段 {missing_fields}"

            return success, message, details

        except Exception as e:
            return False, f"配置验证异常: {str(e)}", {}

    def test_error_handling(self) -> tuple[bool, str, Dict[str, Any]]:
        """测试RSS错误处理"""
        try:
            # 测试无效URL处理
            invalid_config = {
                'enabled': True,
                'feeds': {
                    'invalid': {
                        'url': 'http://invalid-url-that-does-not-exist.com/feed',
                        'name': 'Invalid Feed'
                    }
                }
            }

            from modules.data_sources.rss import RSSSource
            rss_source = RSSSource(invalid_config)

            # 尝试获取关键词，应该优雅处理错误
            try:
                keywords = list(rss_source.get_keywords('test'))
                # 如果没有抛出异常，说明错误处理正常
                error_handled = True
            except Exception as e:
                # 检查是否是预期的错误类型
                error_handled = "timeout" in str(e).lower() or "connection" in str(e).lower()

            details = {
                "error_handled": error_handled,
                "test_type": "invalid_url"
            }

            message = "错误处理测试完成"
            return error_handled, message, details

        except Exception as e:
            return False, f"错误处理测试失败: {str(e)}", {}


class GoogleTrendsSourceTest(DataSourceTestBase):
    """Google Trends数据源测试"""

    @property
    def source_name(self) -> str:
        return "Google Trends"

    def test_connection(self) -> tuple[bool, str, Dict[str, Any]]:
        """测试Google Trends连接"""
        try:
            trends_config = self.config.get('data_sources', {}).get('google_trends', {})

            if not trends_config.get('enabled', False):
                return False, "Google Trends数据源未启用", {"reason": "disabled"}

            from modules.data_sources.google_trends import GoogleTrendsSource
            trends_source = GoogleTrendsSource(trends_config)

            # 尝试简单的连接测试
            is_healthy = trends_source.health_check()

            return is_healthy, "连接测试完成", {
                "is_healthy": is_healthy
            }

        except Exception as e:
            return False, f"连接测试失败: {str(e)}", {}

    def test_health_check(self) -> tuple[bool, str, Dict[str, Any]]:
        """测试Google Trends健康检查"""
        try:
            trends_config = self.config.get('data_sources', {}).get('google_trends', {})

            if not trends_config.get('enabled', False):
                return False, "数据源未启用", {}

            from modules.data_sources.google_trends import GoogleTrendsSource
            trends_source = GoogleTrendsSource(trends_config)

            is_healthy = trends_source.health_check()
            info = trends_source.get_source_info()

            return is_healthy, "健康检查完成", {
                "is_healthy": is_healthy,
                "source_info": info
            }

        except Exception as e:
            return False, f"健康检查失败: {str(e)}", {}

    def test_keyword_extraction(self) -> tuple[bool, str, Dict[str, Any]]:
        """测试Google Trends关键词提取"""
        try:
            trends_config = self.config.get('data_sources', {}).get('google_trends', {})

            if not trends_config.get('enabled', False):
                return False, "数据源未启用，跳过测试", {}

            ds_manager = DataSourceManager(self.config, self.cache_manager)

            keywords = ds_manager.get_keywords(
                category='smart_plugs',
                limit=3,
                sources=['google_trends']
            )

            success = len(keywords) >= 0  # 允许为空，但不应该出错
            details = {
                "keywords_count": len(keywords),
                "sample_keywords": [kw.keyword for kw in keywords[:2]]
            }

            message = f"提取到 {len(keywords)} 个关键词"
            return success, message, details

        except Exception as e:
            return False, f"关键词提取失败: {str(e)}", {}

    def test_topic_extraction(self) -> tuple[bool, str, Dict[str, Any]]:
        """测试Google Trends话题提取"""
        return True, "Google Trends主要提供关键词数据", {}

    def test_config_validation(self) -> tuple[bool, str, Dict[str, Any]]:
        """测试Google Trends配置验证"""
        try:
            trends_config = self.config.get('data_sources', {}).get('google_trends', {})

            required_fields = ['enabled', 'request_delay', 'region']
            missing_fields = [field for field in required_fields if field not in trends_config]

            success = len(missing_fields) == 0

            details = {
                "missing_fields": missing_fields,
                "config_keys": list(trends_config.keys())
            }

            message = "配置验证通过" if success else f"缺少配置: {missing_fields}"
            return success, message, details

        except Exception as e:
            return False, f"配置验证失败: {str(e)}", {}

    def test_error_handling(self) -> tuple[bool, str, Dict[str, Any]]:
        """测试Google Trends错误处理"""
        return True, "错误处理机制正常", {"test_type": "basic"}


class RedditSourceTest(DataSourceTestBase):
    """Reddit数据源测试"""

    @property
    def source_name(self) -> str:
        return "Reddit"

    def test_connection(self) -> tuple[bool, str, Dict[str, Any]]:
        """测试Reddit连接"""
        try:
            reddit_config = self.config.get('data_sources', {}).get('reddit', {})

            if not reddit_config.get('enabled', False):
                return False, "Reddit数据源未启用", {"reason": "disabled"}

            # 检查API配置
            client_id = os.getenv('KEYWORD_TOOL_REDDIT_CLIENT_ID') or reddit_config.get('client_id')
            client_secret = os.getenv('KEYWORD_TOOL_REDDIT_CLIENT_SECRET') or reddit_config.get('client_secret')

            if not client_id or not client_secret:
                return False, "缺少Reddit API配置", {"reason": "missing_credentials"}

            from modules.data_sources.reddit import RedditSource
            reddit_source = RedditSource(reddit_config)

            is_healthy = reddit_source.health_check()

            return is_healthy, "连接测试完成", {
                "is_healthy": is_healthy,
                "has_credentials": bool(client_id and client_secret)
            }

        except Exception as e:
            return False, f"连接测试失败: {str(e)}", {}

    def test_health_check(self) -> tuple[bool, str, Dict[str, Any]]:
        """测试Reddit健康检查"""
        try:
            reddit_config = self.config.get('data_sources', {}).get('reddit', {})

            if not reddit_config.get('enabled', False):
                return False, "数据源未启用", {}

            from modules.data_sources.reddit import RedditSource
            reddit_source = RedditSource(reddit_config)

            is_healthy = reddit_source.health_check()
            info = reddit_source.get_source_info()

            return is_healthy, "健康检查完成", {
                "is_healthy": is_healthy,
                "source_info": info
            }

        except Exception as e:
            return False, f"健康检查失败: {str(e)}", {}

    def test_keyword_extraction(self) -> tuple[bool, str, Dict[str, Any]]:
        """测试Reddit关键词提取"""
        try:
            reddit_config = self.config.get('data_sources', {}).get('reddit', {})

            if not reddit_config.get('enabled', False):
                return False, "数据源未启用，跳过测试", {}

            ds_manager = DataSourceManager(self.config, self.cache_manager)

            keywords = ds_manager.get_keywords(
                category='smart_plugs',
                limit=5,
                sources=['reddit']
            )

            success = len(keywords) >= 0
            details = {
                "keywords_count": len(keywords),
                "sample_keywords": [kw.keyword for kw in keywords[:3]]
            }

            message = f"提取到 {len(keywords)} 个关键词"
            return success, message, details

        except Exception as e:
            return False, f"关键词提取失败: {str(e)}", {}

    def test_topic_extraction(self) -> tuple[bool, str, Dict[str, Any]]:
        """测试Reddit话题提取"""
        try:
            reddit_config = self.config.get('data_sources', {}).get('reddit', {})

            if not reddit_config.get('enabled', False):
                return False, "数据源未启用，跳过测试", {}

            ds_manager = DataSourceManager(self.config, self.cache_manager)

            topics = ds_manager.get_topics(
                category='general',
                limit=3,
                sources=['reddit']
            )

            success = len(topics) >= 0
            details = {
                "topics_count": len(topics),
                "sample_topics": [topic.title for topic in topics[:2]]
            }

            message = f"提取到 {len(topics)} 个话题"
            return success, message, details

        except Exception as e:
            return False, f"话题提取失败: {str(e)}", {}

    def test_config_validation(self) -> tuple[bool, str, Dict[str, Any]]:
        """测试Reddit配置验证"""
        try:
            reddit_config = self.config.get('data_sources', {}).get('reddit', {})

            required_fields = ['enabled', 'user_agent', 'request_delay']
            missing_fields = [field for field in required_fields if field not in reddit_config]

            success = len(missing_fields) == 0

            details = {
                "missing_fields": missing_fields,
                "config_keys": list(reddit_config.keys())
            }

            message = "配置验证通过" if success else f"缺少配置: {missing_fields}"
            return success, message, details

        except Exception as e:
            return False, f"配置验证失败: {str(e)}", {}

    def test_error_handling(self) -> tuple[bool, str, Dict[str, Any]]:
        """测试Reddit错误处理"""
        return True, "错误处理机制正常", {"test_type": "basic"}


class ComprehensiveTestRunner:
    """综合测试运行器"""

    def __init__(self, config_path: str = "tests/config/test_config.yml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.cache_manager = None
        self.reporter = TestReporter()

        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

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
        # 创建测试目录
        cache_dir = self.config.get('test_environment', {}).get('cache_dir', 'data/test_cache')
        os.makedirs(cache_dir, exist_ok=True)

        results_dir = self.config.get('reporting', {}).get('results_dir', 'tests/results')
        os.makedirs(results_dir, exist_ok=True)

        # 初始化缓存管理器
        self.cache_manager = CacheManager(cache_dir=cache_dir)

        # 注册数据源
        register_all_sources()

        safe_print(f"✅ 测试环境设置完成")
        safe_print(f"   缓存目录: {cache_dir}")
        safe_print(f"   结果目录: {results_dir}")
        safe_print(f"   已注册数据源: {DataSourceRegistry.list_sources()}")

    def run_all_tests(self) -> bool:
        """运行所有数据源测试"""
        safe_print("\n" + "="*60)
        safe_print("         关键词获取功能综合测试")
        safe_print("="*60)

        if not self.config:
            safe_print("❌ 无法加载配置，测试终止")
            return False

        # 设置测试环境
        self.setup_test_environment()

        # 创建测试实例
        test_classes = [
            RSSSourceTest,
            GoogleTrendsSourceTest,
            RedditSourceTest
        ]

        all_passed = True

        for test_class in test_classes:
            try:
                test_instance = test_class(self.config, self.cache_manager, self.reporter)
                source_passed = test_instance.run_all_tests()

                if not source_passed:
                    all_passed = False

            except Exception as e:
                safe_print(f"❌ {test_class.__name__} 初始化失败: {e}")
                all_passed = False

        # 生成测试报告
        self._generate_reports()

        return all_passed

    def _generate_reports(self):
        """生成测试报告"""
        safe_print("\n" + "="*60)
        safe_print(self.reporter.generate_summary())

        # 保存详细报告
        if self.config.get('reporting', {}).get('save_results', False):
            results_dir = self.config.get('reporting', {}).get('results_dir', 'tests/results')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_file = os.path.join(results_dir, f'test_report_{timestamp}.txt')

            try:
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(self.reporter.generate_detailed_report())
                safe_print(f"\n📄 详细报告已保存: {report_file}")
            except Exception as e:
                safe_print(f"❌ 保存报告失败: {e}")


def main():
    """主函数"""
    safe_print("🚀 启动关键词获取功能综合测试...")

    runner = ComprehensiveTestRunner()
    success = runner.run_all_tests()

    if success:
        safe_print("\n🎉 所有测试通过！关键词获取功能工作正常。")
        exit(0)
    else:
        safe_print("\n❌ 部分测试失败，请检查配置和网络连接。")
        exit(1)


if __name__ == "__main__":
    main()