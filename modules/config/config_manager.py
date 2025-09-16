#!/usr/bin/env python3
"""
统一配置管理器 - Unified Configuration Manager

支持环境变量和YAML配置文件的混合管理方案。
实现变量引用、跨平台兼容和安全的凭据管理。

特性：
- 环境变量优先级管理
- YAML配置文件解析
- 变量引用语法 ${VARIABLE_NAME}
- 跨平台路径处理
- 配置验证和错误处理
"""

import os
import sys
import yaml
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class ConfigValidationResult:
    """配置验证结果"""
    is_valid: bool
    missing_variables: List[str]
    invalid_values: List[str]
    errors: List[str]
    warnings: List[str]


class ConfigManager:
    """统一配置管理器"""

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_file: 配置文件路径，默认为项目根目录的config.yml
        """
        self.logger = self._setup_logging()

        # 确定配置文件路径
        if config_file is None:
            self.config_file = self._get_default_config_path()
        else:
            self.config_file = Path(config_file)

        # 加载配置
        self._raw_config = {}
        self._processed_config = {}
        self._env_prefix = 'KEYWORD_TOOL_'

        self.load_config()

    def _setup_logging(self) -> logging.Logger:
        """设置日志系统"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)

    def _get_default_config_path(self) -> Path:
        """获取默认配置文件路径"""
        # 查找项目根目录
        current_path = Path(__file__).parent
        while current_path.parent != current_path:
            config_file = current_path / 'config.yml'
            if config_file.exists():
                return config_file

            # 检查是否在项目根目录（包含keyword_engine.yml）
            if (current_path / 'keyword_engine.yml').exists():
                return current_path / 'config.yml'

            current_path = current_path.parent

        # 如果找不到，使用当前脚本所在目录的上上级
        project_root = Path(__file__).parent.parent.parent
        return project_root / 'config.yml'

    def load_config(self) -> None:
        """加载配置文件和环境变量"""
        try:
            # 1. 加载YAML配置文件
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._raw_config = yaml.safe_load(f) or {}
                self.logger.info(f"配置文件已加载: {self.config_file}")
            else:
                self.logger.warning(f"配置文件不存在: {self.config_file}")
                self._raw_config = {}

            # 2. 处理变量引用
            self._processed_config = self._process_variables(self._raw_config)

            # 3. 加载环境变量覆盖
            self._load_env_overrides()

            self.logger.info("配置加载完成")

        except Exception as e:
            self.logger.error(f"配置加载失败: {e}")
            self._processed_config = self._get_fallback_config()

    def _process_variables(self, config: Any) -> Any:
        """处理配置中的变量引用"""
        if isinstance(config, dict):
            return {key: self._process_variables(value) for key, value in config.items()}
        elif isinstance(config, list):
            return [self._process_variables(item) for item in config]
        elif isinstance(config, str):
            return self._substitute_variables(config)
        else:
            return config

    def _substitute_variables(self, value: str) -> str:
        """替换字符串中的变量引用"""
        if not isinstance(value, str):
            return value

        # 匹配 ${VARIABLE_NAME} 格式
        pattern = r'\$\{([^}]+)\}'

        def replace_var(match):
            var_name = match.group(1)
            env_value = os.getenv(var_name)

            if env_value is not None:
                return env_value
            else:
                self.logger.warning(f"环境变量未找到: {var_name}")
                return match.group(0)  # 保持原样

        return re.sub(pattern, replace_var, value)

    def _load_env_overrides(self) -> None:
        """加载环境变量覆盖配置"""
        # 支持通过环境变量直接设置配置项
        env_mapping = {
            f'{self._env_prefix}REDDIT_CLIENT_ID': ['api_credentials', 'reddit_client_id'],
            f'{self._env_prefix}REDDIT_CLIENT_SECRET': ['api_credentials', 'reddit_client_secret'],
            f'{self._env_prefix}YOUTUBE_API_KEY': ['api_credentials', 'youtube_api_key'],
            f'{self._env_prefix}TELEGRAM_BOT_TOKEN': ['api_credentials', 'telegram_bot_token'],
            f'{self._env_prefix}TELEGRAM_CHAT_ID': ['api_credentials', 'telegram_chat_id'],
        }

        for env_var, config_path in env_mapping.items():
            value = os.getenv(env_var)
            if value:
                self._set_nested_config(self._processed_config, config_path, value)

    def _set_nested_config(self, config: Dict, path: List[str], value: Any) -> None:
        """设置嵌套配置项"""
        current = config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value

    def _get_fallback_config(self) -> Dict[str, Any]:
        """获取后备配置"""
        return {
            'api_credentials': {
                'reddit_client_id': os.getenv(f'{self._env_prefix}REDDIT_CLIENT_ID', ''),
                'reddit_client_secret': os.getenv(f'{self._env_prefix}REDDIT_CLIENT_SECRET', ''),
                'youtube_api_key': os.getenv(f'{self._env_prefix}YOUTUBE_API_KEY', ''),
                'telegram_bot_token': os.getenv(f'{self._env_prefix}TELEGRAM_BOT_TOKEN', ''),
                'telegram_chat_id': os.getenv(f'{self._env_prefix}TELEGRAM_CHAT_ID', ''),
            },
            'retry_settings': {
                'max_attempts': 3,
                'backoff_factor': 1.0,
                'timeout_seconds': 30,
                'total_timeout_minutes': 5
            },
            'data_sources': {
                'cache_ttl_hours': 1,
                'enable_fallback': True,
                'user_agents': {
                    'reddit': 'KeywordTool-Reddit/1.0',
                    'youtube': 'KeywordTool-YouTube/1.0',
                    'general': 'KeywordTool/1.0'
                }
            },
            'monitoring': {
                'enable_metrics': True,
                'report_interval_hours': 24,
                'alert_on_failures': True
            }
        }

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项值

        Args:
            key: 配置项键，支持点号分隔的嵌套键 如 'api_credentials.reddit_client_id'
            default: 默认值

        Returns:
            配置项值
        """
        keys = key.split('.')
        current = self._processed_config

        try:
            for k in keys:
                current = current[k]
            return current
        except (KeyError, TypeError):
            return default

    def get_api_credentials(self) -> Dict[str, str]:
        """获取API凭据配置"""
        return self.get('api_credentials', {})

    def get_retry_settings(self) -> Dict[str, Any]:
        """获取重试配置"""
        return self.get('retry_settings', {})

    def get_data_source_config(self) -> Dict[str, Any]:
        """获取数据源配置"""
        return self.get('data_sources', {})

    def validate_config(self) -> ConfigValidationResult:
        """验证配置完整性"""
        missing_vars = []
        invalid_values = []
        errors = []
        warnings = []

        # 检查必需的API凭据
        required_credentials = [
            'reddit_client_id',
            'reddit_client_secret',
            'youtube_api_key',
            'telegram_bot_token',
            'telegram_chat_id'
        ]

        credentials = self.get_api_credentials()
        for cred in required_credentials:
            value = credentials.get(cred, '')
            if not value or value.startswith('${'):
                missing_vars.append(f'api_credentials.{cred}')

        # 检查重试配置的合理性
        retry_config = self.get_retry_settings()
        max_attempts = retry_config.get('max_attempts', 3)
        if not isinstance(max_attempts, int) or max_attempts < 1 or max_attempts > 10:
            invalid_values.append('retry_settings.max_attempts (应该是1-10之间的整数)')

        timeout = retry_config.get('timeout_seconds', 30)
        if not isinstance(timeout, (int, float)) or timeout < 5 or timeout > 300:
            invalid_values.append('retry_settings.timeout_seconds (应该是5-300之间的数字)')

        # 检查必需环境变量
        required_env_vars = [
            f'{self._env_prefix}REDDIT_CLIENT_ID',
            f'{self._env_prefix}REDDIT_CLIENT_SECRET',
            f'{self._env_prefix}YOUTUBE_API_KEY',
            f'{self._env_prefix}TELEGRAM_BOT_TOKEN',
            f'{self._env_prefix}TELEGRAM_CHAT_ID'
        ]

        for env_var in required_env_vars:
            if not os.getenv(env_var):
                missing_vars.append(f'环境变量: {env_var}')

        # 生成摘要
        is_valid = len(missing_vars) == 0 and len(invalid_values) == 0

        if missing_vars:
            errors.append(f"缺少必需配置项: {', '.join(missing_vars)}")

        if invalid_values:
            errors.append(f"无效配置值: {', '.join(invalid_values)}")

        return ConfigValidationResult(
            is_valid=is_valid,
            missing_variables=missing_vars,
            invalid_values=invalid_values,
            errors=errors,
            warnings=warnings
        )

    def create_example_config(self, file_path: Optional[Path] = None) -> None:
        """创建示例配置文件"""
        if file_path is None:
            file_path = self.config_file.parent / 'config.yml.example'

        example_config = {
            'api_credentials': {
                'reddit_client_id': '${KEYWORD_TOOL_REDDIT_CLIENT_ID}',
                'reddit_client_secret': '${KEYWORD_TOOL_REDDIT_CLIENT_SECRET}',
                'youtube_api_key': '${KEYWORD_TOOL_YOUTUBE_API_KEY}',
                'telegram_bot_token': '${KEYWORD_TOOL_TELEGRAM_BOT_TOKEN}',
                'telegram_chat_id': '${KEYWORD_TOOL_TELEGRAM_CHAT_ID}',
            },
            'retry_settings': {
                'max_attempts': 3,
                'backoff_factor': 1.0,
                'timeout_seconds': 30,
                'total_timeout_minutes': 5
            },
            'data_sources': {
                'cache_ttl_hours': 1,
                'enable_fallback': True,
                'user_agents': {
                    'reddit': 'KeywordTool-Reddit/1.0',
                    'youtube': 'KeywordTool-YouTube/1.0',
                    'general': 'KeywordTool/1.0'
                }
            },
            'monitoring': {
                'enable_metrics': True,
                'report_interval_hours': 24,
                'alert_on_failures': True
            }
        }

        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(example_config, f, default_flow_style=False, allow_unicode=True, indent=2)

        self.logger.info(f"示例配置文件已创建: {file_path}")

    def create_env_example(self, file_path: Optional[Path] = None) -> None:
        """创建环境变量示例文件"""
        if file_path is None:
            file_path = self.config_file.parent / '.env.example'

        env_content = """# 关键词分析工具 - 环境变量配置
# 复制此文件为 .env 并填入实际值

# Reddit API 凭据
# 从 https://www.reddit.com/prefs/apps 获取
KEYWORD_TOOL_REDDIT_CLIENT_ID=your_reddit_client_id_here
KEYWORD_TOOL_REDDIT_CLIENT_SECRET=your_reddit_client_secret_here

# YouTube Data API v3 密钥
# 从 Google Cloud Console 获取
KEYWORD_TOOL_YOUTUBE_API_KEY=your_youtube_api_key_here

# Telegram Bot 配置
# 通过 @BotFather 创建bot获取
KEYWORD_TOOL_TELEGRAM_BOT_TOKEN=your_bot_token_here
KEYWORD_TOOL_TELEGRAM_CHAT_ID=your_chat_id_here

# 可选：数据库配置（如果需要）
# KEYWORD_TOOL_DATABASE_URL=sqlite:///data/keywords.db

# 可选：代理配置（如果需要）
# KEYWORD_TOOL_HTTP_PROXY=http://proxy.example.com:8080
# KEYWORD_TOOL_HTTPS_PROXY=https://proxy.example.com:8080
"""

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(env_content)

        self.logger.info(f"环境变量示例文件已创建: {file_path}")

    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要（隐藏敏感信息）"""
        summary = {}

        # API凭据状态（不显示实际值）
        credentials = self.get_api_credentials()
        summary['api_credentials_status'] = {
            key: '已配置' if value else '未配置'
            for key, value in credentials.items()
        }

        # 其他配置
        summary['retry_settings'] = self.get_retry_settings()
        summary['data_sources'] = self.get_data_source_config()
        summary['monitoring'] = self.get('monitoring', {})

        return summary


# 全局配置管理器实例
_config_manager = None

def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

def reload_config() -> None:
    """重新加载配置"""
    global _config_manager
    _config_manager = None
    _config_manager = ConfigManager()


# 演示和测试
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='配置管理器')
    parser.add_argument('--create-examples', action='store_true',
                      help='创建示例配置文件')
    parser.add_argument('--validate', action='store_true',
                      help='验证当前配置')
    parser.add_argument('--show-config', action='store_true',
                      help='显示当前配置摘要')

    args = parser.parse_args()

    config = ConfigManager()

    if args.create_examples:
        print("创建示例配置文件...")
        config.create_example_config()
        config.create_env_example()

    elif args.validate:
        print("验证配置...")
        result = config.validate_config()
        print(f"配置有效: {result.is_valid}")
        if result.errors:
            print("错误:")
            for error in result.errors:
                print(f"  - {error}")
        if result.warnings:
            print("警告:")
            for warning in result.warnings:
                print(f"  - {warning}")

    elif args.show_config:
        print("当前配置摘要:")
        summary = config.get_config_summary()
        print(yaml.dump(summary, default_flow_style=False, allow_unicode=True))

    else:
        print("配置管理器已初始化")
        print("使用 --help 查看可用选项")