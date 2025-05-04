from httpx import Response


class ResponseException(Exception):
    def __init__(self, message: str, response: Response | None = None):
        super().__init__(self)
        self.response = response
        self.message = message

    def __str__(self):
        if self.response is not None:
            return f"{self.message}. \nResponse: status={self.response.status_code}, headers={self.response.headers}, \ncookies={self.response.cookies}"
        else:
            return f"{self.message}"


class InstagramSignInException(ResponseException):
    pass


class InstagramSessionExpiredException(ResponseException):
    pass


class InstagramLoginNonceException(ResponseException):
    """Error in receiving the login_nonce token"""

    pass


class CSRFTokenException(ResponseException):
    pass
