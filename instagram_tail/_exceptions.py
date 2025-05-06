from httpx import Response


class ParseException(Exception):
    def __init__(self, message: str, response: Response | None = None):
        super().__init__(self)
        self.response = response
        self.message = message

    def __str__(self):
        if self.response is not None:
            return f"{self.message}. \nResponse: status={self.response.status_code}, headers={self.response.headers}, \ncookies={self.response.cookies}"
        else:
            return f"{self.message}"


class AccountBlockedException(ParseException):
    pass
