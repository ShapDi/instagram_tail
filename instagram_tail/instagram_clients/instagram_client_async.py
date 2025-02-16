from httpx import AsyncClient
import json

from instagram_tail._model import ReelModel
from instagram_tail._params_service import InstagramApiParamsServicePrivateAsync
from instagram_tail._parsers import ReelInfoParser


class InstagramClientAsync:
    def __init__(self, proxy: None | str = None):
        self.proxy = proxy
        self.client = MediaInfoRequestAsync(proxy=self.proxy)
        self.parser = ReelInfoParser()


    async def reel(self, reel_id: str) -> ReelModel | None:
        data = await self.client.request_info(reel_id)
        return self.parser.parse(data)


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
                # TODO Change exception type
                raise Exception(
                    f"Error on receive data from instagram web api. {reason_string}"
                )
            if response.headers.get("content-type").split(";")[0] == "text/html":
                raise Exception("Error on request instagram web api. Wrong request")
        return None
