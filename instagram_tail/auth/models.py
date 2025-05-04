from dataclasses import dataclass


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
class AuthorizedUser:
    login: str | None
    password: str | None
    session_id: str | None
    token: str | None
