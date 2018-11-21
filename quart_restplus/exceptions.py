from http import HTTPStatus
from quart.exceptions import HTTPStatusException, abort


class Unauthorized(HTTPStatusException):
    status = HTTPStatus.UNAUTHORIZED


class NotAcceptable(HTTPStatusException):
    status = HTTPStatus.NOT_ACCEPTABLE
