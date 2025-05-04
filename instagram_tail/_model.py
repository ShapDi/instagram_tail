from abc import ABC
from dataclasses import dataclass

from instagram_tail.utils._types import PostType


@dataclass
class ParsingError:
    message: str


@dataclass
class Account:
    user_id: str
    username: str
    full_name: str
    followers: int
    following: int
    posts: int


@dataclass
class PlainPost:
    type: PostType
    id: str


@dataclass
class Post(ABC):
    pass


@dataclass
class ReelModel(Post):
    media_id: str
    publish_date: str
    code: str
    description: str
    duration: float
    like_count: int
    view_count: int
    play_count: int


@dataclass
class PostModel(Post):
    media_id: str
    publish_date: str
    code: str
    description: str
    like_count: int


@dataclass
class CollectedData:
    account: Account | ParsingError
    posts: list[Post | ParsingError] | None


@dataclass
class ReelAuthor:
    user_id: str
    username: str
    full_name: str
    profile_pic_url: str


@dataclass
class InstagramShortUser:
    user: bool
    userId: str
    authenticated: bool
    oneTapPrompt: bool
    has_onboarded_to_text_post_app: bool
    status: str
    reactivated: bool = False


@dataclass
class ReelPreview:
    width: int
    height: int
    url: str


@dataclass
class ReelVideo:
    video_id: str
    width: int
    height: int
    url: str


@dataclass
class InstagramSettingDataClassPrivate:
    content: dict
    index: int | None


@dataclass
class InstagramSettingsParamsDataClassPrivate:
    header: dict
    cookie: dict
    body: dict
