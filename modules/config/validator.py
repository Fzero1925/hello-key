"""
配置验证集成模块 - Configuration Validation Integration

提供轻量级的配置验证功能，供主要模块在运行前调用。
与独立的validate_config.py脚本配合使用。

功能：
- 快速配置检查
- 集成到主要工作流
- 错误收集和报告
- 优雅的降级处理
"""

import os
import sys
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from .config_manager import ConfigManager


@dataclass
class ValidationIssue:
    """验证问题"""
    level: str  # 'error', 'warning', 'info'
    category: str  # 'environment', 'api', 'network'
    message: str
    recommendation: str


class QuickValidator:
    """快速配置验证器"""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or ConfigManager()
        self.logger = logging.getLogger(__name__)

    def validate_for_keyword_fetching(self) -> Tuple[bool, List[ValidationIssue]]:
        """验证关键词获取所需的配置"""
        issues = []
        can_proceed = True

        # 检查基础配置
        basic_issues = self._check_basic_config()
        issues.extend(basic_issues)

        # 检查关键词获取相关的API
        reddit_ok = self._check_reddit_config()
        youtube_ok = self._check_youtube_config()

        if not reddit_ok:
            issues.append(ValidationIssue(
                level='warning',
                category='api',
                message='Reddit API凭据未配置',
                recommendation='设置KEYWORD_TOOL_REDDIT_CLIENT_ID和KEYWORD_TOOL_REDDIT_CLIENT_SECRET以启用Reddit数据源'
            ))

        if not youtube_ok:
            issues.append(ValidationIssue(
                level='warning',
                category='api',
                message='YouTube API凭据未配置',
                recommendation='设置KEYWORD_TOOL_YOUTUBE_API_KEY以启用YouTube数据源'
            ))

        # 如果所有API都不可用，则无法继续
        if not (reddit_ok or youtube_ok):
            issues.append(ValidationIssue(
                level='error',
                category='api',
                message='没有可用的数据源API',
                recommendation='至少配置一个API凭据以获取关键词数据'
            ))
            can_proceed = False

        return can_proceed, issues

    def validate_for_topic_fetching(self) -> Tuple[bool, List[ValidationIssue]]:
        """验证话题获取所需的配置"""
        issues = []
        can_proceed = True

        # 检查基础配置
        basic_issues = self._check_basic_config()
        issues.extend(basic_issues)

        # 话题获取需要相同的API
        reddit_ok = self._check_reddit_config()
        youtube_ok = self._check_youtube_config()

        if not reddit_ok:
            issues.append(ValidationIssue(
                level='warning',
                category='api',
                message='Reddit API凭据未配置',
                recommendation='设置Reddit凭据以获取Reddit热门话题'
            ))

        if not youtube_ok:
            issues.append(ValidationIssue(
                level='warning',
                category='api',
                message='YouTube API凭据未配置',
                recommendation='设置YouTube凭据以获取YouTube热门话题'
            ))

        # 话题分析可以在没有API的情况下工作（使用缓存数据）
        if not (reddit_ok or youtube_ok):
            issues.append(ValidationIssue(
                level='warning',
                category='api',
                message='没有配置话题数据源API',
                recommendation='将使用缓存数据进行分析，但无法获取最新话题'
            ))

        return can_proceed, issues

    def validate_for_realtime_analysis(self) -> Tuple[bool, List[ValidationIssue]]:
        """验证实时分析所需的配置"""
        issues = []
        can_proceed = True

        # 检查基础配置
        basic_issues = self._check_basic_config()
        issues.extend(basic_issues)

        # 检查Telegram配置（用于通知）
        telegram_ok = self._check_telegram_config()
        if not telegram_ok:
            issues.append(ValidationIssue(
                level='warning',
                category='api',
                message='Telegram通知未配置',
                recommendation='设置KEYWORD_TOOL_TELEGRAM_BOT_TOKEN和KEYWORD_TOOL_TELEGRAM_CHAT_ID以启用通知'
            ))

        # 实时分析可以在没有通知的情况下运行
        return can_proceed, issues

    def _check_basic_config(self) -> List[ValidationIssue]:
        """检查基础配置"""
        issues = []

        # 检查配置管理器状态
        validation_result = self.config_manager.validate_config()
        if not validation_result.is_valid:
            for error in validation_result.errors:
                issues.append(ValidationIssue(
                    level='error',
                    category='environment',
                    message=error,
                    recommendation='检查环境变量配置'
                ))

        return issues

    def _check_reddit_config(self) -> bool:
        """检查Reddit配置"""
        credentials = self.config_manager.get_api_credentials()
        client_id = credentials.get('reddit_client_id', '')
        client_secret = credentials.get('reddit_client_secret', '')
        return bool(client_id and client_secret)

    def _check_youtube_config(self) -> bool:
        """检查YouTube配置"""
        credentials = self.config_manager.get_api_credentials()
        api_key = credentials.get('youtube_api_key', '')
        return bool(api_key)

    def _check_telegram_config(self) -> bool:
        """检查Telegram配置"""
        credentials = self.config_manager.get_api_credentials()
        bot_token = credentials.get('telegram_bot_token', '')
        chat_id = credentials.get('telegram_chat_id', '')
        return bool(bot_token and chat_id)

    def format_issues_for_logging(self, issues: List[ValidationIssue]) -> str:
        """格式化问题用于日志输出"""
        if not issues:
            return "✅ 配置验证通过"

        lines = ["📋 配置验证问题:"]
        for issue in issues:
            icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(issue.level, "•")
            lines.append(f"  {icon} {issue.message}")
            lines.append(f"    💡 {issue.recommendation}")

        return "\n".join(lines)

    def format_issues_for_telegram(self, issues: List[ValidationIssue]) -> str:
        """格式化问题用于Telegram通知"""
        if not issues:
            return "✅ 配置验证通过"

        lines = ["🔧 <b>配置问题检测</b>"]

        errors = [i for i in issues if i.level == 'error']
        warnings = [i for i in issues if i.level == 'warning']

        if errors:
            lines.append("\n❌ <b>错误:</b>")
            for error in errors[:3]:  # 最多显示3个错误
                lines.append(f"• {error.message}")

        if warnings:
            lines.append("\n⚠️ <b>警告:</b>")
            for warning in warnings[:3]:  # 最多显示3个警告
                lines.append(f"• {warning.message}")

        lines.append(f"\n📝 请运行 <code>python scripts/validate_config.py</code> 查看详细信息")

        return "\n".join(lines)


# 导入编码处理器
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.encoding_handler import safe_print

# 便捷函数
def validate_before_keyword_fetching(config_manager: Optional[ConfigManager] = None) -> Tuple[bool, List[ValidationIssue]]:
    """关键词获取前的验证"""
    validator = QuickValidator(config_manager)
    return validator.validate_for_keyword_fetching()


def validate_before_topic_fetching(config_manager: Optional[ConfigManager] = None) -> Tuple[bool, List[ValidationIssue]]:
    """话题获取前的验证"""
    validator = QuickValidator(config_manager)
    return validator.validate_for_topic_fetching()


def validate_before_realtime_analysis(config_manager: Optional[ConfigManager] = None) -> Tuple[bool, List[ValidationIssue]]:
    """实时分析前的验证"""
    validator = QuickValidator(config_manager)
    return validator.validate_for_realtime_analysis()


def log_validation_issues(issues: List[ValidationIssue], logger: logging.Logger) -> None:
    """记录验证问题到日志"""
    validator = QuickValidator()
    message = validator.format_issues_for_logging(issues)

    # 根据问题级别选择日志级别
    has_errors = any(issue.level == 'error' for issue in issues)
    has_warnings = any(issue.level == 'warning' for issue in issues)

    if has_errors:
        logger.error(message)
    elif has_warnings:
        logger.warning(message)
    else:
        logger.info(message)


# 装饰器版本
def validate_config(validation_type: str = 'basic'):
    """配置验证装饰器"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            validator = QuickValidator()

            if validation_type == 'keyword_fetching':
                can_proceed, issues = validator.validate_for_keyword_fetching()
            elif validation_type == 'topic_fetching':
                can_proceed, issues = validator.validate_for_topic_fetching()
            elif validation_type == 'realtime_analysis':
                can_proceed, issues = validator.validate_for_realtime_analysis()
            else:
                can_proceed, issues = True, []

            if issues:
                logger = logging.getLogger(func.__module__)
                log_validation_issues(issues, logger)

            if not can_proceed:
                raise RuntimeError("配置验证失败，无法继续执行")

            return await func(*args, **kwargs)

        def sync_wrapper(*args, **kwargs):
            validator = QuickValidator()

            if validation_type == 'keyword_fetching':
                can_proceed, issues = validator.validate_for_keyword_fetching()
            elif validation_type == 'topic_fetching':
                can_proceed, issues = validator.validate_for_topic_fetching()
            elif validation_type == 'realtime_analysis':
                can_proceed, issues = validator.validate_for_realtime_analysis()
            else:
                can_proceed, issues = True, []

            if issues:
                logger = logging.getLogger(func.__module__)
                log_validation_issues(issues, logger)

            if not can_proceed:
                raise RuntimeError("配置验证失败，无法继续执行")

            return func(*args, **kwargs)

        # 返回适当的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


if __name__ == "__main__":
    # 测试验证功能
    safe_print("[测试] 测试快速配置验证...")

    validator = QuickValidator()

    safe_print("\n[包] 关键词获取验证:")
    can_proceed, issues = validator.validate_for_keyword_fetching()
    safe_print(f"可以继续: {can_proceed}")
    safe_print(validator.format_issues_for_logging(issues))

    safe_print("\n[新闻] 话题获取验证:")
    can_proceed, issues = validator.validate_for_topic_fetching()
    safe_print(f"可以继续: {can_proceed}")
    safe_print(validator.format_issues_for_logging(issues))

    safe_print("\n[快速] 实时分析验证:")
    can_proceed, issues = validator.validate_for_realtime_analysis()
    safe_print(f"可以继续: {can_proceed}")
    safe_print(validator.format_issues_for_logging(issues))