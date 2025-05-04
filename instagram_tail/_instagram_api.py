from abc import ABC
from types import TracebackType

import httpx
from httpx import AsyncClient

from instagram_tail.auth.web_login_service import WebLoginServiceAsync
from instagram_tail.clients.client_async import (
    ClientPublicAsync,
    ClientPrivateAsync,
    Client,
)


class TailApi(ABC):
    pass


class InstTailApiAsync(TailApi):
    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        inst_session_id: str | None = None,
        token: str | None = None,
        proxy: str | None = None,
    ):
        self._username = username
        self._password = password
        self._inst_session_id = inst_session_id
        self._token = token
        self._proxy = proxy
        self.user_id = None

    def _init_session(self):
        headers = {
            "user-agent": "Mozilla/5.0",
            "x-ig-app-id": "936619743392459",
            "x-instagram-ajax": "1",
            "x-requested-with": "XMLHttpRequest",
        }

        cookies = {
            "sessionid": self._inst_session_id,
            "csrftoken": self._token,
            "ds_user_id": self._inst_session_id.split(":")[0],
        }
        headers["x-csrftoken"] = self._token
        timeout = httpx.Timeout(connect=15.0, read=20.0, write=10.0, pool=5.0)
        self._session = AsyncClient(
            headers=headers, cookies=cookies, proxy=self._proxy, timeout=timeout
        )

    async def __aenter__(self):
        client = None
        if self._username is not None and self._password is not None:
            self._inst_session_id, self._token = await self.get_session_user()
        self._init_session()
        if client is None:
            client = await self.get_client()
        return client

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        await self._session.aclose()
        return None

    async def close(self):
        await self._session.aclose()

    async def get_session_user(self) -> (str, str):
        short_user, user = await WebLoginServiceAsync().login(
            self._username, self._password
        )
        self._inst_session_id = user.session_id
        self._token = user.token
        print(f"Session: {user.session_id}\n Token: {user.token}")
        self.user_id = short_user.userId
        return user.session_id, user.token

    async def get_client(self) -> ClientPublicAsync | ClientPrivateAsync:
        if self._inst_session_id is not None and self._token is not None:
            if self._session is None:
                self._init_session
            return ClientPrivateAsync(
                session=self._session,
                inst_session_id=self._inst_session_id,
                token=self._token,
                proxy=self._proxy,
            )
        if self._username is not None and self._password is not None:
            self._inst_session_id, self._token = await self.get_session_user()
            print(self._inst_session_id, self._token)
            self._init_session()
            self._token = await WebLoginServiceAsync().csrf_token(self._session)
            print(self._token)
            return ClientPrivateAsync(
                session=self._session,
                inst_session_id=self._inst_session_id,
                token=self._token,
                proxy=self._proxy,
            )

        return ClientPublicAsync(proxy=self._proxy)

    async def get_public_client(self) -> ClientPublicAsync:
        return ClientPublicAsync(proxy=self._proxy)

    async def get_private_client(self) -> ClientPrivateAsync:
        if self._session_id is not None and self._token is not None:
            if self._token is None:
                self._token = await WebLoginServiceAsync().csrf_token(self._session_id)
            return ClientPrivateAsync(session_id=self._session_id, proxy=self._proxy)
        if self._username is not None and self._password is not None:
            session_id = await self.get_session_user_async()
            return ClientPrivateAsync(session_id=session_id, proxy=self._proxy)

        raise Exception(
            "Trying to get private client while login data is unknown. Required login/password or session id/token on init"
        )
