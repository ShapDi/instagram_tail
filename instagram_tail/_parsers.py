import json
from datetime import datetime
from json import JSONDecodeError

from instagram_tail._model import ReelModel, ReelAuthor, ReelPreview, ReelVideo, ParsingError


class JsonParser:
    @staticmethod
    def parse(raw_json: str): ...


class AccountInfoParser(JsonParser):
    @staticmethod
    def parse(raw_json: str):
        pass

class ReelInfoParser(JsonParser):
    @staticmethod
    def parse(raw_json: str) -> ReelModel | ParsingError:
        try:
            content = json.loads(raw_json).get('data', {}).get('xdt_shortcode_media')

            if content is None:
                return ParsingError(f"Рилс недоступен (возможно, возрастное ограничение или геоблок)")

            node = content.get("edge_media_to_caption", {}).get("edges", [])[0].get('node', {})
            timestamp = int(node.get('created_at', ''))
            publish_date = datetime.fromtimestamp(timestamp)
        except JSONDecodeError as e:
            raise Exception(
                f"Error on parse json from instagram web api. Exception: {e}"
            )
        return ReelModel(
            media_id=content.get("id"),
            code=content.get("shortcode"),
            description=""
            if content.get("edge_media_to_caption", {}).get("edges", []) == []
            else node.get("text", ""),
            publish_date=publish_date.strftime('%d.%m.%Y'),
            duration=content.get("video_duration"),
            like_count=content["edge_media_preview_like"]["count"],
            view_count=content["video_view_count"],
            play_count=content["video_play_count"],
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

