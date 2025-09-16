#!/usr/bin/env python3
"""
配置验证脚本 - Configuration Validation Script

独立的配置验证工具，检查所有必需的环境变量和API凭据有效性。
在主要功能执行前调用，确保系统配置正确。

功能：
- 检查环境变量完整性
- 验证API凭据有效性
- 测试网络连接
- 生成详细的配置状态报告
- 提供修复建议
"""

import os
import sys
import json
import asyncio
import aiohttp
import requests
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from modules.config import ConfigManager
from modules.utils.encoding_handler import safe_print, safe_write, setup_windows_console

# Windows编码处理
setup_windows_console()


@dataclass
class APIValidationResult:
    """API验证结果"""
    service: str
    is_valid: bool
    response_time_ms: Optional[float]
    error_message: Optional[str]
    quota_remaining: Optional[int]
    recommendations: List[str]


@dataclass
class ConfigValidationReport:
    """完整的配置验证报告"""
    timestamp: str
    overall_status: str  # 'valid', 'partial', 'invalid'
    environment_check: Dict[str, Any]
    api_validations: List[APIValidationResult]
    network_status: Dict[str, Any]
    warnings: List[str]
    errors: List[str]
    recommendations: List[str]
    next_steps: List[str]


class ConfigValidator:
    """配置验证器"""

    def __init__(self):
        self.logger = self._setup_logging()
        self.config_manager = ConfigManager()
        self.report_dir = Path("data/validation_reports")
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def _setup_logging(self) -> logging.Logger:
        """设置日志系统"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)

    async def validate_all(self) -> ConfigValidationReport:
        """执行完整的配置验证"""
        self.logger.info("[搜索] 开始配置验证...")

        timestamp = datetime.now(timezone.utc).isoformat()
        warnings = []
        errors = []
        recommendations = []

        # 1. 环境变量检查
        env_check = self._check_environment_variables()
        if not env_check['all_present']:
            errors.extend(env_check['missing_vars'])

        # 2. API凭据验证
        api_validations = await self._validate_api_credentials()
        failed_apis = [api for api in api_validations if not api.is_valid]
        if failed_apis:
            errors.extend([f"{api.service}: {api.error_message}" for api in failed_apis])

        # 3. 网络连接检查
        network_status = await self._check_network_connectivity()
        if not network_status['internet_available']:
            errors.append("网络连接不可用")

        # 4. 生成建议和下一步
        recommendations.extend(self._generate_recommendations(env_check, api_validations, network_status))
        next_steps = self._generate_next_steps(errors, warnings)

        # 5. 确定整体状态
        if errors:
            overall_status = 'invalid'
        elif warnings or any(not api.is_valid for api in api_validations):
            overall_status = 'partial'
        else:
            overall_status = 'valid'

        report = ConfigValidationReport(
            timestamp=timestamp,
            overall_status=overall_status,
            environment_check=env_check,
            api_validations=api_validations,
            network_status=network_status,
            warnings=warnings,
            errors=errors,
            recommendations=recommendations,
            next_steps=next_steps
        )

        # 保存报告
        await self._save_report(report)

        self.logger.info(f"[完成] 配置验证完成 - 状态: {overall_status}")
        return report

    def _check_environment_variables(self) -> Dict[str, Any]:
        """检查环境变量"""
        required_vars = [
            'KEYWORD_TOOL_REDDIT_CLIENT_ID',
            'KEYWORD_TOOL_REDDIT_CLIENT_SECRET',
            'KEYWORD_TOOL_YOUTUBE_API_KEY',
            'KEYWORD_TOOL_TELEGRAM_BOT_TOKEN',
            'KEYWORD_TOOL_TELEGRAM_CHAT_ID'
        ]

        present_vars = []
        missing_vars = []

        for var in required_vars:
            value = os.getenv(var)
            if value:
                present_vars.append(var)
            else:
                missing_vars.append(f"环境变量缺失: {var}")

        return {
            'total_required': len(required_vars),
            'present_count': len(present_vars),
            'missing_count': len(missing_vars),
            'all_present': len(missing_vars) == 0,
            'present_vars': present_vars,
            'missing_vars': missing_vars
        }

    async def _validate_api_credentials(self) -> List[APIValidationResult]:
        """验证API凭据"""
        validations = []

        # 验证Reddit API
        reddit_result = await self._validate_reddit_api()
        validations.append(reddit_result)

        # 验证YouTube API
        youtube_result = await self._validate_youtube_api()
        validations.append(youtube_result)

        # 验证Telegram Bot
        telegram_result = await self._validate_telegram_bot()
        validations.append(telegram_result)

        return validations

    async def _validate_reddit_api(self) -> APIValidationResult:
        """验证Reddit API"""
        credentials = self.config_manager.get_api_credentials()
        client_id = credentials.get('reddit_client_id', '')
        client_secret = credentials.get('reddit_client_secret', '')

        if not client_id or not client_secret:
            return APIValidationResult(
                service='Reddit API',
                is_valid=False,
                response_time_ms=None,
                error_message='凭据未配置',
                quota_remaining=None,
                recommendations=['设置 KEYWORD_TOOL_REDDIT_CLIENT_ID 和 KEYWORD_TOOL_REDDIT_CLIENT_SECRET']
            )

        try:
            # 使用轻量级的API调用测试
            start_time = datetime.now()

            auth_data = {
                'grant_type': 'client_credentials'
            }

            async with aiohttp.ClientSession() as session:
                auth = aiohttp.BasicAuth(client_id, client_secret)
                headers = {'User-Agent': 'KeywordTool-Validator/1.0'}

                async with session.post(
                    'https://www.reddit.com/api/v1/access_token',
                    data=auth_data,
                    auth=auth,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response_time = (datetime.now() - start_time).total_seconds() * 1000

                    if response.status == 200:
                        data = await response.json()
                        if 'access_token' in data:
                            return APIValidationResult(
                                service='Reddit API',
                                is_valid=True,
                                response_time_ms=response_time,
                                error_message=None,
                                quota_remaining=None,
                                recommendations=[]
                            )

                    return APIValidationResult(
                        service='Reddit API',
                        is_valid=False,
                        response_time_ms=response_time,
                        error_message=f'HTTP {response.status}',
                        quota_remaining=None,
                        recommendations=['检查Reddit API凭据是否正确']
                    )

        except Exception as e:
            return APIValidationResult(
                service='Reddit API',
                is_valid=False,
                response_time_ms=None,
                error_message=str(e),
                quota_remaining=None,
                recommendations=['检查网络连接和Reddit API凭据']
            )

    async def _validate_youtube_api(self) -> APIValidationResult:
        """验证YouTube API"""
        credentials = self.config_manager.get_api_credentials()
        api_key = credentials.get('youtube_api_key', '')

        if not api_key:
            return APIValidationResult(
                service='YouTube API',
                is_valid=False,
                response_time_ms=None,
                error_message='API密钥未配置',
                quota_remaining=None,
                recommendations=['设置 KEYWORD_TOOL_YOUTUBE_API_KEY']
            )

        try:
            start_time = datetime.now()

            # 使用轻量级的搜索测试
            url = 'https://www.googleapis.com/youtube/v3/search'
            params = {
                'part': 'snippet',
                'q': 'test',
                'type': 'video',
                'maxResults': 1,
                'key': api_key
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response_time = (datetime.now() - start_time).total_seconds() * 1000

                    if response.status == 200:
                        data = await response.json()
                        if 'items' in data:
                            return APIValidationResult(
                                service='YouTube API',
                                is_valid=True,
                                response_time_ms=response_time,
                                error_message=None,
                                quota_remaining=None,
                                recommendations=[]
                            )

                    error_data = await response.json() if response.content_type == 'application/json' else {}
                    error_msg = error_data.get('error', {}).get('message', f'HTTP {response.status}')

                    return APIValidationResult(
                        service='YouTube API',
                        is_valid=False,
                        response_time_ms=response_time,
                        error_message=error_msg,
                        quota_remaining=None,
                        recommendations=['检查YouTube API密钥是否正确和有效']
                    )

        except Exception as e:
            return APIValidationResult(
                service='YouTube API',
                is_valid=False,
                response_time_ms=None,
                error_message=str(e),
                quota_remaining=None,
                recommendations=['检查网络连接和YouTube API密钥']
            )

    async def _validate_telegram_bot(self) -> APIValidationResult:
        """验证Telegram Bot"""
        credentials = self.config_manager.get_api_credentials()
        bot_token = credentials.get('telegram_bot_token', '')
        chat_id = credentials.get('telegram_chat_id', '')

        if not bot_token:
            return APIValidationResult(
                service='Telegram Bot',
                is_valid=False,
                response_time_ms=None,
                error_message='Bot token未配置',
                quota_remaining=None,
                recommendations=['设置 KEYWORD_TOOL_TELEGRAM_BOT_TOKEN']
            )

        try:
            start_time = datetime.now()

            # 测试getMe API
            url = f'https://api.telegram.org/bot{bot_token}/getMe'

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response_time = (datetime.now() - start_time).total_seconds() * 1000

                    if response.status == 200:
                        data = await response.json()
                        if data.get('ok'):
                            # 如果有chat_id，测试发送消息权限
                            if chat_id:
                                send_result = await self._test_telegram_send(bot_token, chat_id)
                                if not send_result:
                                    return APIValidationResult(
                                        service='Telegram Bot',
                                        is_valid=False,
                                        response_time_ms=response_time,
                                        error_message='无法发送消息到指定chat_id',
                                        quota_remaining=None,
                                        recommendations=['检查 KEYWORD_TOOL_TELEGRAM_CHAT_ID 是否正确']
                                    )

                            return APIValidationResult(
                                service='Telegram Bot',
                                is_valid=True,
                                response_time_ms=response_time,
                                error_message=None,
                                quota_remaining=None,
                                recommendations=[]
                            )

                    return APIValidationResult(
                        service='Telegram Bot',
                        is_valid=False,
                        response_time_ms=response_time,
                        error_message=f'HTTP {response.status}',
                        quota_remaining=None,
                        recommendations=['检查Telegram Bot token是否正确']
                    )

        except Exception as e:
            return APIValidationResult(
                service='Telegram Bot',
                is_valid=False,
                response_time_ms=None,
                error_message=str(e),
                quota_remaining=None,
                recommendations=['检查网络连接和Telegram Bot配置']
            )

    async def _test_telegram_send(self, bot_token: str, chat_id: str) -> bool:
        """测试Telegram发送消息"""
        try:
            url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
            data = {
                'chat_id': chat_id,
                'text': '🔧 配置验证测试消息 - Configuration Test',
                'disable_notification': True
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return response.status == 200

        except Exception:
            return False

    async def _check_network_connectivity(self) -> Dict[str, Any]:
        """检查网络连接"""
        test_urls = [
            'https://www.google.com',
            'https://api.reddit.com',
            'https://www.googleapis.com',
            'https://api.telegram.org'
        ]

        results = {}
        successful_connections = 0

        for url in test_urls:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        results[url] = {
                            'status': response.status,
                            'accessible': response.status < 400
                        }
                        if response.status < 400:
                            successful_connections += 1
            except Exception as e:
                results[url] = {
                    'status': None,
                    'accessible': False,
                    'error': str(e)
                }

        return {
            'internet_available': successful_connections > 0,
            'connectivity_score': successful_connections / len(test_urls),
            'test_results': results,
            'total_tests': len(test_urls),
            'successful_connections': successful_connections
        }

    def _generate_recommendations(self, env_check: Dict, api_validations: List[APIValidationResult],
                                network_status: Dict) -> List[str]:
        """生成修复建议"""
        recommendations = []

        # 环境变量建议
        if env_check['missing_count'] > 0:
            recommendations.append("📝 创建 .env 文件并设置缺失的环境变量")
            recommendations.append("📖 参考 .env.example 文件了解所需配置")

        # API建议
        failed_apis = [api for api in api_validations if not api.is_valid]
        if failed_apis:
            recommendations.append("🔑 检查并更新失效的API凭据")
            for api in failed_apis:
                recommendations.extend(api.recommendations)

        # 网络建议
        if network_status['connectivity_score'] < 0.5:
            recommendations.append("🌐 检查网络连接和防火墙设置")

        # 通用建议
        if not recommendations:
            recommendations.append("✅ 配置看起来正常，可以开始使用工具")

        return recommendations

    def _generate_next_steps(self, errors: List[str], warnings: List[str]) -> List[str]:
        """生成下一步操作建议"""
        next_steps = []

        if errors:
            next_steps.append("1. 解决上述错误问题")
            next_steps.append("2. 重新运行配置验证")
            next_steps.append("3. 确认所有API凭据有效")
        elif warnings:
            next_steps.append("1. 检查警告信息")
            next_steps.append("2. 可以继续使用但建议解决警告")
        else:
            next_steps.append("1. 配置验证通过")
            next_steps.append("2. 可以正常使用关键词分析工具")
            next_steps.append("3. 建议定期运行配置验证")

        return next_steps

    async def _save_report(self, report: ConfigValidationReport) -> None:
        """保存验证报告"""
        # JSON格式报告
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = self.report_dir / f"validation_report_{timestamp_str}.json"

        try:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(report), f, indent=2, ensure_ascii=False, default=str)

            # 文本格式报告
            text_file = self.report_dir / f"validation_report_{timestamp_str}.txt"
            await self._generate_text_report(report, text_file)

            self.logger.info(f"验证报告已保存: {json_file}")

        except Exception as e:
            self.logger.error(f"保存报告失败: {e}")

    async def _generate_text_report(self, report: ConfigValidationReport, file_path: Path) -> None:
        """生成可读的文本报告"""
        content = f"""
# 关键词分析工具 - 配置验证报告
时间: {report.timestamp}
状态: {report.overall_status.upper()}

## 环境变量检查
- 总计需要: {report.environment_check['total_required']} 个
- 已配置: {report.environment_check['present_count']} 个
- 缺失: {report.environment_check['missing_count']} 个

## API验证结果
"""

        for api in report.api_validations:
            status_icon = "✅" if api.is_valid else "❌"
            content += f"{status_icon} {api.service}\n"
            if api.response_time_ms:
                content += f"   响应时间: {api.response_time_ms:.0f}ms\n"
            if api.error_message:
                content += f"   错误: {api.error_message}\n"

        content += f"""
## 网络连接
- 连接性评分: {report.network_status['connectivity_score']:.2%}
- 成功连接: {report.network_status['successful_connections']}/{report.network_status['total_tests']}

## 问题和建议
"""

        if report.errors:
            content += "### 错误:\n"
            for error in report.errors:
                content += f"- ❌ {error}\n"

        if report.warnings:
            content += "### 警告:\n"
            for warning in report.warnings:
                content += f"- ⚠️ {warning}\n"

        if report.recommendations:
            content += "### 建议:\n"
            for rec in report.recommendations:
                content += f"- {rec}\n"

        if report.next_steps:
            content += "### 下一步:\n"
            for step in report.next_steps:
                content += f"- {step}\n"

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            self.logger.error(f"生成文本报告失败: {e}")


# 便捷函数
async def validate_configuration() -> ConfigValidationReport:
    """验证配置的便捷函数"""
    validator = ConfigValidator()
    return await validator.validate_all()


def print_validation_summary(report: ConfigValidationReport) -> None:
    """打印验证摘要"""
    safe_print(f"\n[搜索] 配置验证结果: {report.overall_status.upper()}")
    safe_print(f"[日期] 验证时间: {report.timestamp}")

    safe_print(f"\n[数据] 环境变量: {report.environment_check['present_count']}/{report.environment_check['total_required']}")

    safe_print("\n[网络] API状态:")
    for api in report.api_validations:
        status_icon = "[完成]" if api.is_valid else "[错误]"
        response_info = f" ({api.response_time_ms:.0f}ms)" if api.response_time_ms else ""
        safe_print(f"  {status_icon} {api.service}{response_info}")

    safe_print(f"\n[网络] 网络连接: {report.network_status['connectivity_score']:.0%}")

    if report.errors:
        safe_print("\n[错误] 错误:")
        for error in report.errors:
            safe_print(f"  - {error}")

    if report.recommendations:
        safe_print("\n[建议] 建议:")
        for rec in report.recommendations[:3]:  # 只显示前3个建议
            safe_print(f"  - {rec}")


# 命令行接口
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='配置验证工具')
    parser.add_argument('--quiet', '-q', action='store_true', help='静默模式，只输出错误')
    parser.add_argument('--json', action='store_true', help='输出JSON格式结果')
    parser.add_argument('--save-report', action='store_true', help='保存详细报告到文件')

    args = parser.parse_args()

    async def main():
        try:
            report = await validate_configuration()

            if args.json:
                print(json.dumps(asdict(report), indent=2, default=str))
            elif not args.quiet:
                print_validation_summary(report)

            # 返回相应的退出代码
            if report.overall_status == 'valid':
                return 0
            elif report.overall_status == 'partial':
                return 1
            else:
                return 2

        except Exception as e:
            if not args.quiet:
                safe_print(f"[错误] 验证过程出错: {e}")
            return 3

    exit_code = asyncio.run(main())
    sys.exit(exit_code)