import json
import datetime
from json import JSONDecodeError

from instagram_tail._model import ReelModel, ReelAuthor, ReelPreview, ReelVideo


class JsonParser:
    @staticmethod
    def parse(raw_json: str): ...


class ReelInfoParser(JsonParser):
    @staticmethod
    def parse(raw_json: str):
        print(raw_json)
        try:
            content: dict = json.loads(raw_json).get("data").get("xdt_shortcode_media")
        except JSONDecodeError as e:
            raise Exception(
                f"Error on parse json from instagram web api. Exception: {e}"
            )
        return ReelModel(
            media_id=content.get("id"),
            publish_date=datetime.datetime.utcfromtimestamp(int(content.get("taken_at_timestamp"))),
            code=content.get("shortcode"),
            description=""
            if content.get("edge_media_to_caption", {}).get("edges", []) == []
            else content.get("edge_media_to_caption", {})
            .get("edges", [])[0]
            .get("node", {})
            .get("text", ""),
            duration=content.get("video_duration"),
            like_count=content["edge_media_preview_like"]["count"],
            view_count=content["video_view_count"],
            play_count=content["video_play_count"],
            author=ReelAuthor(
                user_id=content["owner"]["id"],
                username=content["owner"]["username"],
                full_name=content["owner"]["full_name"],
                profile_pic_url=content["owner"]["profile_pic_url"],
            ),
            previews=[
                ReelPreview(
                    url=preview["src"],
                    width=preview["config_width"],
                    height=preview["config_height"],
                )
                for preview in content["display_resources"]
            ],
            videos=[
                ReelVideo(
                    video_id="0",
                    width=content["dimensions"]["width"],
                    height=content["dimensions"]["height"],
                    url=content["video_url"],
                )
            ],
        )


class MediaInfoParserAuth(JsonParser):

    @staticmethod
    def parse(raw_json: str) -> ReelModel | None:
        parsed: dict = json.loads(raw_json)
        media_info_list: list | None = parsed.get("items", None)
        if media_info_list is not None and len(media_info_list) > 0:
            media_info: dict = media_info_list[0]
            reel_caption = media_info["caption"]
            reel_author_user = media_info["user"]
            reel_previews: list = media_info["image_versions2"]["candidates"]
            reel_videos: list = media_info["video_versions"]
            return ReelModel(
                media_id=media_info["pk"],
                code=media_info["code"],
                description=reel_caption["text"] if reel_caption is not None else "",
                duration=float(media_info.get("video_duration", 0)),
                like_count=int(media_info.get("like_count", 0)),
                view_count=int(media_info.get("view_count", 0)),
                play_count=int(media_info.get("play_count", 0)),
                author=ReelAuthor(
                    user_id=reel_author_user["pk"],
                    username=reel_author_user["username"],
                    full_name=reel_author_user.get("full_name", ""),
                    profile_pic_url=reel_author_user.get("profile_pic_url", "")
                ),
                previews=[ReelPreview(
                    width=int(preview["width"]),
                    height=int(preview["height"]),
                    url=preview["url"]
                ) for preview in reel_previews],
                videos=[ReelVideo(
                    video_id=video["id"],
                    width=int(video["width"]),
                    height=int(video["height"]),
                    url=video["url"]
                ) for video in reel_videos]
            )
        else:
            return None

