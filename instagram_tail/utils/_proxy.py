import asyncio
import time
from typing import List, Optional

MAX_FAILS = 5

class Proxy:
    def __init__(self, url: str):
        self.url = url
        self.fail_count = 0
        self.last_used = 0.0
        self.cooldown_until = 0.0

    def mark_fail(self):
        self.fail_count += 1
        self.cooldown_until = time.time() + min(60 * self.fail_count, 300)

    def mark_success(self):
        self.fail_count = 0
        self.cooldown_until = 0.0

    def is_available(self) -> bool:
        return time.time() >= self.cooldown_until

    def mark_used(self):
        self.last_used = time.time()

class ProxyPool:
    def __init__(self, proxy_urls: List[str]):
        self._proxies: List[Proxy] = [Proxy(url) for url in proxy_urls]
        self._lock = asyncio.Lock()
        self._notifier = asyncio.Condition()

    async def get_proxy(self, wait: bool = True, timeout: float = 30.0) -> Optional[Proxy]:
        start = time.time()
        while True:
            async with self._lock:
                available = [p for p in self._proxies if p.is_available()]
                if available:
                    proxy = min(available, key=lambda p: p.last_used)
                    proxy.mark_used()
                    return proxy

            if not wait or (time.time() - start) > timeout:
                return None

            async with self._notifier:
                try:
                    await asyncio.wait_for(self._notifier.wait(), timeout=5)
                except asyncio.TimeoutError:
                    pass

    async def mark_fail(self, proxy: Proxy):
        async with self._lock:
            proxy.mark_fail()
            if proxy.fail_count >= MAX_FAILS:
                print(f"Удаление прокси после {MAX_FAILS} неудач: {proxy.url}")
                self._proxies.remove(proxy)
            self._notify()

    async def mark_success(self, proxy: Proxy):
        async with self._lock:
            proxy.mark_success()
            self._notify()

    def _notify(self):
        async def notify():
            async with self._notifier:
                self._notifier.notify_all()
        asyncio.create_task(notify())
