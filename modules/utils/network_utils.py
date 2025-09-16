#!/usr/bin/env python3
"""
网络工具模块 - Network Utilities

提供网络请求的重试机制、错误处理和跨平台支持

特性：
- HTTP请求重试机制
- 网络连接检查
- 用户代理轮换
- 速率限制处理
- 超时和错误恢复
"""

import time
import random
import asyncio
import aiohttp
import requests
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from urllib.parse import urlparse

from .encoding_handler import safe_print, retry_with_backoff


@dataclass
class RequestConfig:
    """网络请求配置"""
    max_retries: int = 3
    base_delay: float = 1.0
    timeout: float = 30.0
    headers: Dict[str, str] = None
    use_random_delay: bool = True

    def __post_init__(self):
        if self.headers is None:
            self.headers = self._get_default_headers()

    def _get_default_headers(self) -> Dict[str, str]:
        """获取默认请求头"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]

        return {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }


class NetworkClient:
    """统一的网络客户端，提供重试和错误处理"""

    def __init__(self, config: Optional[RequestConfig] = None):
        self.config = config or RequestConfig()
        self.session = requests.Session()
        self.session.headers.update(self.config.headers)

    def get(self, url: str, **kwargs) -> requests.Response:
        """GET请求，带重试机制"""
        @retry_with_backoff
        def _make_request():
            response = self.session.get(
                url,
                timeout=self.config.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response

        # 随机延迟避免被限制
        if self.config.use_random_delay:
            time.sleep(random.uniform(0.1, 0.5))

        return _make_request()

    def post(self, url: str, **kwargs) -> requests.Response:
        """POST请求，带重试机制"""
        @retry_with_backoff
        def _make_request():
            response = self.session.post(
                url,
                timeout=self.config.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response

        if self.config.use_random_delay:
            time.sleep(random.uniform(0.1, 0.5))

        return _make_request()

    def close(self):
        """关闭会话"""
        self.session.close()


class AsyncNetworkClient:
    """异步网络客户端"""

    def __init__(self, config: Optional[RequestConfig] = None):
        self.config = config or RequestConfig()
        self.session = None

    async def __aenter__(self):
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)

        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.config.headers
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """异步GET请求"""
        for attempt in range(self.config.max_retries):
            try:
                if self.config.use_random_delay:
                    await asyncio.sleep(random.uniform(0.1, 0.5))

                async with self.session.get(url, **kwargs) as response:
                    response.raise_for_status()
                    return response

            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    raise

                delay = self.config.base_delay * (2 ** attempt)
                safe_print(f"请求失败，{delay:.1f}秒后重试: {str(e)}")
                await asyncio.sleep(delay)

    async def post(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """异步POST请求"""
        for attempt in range(self.config.max_retries):
            try:
                if self.config.use_random_delay:
                    await asyncio.sleep(random.uniform(0.1, 0.5))

                async with self.session.post(url, **kwargs) as response:
                    response.raise_for_status()
                    return response

            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    raise

                delay = self.config.base_delay * (2 ** attempt)
                safe_print(f"请求失败，{delay:.1f}秒后重试: {str(e)}")
                await asyncio.sleep(delay)


def check_internet_connection(test_urls: List[str] = None) -> bool:
    """检查网络连接"""
    if test_urls is None:
        test_urls = [
            'https://www.google.com',
            'https://www.cloudflare.com',
            'https://httpbin.org/status/200'
        ]

    for url in test_urls:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return True
        except Exception:
            continue

    return False


def is_valid_url(url: str) -> bool:
    """检查URL是否有效"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def extract_domain(url: str) -> Optional[str]:
    """从URL提取域名"""
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except Exception:
        return None


class RateLimiter:
    """简单的速率限制器"""

    def __init__(self, max_requests: int = 10, time_window: float = 60.0):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []

    def wait_if_needed(self):
        """如果需要，等待以遵守速率限制"""
        now = time.time()

        # 移除时间窗口外的请求记录
        self.requests = [req_time for req_time in self.requests
                        if now - req_time < self.time_window]

        # 如果请求太多，等待
        if len(self.requests) >= self.max_requests:
            oldest_request = min(self.requests)
            wait_time = self.time_window - (now - oldest_request)
            if wait_time > 0:
                safe_print(f"速率限制：等待 {wait_time:.1f} 秒")
                time.sleep(wait_time)

        # 记录这次请求
        self.requests.append(now)


# 便捷函数
def safe_request(url: str, method: str = 'GET', **kwargs) -> Optional[requests.Response]:
    """安全的HTTP请求，带错误处理"""
    try:
        client = NetworkClient()
        if method.upper() == 'GET':
            return client.get(url, **kwargs)
        elif method.upper() == 'POST':
            return client.post(url, **kwargs)
        else:
            raise ValueError(f"不支持的HTTP方法: {method}")
    except Exception as e:
        safe_print(f"网络请求失败 {url}: {e}")
        return None
    finally:
        if 'client' in locals():
            client.close()


async def async_safe_request(url: str, method: str = 'GET', **kwargs) -> Optional[aiohttp.ClientResponse]:
    """安全的异步HTTP请求"""
    try:
        async with AsyncNetworkClient() as client:
            if method.upper() == 'GET':
                return await client.get(url, **kwargs)
            elif method.upper() == 'POST':
                return await client.post(url, **kwargs)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
    except Exception as e:
        safe_print(f"异步网络请求失败 {url}: {e}")
        return None


if __name__ == "__main__":
    # 测试网络工具
    safe_print("测试网络工具模块...")

    # 测试网络连接
    if check_internet_connection():
        safe_print("[网络] 网络连接正常")
    else:
        safe_print("[网络] 网络连接异常")

    # 测试同步请求
    try:
        response = safe_request("https://httpbin.org/json")
        if response:
            safe_print(f"[网络] 同步请求成功: {response.status_code}")
    except Exception as e:
        safe_print(f"[网络] 同步请求失败: {e}")

    # 测试速率限制
    limiter = RateLimiter(max_requests=2, time_window=5.0)

    safe_print("[网络] 测试速率限制...")
    for i in range(3):
        limiter.wait_if_needed()
        safe_print(f"  请求 {i+1} 已发送")

    safe_print("网络工具测试完成")