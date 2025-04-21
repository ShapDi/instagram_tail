import asyncio
import re
from asyncio import sleep
from urllib.parse import quote

import httpx
from httpx import AsyncClient
import json

from instagram_tail._model import ReelModel
from instagram_tail._params_service import InstagramApiParamsServicePrivateAsync
from instagram_tail._parsers import ReelInfoParser, MediaInfoParserAuth
from instagram_tail.instagram_auth.exceptions import InstagramSessionExpiredException


class InstagramClientAsync:
    def __init__(self, proxy: None | str = None):
        self.proxy = proxy
        self.client = MediaInfoRequestAsync(proxy=self.proxy)
        self.parser = ReelInfoParser()


    async def reel(self, reel_id: str) -> ReelModel | None:
        data = await self.client.request_info(reel_id)
        return self.parser.parse(data)


class InstagramClientAsyncAuth:

    def __init__(self, session_id: str):
        self.__session_id = session_id
        self.media_info = MediaInfoServiceAuth(MediaInfoClientAuth(session_id=session_id))

    async def reels(self, reel_id: str) -> ReelModel | None:
        cookies = {
            "sessionid": self.__session_id
        }
        # Иногда куки мешают получить рилс. TODO переделать получение media_id через meta тэг
        reel = await self.__process(await self.__try_one(reel_id))
        if reel is None:
            await sleep(1)
            reel = await self.__process(await self.__try_one(reel_id, cookies))
            if reel is None:
                await sleep(1)
                reel = await self.__process(self.__try_two(reel_id))
                if reel is None:
                    await sleep(1)
                    reel = await self.__process(self.__try_two(reel_id, cookies))
                    if reel is None:
                        return None
        print(f'Reel: {reel}')
        return reel

    async def get_all_posts(self, username: str) -> list:
        headers = {
            'user-agent': 'Mozilla/5.0',
            'x-ig-app-id': '936619743392459',
            'x-instagram-ajax': '1',
            'x-requested-with': 'XMLHttpRequest',
            'x-csrftoken': 'ND-8ABfgmlHuuudw0890yZ',
            'referer': f'https://www.instagram.com/{username}/',
        }

        cookies = {
            "sessionid": self.__session_id,
            "csrftoken": 'ND-8ABfgmlHuuudw0890yZ',
            'ds_user_id': '69626403900'
        }

        async with AsyncClient(headers=headers, cookies=cookies) as session:
            async def get_user_id() -> str:
                url = f"https://www.instagram.com/{username}/"
                r = await session.get(url)
                r.raise_for_status()
                match = re.search(r'"profilePage_([0-9]+)"', r.text)
                if match:
                    return match.group(1)
                raise Exception('User id не найден')

            user_id = await get_user_id()

            posts = []
            has_next_page = True
            end_cursor = None
            doc_id = '8931245513664134'

            while has_next_page:
                variables = {
                    "after":"QVFDV0ZtRWtwYWh5OXhiMlIzaHIybmI0NzRoUjdwZDNCMXgtMENBTzF2ajROMVFKbXM5bmtsR3AwLWFiQjNsZVpBWFNDczB4NTR5Mld5UGVwbmpvTEU1Tg==",
                    "before":None,
                    "data":{"include_feed_video":True,"page_size":12,"target_user_id":"7830106401"},
                    "first":4,
                    "last":None
                }
                if end_cursor:
                    variables['after'] = end_cursor

                variables_str = quote(json.dumps(variables, separators=(',', ':')))
                url = f"https://www.instagram.com/graphql/query/?doc_id={doc_id}&variables={variables_str}"

                r = await session.get(url)

                data = r.json()

                media = data['data']['xdt_api__v1__clips__user__connection_v2']
                edges = media['edges']

                for edge in edges:
                    node = edge['node']
                    print(json.dumps(node, indent=2, ensure_ascii=False))
                    # print(node)
                    # print(f'https://www.instagram.com/p/{node['media']['code']}/')
                    posts.append({
                        'view_count': node.get('video_view_count'),
                        # 'like_count': node['view_count'],
                        # 'comment_count': node['edge_media_to_comment']['count'],
                    })

                page_info = media['page_info']
                has_next_page = page_info['has_next_page']
                end_cursor = page_info['end_cursor']

                await asyncio.sleep(1)

        # for post in posts:
        #     print(post)

        return posts

    async def __process(self, raw_html: str) -> ReelModel | None:
        from bs4 import BeautifulSoup
        parser = BeautifulSoup(raw_html, "html.parser")
        meta_tag = parser.find('meta', attrs={'property': 'al:ios:url'})

        if meta_tag:
            content = meta_tag.get('content', '')
            if 'media?id=' in content:
                media_id = content.split('media?id=')[-1]
                media_info = await self.media_info.get_info(media_id)
                return media_info

    @classmethod
    async def __try_one(cls, reel_id: str, cookies: dict | None = None) -> str | None:
        async with AsyncClient(cookies=cookies) as session:
            response = await session.get(f"https://www.instagram.com/reel/{reel_id}/")
            if response.status_code == 200:
                return response.text

    @classmethod
    def __try_two(cls, reel_id: str, cookies: dict | None = None) -> str | None:
        response = httpx.get(f"https://www.instagram.com/reel/{reel_id}/", cookies=cookies)
        if response.status_code == 200:
            return response.text

    @classmethod
    def __parse_media_id(cls, raw_media_id: str) -> str | None:
        try:
            media_id = raw_media_id.split('"')[2]
            return media_id
        except Exception as e:
            return None



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

    async def request_info(self, reel_id: str) -> str | None:
        headers = self.headers.copy()
        cookies = {}
        settings = await self.params_service.params()
        async with AsyncClient(headers=headers, cookies=cookies, proxy=self.proxy) as session:
            cookies.update(
                {"ig_nrcb": "1", "ps_l": "0", "ps_n": "0", **settings.cookie}
            )
            headers.update(
                {
                    "Referer": f"https://www.instagram.com/reel/{reel_id}/",
                    **settings.header,
                }
            )
            variables = {
                "shortcode": reel_id,
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


