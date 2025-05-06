from urllib.parse import unquote

from httpx import Client, AsyncClient
from instagram_tail.auth.exceptions import (
    InstagramSignInException,
    InstagramLoginNonceException,
    CSRFTokenException,
)
from instagram_tail.auth.models import InstagramShortUser, AuthorizedUser
from instagram_tail.auth.password_util import PasswordUtilAsync, PasswordUtil


class WebLoginServiceAsync:
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "X-Ig-App-Id": "936619743392459",
        "X-Instagram-Ajax": "1010801225",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://www.instagram.com",
        "Viewport-Width": "1728",
        "dpr": "1",
    }

    DEFAULT_COOKIES = {
        "ig_did": "183D0C6A-2A2F-4D13-ACAB-1F699F93BDEA",
        "datr": "blCgZXM302jOB7BO4tR4nZqY",
        "mid": "ZaBXswAEAAGylo7iozvu4FDXWmPn",
        "ig_nrcb": "1",
    }

    def __init__(
        self,
        session: AsyncClient | None = None,
        default_cookies: dict = None,
        default_headers: dict = None,
    ):
        self.session = session
        if default_cookies is not None:
            self.DEFAULT_COOKIES = default_cookies
        if default_headers is not None:
            self.DEFAULT_HEADERS = default_headers

    async def login(self, username, password) -> (InstagramShortUser, str):
        """
        :return: (user_info_model, sessionid)
        """
        if username == "" or password == "":
            raise InstagramSignInException(
                "Username and Password is required to be not empty"
            )
        headers = self.DEFAULT_HEADERS.copy()
        async with self.session or AsyncClient(headers=headers) as session:
            password_utils = PasswordUtilAsync()
            url = "https://www.instagram.com/api/v1/web/accounts/login/ajax/"
            data = {
                "username": username,
                "enc_password": await password_utils.encrypt(password),
                "optIntoOneTap": False,
                "queryParams": {},
                "trustedDeviceRecords": {},
            }
            headers, cookies = await self.__build_headers_and_cookies(
                session=session, headers=headers
            )
            print(headers)
            print(cookies)
            # TODO add certificate for 'www.instagram.com' to client/system

            response = await session.post(
                url, data=data, headers=headers, cookies=cookies, timeout=10.0
            )
            if response.status_code == 200:
                print(response.status_code)
                print(response.cookies)
                response_data: dict = response.json()
                cookies = {}
                for part in str(response.cookies).split("<Cookie ")[1:]:
                    kv = part.split(" for")[0]  # sessionid=... до ' for'
                    key, value = kv.split("=", 1)
                    cookies[key] = value

                if response_data.get("authenticated", False):
                    return InstagramShortUser(**response_data), AuthorizedUser(
                        login=username,
                        password=password,
                        session_id=unquote(cookies["sessionid"]),
                        token=unquote(cookies["csrftoken"]),
                    )
                else:
                    raise InstagramSignInException(
                        f"Error on sign in. Maybe wrong password", response
                    )
            else:
                raise InstagramSignInException(f"Error on sign in", response)

    async def reissue_session_id(
        self, session_id: str, user_id: str, login_nonce: str | None = None
    ) -> (str, str):
        """
        Reissue sessionid

        :param session_id:
        :param user_id:
        :param login_nonce: if available, then you can use it. Otherwise a new one will be released
        :return: (new_login_nonce, new_session_id)
        """
        headers = self.DEFAULT_HEADERS.copy()
        url = "https://www.instagram.com/api/v1/web/accounts/one_tap_web_login/"
        async with AsyncClient(headers=headers) as session:
            if login_nonce is None:
                login_nonce = await self.login_nonce(session, session_id)
            headers, cookies = await self.__build_headers_and_cookies(
                session=session, sessionid=session_id, headers=headers
            )
            body = {
                "login_nonce": login_nonce,
                "queryParams": {},
                "trustedDeviceRecords": {},
                "user_id": user_id,
            }
            async with session.post(
                url, data=body, headers=headers, cookies=cookies
            ) as response:
                if (
                    response.status == 200
                    and response.content_type == "application/json"
                ):
                    data = await response.json()
                    if data.get("authenticated", False):
                        new_login_nonce: str | None = data.get("login_nonce", None)
                        new_session_id = response.cookies.get("sessionid", None)
                        if new_login_nonce is not None or new_session_id is not None:
                            return new_login_nonce, new_session_id.value
                else:
                    return None

    @classmethod
    async def login_nonce(cls, session: AsyncClient, session_id: str) -> str | None:
        headers, cookies = await cls.__build_headers_and_cookies(
            session=session, sessionid=session_id
        )
        url = (
            "https://www.instagram.com/api/v1/web/accounts/request_one_tap_login_nonce/"
        )
        async with session.post(url, headers=headers, cookies=cookies) as response:
            if response.status == 200 and response.content_type == "application/json":
                data: dict = await response.json()
                return data.get("login_nonce", None)
            else:
                raise InstagramLoginNonceException(
                    f"Error on get login nonce", response
                )

    @staticmethod
    async def csrf_token(session) -> str:
        default_url = "https://www.instagram.com/data/shared_data/"
        fallback_url = "https://storage.yandexcloud.net/bit-static/instagram/shared_data.json"  # FIXME

        async def try_download(url: str):
            response = await session.get(url)
            if (
                response.status_code == 200
                and response.headers.get("content-type") == "application/json"
            ):
                data = response.json()
                config: dict = data.get("config", {})
                csrf_token: str | None = config.get("csrf_token", None)
                if csrf_token is not None:
                    return csrf_token
                else:
                    raise CSRFTokenException(f"Error on get csrftoken", response)
            else:
                raise CSRFTokenException(f"error on get csrftoken", response)

        try:
            return await try_download(default_url)
        except Exception:
            return await try_download(fallback_url)

    @classmethod
    async def csrf_token_header(cls, session: AsyncClient) -> (dict, str):
        """
        :return: (csrf_header, csrf_token)
        """
        csrf_token = await cls.csrf_token(session)
        if csrf_token is not None:
            return {"X-Csrftoken": csrf_token}, csrf_token
        else:
            raise CSRFTokenException(
                "Error on get csrf_token. Reason: csrf_token is None"
            )

    @classmethod
    async def __build_headers_and_cookies(
        cls,
        session: AsyncClient,
        sessionid: str | None = None,
        headers: dict | None = None,
        cookies: dict | None = None,
    ) -> (dict, dict):
        """
        :return: (headers, cookies)
        """
        csrf_header, csrf_token = await cls.csrf_token_header(session)
        if headers is None:
            headers = cls.DEFAULT_HEADERS.copy()
        headers.update(csrf_header)
        if cookies is None:
            cookies = cls.DEFAULT_COOKIES.copy()
        cookies.update(
            {
                "csrftoken": csrf_token,
            }
        )
        if sessionid is not None:
            cookies.update({"sessionid": sessionid})
        return headers, cookies


class WebLoginService:
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "X-Ig-App-Id": "936619743392459",
        "X-Instagram-Ajax": "1010801225",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://www.instagram.com",
        "Viewport-Width": "1728",
        "dpr": "1",
    }

    DEFAULT_COOKIES = {
        "ig_did": "183D0C6A-2A2F-4D13-ACAB-1F699F93BDEA",
        "datr": "blCgZXM302jOB7BO4tR4nZqY",
        "mid": "ZaBXswAEAAGylo7iozvu4FDXWmPn",
        "ig_nrcb": "1",
    }

    def __init__(
        self,
        session: Client | None = None,
        default_cookies: dict = None,
        default_headers: dict = None,
    ):
        self.session = session
        if default_cookies is not None:
            self.DEFAULT_COOKIES = default_cookies
        if default_headers is not None:
            self.DEFAULT_HEADERS = default_headers

    def login(self, username, password) -> (InstagramShortUser, str):
        """
        :return: (user_info_model, sessionid)
        """
        if username == "" or password == "":
            raise InstagramSignInException(
                "Username and Password is required to be not empty"
            )
        headers = self.DEFAULT_HEADERS.copy()
        with self.session or Client(headers=headers) as session:
            password_utils = PasswordUtil()
            url = "https://www.instagram.com/api/v1/web/accounts/login/ajax/"
            data = {
                "username": username,
                "enc_password": password_utils.encrypt(password),
                "optIntoOneTap": False,
                "queryParams": {},
                "trustedDeviceRecords": {},
            }
            headers, cookies = self.__build_headers_and_cookies(
                session=session, headers=headers
            )
            print(headers)
            print(cookies)
            # TODO add certificate for 'www.instagram.com' to client/system

            response = session.post(
                url, data=data, headers=headers, cookies=cookies, timeout=10.0
            )
            if response.status_code == 200:
                print(response.status_code)
                print(response.cookies)
                response_data: dict = response.json()
                cookies = {}
                for part in str(response.cookies).split("<Cookie ")[1:]:
                    kv = part.split(" for")[0]  # sessionid=... до ' for'
                    key, value = kv.split("=", 1)
                    cookies[key] = value

                if response_data.get("authenticated", False):
                    return InstagramShortUser(**response_data), AuthorizedUser(
                        login=username,
                        password=password,
                        session_id=unquote(cookies["sessionid"]),
                        token=unquote(cookies["csrftoken"]),
                    )
                else:
                    raise InstagramSignInException(
                        f"Error on sign in. Maybe wrong password", response
                    )
            else:
                raise InstagramSignInException(f"Error on sign in", response)

    def reissue_session_id(
        self, session_id: str, user_id: str, login_nonce: str | None = None
    ) -> (str, str):
        """
        Reissue sessionid

        :param session_id:
        :param user_id:
        :param login_nonce: if available, then you can use it. Otherwise a new one will be released
        :return: (new_login_nonce, new_session_id)
        """
        headers = self.DEFAULT_HEADERS.copy()
        url = "https://www.instagram.com/api/v1/web/accounts/one_tap_web_login/"
        with Client(headers=headers) as session:
            if login_nonce is None:
                login_nonce = self.login_nonce(session, session_id)
            headers, cookies = self.__build_headers_and_cookies(
                session=session, sessionid=session_id, headers=headers
            )
            body = {
                "login_nonce": login_nonce,
                "queryParams": {},
                "trustedDeviceRecords": {},
                "user_id": user_id,
            }
            with session.post(
                url, data=body, headers=headers, cookies=cookies
            ) as response:
                if (
                    response.status == 200
                    and response.content_type == "application/json"
                ):
                    data = response.json()
                    if data.get("authenticated", False):
                        new_login_nonce: str | None = data.get("login_nonce", None)
                        new_session_id = response.cookies.get("sessionid", None)
                        if new_login_nonce is not None or new_session_id is not None:
                            return new_login_nonce, new_session_id.value
                else:
                    return None

    @classmethod
    def login_nonce(cls, session: Client, session_id: str) -> str | None:
        headers, cookies = cls.__build_headers_and_cookies(
            session=session, sessionid=session_id
        )
        url = (
            "https://www.instagram.com/api/v1/web/accounts/request_one_tap_login_nonce/"
        )
        with session.post(url, headers=headers, cookies=cookies) as response:
            if response.status == 200 and response.content_type == "application/json":
                data: dict = response.json()
                return data.get("login_nonce", None)
            else:
                raise InstagramLoginNonceException(
                    f"Error on get login nonce", response
                )

    @staticmethod
    def csrf_token(session) -> str:
        default_url = "https://www.instagram.com/data/shared_data/"
        fallback_url = "https://storage.yandexcloud.net/bit-static/instagram/shared_data.json"  # FIXME

        def try_download(url: str):
            response = session.get(url)
            if (
                response.status_code == 200
                and response.headers.get("content-type") == "application/json"
            ):
                data = response.json()
                config: dict = data.get("config", {})
                csrf_token: str | None = config.get("csrf_token", None)
                if csrf_token is not None:
                    return csrf_token
                else:
                    raise CSRFTokenException(f"Error on get csrftoken", response)
            else:
                raise CSRFTokenException(f"error on get csrftoken", response)

        try:
            return try_download(default_url)
        except Exception:
            return try_download(fallback_url)

    @classmethod
    def csrf_token_header(cls, session: Client) -> (dict, str):
        """
        :return: (csrf_header, csrf_token)
        """
        csrf_token = cls.csrf_token(session)
        if csrf_token is not None:
            return {"X-Csrftoken": csrf_token}, csrf_token
        else:
            raise CSRFTokenException(
                "Error on get csrf_token. Reason: csrf_token is None"
            )

    @classmethod
    def __build_headers_and_cookies(
        cls,
        session: Client,
        sessionid: str | None = None,
        headers: dict | None = None,
        cookies: dict | None = None,
    ) -> (dict, dict):
        """
        :return: (headers, cookies)
        """
        csrf_header, csrf_token = cls.csrf_token_header(session)
        if headers is None:
            headers = cls.DEFAULT_HEADERS.copy()
        headers.update(csrf_header)
        if cookies is None:
            cookies = cls.DEFAULT_COOKIES.copy()
        cookies.update(
            {
                "csrftoken": csrf_token,
            }
        )
        if sessionid is not None:
            cookies.update({"sessionid": sessionid})
        return headers, cookies