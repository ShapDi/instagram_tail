from instagram_tail.auth.web_login_service import WebLoginService
from instagram_tail.clients.client_async import ClientPublic, ClientPrivate, Client


class InstagramApi:
    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        session_id: str | None = None,
        token: str | None = None,
        proxy: str | None = None,
    ):
        self._username = username
        self._password = password
        self._session_id = session_id
        self._token = token
        self._proxy = proxy
        self.user_id = None

    async def get_session_user_async(self) -> str:
        short_user, user = await WebLoginService().login_async(self._username, self._password)
        self._session_id = user.session_id
        self._token = user.token
        print(f'Session: {user.session_id}\n Token: {user.token}')
        self.user_id = short_user.userId
        return user.session_id
    # ? Зачем он нужен
    # def get_session_token(self):
    #     self.user_id = int(self._session_id.split(":")[0])
    #     return self


    def get_client(self):
        if self._session_id is not None:
            pass
        if self._session_id is None:
            pass


    async def get_client_async(self) -> Client:
        if self._session_id is not None:
            return ClientPrivate(session_id=self._session_id, proxy=self._proxy)
        if self._username is not None and self._password is not None:
            session_id = await self.get_session_user_async()
            return ClientPrivate(session_id=session_id, proxy=self._proxy)

        return ClientPublic(proxy=self._proxy)

    async def get_public_client(self) -> ClientPublic:
        return ClientPublic(proxy=self._proxy)

    async def get_private_client(self) -> ClientPrivate:
        if self._session_id is not None:
            if self._token is None:
                self._token = await WebLoginService().csrf_token(self._session_id)
            return ClientPrivate(session_id=self._session_id, proxy=self._proxy)
        if self._username is not None and self._password is not None:
            session_id = await self.get_session_user_async()
            return ClientPrivate(session_id=session_id, proxy=self._proxy)

        raise Exception('Trying to get private client while login data is unknown. Required login/password or session id/token on init')

    async def get_mobile_client(self) -> ClientPrivate:
        return ClientPrivate(session_id="", is_mobile=True, proxy=self._proxy)
