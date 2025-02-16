from instagram_tail.instagram_clients.no_auth_client import InstagramClient


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

    def get_client(self):
        if self._session_id is None:
            return InstagramClient
