from configparser import ParsingError

import httpx
from httpx import AsyncClient

from instagram_tail._model import CollectedData
from instagram_tail.api.exceptions import AccountBlockedException
from instagram_tail.auth.exceptions import InstagramSignInException
from instagram_tail.utils._accounts import Account, AccountPool
from instagram_tail.utils._proxy import ProxyPool


class Tail:
    def __init__(self, proxy_pool: ProxyPool):
        self._proxy_pool = proxy_pool
        self._headers = {
            "user-agent": "Mozilla/5.0",
            "x-ig-app-id": "936619743392459",
            "x-instagram-ajax": "1",
            "x-requested-with": "XMLHttpRequest",
        }

    async def get_data_of_user(
        self, target_username: str, host_account: Account, pool: AccountPool
    ) -> CollectedData:
        proxy = await self._proxy_pool.get_proxy()
        if not proxy:
            print("Нет доступных прокси даже после ожидания")
            return CollectedData(
                account=ParsingError("Все прокси отлетели"), posts=None
            )

        try:
            authorized_api = InstagramApi(
                username=host_account.login,
                password=host_account.password,
                session_id=host_account.session_id,
                token=host_account.token,
                proxy=proxy.url,
            )
            print("api")
            authorized_client = await authorized_api.get_private_client()
            print("a_cl")
            unauthorized_client = await InstagramApi(
                proxy=proxy.url
            ).get_public_client()
            print("u_cl")

            if host_account.session_id is None or host_account.token is None:
                print("s_t")
                await pool.set_account_session_and_token(
                    account=host_account,
                    session_id=authorized_api._session_id,
                    token=authorized_api._token,
                )

            cookies = {
                "sessionid": authorized_api._session_id,
                "csrftoken": authorized_api._token,
                "ds_user_id": authorized_api._session_id.split(":")[0],
            }

            self._headers["x-csrftoken"] = authorized_api._token

            timeout = httpx.Timeout(connect=15.0, read=20.0, write=10.0, pool=5.0)
            client = httpx.AsyncClient(
                headers=self._headers, cookies=cookies, proxy=proxy.url, timeout=timeout
            )
            async with AsyncClient(
                headers=self._headers, cookies=cookies, proxy=proxy.url, timeout=timeout
            ) as session:
                account_data = await authorized_client.get_account_data(
                    target_username, session
                )
                print(f"Account: {account_data}")

                if isinstance(account_data, ParsingError):
                    return CollectedData(account=account_data, posts=None)

                plain_posts = await authorized_client.get_plain_posts_data(
                    target_username, session
                )
                posts = await unauthorized_client.get_full_posts(plain_posts, session)
                print(f"Posts: {posts}")

                await self._proxy_pool.mark_success(proxy)
                return CollectedData(account=account_data, posts=posts)

        except httpx.ProxyError as e:
            print(f"Ошибка прокси: {e}")
            await self._proxy_pool.mark_fail(proxy)
            return CollectedData(
                account=ParsingError(f"Ошибка прокси: {proxy.url}, ошибка: {e}"),
                posts=None,
            )
        except httpx.ConnectError as e:
            print(f"Ошибка подключения: {e}")
            return CollectedData(
                account=ParsingError(f"Ошибка подключения: {proxy.url}, ошибка: {e}"),
                posts=None,
            )
        except httpx.ReadTimeout as e:
            print("Таймаут при чтении ответа")
            return CollectedData(
                account=ParsingError(
                    f"Таймаут при чтении ответа: {proxy.url}, ошибка: {e}"
                ),
                posts=None,
            )
        except httpx.RequestError as e:
            print(f"Прокси упал: {proxy.url}, ошибка: {e}")
            await self._proxy_pool.mark_fail(proxy)
            return CollectedData(
                account=ParsingError(f"Прокси упал: {proxy.url}, ошибка: {e}"),
                posts=None,
            )
        except AccountBlockedException as e:
            raise AccountBlockedException(e.message)
        except InstagramSignInException as e:
            print(e.response.text)
            return CollectedData(
                account=ParsingError(f"Ошибка при входе: {e}"), posts=None
            )
        except Exception as e:
            print(f"Ошибка при парсинге: {e}")
            # await self._proxy_pool.mark_fail(proxy)
            return CollectedData(
                account=ParsingError(f"Ошибка при парсинге: {e}"), posts=None
            )
