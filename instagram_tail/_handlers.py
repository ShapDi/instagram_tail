from itertools import cycle

from instagram_tail.auth.models import AuthorizedUser


class Accounts:
    _accounts = cycle([

    ])
    # _current_account = None

    # def get_next_session_id(self) -> str:
    #     self._current_account = next(self._accounts)
    #     return self._current_account['session_id']

    def get_next_user(self) -> AuthorizedUser:
        return next(self._accounts)
