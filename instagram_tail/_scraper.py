import asyncio
import json
import random
import re
from datetime import datetime
from urllib.parse import quote

from httpx import AsyncClient

from instagram_tail._model import Account, PlainPost, PostModel
from instagram_tail.utils import _converters


class Scraper:
    async def get_account_data(self, username: str, session: AsyncClient) -> Account:
        url = f"https://www.instagram.com/{username}/"
        r = await session.get(url)
        r.raise_for_status()

        # print(f'Account scraping: {r.text}')

        match = re.search(r'"profilePage_([0-9]+)"', r.text)
        if match:
            self.id = match.group(1)
        else:
            raise Exception('User id не найден')

        doc_id = '10068642573147916'
        variables = {
            'id': self.id,
            "render_surface": "PROFILE"
        }

        variables_str = quote(json.dumps(variables, separators=(',', ':')))
        url = f"https://www.instagram.com/graphql/query/?doc_id={doc_id}&variables={variables_str}"

        r = await session.get(url)

        data = r.json()
        user = data['data']['user']

        return Account(
            user_id=self.id,
            username=user['username'],
            full_name=user['full_name'],
            followers=user["follower_count"],
            following=user["following_count"],
            posts=user["media_count"]
        )

    async def get_all_posts(self, username: str, session: AsyncClient) -> list[PlainPost]:
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

            r = await session.get(url)

            data = r.json()

            # print(json.dumps(data, indent=2))

            media = data['data']['xdt_api__v1__feed__user_timeline_graphql_connection']
            edges = media['edges']

            for edge in edges:
                node = edge['node']
                if node.get('media_type') == 8:
                    continue
                posts.append(PlainPost(_converters.media_type_to_post_type(node.get('media_type')),
                                       node.get('code')))

            page_info = media['page_info']
            has_next_page = page_info['has_next_page']
            end_cursor = page_info['end_cursor']

            timeout = random.uniform(0.5, 1.5)

            await asyncio.sleep(timeout)

        return posts

    async def get_post_info(self, post_id: str, session: AsyncClient) -> PostModel:
        doc_id = '8845758582119845'
        variables = {
            "shortcode": post_id,
            "fetch_tagged_user_count": None,
            "hoisted_comment_id": None,
            "hoisted_reply_id": None
        }
        variables_str = quote(json.dumps(variables, separators=(',', ':')))
        url = f"https://www.instagram.com/graphql/query/?doc_id={doc_id}&variables={variables_str}"

        r = await session.get(url)

        data = r.json()

        media = data['data']['xdt_shortcode_media']
        print(f'Parsing post: media - {media}')
        print(f'Parsing post: caption - {media.get("edge_media_to_caption", {})}')
        print(f'Parsing post: edges - {media.get("edge_media_to_caption", {}).get("edges", [])[0]}')
        print(f'Parsing post: node - {media.get("edge_media_to_caption", {}).get("edges", [])[0].get('node', {})}')
        node = media.get("edge_media_to_caption", {}).get("edges", [])[0].get('node', {})

        timestamp = media.get('taken_at_timestamp', int)
        print(f'Parsing post: timestamp - {timestamp}')
        publish_date = datetime.fromtimestamp(timestamp)

        return PostModel(
            media_id=media.get('id'),
            publish_date=publish_date.strftime('%d.%m.%Y'),
            code=post_id,
            description=node.get('text'),
            like_count=media.get('edge_media_preview_like', {}).get('count')
        )
