from httpx import AsyncClient

from instagram_tail import InstagramApi
from instagram_tail._model import CollectedData
from instagram_tail.auth.models import AuthorizedUser


class Tail:
    def __init__(self):
        self._headers = {
            'user-agent': 'Mozilla/5.0',
            'x-ig-app-id': '936619743392459',
            'x-instagram-ajax': '1',
            'x-requested-with': 'XMLHttpRequest',
        }

    async def get_data_of_user(self, target_username: str, host_account: AuthorizedUser, proxy: str | None = None) -> CollectedData:
        authorized_api = InstagramApi(username=host_account.login,
                                    password=host_account.password,
                                    session_id=host_account.session_id,
                                    token=host_account.token,
                                    proxy=proxy)
        authorized_client = await authorized_api.get_private_client()
        unauthorized_client = await InstagramApi(proxy=proxy).get_public_client()

        cookies = {
            "sessionid": authorized_api._session_id,
            "csrftoken": authorized_api._token,
            'ds_user_id': authorized_api._session_id.split(':')[0]
        }

        self._headers['x-csrftoken'] = authorized_api._token

        async with AsyncClient(headers=self._headers, cookies=cookies, proxy=proxy) as session:
            account_data = await authorized_client.get_account_data(target_username, session)
            print(f'Account: {account_data}')
            plain_posts = await authorized_client.get_plain_posts_data(target_username, session)

            posts = await unauthorized_client.get_full_posts(plain_posts, session)
            print(f'Posts: {posts}')

            return CollectedData(account=account_data, posts=posts)
