# -*- coding: utf-8 -*-
try:
    from ujson import dumps
except ImportError:
    from json import dumps

from quart import make_response, current_app


async def output_json(data, code, headers=None):
    """Makes a Quart response with a JSON encoded body"""

    settings = current_app.config.get('RESTPLUS_JSON', {})

    # If we're in debug mode, and the indent is not set, we set it to a
    # reasonable value here.  Note that this won't override any existing value
    # that was set.
    if current_app.debug:
        settings.setdefault('indent', 4)

    # always end the json dumps with a new line
    # see https://github.com/mitsuhiko/quart/pull/1262
    dumped = dumps(data, **settings) + "\n"

    resp = await make_response(dumped, code)
    resp.headers.extend(headers or {})
    return resp
