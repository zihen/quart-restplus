# -*- coding: utf-8 -*-
import asyncio

from datetime import timedelta
from quart import make_response, request, current_app
from functools import update_wrapper


def crossdomain(origin=None, methods=None, headers=None, expose_headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True, credentials=False):
    """
    http://quart.pocoo.org/snippets/56/
    """
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, str):
        headers = ', '.join(x.upper() for x in headers)
    if expose_headers is not None and not isinstance(expose_headers, str):
        expose_headers = ', '.join(x.upper() for x in expose_headers)
    if not isinstance(origin, str):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    async def get_methods():
        if methods is not None:
            return methods

        options_resp = await current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        async def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = await current_app.make_default_options_response()
            else:
                result = f(*args, **kwargs)
                while asyncio.iscoroutine(result):
                    result = await result
                resp = await make_response(result)
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = await get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if credentials:
                h['Access-Control-Allow-Credentials'] = 'true'
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            if expose_headers is not None:
                h['Access-Control-Expose-Headers'] = expose_headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)

    return decorator
