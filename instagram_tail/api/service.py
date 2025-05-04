import asyncio
import random
import urllib.parse
from configparser import ParsingError

import httpx
from httpx import AsyncClient

from instagram_tail import InstagramApi
from instagram_tail._model import CollectedData, PlainPost
from instagram_tail.api.exceptions import AccountBlockedException, AllProxyExpiredException, ProxyBreakException
from instagram_tail.auth.exceptions import InstagramSignInException
from instagram_tail.utils import _converters
from instagram_tail.utils._accounts import Account, AccountPool
from instagram_tail.utils._proxy import ProxyPool
from instagram_tail.utils._types import AccountStatus

from instagram_tail._model import Account as Acc


class Tail:
    def __init__(self, proxy_pool: ProxyPool):
        self._proxy_pool = proxy_pool
        self._headers = {
            'user-agent': 'Mozilla/5.0',
            'x-ig-app-id': '936619743392459',
            'x-instagram-ajax': '1',
            'x-requested-with': 'XMLHttpRequest',
        }
        self._last_user = None
        self._last_plain_posts = None

    async def get_data_of_user(self, target_username: str, host_account: Account, pool: AccountPool) -> CollectedData:
        proxy = await self._proxy_pool.get_proxy()
        if not proxy:
            print("Нет доступных прокси даже после ожидания")
            raise AllProxyExpiredException('Закончились доступные прокси')

        try:
            # authorized_api = InstagramApi(username=host_account.login,
            #                             password=host_account.password,
            #                             session_id=host_account.session_id,
            #                             token=host_account.token,
            #                             proxy=proxy.url)
            # print('api')
            # authorized_client = await authorized_api.get_private_client()
            # print('a_cl')
            # unauthorized_client = await InstagramApi(proxy=proxy.url).get_public_client()
            # print('u_cl')

            # if host_account.session_id is None or host_account.token is None:
            #     print('s_t')
            #     await pool.set_account_session_and_token(account=host_account, session_id=authorized_api._session_id, token=authorized_api._token)

            # cookies = {
            #     "sessionid": authorized_api._session_id,
            #     "csrftoken": authorized_api._token,
            #     'ds_user_id': authorized_api._session_id.split(':')[0]
            # }
            #
            # self._headers['x-csrftoken'] = authorized_api._token

            timeout = httpx.Timeout(
                connect=20.0,
                read=30.0,
                write=15.0,
                pool=10.0
            )

            # async with AsyncClient(headers=self._headers, cookies=cookies, proxy=proxy.url, timeout=timeout) as session:
            #     account_data = await authorized_client.get_account_data(target_username, session)
            #     print(f'Account: {account_data}')
            #
            #     if isinstance(account_data, ParsingError):
            #         return CollectedData(account=account_data, posts=None)
            #
            #     plain_posts = await authorized_client.get_plain_posts_data(target_username, session)
            #     posts = await unauthorized_client.get_full_posts(plain_posts, session)
            #     print(f'Posts: {posts}')
            #
            #     await self._proxy_pool.mark_success(proxy)
            #     return CollectedData(account=account_data, posts=posts)

            cookies = {
                'ds_user_id': host_account.headers['IG-U-DS-USER-ID'],
                'mid': host_account.headers['X-MID'],
                'rur': host_account.headers['IG-U-RUR'],
            }

            async with AsyncClient(headers=host_account.headers, cookies=cookies, proxy=proxy.url, timeout=timeout) as session:
                authorized_client = await InstagramApi(proxy=proxy.url).get_mobile_client()
                unauthorized_client = await InstagramApi(proxy=proxy.url).get_public_client()

                if self._last_user is None:
                    account_data = await authorized_client.get_account_data(target_username, session)
                    self._last_user = account_data
                else:
                    account_data = self._last_user
                print(f'Account: {self._last_user}')

                if isinstance(account_data, ParsingError):
                    return CollectedData(account=account_data, posts=None)

                if self._last_plain_posts is None:
                    plain_posts = await authorized_client.get_plain_posts_data(account_data.user_id, session)
                    self._last_plain_posts = plain_posts
                else:
                    plain_posts = self._last_plain_posts
                print(f'Plain Posts: {self._last_plain_posts}')

                posts = await unauthorized_client.get_full_posts(self._last_plain_posts)
                print(f'Posts: {posts}')

                await self._proxy_pool.mark_success(proxy)

                self._last_user = None
                self._last_plain_posts = None

                return CollectedData(account=account_data, posts=posts)

        except httpx.ProxyError as e:
            await self._proxy_pool.mark_fail(proxy)
            raise ProxyBreakException(f"Ошибка прокси: {e}")
        except httpx.ConnectError as e:
            print(f"Ошибка подключения: {e}")
            await self._proxy_pool.mark_fail(proxy)
            raise ProxyBreakException(f"Ошибка прокси: {e}")
        except httpx.ReadTimeout as e:
            print("Таймаут при чтении ответа")
            await self._proxy_pool.mark_fail(proxy)
            raise ProxyBreakException(f"Ошибка прокси: {e}")
        except httpx.RequestError as e:
            print(f"Ошибка реквеста: {proxy.url}, ошибка: {e}")
            await self._proxy_pool.mark_fail(proxy)
            raise ProxyBreakException(f"Ошибка прокси: {e}")
        except AccountBlockedException as e:
            raise AccountBlockedException(e.message)
        except InstagramSignInException as e:
            print(e.response.text)
            raise AccountBlockedException(e.message)
        except Exception as e:
            print(f"Ошибка при парсинге: {e}")
            if hasattr(e, 'response'):
                print(f"Респонс: {e.response.text}")
                if e.response.status_code == 400 or 'challenge_required' in e.response.text:
                    await pool.mark_account_status(account=host_account, new_status=AccountStatus.CHALLENGE_REQUIRED)
                    raise AccountBlockedException(f'Аккаунт {host_account.login} заблокирован')

            return CollectedData(account=ParsingError(f"Ошибка при парсинге: {e}"), posts=None)
