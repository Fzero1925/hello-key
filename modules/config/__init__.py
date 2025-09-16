"""
Configuration Management Package - 配置管理包

提供统一的配置加载、验证和管理功能。
支持环境变量和YAML配置文件的混合方案。

包含：
- ConfigManager: 统一配置管理器
- QuickValidator: 快速配置验证器
- 环境变量加载和验证
- 配置文件解析和变量替换
- 跨平台兼容性处理
"""

from .config_manager import ConfigManager
from .validator import (
    QuickValidator,
    ValidationIssue,
    validate_before_keyword_fetching,
    validate_before_topic_fetching,
    validate_before_realtime_analysis,
    log_validation_issues,
    validate_config
)

__all__ = [
    'ConfigManager',
    'QuickValidator',
    'ValidationIssue',
    'validate_before_keyword_fetching',
    'validate_before_topic_fetching',
    'validate_before_realtime_analysis',
    'log_validation_issues',
    'validate_config'
]