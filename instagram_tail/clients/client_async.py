import asyncio
import json
import random
from abc import ABC, abstractmethod
from asyncio import sleep

import httpx
from httpx import AsyncClient

from instagram_tail._model import ReelModel, CollectedData, Account, PlainPost, Post, PostModel, ParsingError
from instagram_tail._params_service import InstagramApiParamsServicePrivateAsync
from instagram_tail._parsers import ReelInfoParser, MediaInfoParserAuth
from instagram_tail._scraper import Scraper, ScraperMobile
from instagram_tail.auth.exceptions import InstagramSessionExpiredException
from instagram_tail.utils._headers import HeadersHandler
from instagram_tail.utils._types import PostType


class Client(ABC):
    def __init__(self, is_mobile = False, proxy: str | None = None):
        self._scraper = Scraper() if not is_mobile else ScraperMobile()
        self._proxy = proxy

class ClientPublic(Client):
    def __init__(self, is_mobile = False, proxy: None | str = None):
        super().__init__(is_mobile, proxy)
        self.client = MediaInfoRequestAsync(proxy=proxy)
        self.parser = ReelInfoParser()
        self.headers_handler = HeadersHandler()

    async def get_full_posts(self, plain_posts: list[PlainPost]) -> list[Post | ParsingError]:
        posts: list[Post | ParsingError] = []

        for post in plain_posts:
            if isinstance(post, ParsingError):
                posts.append(post)
                continue

            data = await self.client.request_info(post.id)
            data = self.parser.parse(data)
            posts.append(data)

        return posts

        # async with AsyncClient(headers=self.headers_handler.get_random_headers(), proxy=self._proxy, timeout=timeout) as session:
        #     posts: list[Post | ParsingError] = []
        #
        #     for post in plain_posts:
        #         if isinstance(post, ParsingError):
        #             posts.append(post)
        #             continue
        #
        #         data = await self._scraper.get_post_info(post.id, session)
        #         posts.append(data)
        #
        #         timeout = random.uniform(0.5, 1.5)
        #         await asyncio.sleep(timeout)
        #
        #     return posts

    async def reel(self, reel_id: str) -> ReelModel | None:
        data = await self.client.request_info(reel_id)
        return self.parser.parse(data)


class ClientPrivate(Client):
    def __init__(self, session_id: str, is_mobile = False, proxy: str | None = None):
        super().__init__(is_mobile, proxy)
        self.__session_id = session_id
        # self.media_info = MediaInfoServiceAuth(MediaInfoClientAuth(session_id=session_id))

    async def get_account_data(self, username: str, session: AsyncClient) -> Account | ParsingError:
        return await self._scraper.get_account_data(username, session)

    async def get_plain_posts_data(self, username: str, session: AsyncClient) -> list[PlainPost | ParsingError]:
        return await self._scraper.get_all_posts(username, session)


class MediaInfoRequestAsync:
    DEFAULT_HEADERS = {
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "origin": "https://www.instagram.com",
        "Viewport-Width": "1728",
        "dpr": "1",
        "accept": "*/*",
        "host": "www.instagram.com",
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "sec-ch-ua-platform-version": '"5.15.148"',
        "sec-ch-ua-platform": '"Linux"',
        "sec-ch-ua-model": '""',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-full-version-list": '"Chromium";v="122.0.6261.69", "Not(A:Brand";v="24.0.0.0", "Google Chrome";v="122.0.6261.69"',
        "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "sec-ch-prefers-color-scheme": "dark",
        "pragma": "no-cache",
        "accept-language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7,ja;q=0.6",
        "authority": "www.instagram.com",
        "X-Fb-Friendly-Name": "PolarisPostActionLoadPostQueryQuery",
        "X-Asbd-Id": "129477",
        "Cache-Control": "no-cache",
    }

    def __init__(self, headers: dict = None, proxy:str|None= None):
        self.proxy = proxy
        self.params_service = InstagramApiParamsServicePrivateAsync(proxy=self.proxy)
        self.headers: dict = self.DEFAULT_HEADERS if headers is None else headers

    async def request_info(self, post_id: str) -> str | None:
        headers = self.headers.copy()
        cookies = {}
        settings = await self.params_service.params()
        timeout = httpx.Timeout(
            connect=20.0,
            read=30.0,
            write=15.0,
            pool=10.0
        )
        async with AsyncClient(headers=headers, cookies=cookies, timeout=timeout, proxy=self.proxy) as session:
            cookies.update(
                {"ig_nrcb": "1", "ps_l": "0", "ps_n": "0", **settings.cookie}
            )
            headers.update(
                {
                    "Referer": f"https://www.instagram.com/p/{post_id}/",
                    **settings.header,
                }
            )
            variables = {
                "shortcode": post_id,
                "fetch_comment_count": 40,
                "fetch_related_profile_media_count": 3,
                "parent_comment_count": 24,
                "child_comment_count": 3,
                "fetch_like_count": 10,
                "fetch_tagged_user_count": None,
                "fetch_preview_comment_count": 2,
                "has_threaded_comments": True,
                "hoisted_comment_id": None,
                "hoisted_reply_id": None,
            }
            data = {
                "variables": json.dumps(variables),
                "fb_api_caller_class": "RelayModern",
                "fb_api_req_friendly_name": "PolarisPostActionLoadPostQueryQuery",
                "dpr": 1,
                "server_timestamps": True,
                "doc_id": 10015901848480474,
                "av": 0,
                "__d": "www",
                "__user": 0,
                "__a": 1,
                "__req": 3,
                "__ccg": "UNKNOWN",
                "__comet_req": 7,
                **settings.body,
            }
            response = await session.post(
                url=f"https://www.instagram.com/api/graphql",
                data=data,
                headers=headers,
                cookies=cookies,
            )
            if response.headers.get("content-type").split(";")[0] == "text/javascript":
                return response.text
            if (
                response.headers.get("content-type").split(";")[0]
                == "application/x-javascript"
            ):
                json_str = response.text
                json_str = json_str[json_str.find("{") : json_str.rfind("}") + 1]
                json_data = json.loads(json_str)
                reason_string = f"Reason: error_id='{json_data.get('error')}' summary='{json_data.get('errorSummary')}', description='{json_data.get('errorDescription')}'"
                # TODO Change exceptions type
                raise Exception(
                    f"Error on receive data from instagram web api. {reason_string}"
                )
            if response.headers.get("content-type").split(";")[0] == "text/html":
                raise Exception("Error on request instagram web api. Wrong request")
        return None


class MediaInfoClientAuth:
    USER_AGENT = "'User-Agent':'Instagram 76.0.0.15.395 Android (24/7.0; 640dpi; 1440x2560; samsung; SM-G930F; herolte; samsungexynos8890; en_US; 138226743)'"

    def __init__(
            self,
            session_id: str,
            instagram_app_id_header: str = "936619743392459"
    ):
        self.__headers = {
            "x-ig-app-id": instagram_app_id_header,
            'User-Agent':'Instagram 76.0.0.15.395 Android (24/7.0; 640dpi; 1440x2560; samsung; SM-G930F; herolte; samsungexynos8890; en_US; 138226743)',
        }

        self.__cookies = {
                "sessionid": session_id,
                "csrftoken": 'ND-8ABfgmlHuuudw0890yZ',
                'ds_user_id': '69626403900'
        }

    async def get(self, media_id: str) -> str | None:
        # self.__headers.update(
        #     {
        #         "Referer": f"https://www.instagram.com/reel/DIf1n68ClEc/",
        #     }
        # )
        async with AsyncClient(headers=self.__headers, cookies=self.__cookies) as session:
            response = await session.get(f"https://www.instagram.com/api/v1/media/{media_id}/info/")
            # response = await session.get(f"https://i.instagram.com/api/v1/media/3611841265983443228/info/")
            # response = await session.get(f"https://www.instagram.com/api/graphql")
            # print(response.status_code)
            # print(response.content)
            if response.status_code == 200 and "application/json" in response.headers.get("content-type"):
                return response.text
            else:
                return None


class MediaInfoServiceAuth:
    def __init__(self, client: MediaInfoClientAuth, parser: MediaInfoParserAuth = MediaInfoParserAuth()):
        self.__client = client
        self.__parser = parser

    async def get_info(self, media_id: str) -> ReelModel | None:
        response_text = await self.__client.get(media_id)
        print(f"ID: {media_id}, Response: {response_text}")
        if response_text is not None:
            return self.__parser.parse(response_text)
        else:
            raise InstagramSessionExpiredException("Maybe your session id is expired or invalid")
