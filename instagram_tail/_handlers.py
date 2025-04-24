from itertools import cycle

from instagram_tail.auth.models import AuthorizedUser


class Accounts:
    _accounts = cycle([
        AuthorizedUser(login='arseniy_1win', password='FXF4Gv8pMj',
                       session_id='64517637785:bP5UlcmplOegW3:3:AYcHmGxhF9qzsgS5zXyTxe80Yhsq6xtQGXwuQ7llAw',
                       token='sem6uNmDINdE1vzNQc4LIZMz84ZGQnIH'),
        AuthorizedUser(login='Igor__1win', password='2?JiN2EK',
                       session_id='57290682830:rbuyIsOEm9SX1I:14:AYfAMYlr1QjWUVkx9mOQYT264WPinGgPGN5ZYeSqCg',
                       token='sem6uNmDINdE1vzNQc4LIZMz84ZGQnIH'),
        AuthorizedUser(login='1win_dali', password='Lf-4#g8g^%Khfd45',
                       session_id='286281810:V66TRMwPZxjZXl:18:AYdMvqEAHzXy_p4VaOR-EGmrR15CjNbB4ETgq58wMw',
                       token=None),
    ])
    # _current_account = None

    # def get_next_session_id(self) -> str:
    #     self._current_account = next(self._accounts)
    #     return self._current_account['session_id']

    def get_next_user(self) -> AuthorizedUser:
        return next(self._accounts)
