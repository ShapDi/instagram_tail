from instagram_tail.instagram_auth.web_login_service import WebLoginService
from instagram_tail.instagram_clients.instagram_client import InstagramClient
from instagram_tail.instagram_clients.instagram_client_async import InstagramClientAsync, InstagramClientAsyncAuth


class InstagramApi:
    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        session_id: str | None = None,
        proxy: str | None = None,
    ):
        self._username = username
        self._password = password
        self._session_id = session_id
        self._proxy = proxy
        self.user_id = None

    async def get_session_user_async(self):
        user, session_id = await WebLoginService().login_async(self._username, self._password)
        self._session_id = session_id
        self.user_id = user.userId
        return self
    # ? Зачем он нужен
    # def get_session_token(self):
    #     self.user_id = int(self._session_id.split(":")[0])
    #     return self


    def get_client(self):
        if self._session_id is not None:
            pass
        if self._session_id is None:
            return InstagramClient


    async def get_client_async(self):
        if self._session_id is not None:
            return InstagramClientAsyncAuth(session_id=self._session_id)
        if self._username is not None and self._password is not None:
            await self.get_session_user_async()
            return InstagramClientAsyncAuth(session_id=self._session_id)
        if self._session_id is None:
            return InstagramClientAsync
