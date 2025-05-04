from enum import Enum


class PostType(Enum):
    Post = "Post"
    Reel = "Reel"
    Carousel = "Carousel"


class AccountStatus(Enum):
    WORKING = "working"
    CHALLENGE_REQUIRED = "challenge"
    TEMP_BLOCKED = "temp_blocked"
    BANNED = "banned"
    PASSWORD_CHANGE_REQUIRED = "password_change"
    CHECKPOINT_REQUIRED = "checkpoint"
    UNKNOWN = "unknown"
