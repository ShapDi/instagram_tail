from dataclasses import dataclass


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
class ReelModel:
    media_id: str
    code: str
    description: str
    duration: float
    like_count: int
    view_count: int
    play_count: int
    author: ReelAuthor
    previews: list[ReelPreview]
    videos: list[ReelVideo]


@dataclass
class InstagramSettingDataClassPrivate:
    content: dict
    index: int | None


@dataclass
class InstagramSettingsParamsDataClassPrivate:
    header: dict
    cookie: dict
    body: dict
