import asyncio
import json
import time
import random
import re
import urllib
from datetime import datetime
from urllib.parse import quote, urljoin

import httpx
from httpx import AsyncClient, HTTPStatusError,Client

from instagram_tail._exceptions import AccountBlockedException
from instagram_tail._model import Account, PlainPost, PostModel, ParsingError, ReelModel
from instagram_tail.utils import _converters


class ScraperAsync:
    async def get_account_data(
        self, username: str, session: AsyncClient
    ) -> Account | ParsingError:
        url = f"https://www.instagram.com/{username}/"

        try:
            r = await session.get(url)
            print(r)
            r.raise_for_status()
        except HTTPStatusError as e:
            if e.response.status_code == 404:
                return ParsingError(f"Account {username} not found (possibly deleted)")
            elif e.response.status_code == 302:
                print(
                    f"Status 302 when parsing {username}. Text: {e.response.headers}"
                )
                redirect_url = urljoin(url, r.headers.get("location", ""))
                if "/challenge/" in redirect_url:
                    raise AccountBlockedException(
                        f"The account requires passing a captcha. Redirect: {redirect_url}"
                    )
                return ParsingError(
                    f"When parsing the {username} account, a redirect occurred (perhaps the account from which the parsing is taking place is blocked)"
                )
            return ParsingError(
                f"Error when requesting account page {username}: {e.response.status_code}"
            )

        match = re.search(r'"profilePage_([0-9]+)"', r.text)
        if match:
            self.id = match.group(1)
        else:
            return ParsingError(
                f"Failed to retrieve user ID for {username}. Possible blocking or changes in markup"
            )

        doc_id = "10068642573147916"
        variables = {"id": self.id, "render_surface": "PROFILE"}

        variables_str = quote(json.dumps(variables, separators=(",", ":")))
        url = f"https://www.instagram.com/graphql/query/?doc_id={doc_id}&variables={variables_str}"

        r = await session.get(url)

        try:
            data = r.json()
        except Exception:
            return ParsingError(
                "Error when decoding JSON account response from GraphQL"
            )

        user = data["data"]["user"]

        if not user:
            return ParsingError(
                f"There is no data about the user with id {self.id}. Account may be blocked"
            )

        return Account(
            user_id=self.id,
            username=user["username"],
            full_name=user["full_name"],
            followers=user["follower_count"],
            following=user["following_count"],
            posts=user["media_count"],
        )

    async def get_all_posts(
        self, username: str, session: AsyncClient, min_timestamp: int
    ) -> list[PlainPost | ParsingError]:
        posts = []
        has_next_page = True
        end_cursor = None
        doc_id = "9456479251133434"
        min_timestamp = min_timestamp

        while has_next_page:
            variables = {
                "after": None,
                "before": None,
                "data": {
                    "count": 12,
                    "include_reel_media_seen_timestamp": True,
                    "include_relationship_info": True,
                    "latest_besties_reel_media": True,
                    "latest_reel_media": True,
                },
                "first": 12,
                "last": None,
                "username": username,
                "__relay_internal__pv__PolarisIsLoggedInrelayprovider": True,
                "__relay_internal__pv__PolarisShareSheetV3relayprovider": True,
            }
            if end_cursor:
                variables["after"] = end_cursor

            variables_str = quote(json.dumps(variables, separators=(",", ":")))
            url = f"https://www.instagram.com/graphql/query/?doc_id={doc_id}&variables={variables_str}"

            try:
                r = await session.get(url)
                data = r.json()
                media = data["data"][
                    "xdt_api__v1__feed__user_timeline_graphql_connection"
                ]
                edges = media["edges"]
                page_info = media["page_info"]
            except Exception as e:
                return [
                    ParsingError(
                        f"Error requesting or decoding JSON while collecting posts: {e}"
                    )
                ]

            for edge in edges:
                node = edge.get("node")
                if not node:
                    posts.append(ParsingError("Missing node field in edge"))
                    continue
                try:
                    timestamp = node.get("taken_at")
                    if timestamp < min_timestamp:
                        break
                    post_type = _converters.media_type_to_post_type(
                        node.get("media_type")
                    )
                    shortcode = node.get("code")
                    if not shortcode:
                        posts.append(ParsingError("Post shortcode is missing"))
                        continue
                    posts.append(PlainPost(post_type, shortcode))
                except Exception as e:
                    posts.append(ParsingError(f"Error processing post: {e}"))

            has_next_page = page_info["has_next_page"]
            end_cursor = page_info["end_cursor"]

            timeout = random.uniform(0.5, 1.5)

            await asyncio.sleep(timeout)

        return posts

    async def get_post_info(
        self, post_id: str, session: AsyncClient
    ) -> PostModel | ReelModel | ParsingError:
        doc_id = "8845758582119845"
        variables = {
            "shortcode": post_id,
            "fetch_tagged_user_count": None,
            "hoisted_comment_id": None,
            "hoisted_reply_id": None,
        }
        variables_str = quote(json.dumps(variables, separators=(",", ":")))
        url = f"https://www.instagram.com/graphql/query/?doc_id={doc_id}&variables={variables_str}"

        try:
            r = await session.get(url)
            data = r.json()
        except Exception as e:
            return ParsingError(
                f"Error requesting or decoding JSON for post {post_id}: {e}"
            )

        media = data.get("data", {}).get("xdt_shortcode_media")
        if media.get("message") == "feedback_required":
            return ParsingError("An unauthorized account was banned")
        if media is None:
            return ParsingError(
                f"Post {post_id} is unavailable (perhaps age restriction or geoblock)"
            )

        media_id = media.get("id")

        description_node = media.get("edge_media_to_caption", {}).get("edges", [])
        description = description_node[0]["node"]["text"] if description_node else None

        timestamp = media.get("taken_at_timestamp", int)
        publish_date = datetime.fromtimestamp(timestamp).strftime("%d.%m.%Y")

        like_count = media.get("edge_media_preview_like", {}).get("count")

        if not media.get("is_video"):
            return PostModel(
                media_id=media_id,
                publish_date=publish_date,
                code=post_id,
                description=description,
                like_count=like_count,
            )

        return ReelModel(
            media_id=media_id,
            publish_date=publish_date,
            code=post_id,
            description=description,
            like_count=like_count,
            duration=media.get("video_duration"),
            view_count=media.get("video_view_count"),
            play_count=media.get("video_play_count"),
        )

class Scraper:
    def get_account_data(
        self, username: str, session: Client
    ) -> Account | ParsingError:
        url = f"https://www.instagram.com/{username}/"

        try:
            r = session.get(url)
            r.raise_for_status()
        except HTTPStatusError as e:
            if e.response.status_code == 404:
                return ParsingError(f"Account {username} not found (possibly deleted)")
            elif e.response.status_code == 302:
                print(
                    f"Status 302 when parsing {username}. Text: {e.response.headers}"
                )
                redirect_url = urljoin(url, r.headers.get("location", ""))
                if "/challenge/" in redirect_url:
                    raise AccountBlockedException(
                        f"The account requires passing a captcha. Redirect: {redirect_url}"
                    )
                return ParsingError(
                    f"When parsing the {username} account, a redirect occurred (perhaps the account from which the parsing is taking place is blocked)"
                )
            return ParsingError(
                f"Error when requesting account page {username}: {e.response.status_code}"
            )

        match = re.search(r'"profilePage_([0-9]+)"', r.text)
        if match:
            self.id = match.group(1)
        else:
            return ParsingError(
                f"Failed to retrieve user ID for {username}. Possible blocking or changes in markup"
            )

        doc_id = "10068642573147916"
        variables = {"id": self.id, "render_surface": "PROFILE"}

        variables_str = quote(json.dumps(variables, separators=(",", ":")))
        url = f"https://www.instagram.com/graphql/query/?doc_id={doc_id}&variables={variables_str}"

        r = session.get(url)

        try:
            data = r.json()
        except Exception:
            return ParsingError(
                "Error when decoding JSON account response from GraphQL"
            )

        user = data["data"]["user"]

        if not user:
            return ParsingError(
                f"There is no data about the user with id {self.id}. Account may be blocked"
            )

        return Account(
            user_id=self.id,
            username=user["username"],
            full_name=user["full_name"],
            followers=user["follower_count"],
            following=user["following_count"],
            posts=user["media_count"],
        )

    def get_all_posts(
        self, username: str, session: AsyncClient, min_timestamp: int
    ) -> list[PlainPost | ParsingError]:
        posts = []
        has_next_page = True
        end_cursor = None
        doc_id = "9456479251133434"
        min_timestamp = min_timestamp

        while has_next_page:
            variables = {
                "after": None,
                "before": None,
                "data": {
                    "count": 12,
                    "include_reel_media_seen_timestamp": True,
                    "include_relationship_info": True,
                    "latest_besties_reel_media": True,
                    "latest_reel_media": True,
                },
                "first": 12,
                "last": None,
                "username": username,
                "__relay_internal__pv__PolarisIsLoggedInrelayprovider": True,
                "__relay_internal__pv__PolarisShareSheetV3relayprovider": True,
            }
            if end_cursor:
                variables["after"] = end_cursor

            variables_str = quote(json.dumps(variables, separators=(",", ":")))
            url = f"https://www.instagram.com/graphql/query/?doc_id={doc_id}&variables={variables_str}"

            try:
                r = session.get(url)
                data = r.json()
                media = data["data"][
                    "xdt_api__v1__feed__user_timeline_graphql_connection"
                ]
                edges = media["edges"]
                page_info = media["page_info"]
            except Exception as e:
                return [
                    ParsingError(
                        f"Error requesting or decoding JSON while collecting posts: {e}"
                    )
                ]

            for edge in edges:
                node = edge.get("node")
                if not node:
                    posts.append(ParsingError("Missing node field in edge"))
                    continue
                try:
                    timestamp = node.get("taken_at")
                    if timestamp < min_timestamp:
                        break
                    post_type = _converters.media_type_to_post_type(
                        node.get("media_type")
                    )
                    shortcode = node.get("code")
                    if not shortcode:
                        posts.append(ParsingError("Post shortcode is missing"))
                        continue
                    posts.append(PlainPost(post_type, shortcode))
                except Exception as e:
                    posts.append(ParsingError(f"Error processing post: {e}"))

            has_next_page = page_info["has_next_page"]
            end_cursor = page_info["end_cursor"]

            timeout = random.uniform(0.5, 1.5)

            time.sleep(timeout)

        return posts

    def get_post_info(
        self, post_id: str, session: Client
    ) -> PostModel | ReelModel | ParsingError:
        doc_id = "8845758582119845"
        variables = {
            "shortcode": post_id,
            "fetch_tagged_user_count": None,
            "hoisted_comment_id": None,
            "hoisted_reply_id": None,
        }
        variables_str = quote(json.dumps(variables, separators=(",", ":")))
        url = f"https://www.instagram.com/graphql/query/?doc_id={doc_id}&variables={variables_str}"

        try:
            r = session.get(url)
            data = r.json()
        except Exception as e:
            return ParsingError(
                f"Error requesting or decoding JSON for post {post_id}: {e}"
            )

        media = data.get("data", {}).get("xdt_shortcode_media")
        if media.get("message") == "feedback_required":
            return ParsingError("An unauthorized account was banned")
        if media is None:
            return ParsingError(
                f"Post {post_id} is unavailable (perhaps age restriction or geoblock)"
            )

        media_id = media.get("id")

        description_node = media.get("edge_media_to_caption", {}).get("edges", [])
        description = description_node[0]["node"]["text"] if description_node else None

        timestamp = media.get("taken_at_timestamp", int)
        publish_date = datetime.fromtimestamp(timestamp).strftime("%d.%m.%Y")

        like_count = media.get("edge_media_preview_like", {}).get("count")

        if not media.get("is_video"):
            return PostModel(
                media_id=media_id,
                publish_date=publish_date,
                code=post_id,
                description=description,
                like_count=like_count,
            )

        return ReelModel(
            media_id=media_id,
            publish_date=publish_date,
            code=post_id,
            description=description,
            like_count=like_count,
            duration=media.get("video_duration"),
            view_count=media.get("video_view_count"),
            play_count=media.get("video_play_count"),
        )

class ScraperMobile:
    async def get_account_data(self, username: str, session: AsyncClient) -> Account | ParsingError:
        encoded = urllib.parse.quote(username)
        print(f'Request: https://i.instagram.com/api/v1/users/search/?q={encoded}\n headers: {session.headers}')
        resp = await session.get(f"https://i.instagram.com/api/v1/users/search/?q={encoded}")
        resp.raise_for_status()
        users = resp.json().get("users", [])
        user = next((u for u in users if u["username"] == username), None)

        if not user:
            return ParsingError(f'Не удалось найти {username}')

        user_id = user["pk"]

        info_url = f"https://i.instagram.com/api/v1/users/{user_id}/info/"
        r = await session.get(info_url)
        r.raise_for_status()
        data = r.json().get('user', {})

        return Account(
            user_id=user_id,
            username=data['username'],
            full_name=data['full_name'],
            followers=data["follower_count"],
            following=data["following_count"],
            posts=data["media_count"]
        )

    async def get_all_posts(self, username: str, session: AsyncClient, min_timestamp: int) -> list[PlainPost | ParsingError]:
        posts: list[PlainPost | ParsingError] = []
        max_id = ""
        min_timestamp = min_timestamp

        while True:
            feed_url = f"https://i.instagram.com/api/v1/feed/user/{username}/?count=50"

            if max_id:
                feed_url += f"&max_id={max_id}"

            r = await session.get(feed_url)

            if r.status_code != 200:
                posts.append(ParsingError(f"Не удалось выгрузить посты: {r.status_code} {r.text}"))
                break

            data = r.json()
            items = data.get("items", [])

            for item in items:
                timestamp = item.get('taken_at')
                if timestamp < min_timestamp:
                    break
                post_type = _converters.media_type_to_post_type(item.get('media_type'))
                shortcode = item.get('code')
                if not shortcode:
                    posts.append(ParsingError("Отсутствует shortcode поста"))
                    continue
                posts.append(PlainPost(post_type, shortcode))

            if not data.get("more_available"):
                break
            max_id = data.get("next_max_id")
            if not max_id:
                break

            timeout = random.uniform(0.5, 1.5)
            await asyncio.sleep(timeout)

        return posts

    async def get_post_info(self, post_id: str, session: AsyncClient) -> PostModel | ReelModel | ParsingError:
        doc_id = '8845758582119845'
        variables = {
            "shortcode": post_id,
            "fetch_tagged_user_count": None,
            "hoisted_comment_id": None,
            "hoisted_reply_id": None
        }
        variables_str = quote(json.dumps(variables, separators=(',', ':')))
        url = f"https://www.instagram.com/graphql/query/?doc_id={doc_id}&variables={variables_str}"

        try:
            r = await session.get(url)
            data = r.json()
            if data.get('message') and 'Please wait a few minutes before you try again' in data['message']:
                delay = random.uniform(1500, 1800)
                print(f'IP временно заблочен. Ждёмс {delay} секунд')
                await asyncio.sleep(delay)
                r = await session.get(url)
                data = r.json()
                if data.get('message') and 'Please wait a few minutes before you try again' in data['message']:
                    raise httpx.ProxyError('Прокси полетел')
        except Exception as e:
            return ParsingError(f"Ошибка запроса или декодирования JSON для поста {post_id}: {e}")

        media = data.get('data', {}).get('xdt_shortcode_media')
        if media.get('message') == "feedback_required":
            return ParsingError('Получен бан неавторизованного аккаунта')
        if media is None:
            return ParsingError(f"Пост {post_id} недоступен (возможно, возрастное ограничение или геоблок)")

        media_id = media.get('id')

        description_node = media.get("edge_media_to_caption", {}).get("edges", [])
        description = description_node[0]["node"]["text"] if description_node else None

        timestamp = media.get('taken_at_timestamp', int)
        publish_date = datetime.fromtimestamp(timestamp).strftime('%d.%m.%Y')

        like_count = media.get('edge_media_preview_like', {}).get('count')

        if not media.get('is_video'):
            return PostModel(
                media_id=media_id,
                publish_date=publish_date,
                code=post_id,
                description=description,
                like_count=like_count
            )

        return ReelModel(
            media_id=media_id,
            publish_date=publish_date,
            code=post_id,
            description=description,
            like_count=like_count,
            duration=media.get("video_duration"),
            view_count=media.get("video_view_count"),
            play_count=media.get("video_play_count")
        )