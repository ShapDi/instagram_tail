import asyncio
import json
import random
import time
from pathlib import Path
from typing import Optional, List

from instagram_tail.utils._types import AccountStatus


class Account:
    def __init__(self, data: dict):
        self.id = data.get("id")
        self.login = data.get("login")
        self.password = data.get("password")
        self.session_id = data.get("session_id")
        self.token = data.get("token")
        self.status = AccountStatus(data.get("status", AccountStatus.WORKING))
        self.last_checked = data.get("last_checked")
        self.fail_count = data.get("fail_count", 0)
        self.headers = data.get("headers")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "login": self.login,
            "password": self.password,
            "session_id": self.session_id,
            "token": self.token,
            "status": self.status,
            "last_checked": self.last_checked,
            "fail_count": self.fail_count,
        }


class AccountPool:
    def __init__(self, json_path: str):
        self.json_path = Path(json_path)
        self._accounts: List[Account] = []
        self._lock = asyncio.Lock()
        self._current_index = 0

    async def load_accounts(self):
        if not self.json_path.exists():
            raise FileNotFoundError(f"File {self.json_path} not found")

        with self.json_path.open("r", encoding="utf-8") as f:
            accounts_data = json.load(f)

        self._accounts = [Account(data) for data in accounts_data]

    async def save_accounts(self):
        data = [account.to_dict() for account in self._accounts]
        with self.json_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    async def get_working_account(self) -> Optional[Account]:
        async with self._lock:
            working_accounts = [
                acc for acc in self._accounts if acc.status == AccountStatus.WORKING
            ]

            if not working_accounts:
                return None

            account = working_accounts[self._current_index % len(working_accounts)]
            self._current_index += 1
            return account

    async def mark_account_status(self, account: Account, new_status: AccountStatus):
        async with self._lock:
            account.status = new_status
            if account.status != AccountStatus.WORKING:
                self._current_index = self._current_index % len(
                    [
                        acc
                        for acc in self._accounts
                        if acc.status == AccountStatus.WORKING
                    ]
                )
            await self.save_accounts()

    async def set_account_session_and_token(
        self, account: Account, session_id: str, token: str
    ):
        async with self._lock:
            account.session_id = session_id
            account.token = token
            await self.save_accounts()

    async def wait_for_working_account(
        self, check_interval: float = 5.0, timeout: Optional[float] = None
    ) -> Account:
        start_time = time.monotonic()

        while True:
            async with self._lock:
                working_accounts = [
                    acc for acc in self._accounts if acc.status == AccountStatus.WORKING
                ]
                if working_accounts:
                    return random.choice(working_accounts)

            if timeout is not None and (time.monotonic() - start_time) > timeout:
                raise TimeoutError(f"Could not find work account in {timeout} seconds")

            # print(
            #     f"[AccountPool] Нет рабочих аккаунтов, жду {check_interval} секунд..."
            # )
            await asyncio.sleep(check_interval)
