# -*- coding: utf-8 -*-
import pytest
import quart_restplus as restplus

from quart import url_for, Blueprint
from quart.routing import BuildError


async def test_default_apidoc_on_root(app, client):
    restplus.Api(app, version='1.0')

    async with app.test_request_context():
        assert url_for('doc') == url_for('root')
        response = await client.get(url_for('doc'))
    assert response.status_code == 200
    assert response.content_type == 'text/html; charset=utf-8'


async def test_default_apidoc_on_root_lazy(app, client):
    api = restplus.Api(version='1.0')
    api.init_app(app)

    async with app.test_request_context():
        assert url_for('doc') == url_for('root')
        response = await client.get(url_for('doc'))
    assert response.status_code == 200
    assert response.content_type == 'text/html; charset=utf-8'


async def test_default_apidoc_on_root_with_blueprint(app, client):
    blueprint = Blueprint('api', __name__, url_prefix='/api')
    restplus.Api(blueprint, version='1.0')
    app.register_blueprint(blueprint)

    async with app.test_request_context():
        assert url_for('api.doc') == url_for('api.root')
        response = await client.get(url_for('api.doc'))
    assert response.status_code == 200
    assert response.content_type == 'text/html; charset=utf-8'


async def test_apidoc_with_custom_validator(app, client):
    app.config['SWAGGER_VALIDATOR_URL'] = 'http://somewhere.com/validator'
    restplus.Api(app, version='1.0')

    async with app.test_request_context():
        response = await client.get(url_for('doc'))
        data = await response.get_data()

    assert response.status_code == 200
    assert response.content_type == 'text/html; charset=utf-8'
    assert 'validatorUrl: "http://somewhere.com/validator" || null,' in data.decode()


async def test_apidoc_doc_expansion_parameter(app, client):
    restplus.Api(app)

    async with app.test_request_context():
        response = await client.get(url_for('doc'))
        assert 'docExpansion: "none"' in (await response.get_data(False))

        app.config['SWAGGER_UI_DOC_EXPANSION'] = 'list'
        response = await client.get(url_for('doc'))
        assert 'docExpansion: "list"' in (await response.get_data(False))

        app.config['SWAGGER_UI_DOC_EXPANSION'] = 'full'
        response = await client.get(url_for('doc'))
        assert 'docExpansion: "full"' in (await response.get_data(False))


async def test_apidoc_doc_display_operation_id(app, client):
    restplus.Api(app)

    async with app.test_request_context():
        response = await client.get(url_for('doc'))
        assert 'displayOperationId: false' in (await response.get_data(False))

        app.config['SWAGGER_UI_OPERATION_ID'] = False
        response = await client.get(url_for('doc'))
        assert 'displayOperationId: false' in (await response.get_data(False))

        app.config['SWAGGER_UI_OPERATION_ID'] = True
        response = await client.get(url_for('doc'))
        assert 'displayOperationId: true' in (await response.get_data(False))


async def test_apidoc_doc_display_request_duration(app, client):
    restplus.Api(app)

    async with app.test_request_context():
        response = await client.get(url_for('doc'))
        assert 'displayRequestDuration: false' in (await response.get_data(False))

        app.config['SWAGGER_UI_REQUEST_DURATION'] = False
        response = await client.get(url_for('doc'))
        assert 'displayRequestDuration: false' in (await response.get_data(False))

        app.config['SWAGGER_UI_REQUEST_DURATION'] = True
        response = await client.get(url_for('doc'))
        assert 'displayRequestDuration: true' in (await response.get_data(False))


async def test_custom_apidoc_url(app, client):
    restplus.Api(app, version='1.0', doc='/doc/')

    async with app.test_request_context():
        doc_url = url_for('doc')
        root_url = url_for('root')

    assert doc_url != root_url

    response = await client.get(root_url)
    assert response.status_code == 404

    assert doc_url == '/doc/'
    response = await client.get(doc_url)
    assert response.status_code == 200
    assert response.content_type == 'text/html; charset=utf-8'


async def test_custom_api_prefix(app):
    prefix = '/api'
    api = restplus.Api(app, prefix=prefix)
    api.namespace('resource')
    async with app.test_request_context():
        assert url_for('root') == prefix


async def test_custom_apidoc_page(app, client):
    api = restplus.Api(app, version='1.0')
    content = 'My Custom API Doc'

    @api.documentation
    def api_doc():
        return content

    async with app.test_request_context():
        response = await client.get(url_for('doc'))
        assert response.status_code == 200
        assert (await response.get_data(False)) == content


async def test_custom_apidoc_page_lazy(app, client):
    blueprint = Blueprint('api', __name__, url_prefix='/api')
    api = restplus.Api(blueprint, version='1.0')
    content = 'My Custom API Doc'

    @api.documentation
    def api_doc():
        return content

    app.register_blueprint(blueprint)

    async with app.test_request_context():
        response = await client.get(url_for('api.doc'))
        assert response.status_code == 200
        assert (await response.get_data(False)) == content


async def test_disabled_apidoc(app, client):
    restplus.Api(app, version='1.0', doc=False)

    async with app.test_request_context():
        with pytest.raises(BuildError):
            url_for('doc')

        response = await client.get(url_for('root'))
    assert response.status_code == 404
