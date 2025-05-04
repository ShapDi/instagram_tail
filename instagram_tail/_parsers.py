import json
from datetime import datetime
from json import JSONDecodeError

from instagram_tail._model import ReelModel, ReelAuthor, ReelPreview, ReelVideo, ParsingError, PostModel


class JsonParser:
    @staticmethod
    def parse(raw_json: str): ...


class AccountInfoParser(JsonParser):
    @staticmethod
    def parse(raw_json: str):
        pass

class ReelInfoParser(JsonParser):
    @staticmethod
    def parse(raw_json: str) -> PostModel | ReelModel | ParsingError:
        media = json.loads(raw_json).get('data', {}).get('xdt_shortcode_media')

        if media is None:
            return ParsingError(f"Рилс недоступен (возможно, возрастное ограничение или геоблок)")

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
                code=media.get("shortcode"),
                description=description,
                like_count=like_count
            )

        return ReelModel(
            media_id=media_id,
            publish_date=publish_date,
            code=media.get("shortcode"),
            description=description,
            like_count=like_count,
            duration=media.get("video_duration"),
            view_count=media.get("video_view_count"),
            play_count=media.get("video_play_count")
        )


class MediaInfoParserAuth(JsonParser):
    @staticmethod
    def parse(raw_json: str) -> ReelModel | None:
        parsed: dict = json.loads(raw_json)
        media_info_list: list | None = parsed.get("items", None)
        if media_info_list is not None and len(media_info_list) > 0:
            media_info: dict = media_info_list[0]
            reel_caption = media_info["caption"]
            # timestamp = int(node.get('created_at', ''))
            # publish_date = datetime.fromtimestamp(timestamp)
            return ReelModel(
                media_id=media_info["pk"],
                code=media_info["code"],
                description=reel_caption["text"] if reel_caption is not None else "",
                # publish_date=publish_date.strftime('%d.%m.%Y'),
                duration=float(media_info.get("video_duration", 0)),
                like_count=int(media_info.get("like_count", 0)),
                view_count=int(media_info.get("view_count", 0)),
                play_count=int(media_info.get("play_count", 0)),
            )
        else:
            return None

