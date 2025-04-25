import asyncio
import json
import random
import re
from datetime import datetime
from urllib.parse import quote

import httpx
from httpx import AsyncClient, HTTPStatusError

from instagram_tail._model import Account, PlainPost, PostModel, ParsingError, ReelModel
from instagram_tail.utils import _converters


class Scraper:
    async def get_account_data(self, username: str, session: AsyncClient) -> Account | ParsingError:
        url = f"https://www.instagram.com/{username}/"

        try:
            r = await session.get(url)
            r.raise_for_status()
        except httpx.ProxyError as e:
            print(f"Ошибка прокси: {e}")
        except HTTPStatusError as e:
            if e.response.status_code == 404:
                return ParsingError(f"Аккаунт {username} не найден (возможно, удалён)")
            return ParsingError(f"Ошибка при запросе страницы аккаунта: {e.response.status_code}")

        match = re.search(r'"profilePage_([0-9]+)"', r.text)
        if match:
            self.id = match.group(1)
        else:
            return ParsingError(f"Не удалось извлечь user ID для {username}. Возможна блокировка или изменения в разметке.")

        doc_id = '10068642573147916'
        variables = {
            'id': self.id,
            "render_surface": "PROFILE"
        }

        variables_str = quote(json.dumps(variables, separators=(',', ':')))
        url = f"https://www.instagram.com/graphql/query/?doc_id={doc_id}&variables={variables_str}"

        r = await session.get(url)

        try:
            data = r.json()
        except Exception:
            return ParsingError("Ошибка при декодировании JSON-ответа об аккаунте от GraphQL.")

        user = data['data']['user']

        if not user:
            return ParsingError(f"Нет данных о пользователе с id {self.id}. Аккаунт может быть заблокирован.")

        return Account(
            user_id=self.id,
            username=user['username'],
            full_name=user['full_name'],
            followers=user["follower_count"],
            following=user["following_count"],
            posts=user["media_count"]
        )

    async def get_all_posts(self, username: str, session: AsyncClient) -> list[PlainPost | ParsingError]:
        posts = []
        has_next_page = True
        end_cursor = None
        doc_id = '9456479251133434'

        while has_next_page:
            variables = {
                "after": None,
                "before": None,
                "data": {"count": 12, "include_reel_media_seen_timestamp": True, "include_relationship_info": True,
                         "latest_besties_reel_media": True, "latest_reel_media": True},
                "first": 12,
                "last": None,
                "username": username,
                "__relay_internal__pv__PolarisIsLoggedInrelayprovider": True,
                "__relay_internal__pv__PolarisShareSheetV3relayprovider": True
            }
            if end_cursor:
                variables['after'] = end_cursor

            variables_str = quote(json.dumps(variables, separators=(',', ':')))
            url = f"https://www.instagram.com/graphql/query/?doc_id={doc_id}&variables={variables_str}"

            try:
                r = await session.get(url)
                data = r.json()
                media = data['data']['xdt_api__v1__feed__user_timeline_graphql_connection']
                edges = media['edges']
                page_info = media['page_info']
            except Exception as e:
                return [ParsingError(f"Ошибка при запросе или декодировании JSON при сборе постов: {e}")]

            for edge in edges:
                node = edge.get('node')
                if not node:
                    posts.append(ParsingError("Отсутствует поле node в edge"))
                    continue
                try:
                    post_type = _converters.media_type_to_post_type(node.get('media_type'))
                    shortcode = node.get('code')
                    if not shortcode:
                        posts.append(ParsingError("Отсутствует shortcode поста"))
                        continue
                    posts.append(PlainPost(post_type, shortcode))
                except Exception as e:
                    posts.append(ParsingError(f"Ошибка при обработке поста: {e}"))

            has_next_page = page_info['has_next_page']
            end_cursor = page_info['end_cursor']

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
            duration = media.get("video_duration"),
            view_count = media.get("video_view_count"),
            play_count = media.get("video_play_count")
        )
