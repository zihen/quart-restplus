# -*- coding: utf-8 -*-
import asyncio

from typing import Union, Tuple, AnyStr, Any
from json import dumps, loads
from urllib.parse import urlencode, parse_qs, urlparse

from requests.models import PreparedRequest

from quart import Quart, Request, Response
from quart.ctx import RequestContext
from quart.datastructures import CIMultiDict
from quart.testing import QuartClient

sentinel = object()


def make_test_headers_path_and_query_string(
    app: Quart,
    path: str,
    headers: Union[dict, CIMultiDict] = None,
    query_string: dict = None,
) -> Tuple[CIMultiDict, str, bytes]:
    """Make the headers and path with defaults for testing.

    Arguments:
        app: The application to test against.
        path: The path to request. If the query_string argument is not
            defined this argument will be partitioned on a '?' with
            the following part being considered the query_string.
        headers: Initial headers to send.
        query_string: To send as a dictionary, alternatively the
            query_string can be determined from the path.
    """
    if headers is None:
        headers = CIMultiDict()
    elif isinstance(headers, CIMultiDict):
        headers = headers
    elif headers is not None:
        headers = CIMultiDict(headers)
    headers.setdefault('Remote-Addr', '127.0.0.1')
    headers.setdefault('User-Agent', 'Quart')
    headers.setdefault('host', app.config['SERVER_NAME'] or 'localhost')
    if '?' in path and query_string is not None:
        raise ValueError('Query string is defined in the path and as an argument')
    if query_string is None:
        path, _, query_string_raw = path.partition('?')
        if query_string_raw:
            query_string_raw = urlencode(parse_qs(query_string_raw), doseq=True)
    else:
        query_string_raw = urlencode(query_string, doseq=True)
    query_string_bytes = query_string_raw.encode()
    return headers, path, query_string_bytes  # type: ignore


class TestQuart(Quart):
    def test_request_context(
        self,
        path: str = '/',
        method: str = 'GET',
        *,
        scheme: str = 'http',
        headers: Union[dict, CIMultiDict] = None,
        data: Union[AnyStr, dict] = None
    ) -> RequestContext:
        headers, path, query_string = make_test_headers_path_and_query_string(self, path, headers=headers)

        if headers and headers.get('Content-Type', None) == 'application/json':
            body_data = dumps(data).encode() if data else b''
        elif data:
            if isinstance(data, str):
                headers.setdefault('Content-Type', 'application/x-www-form-urlencoded')
                body_data = data.encode()
            else:
                form = {}
                files = {}
                for key, value in data.items():
                    if isinstance(value, (list, tuple)):
                        files[key] = value
                    else:
                        form[key] = value
                prep = PreparedRequest()
                prep.headers = {}
                prep.prepare_body(data=form or None, files=files)
                body_data = prep.body
                headers.update(prep.headers)
        else:
            body_data = b''

        request = self.request_class(method, scheme, path, query_string, headers)
        request.body.set_result(body_data)
        return self.request_context(request)


class TestClient(QuartClient):
    async def open(
        self,
        path: str,
        *,
        method: str = 'GET',
        headers: Union[dict, CIMultiDict] = None,
        data: AnyStr = None,
        form: dict = None,
        query_string: dict = None,
        json: Any = sentinel,
        scheme: str = 'http',
        base_url: str = None
    ) -> Response:
        """Open a request to the app associated with this client.

        Arguemnts:
            path: The path to request. If the query_string argument is
                not defined this argument will be partitioned on a '?'
                with the following part being considered the
                query_string.
            method: The method to make the request with, defaults GET.
            headers: Headers to include in the request.
            data: Raw data to send in the request body.
            form: Data to send form encoded in the request body.
            query_string: To send as a dictionary, alternatively the
                query_string can be determined from the path.
            json: Data to send json encoded in the request body.
            scheme: The scheme to use in the request, default http.

        Returns:
            The response from the app handling the request.
        """
        headers, path, query_string_bytes = make_test_headers_path_and_query_string(
            self.app, path, headers, query_string,
        )

        if [json is not sentinel, form is not None, data is not None].count(True) > 1:
            raise ValueError("Quart test args 'json', 'form', and 'data' are mutually exclusive")

        request_data = b''

        if isinstance(data, str):
            request_data = data.encode('utf-8')
        elif isinstance(data, bytes):
            request_data = data

        if json is not sentinel:
            request_data = dumps(json).encode('utf-8')
            headers['Content-Type'] = 'application/json'

        if form is not None:
            request_data = urlencode(form).encode('utf-8')
            headers['Content-Type'] = 'application/x-www-form-urlencoded'

        if self.cookie_jar is not None:
            headers.add('Cookie', self.cookie_jar.output(header=''))  # type: ignore

        if base_url is not None:
            result = urlparse(base_url)
            scheme = result.scheme
            if result.path:
                path = '{}/{}'.format(result.path.rstrip('/'), path.lstrip('/'))
            headers.update({'Host': result.hostname})

        request = Request(method, scheme, path, query_string_bytes, headers)  # type: ignore
        request.body.set_result(request_data)
        response = await asyncio.create_task(self.app.handle_request(request))
        if self.cookie_jar is not None and 'Set-Cookie' in response.headers:
            self.cookie_jar.load(";".join(response.headers.getall('Set-Cookie')))
        return response

    async def open_json(self, url, json=sentinel, status=200, **kwargs):
        if json is not sentinel:
            response = await self.post(url, json=json, **kwargs)
        else:
            response = await self.get(url, **kwargs)
        assert response.status_code == status
        assert response.content_type == 'application/json'
        return loads(await response.get_data(False))

    def get_json(self, url, status=200, **kwargs):
        return self.open_json(url, status=status, **kwargs)

    def post_json(self, url, data, status=200, **kwargs):
        return self.open_json(url, status=status, json=data, **kwargs)

    def get_specs(self, prefix='', status=200, **kwargs):
        """Get a Swagger specification for a RestPlus API"""
        return self.get_json('{0}/swagger.json'.format(prefix), status=status, **kwargs)
