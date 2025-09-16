#!/usr/bin/env python3
"""
统一编码处理器 - Unified Encoding Handler

解决Windows环境下的UTF-8编码问题，提供跨平台兼容的文本处理功能。

特性：
- Windows控制台UTF-8支持
- 统一的文件读写编码
- 安全的字符串处理
- 跨平台兼容性
- 错误回退机制
"""

import os
import sys
import locale
import logging
from pathlib import Path
from typing import Optional, Union, Any, TextIO
import codecs
import time
from contextlib import contextmanager


class EncodingHandler:
    """统一编码处理器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.platform = sys.platform
        self.is_windows = self.platform.startswith('win')

        # 检测系统编码
        self.system_encoding = self._detect_system_encoding()
        self.preferred_encoding = 'utf-8'

        # 初始化控制台编码
        self._setup_console_encoding()

    def _detect_system_encoding(self) -> str:
        """检测系统编码"""
        try:
            # 优先使用locale检测
            encoding = locale.getpreferredencoding()
            if encoding:
                return encoding.lower()
        except Exception:
            pass

        # fallback到系统默认
        if self.is_windows:
            return 'gbk'  # Windows中文系统默认
        else:
            return 'utf-8'  # Unix系统默认

    def _setup_console_encoding(self) -> None:
        """设置控制台编码"""
        if not self.is_windows:
            return

        try:
            # 尝试设置控制台为UTF-8模式
            if hasattr(sys.stdout, 'buffer'):
                sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
            if hasattr(sys.stderr, 'buffer'):
                sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')

            # 设置标准输入
            if hasattr(sys.stdin, 'buffer'):
                sys.stdin = codecs.getreader('utf-8')(sys.stdin.buffer, 'replace')

            self.logger.debug("Windows控制台UTF-8编码已配置")

        except Exception as e:
            self.logger.warning(f"配置控制台编码失败: {e}")

    def safe_encode(self, text: str, encoding: Optional[str] = None, errors: str = 'replace') -> bytes:
        """安全编码字符串"""
        if not isinstance(text, str):
            text = str(text)

        target_encoding = encoding or self.preferred_encoding

        try:
            return text.encode(target_encoding, errors=errors)
        except Exception as e:
            self.logger.warning(f"编码失败 ({target_encoding}): {e}")
            # fallback到系统编码
            try:
                return text.encode(self.system_encoding, errors='replace')
            except Exception:
                # 最后的fallback
                return text.encode('ascii', errors='replace')

    def safe_decode(self, data: bytes, encoding: Optional[str] = None, errors: str = 'replace') -> str:
        """安全解码字节串"""
        if isinstance(data, str):
            return data

        target_encoding = encoding or self.preferred_encoding

        try:
            return data.decode(target_encoding, errors=errors)
        except Exception as e:
            self.logger.warning(f"解码失败 ({target_encoding}): {e}")
            # 尝试系统编码
            try:
                return data.decode(self.system_encoding, errors='replace')
            except Exception:
                # 最后的fallback
                return data.decode('ascii', errors='replace')

    def open_file(self, file_path: Union[str, Path], mode: str = 'r',
                  encoding: Optional[str] = None, **kwargs) -> TextIO:
        """安全打开文件"""
        target_encoding = encoding or self.preferred_encoding

        try:
            return open(file_path, mode, encoding=target_encoding, **kwargs)
        except Exception as e:
            self.logger.warning(f"使用{target_encoding}编码打开文件失败: {e}")
            # fallback到系统编码
            try:
                return open(file_path, mode, encoding=self.system_encoding, **kwargs)
            except Exception:
                # 最后的fallback - 不指定编码
                return open(file_path, mode, **kwargs)

    def read_file(self, file_path: Union[str, Path], encoding: Optional[str] = None) -> str:
        """安全读取文件"""
        target_encoding = encoding or self.preferred_encoding

        try:
            with open(file_path, 'r', encoding=target_encoding) as f:
                return f.read()
        except UnicodeDecodeError as e:
            self.logger.warning(f"使用{target_encoding}读取文件失败: {e}")
            # 尝试系统编码
            try:
                with open(file_path, 'r', encoding=self.system_encoding) as f:
                    return f.read()
            except Exception:
                # 尝试二进制读取后解码
                try:
                    with open(file_path, 'rb') as f:
                        data = f.read()
                    return self.safe_decode(data)
                except Exception as final_e:
                    self.logger.error(f"读取文件彻底失败: {final_e}")
                    raise

    def write_file(self, file_path: Union[str, Path], content: str,
                   encoding: Optional[str] = None, mode: str = 'w') -> None:
        """安全写入文件"""
        target_encoding = encoding or self.preferred_encoding

        # 确保目录存在
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(file_path, mode, encoding=target_encoding) as f:
                f.write(content)
        except Exception as e:
            self.logger.warning(f"使用{target_encoding}写入文件失败: {e}")
            # fallback到系统编码
            try:
                with open(file_path, mode, encoding=self.system_encoding) as f:
                    f.write(content)
            except Exception as final_e:
                self.logger.error(f"写入文件失败: {final_e}")
                raise

    def normalize_text(self, text: str) -> str:
        """标准化文本（处理特殊字符）"""
        if not isinstance(text, str):
            text = str(text)

        # 如果是Windows且包含特殊Unicode字符，进行处理
        if self.is_windows:
            # 替换常见的Unicode字符为ASCII等价物
            replacements = {
                '🔍': '[搜索]',
                '✅': '[完成]',
                '❌': '[错误]',
                '⚠️': '[警告]',
                '📊': '[数据]',
                '🚀': '[启动]',
                '💡': '[建议]',
                '🔧': '[配置]',
                '📝': '[文档]',
                '🎯': '[目标]',
                '⏳': '[等待]',
                '🧪': '[测试]',
                '📦': '[包]',
                '📰': '[新闻]',
                '⚡': '[快速]',
                '🌐': '[网络]',
                '🔑': '[密钥]',
                '📱': '[手机]',
                '🔥': '[热门]',
                '📈': '[趋势]',
                '💰': '[收益]',
                '📅': '[日期]',
                '📋': '[清单]',
                '⭐': '[星星]',
                '🎉': '[庆祝]',
                '🛠️': '[工具]',
                '📄': '[文件]',
                '🔒': '[锁定]',
                '🔓': '[解锁]'
            }

            for unicode_char, ascii_replacement in replacements.items():
                text = text.replace(unicode_char, ascii_replacement)

        return text

    def console_print(self, text: str, **kwargs) -> None:
        """控制台安全打印"""
        if self.is_windows:
            # Windows下先标准化文本
            text = self.normalize_text(text)

        try:
            print(text, **kwargs)
        except UnicodeEncodeError:
            # 如果还是失败，强制ASCII化
            safe_text = text.encode('ascii', errors='replace').decode('ascii')
            print(safe_text, **kwargs)

    @contextmanager
    def safe_stdout(self):
        """安全的stdout上下文管理器"""
        original_stdout = sys.stdout
        try:
            if self.is_windows and hasattr(sys.stdout, 'buffer'):
                sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
            yield
        finally:
            sys.stdout = original_stdout

    def get_safe_filename(self, filename: str) -> str:
        """获取安全的文件名（去除特殊字符）"""
        if not isinstance(filename, str):
            filename = str(filename)

        # 移除或替换文件名中的不安全字符
        unsafe_chars = '<>:"/\\|?*'
        safe_filename = filename

        for char in unsafe_chars:
            safe_filename = safe_filename.replace(char, '_')

        # 限制长度
        if len(safe_filename) > 200:
            safe_filename = safe_filename[:200]

        return safe_filename

    def format_for_json(self, data: Any) -> Any:
        """格式化数据用于JSON序列化"""
        if isinstance(data, str):
            return data
        elif isinstance(data, dict):
            return {key: self.format_for_json(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self.format_for_json(item) for item in data]
        elif isinstance(data, bytes):
            return self.safe_decode(data)
        else:
            return str(data)


# 全局编码处理器实例
_encoding_handler = None

def get_encoding_handler() -> EncodingHandler:
    """获取全局编码处理器实例"""
    global _encoding_handler
    if _encoding_handler is None:
        _encoding_handler = EncodingHandler()
    return _encoding_handler


# 便捷函数
def setup_windows_console() -> None:
    """设置Windows控制台编码"""
    handler = get_encoding_handler()
    # 编码处理器初始化时已经设置了控制台


def safe_print(text: str, **kwargs) -> None:
    """安全打印函数"""
    handler = get_encoding_handler()
    handler.console_print(text, **kwargs)


def safe_write(file_path: Union[str, Path], content: str, encoding: Optional[str] = None) -> None:
    """安全写文件函数"""
    handler = get_encoding_handler()
    handler.write_file(file_path, content, encoding)


def safe_read(file_path: Union[str, Path], encoding: Optional[str] = None) -> str:
    """安全读文件函数"""
    handler = get_encoding_handler()
    return handler.read_file(file_path, encoding)


def normalize_for_console(text: str) -> str:
    """标准化文本用于控制台显示"""
    handler = get_encoding_handler()
    return handler.normalize_text(text)


def retry_with_backoff(func, max_retries: int = 3, base_delay: float = 1.0):
    """重试机制装饰器，支持指数退避"""
    def wrapper(*args, **kwargs):
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise  # 最后一次尝试失败，抛出异常

                delay = base_delay * (2 ** attempt)  # 指数退避
                safe_print(f"尝试 {attempt + 1} 失败: {str(e)}")
                safe_print(f"等待 {delay:.1f} 秒后重试...")
                time.sleep(delay)

    return wrapper


def ensure_cross_platform_path(path: Union[str, Path]) -> Path:
    """确保路径跨平台兼容"""
    path_obj = Path(path)

    # 处理Windows路径分隔符
    if sys.platform.startswith('win'):
        # 确保Windows路径使用正确的分隔符
        return path_obj.resolve()
    else:
        # Unix系统路径处理
        return path_obj.resolve()


def safe_mkdir(path: Union[str, Path], parents: bool = True, exist_ok: bool = True) -> None:
    """安全创建目录，跨平台兼容"""
    try:
        path_obj = ensure_cross_platform_path(path)
        path_obj.mkdir(parents=parents, exist_ok=exist_ok)
    except Exception as e:
        safe_print(f"创建目录失败 {path}: {e}")
        raise


def get_temp_dir() -> Path:
    """获取临时目录，跨平台兼容"""
    if sys.platform.startswith('win'):
        return Path(os.environ.get('TEMP', 'C:/temp'))
    else:
        return Path('/tmp')


def check_disk_space(path: Union[str, Path], min_space_mb: int = 100) -> bool:
    """检查磁盘空间是否足够"""
    try:
        import shutil
        path_obj = ensure_cross_platform_path(path)
        if path_obj.exists():
            free_bytes = shutil.disk_usage(path_obj).free
            free_mb = free_bytes / (1024 * 1024)
            return free_mb >= min_space_mb
        return True  # 如果路径不存在，假设有足够空间
    except Exception:
        return True  # 检查失败时假设有足够空间


# 自动初始化（当模块被导入时）
if sys.platform.startswith('win'):
    try:
        setup_windows_console()
    except Exception:
        pass  # 静默失败


if __name__ == "__main__":
    # 测试编码处理功能
    print("Testing encoding handler...")

    handler = EncodingHandler()

    # 测试文本标准化
    test_text = "🔍 搜索中... ✅ 完成 ❌ 错误"
    normalized = handler.normalize_text(test_text)
    print(f"Original: {test_text}")
    print(f"Normalized: {normalized}")

    # 测试安全打印
    safe_print("🧪 测试安全打印功能")
    safe_print("包含中文和特殊字符：数据分析 📊")

    # 测试文件操作
    test_file = "test_encoding.txt"
    test_content = "测试内容\n包含中文和特殊字符 🎯\n"

    try:
        handler.write_file(test_file, test_content)
        read_content = handler.read_file(test_file)
        print(f"File test successful: {len(read_content)} chars read")

        # 清理
        os.remove(test_file)
    except Exception as e:
        print(f"File test failed: {e}")

    print("Encoding handler test completed!")