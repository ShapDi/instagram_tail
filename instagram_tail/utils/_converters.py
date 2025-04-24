from instagram_tail.utils._types import PostType


def post_id_to_url(id: str) -> str:
    return f'https://www.instagram.com/p/{id}/'

def media_type_to_post_type(type: str) -> PostType:
    match type:
        case 1:
            return PostType.Post
        case 2:
            return PostType.Reel
        case _:
            raise Exception(f'Unexpected media type. Type index: {type}')