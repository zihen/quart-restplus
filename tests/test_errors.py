# -*- coding: utf-8 -*-
import json
import pytest
import quart_restplus as restplus

from http import HTTPStatus
from quart import Blueprint, abort
from quart.signals import got_request_exception
from quart.exceptions import (
    HTTPException,
    HTTPStatusException,
    BadRequest,
    NotFound
)
from quart_restplus.utils import quote_etag, unquote_etag


def test_abort_type():
    with pytest.raises(HTTPException):
        restplus.abort(404)


def test_abort_data():
    with pytest.raises(HTTPException) as cm:
        restplus.abort(404, foo='bar')
    assert cm.value.data == {'foo': 'bar'}


def test_abort_no_data():
    with pytest.raises(HTTPException) as cm:
        restplus.abort(404)
    assert not hasattr(cm.value, 'data')


def test_abort_custom_message():
    with pytest.raises(HTTPException) as cm:
        restplus.abort(404, 'My message')
    assert cm.value.data['message'] == 'My message'


async def test_abort_code_only_with_defaults(app, client):
    api = restplus.Api(app)

    @api.route('/test/', endpoint='test')
    class TestResource(restplus.Resource):
        async def get(self):
            api.abort(403)

    response = await client.get('/test/')
    assert response.status_code == 403
    assert response.content_type == 'application/json'

    data = json.loads(await response.get_data(False))
    assert 'message' in data


async def test_abort_with_message(app, client):
    api = restplus.Api(app)

    @api.route('/test/', endpoint='test')
    class TestResource(restplus.Resource):
        async def get(self):
            api.abort(403, 'A message')

    response = await client.get('/test/')
    assert response.status_code == 403
    assert response.content_type == 'application/json'

    data = json.loads(await response.get_data(False))
    assert data['message'] == 'A message'


async def test_abort_with_lazy_init(app, client):
    api = restplus.Api()

    @api.route('/test/', endpoint='test')
    class TestResource(restplus.Resource):
        async def get(self):
            api.abort(403)

    api.init_app(app)

    response = await client.get('/test/')
    assert response.status_code == 403
    assert response.content_type == 'application/json'

    data = json.loads(await response.get_data(False))
    assert 'message' in data


async def test_abort_on_exception(app, client):
    api = restplus.Api(app)

    @api.route('/test/', endpoint='test')
    class TestResource(restplus.Resource):
        async def get(self):
            raise ValueError()

    response = await client.get('/test/')
    assert response.status_code == 500
    assert response.content_type == 'application/json'

    data = json.loads(await response.get_data(False))
    assert 'message' in data


async def test_abort_on_exception_with_lazy_init(app, client):
    api = restplus.Api()

    @api.route('/test/', endpoint='test')
    class TestResource(restplus.Resource):
        async def get(self):
            raise ValueError()

    api.init_app(app)

    response = await client.get('/test/')
    assert response.status_code == 500
    assert response.content_type == 'application/json'

    data = json.loads(await response.get_data(False))
    assert 'message' in data


async def test_errorhandler_for_exception_inheritance(app, client):
    api = restplus.Api(app)

    class CustomException(RuntimeError):
        pass

    @api.route('/test/', endpoint='test')
    class TestResource(restplus.Resource):
        async def get(self):
            raise CustomException('error')

    @api.errorhandler(RuntimeError)
    def handle_custom_exception(error):
        return {'message': str(error), 'test': 'value'}, 400

    response = await client.get('/test/')
    assert response.status_code == 400
    assert response.content_type == 'application/json'

    data = json.loads(await response.get_data(False))
    assert data == {
        'message': 'error',
        'test': 'value',
    }


async def test_errorhandler_for_custom_exception(app, client):
    api = restplus.Api(app)

    class CustomException(RuntimeError):
        pass

    @api.route('/test/', endpoint='test')
    class TestResource(restplus.Resource):
        async def get(self):
            raise CustomException('error')

    @api.errorhandler(CustomException)
    def handle_custom_exception(error):
        return {'message': str(error), 'test': 'value'}, 400

    response = await client.get('/test/')
    assert response.status_code == 400
    assert response.content_type == 'application/json'

    data = json.loads(await response.get_data(False))
    assert data == {
        'message': 'error',
        'test': 'value',
    }


async def test_errorhandler_for_custom_exception_with_headers(app, client):
    api = restplus.Api(app)

    class CustomException(RuntimeError):
        pass

    @api.route('/test/', endpoint='test')
    class TestResource(restplus.Resource):
        async def get(self):
            raise CustomException('error')

    @api.errorhandler(CustomException)
    def handle_custom_exception(error):
        return {'message': 'some maintenance'}, 503, {'Retry-After': 120}

    response = await client.get('/test/')
    assert response.status_code == 503
    assert response.content_type == 'application/json'

    data = json.loads(await response.get_data(False))
    assert data == {'message': 'some maintenance'}
    assert response.headers['Retry-After'] == 120


async def test_errorhandler_for_httpexception(app, client):
    api = restplus.Api(app)

    @api.route('/test/', endpoint='test')
    class TestResource(restplus.Resource):
        async def get(self):
            raise BadRequest()

    @api.errorhandler(BadRequest)
    def handle_badrequest_exception(error):
        return {'message': str(error), 'test': 'value'}, 400

    response = await client.get('/test/')
    assert response.status_code == 400
    assert response.content_type == 'application/json'

    data = json.loads(await response.get_data(False))
    assert data == {
        'message': str(BadRequest()),
        'test': 'value',
    }


async def test_errorhandler_with_namespace(app, client):
    api = restplus.Api(app)

    ns = restplus.Namespace("ExceptionHandler", path="/")

    class CustomException(RuntimeError):
        pass

    @ns.route('/test/', endpoint='test')
    class TestResource(restplus.Resource):
        async def get(self):
            raise CustomException('error')

    @ns.errorhandler(CustomException)
    def handle_custom_exception(error):
        return {'message': str(error), 'test': 'value'}, 400

    api.add_namespace(ns)

    response = await client.get('/test/')
    assert response.status_code == 400
    assert response.content_type == 'application/json'

    data = json.loads(await response.get_data(False))
    assert data == {
        'message': 'error',
        'test': 'value',
    }


async def test_errorhandler_with_namespace_from_api(app, client):
    api = restplus.Api(app)

    ns = api.namespace("ExceptionHandler", path="/")

    class CustomException(RuntimeError):
        pass

    @ns.route('/test/', endpoint='test')
    class TestResource(restplus.Resource):
        async def get(self):
            raise CustomException('error')

    @ns.errorhandler(CustomException)
    def handle_custom_exception(error):
        return {'message': str(error), 'test': 'value'}, 400

    response = await client.get('/test/')
    assert response.status_code == 400
    assert response.content_type == 'application/json'

    data = json.loads(await response.get_data(False))
    assert data == {
        'message': 'error',
        'test': 'value',
    }


async def test_default_errorhandler(app, client):
    api = restplus.Api(app)

    @api.route('/test/')
    class TestResource(restplus.Resource):
        async def get(self):
            raise Exception('error')

    response = await client.get('/test/')
    assert response.status_code == 500
    assert response.content_type == 'application/json'

    data = json.loads(await response.get_data(False))
    assert 'message' in data


async def test_default_errorhandler_with_propagate_true(app, client):
    blueprint = Blueprint('api', __name__, url_prefix='/api')
    api = restplus.Api(blueprint)

    @api.route('/test/')
    class TestResource(restplus.Resource):
        async def get(self):
            raise Exception('error')

    app.register_blueprint(blueprint)

    app.config['PROPAGATE_EXCEPTIONS'] = True

    response = await client.get('/api/test/')
    assert response.status_code == 500
    assert response.content_type == 'application/json'

    data = json.loads(await response.get_data(False))
    assert 'message' in data


async def test_custom_default_errorhandler(app, client):
    api = restplus.Api(app)

    @api.route('/test/', endpoint='test')
    class TestResource(restplus.Resource):
        async def get(self):
            raise Exception('error')

    @api.errorhandler
    def default_error_handler(error):
        return {'message': str(error), 'test': 'value'}, 500

    response = await client.get('/test/')
    assert response.status_code == 500
    assert response.content_type == 'application/json'

    data = json.loads(await response.get_data(False))
    assert data == {
        'message': 'error',
        'test': 'value',
    }


async def test_custom_default_errorhandler_with_headers(app, client):
    api = restplus.Api(app)

    @api.route('/test/', endpoint='test')
    class TestResource(restplus.Resource):
        async def get(self):
            raise Exception('error')

    @api.errorhandler
    def default_error_handler(error):
        return {'message': 'some maintenance'}, 503, {'Retry-After': 120}

    response = await client.get('/test/')
    assert response.status_code == 503
    assert response.content_type == 'application/json'

    data = json.loads(await response.get_data(False))
    assert data == {'message': 'some maintenance'}
    assert response.headers['Retry-After'] == 120


async def test_errorhandler_lazy(app, client):
    api = restplus.Api()

    class CustomException(RuntimeError):
        pass

    @api.route('/test/', endpoint='test')
    class TestResource(restplus.Resource):
        async def get(self):
            raise CustomException('error')

    @api.errorhandler(CustomException)
    def handle_custom_exception(error):
        return {'message': str(error), 'test': 'value'}, 400

    api.init_app(app)

    response = await client.get('/test/')
    assert response.status_code == 400
    assert response.content_type == 'application/json'

    data = json.loads(await response.get_data(False))
    assert data == {
        'message': 'error',
        'test': 'value',
    }


async def test_handle_api_error(app, client):
    api = restplus.Api(app)

    @api.route('/api', endpoint='api')
    class Test(restplus.Resource):
        async def get(self):
            abort(404)

    response = await client.get('/api')
    assert response.status_code == 404
    assert response.headers['Content-Type'] == 'application/json'
    data = json.loads(await response.get_data(False))
    assert 'message' in data


async def test_handle_non_api_error(app, client):
    restplus.Api(app)

    response = await client.get('/foo')
    assert response.status_code == 404
    assert response.headers['Content-Type'] == 'text/html'


async def test_non_api_error_404_catchall(app, client):
    api = restplus.Api(app, catch_all_404s=True)

    response = await client.get('/foo')
    assert response.headers['Content-Type'] == api.default_mediatype


async def test_handle_error_signal(app):
    api = restplus.Api(app)
    exception = BadRequest()
    recorded = []

    def record(sender, exception):
        recorded.append(exception)

    async with app.test_request_context():
        got_request_exception.connect(record, app, weak=False)
        try:
            await api.handle_error(exception)
            assert len(recorded) == 1
            assert exception is recorded[0]
        finally:
            got_request_exception.disconnect(record, app)


async def test_handle_error(app):
    api = restplus.Api(app)

    async with app.test_request_context():
        err = BadRequest()
        response = await api.handle_error(err)
        assert response.status_code == 400
        assert json.loads(await response.get_data(False)) == {
            'message': err.description,
        }


async def test_handle_error_does_not_duplicate_content_length(app):
    api = restplus.Api(app)

    async with app.test_request_context():
        response = await api.handle_error(BadRequest())
        assert len(response.headers.getlist('Content-Length')) == 1


async def test_handle_smart_errors(app):
    api = restplus.Api(app)
    view = restplus.Resource

    api.add_resource(view, '/foo', endpoint='bor')
    api.add_resource(view, '/fee', endpoint='bir')
    api.add_resource(view, '/fii', endpoint='ber')

    async with app.test_request_context('/faaaaa'):
        err = NotFound()
        response = await api.handle_error(err)
        assert response.status_code == 404
        assert json.loads(await response.get_data(False)) == {
            'message': err.description,
        }

    async with app.test_request_context('/fOo'):
        err = NotFound()
        response = await api.handle_error(err)
        assert response.status_code == 404
        assert 'did you mean /foo ?' in await response.get_data(False)

        app.config['ERROR_404_HELP'] = False

        err = NotFound()
        response = await api.handle_error(err)
        assert response.status_code == 404
        assert json.loads(await response.get_data(False)) == {
            'message': err.description
        }


async def test_handle_include_error_message(app):
    api = restplus.Api(app)
    view = restplus.Resource

    api.add_resource(view, '/foo', endpoint='bor')

    async with app.test_request_context('/faaaaa'):
        response = await api.handle_error(NotFound())
        assert 'message' in json.loads(await response.get_data(False))


async def test_handle_not_include_error_message(app):
    app.config['ERROR_INCLUDE_MESSAGE'] = False

    api = restplus.Api(app)
    view = restplus.Resource

    api.add_resource(view, '/foo', endpoint='bor')

    async with app.test_request_context('/faaaaa'):
        response = await api.handle_error(NotFound())
        assert 'message' not in json.loads(await response.get_data(False))


async def test_error_router_falls_back_to_original(app, mocker):
    api = restplus.Api(app)
    api.handle_error = mocker.Mock(side_effect=Exception())
    api._has_fr_route = mocker.Mock(return_value=True)
    exception = mocker.Mock(spec=HTTPException)
    called = []

    async def handle_exception(e):
        called.append(e)
        mocker.Mock()(e)

    app.handle_exception = handle_exception

    async with app.test_request_context():
        await api.error_router(app.handle_exception, exception)
        assert len(called) == 1
        assert called[0] is exception


async def test_fr_405(app, client):
    api = restplus.Api(app)

    @api.route('/ids/<int:id>', endpoint='hello')
    class HelloWorld(restplus.Resource):
        async def get(self):
            return {}

    response = await client.post('/ids/3')
    assert response.status_code == 405
    assert response.content_type == api.default_mediatype
    # Allow can be of the form 'GET, PUT, POST'
    allow = ', '.join(set(response.headers.getall('Allow')))
    allow = set(method.strip() for method in allow.split(','))
    assert allow == {'HEAD', 'OPTIONS', 'GET'}


@pytest.mark.config(debug=True)
async def test_exception_header_forwarded(app, client):
    """Ensure that HTTPException's headers are extended properly"""
    api = restplus.Api(app)

    class NotModified(HTTPStatusException):
        status = HTTPStatus.NOT_MODIFIED

        def __init__(self, etag, *args, **kwargs):
            super(NotModified, self).__init__(*args, **kwargs)
            self.etag = quote_etag(etag)

        def get_headers(self, *args, **kwargs):
            return [('ETag', self.etag)]

    @api.route('/foo')
    class Foo1(restplus.Resource):
        async def get(self):
            raise NotModified('myETag')

    foo = await client.get('/foo')
    assert foo.get_etag() == unquote_etag(quote_etag('myETag'))


async def test_handle_server_error(app):
    api = restplus.Api(app)

    async with app.test_request_context():
        resp = await api.handle_error(Exception())
        assert resp.status_code == 500
        assert json.loads(await resp.get_data(False)) == {
            'message': 'Internal Server Error'
        }


async def test_handle_error_with_code(app):
    api = restplus.Api(app, serve_challenge_on_401=True)

    exception = Exception()
    exception.code = 'Not an integer'
    exception.data = {'foo': 'bar'}

    async with app.test_request_context():
        response = await api.handle_error(exception)
        assert response.status_code == 500
        assert json.loads(await response.get_data(False)) == {'foo': 'bar'}


async def test_errorhandler_swagger_doc(app, client):
    api = restplus.Api(app)

    class CustomException(RuntimeError):
        pass

    error = api.model('Error', {
        'message': restplus.fields.String()
    })

    @api.route('/test/', endpoint='test')
    class TestResource(restplus.Resource):
        async def get(self):
            """
            Do something

            :raises CustomException: In case of something
            """
            pass

    @api.errorhandler(CustomException)
    @api.header('Custom-Header', 'Some custom header')
    @api.marshal_with(error, code=503)
    async def handle_custom_exception(error):
        """Some description"""
        pass

    specs = await client.get_specs()

    assert 'Error' in specs['definitions']
    assert 'CustomException' in specs['responses']

    response = specs['responses']['CustomException']
    assert response['description'] == 'Some description'
    assert response['schema'] == {
        '$ref': '#/definitions/Error'
    }
    assert response['headers'] == {
        'Custom-Header': {
            'description': 'Some custom header',
            'type': 'string'
        }
    }

    operation = specs['paths']['/test/']['get']
    assert 'responses' in operation
    assert operation['responses'] == {
        '503': {
            '$ref': '#/responses/CustomException'
        }
    }
