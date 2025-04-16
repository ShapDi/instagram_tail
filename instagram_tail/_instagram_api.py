from instagram_tail.instagram_clients.instagram_client import InstagramClient
from instagram_tail.instagram_clients.instagram_client_async import InstagramClientAsync


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
        # if self._session_id is not None:
        #     pass
        if self._session_id is None:
            return InstagramClient


    def get_client_async(self):
        if self._session_id is None:
            return InstagramClientAsync
