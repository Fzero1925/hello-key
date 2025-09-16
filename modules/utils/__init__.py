"""
Utilities Package - 工具包

提供通用的工具函数和跨平台兼容性处理。

包含：
- EncodingHandler: 统一编码处理
- 跨平台文件操作
- 字符串处理工具
- 系统兼容性函数
"""

from .encoding_handler import (
    EncodingHandler,
    setup_windows_console,
    safe_print,
    safe_write,
    safe_read,
    normalize_for_console,
    retry_with_backoff,
    ensure_cross_platform_path,
    safe_mkdir,
    get_temp_dir,
    check_disk_space
)

from .network_utils import (
    NetworkClient,
    AsyncNetworkClient,
    RequestConfig,
    RateLimiter,
    safe_request,
    async_safe_request,
    check_internet_connection,
    is_valid_url,
    extract_domain
)

__all__ = [
    # 编码处理
    'EncodingHandler',
    'setup_windows_console',
    'safe_print',
    'safe_write',
    'safe_read',
    'normalize_for_console',
    'retry_with_backoff',
    'ensure_cross_platform_path',
    'safe_mkdir',
    'get_temp_dir',
    'check_disk_space',
    # 网络工具
    'NetworkClient',
    'AsyncNetworkClient',
    'RequestConfig',
    'RateLimiter',
    'safe_request',
    'async_safe_request',
    'check_internet_connection',
    'is_valid_url',
    'extract_domain'
]