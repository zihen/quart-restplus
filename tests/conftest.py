# -*- coding: utf-8 -*-
import inspect
import asyncio
import pytest
import quart_restplus as restplus

from _pytest.python import Function
from _pytest.fixtures import SubRequest

from quart import Blueprint
from quart_restplus.testing import TestQuart, TestClient


@pytest.fixture
def app():
    app = TestQuart(__name__)
    app.test_client_class = TestClient
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def api(request: SubRequest, app: TestQuart):
    marker = request.node.get_closest_marker('api')
    bpkwargs = {}
    kwargs = {}
    if marker:
        if 'prefix' in marker.kwargs:
            bpkwargs['url_prefix'] = marker.kwargs.pop('prefix')
        if 'subdomain' in marker.kwargs:
            bpkwargs['subdomain'] = marker.kwargs.pop('subdomain')
        kwargs = marker.kwargs
    blueprint = Blueprint('api', __name__, **bpkwargs)
    api = restplus.Api(blueprint, **kwargs)
    app.register_blueprint(blueprint)
    yield api


@pytest.fixture(autouse=True)
def _config_app(request: SubRequest, app: TestQuart):
    marker = request.node.get_closest_marker('config')
    if marker:
        for key, value in marker.kwargs.items():
            app.config[key.upper()] = value


@pytest.fixture(autouse=True)
def _mark_asyncio(request: SubRequest, event_loop: asyncio.AbstractEventLoop):
    node: Function = request.node
    if inspect.iscoroutinefunction(request.function):
        node.funcargs.setdefault('event_loop', event_loop)
        node.add_marker(pytest.mark.asyncio)
