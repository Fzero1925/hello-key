#!/usr/bin/env python3
"""
一键运行所有关键词获取功能测试
包含数据源测试、集成测试和性能验证
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from modules.utils.encoding_handler import safe_print
except ImportError:
    def safe_print(text, **kwargs):
        print(text, **kwargs)


class TestRunner:
    """测试运行器"""

    def __init__(self):
        self.test_results = {}
        self.start_time = time.time()

    def run_test(self, test_name: str, test_script: str, description: str) -> bool:
        """运行单个测试"""
        safe_print(f"\n🔄 运行 {test_name}...")
        safe_print(f"   📄 {description}")

        if not os.path.exists(test_script):
            safe_print(f"   ❌ 测试脚本不存在: {test_script}")
            return False

        try:
            start_time = time.time()
            result = subprocess.run([sys.executable, test_script],
                                  capture_output=True, text=True, timeout=300)
            execution_time = time.time() - start_time

            success = result.returncode == 0

            self.test_results[test_name] = {
                'success': success,
                'execution_time': execution_time,
                'stdout': result.stdout,
                'stderr': result.stderr
            }

            if success:
                safe_print(f"   ✅ {test_name} 通过 (耗时: {execution_time:.1f}s)")
            else:
                safe_print(f"   ❌ {test_name} 失败 (耗时: {execution_time:.1f}s)")
                if result.stderr:
                    safe_print(f"   错误信息: {result.stderr[:200]}...")

            return success

        except subprocess.TimeoutExpired:
            safe_print(f"   ⏱️  {test_name} 超时 (>300s)")
            return False
        except Exception as e:
            safe_print(f"   ❌ {test_name} 执行异常: {e}")
            return False

    def run_all_tests(self):
        """运行所有测试"""
        safe_print("╔══════════════════════════════════════════════════════════════╗")
        safe_print("║                   关键词获取功能测试套件                     ║")
        safe_print("╚══════════════════════════════════════════════════════════════╝\n")

        # 定义测试序列
        tests = [
            {
                'name': 'RSS数据源专项测试',
                'script': 'tests/scripts/test_rss_source.py',
                'description': '测试RSS数据源的连接、获取和性能'
            },
            {
                'name': '数据源综合测试',
                'script': 'tests/test_keyword_fetcher_comprehensive.py',
                'description': '测试所有数据源的功能和兼容性'
            },
            {
                'name': 'KeywordFetcherV2集成测试',
                'script': 'tests/test_integration_keyword_fetcher.py',
                'description': '测试关键词获取器的完整功能集成'
            }
        ]

        safe_print("📋 测试计划:")
        for i, test in enumerate(tests, 1):
            safe_print(f"   {i}. {test['name']}")
            safe_print(f"      {test['description']}")

        safe_print("\n" + "="*60)

        # 执行测试
        overall_success = True
        for test in tests:
            success = self.run_test(test['name'], test['script'], test['description'])
            if not success:
                overall_success = False

        # 生成总结报告
        self.generate_summary_report(overall_success)

        return overall_success

    def generate_summary_report(self, overall_success: bool):
        """生成总结报告"""
        total_time = time.time() - self.start_time

        safe_print("\n" + "="*60)
        safe_print("📊 测试套件总结报告")
        safe_print("="*60)

        passed_tests = sum(1 for result in self.test_results.values() if result['success'])
        total_tests = len(self.test_results)

        safe_print(f"总体状态: {'✅ 通过' if overall_success else '❌ 失败'}")
        safe_print(f"测试通过率: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)")
        safe_print(f"总执行时间: {total_time:.1f}s")

        safe_print("\n详细结果:")
        for test_name, result in self.test_results.items():
            status = "✅ 通过" if result['success'] else "❌ 失败"
            execution_time = result['execution_time']
            safe_print(f"  {status} {test_name} ({execution_time:.1f}s)")

        if not overall_success:
            safe_print("\n💡 故障排除建议:")
            safe_print("  1. 检查网络连接")
            safe_print("  2. 验证API密钥配置")
            safe_print("  3. 查看 tests/config/test_config.yml 配置")
            safe_print("  4. 运行单个测试脚本查看详细错误信息")

        safe_print("\n📁 相关文件:")
        safe_print("  - 测试配置: tests/config/test_config.yml")
        safe_print("  - 测试结果: tests/results/")
        safe_print("  - 缓存目录: data/test_cache/")


def check_environment():
    """检查测试环境"""
    safe_print("🔍 检查测试环境...")

    # 检查必要目录
    required_dirs = [
        'tests/config',
        'tests/results',
        'data/test_cache'
    ]

    for directory in required_dirs:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            safe_print(f"   📁 创建目录: {directory}")
        else:
            safe_print(f"   ✅ 目录存在: {directory}")

    # 检查配置文件
    config_file = 'tests/config/test_config.yml'
    if os.path.exists(config_file):
        safe_print(f"   ✅ 配置文件: {config_file}")
    else:
        safe_print(f"   ❌ 配置文件不存在: {config_file}")
        safe_print("   💡 请先运行测试以生成默认配置")

    safe_print("   ✅ 环境检查完成")


def main():
    """主函数"""
    safe_print("🚀 启动关键词获取功能测试套件...\n")

    # 检查环境
    check_environment()

    # 运行测试
    runner = TestRunner()
    success = runner.run_all_tests()

    if success:
        safe_print("\n🎉 恭喜！所有测试通过，关键词获取功能工作正常。")
        exit(0)
    else:
        safe_print("\n❌ 部分测试失败，请检查上述故障排除建议。")
        exit(1)


if __name__ == "__main__":
    main()