# -*- coding: utf-8 -*-
import quart_restplus as restplus

from quart_restplus import Namespace, Model, OrderedModel


def test_parser():
    api = Namespace('test')
    assert isinstance(api.parser(), restplus.reqparse.RequestParser)


def test_doc_decorator():
    api = Namespace('test')
    params = {'q': {'description': 'some description'}}

    @api.doc(params=params)
    class TestResource(restplus.Resource):
        pass

    assert hasattr(TestResource, '__apidoc__')
    assert TestResource.__apidoc__ == {'params': params}


def test_doc_with_inheritance():
    api = Namespace('test')
    base_params = {'q': {'description': 'some description', 'type': 'string', 'paramType': 'query'}}
    child_params = {'q': {'description': 'some new description'}, 'other': {'description': 'another param'}}

    @api.doc(params=base_params)
    class BaseResource(restplus.Resource):
        pass

    @api.doc(params=child_params)
    class TestResource(BaseResource):
        pass

    assert TestResource.__apidoc__ == {'params': {
        'q': {
            'description': 'some new description',
            'type': 'string',
            'paramType': 'query'
        },
        'other': {'description': 'another param'},
    }}


def test_model():
    api = Namespace('test')
    api.model('Person', {})
    assert 'Person' in api.models
    assert isinstance(api.models['Person'], Model)


def test_ordered_model():
    api = Namespace('test', ordered=True)
    api.model('Person', {})
    assert 'Person' in api.models
    assert isinstance(api.models['Person'], OrderedModel)


def test_schema_model():
    api = Namespace('test')
    api.schema_model('Person', {})
    assert 'Person' in api.models


def test_clone():
    api = Namespace('test')
    parent = api.model('Parent', {})
    api.clone('Child', parent, {})

    assert 'Child' in api.models
    assert 'Parent' in api.models


def test_clone_with_multiple_parents():
    api = Namespace('test')
    grand_parent = api.model('GrandParent', {})
    parent = api.model('Parent', {})
    api.clone('Child', grand_parent, parent, {})

    assert 'Child' in api.models
    assert 'Parent' in api.models
    assert 'GrandParent' in api.models


def test_inherit():
    authorizations = {
        'apikey': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'X-API-KEY'
        }
    }
    api = Namespace('test', authorizations=authorizations)
    parent = api.model('Parent', {})
    api.inherit('Child', parent, {})

    assert 'Parent' in api.models
    assert 'Child' in api.models
    assert api.authorizations == authorizations


def test_inherit_from_multiple_parents():
    api = Namespace('test')
    grand_parent = api.model('GrandParent', {})
    parent = api.model('Parent', {})
    api.inherit('Child', grand_parent, parent, {})

    assert 'GrandParent' in api.models
    assert 'Parent' in api.models
    assert 'Child' in api.models


async def test_api_payload(app, client):
    api = restplus.Api(app, validate=True)
    ns = restplus.Namespace('apples')
    api.add_namespace(ns)

    fields = ns.model('Person', {
        'name': restplus.fields.String(required=True),
        'age': restplus.fields.Integer,
        'birthdate': restplus.fields.DateTime,
    })

    @ns.route('/validation/')
    class Payload(restplus.Resource):
        payload = None

        @ns.expect(fields)
        async def post(self):
            Payload.payload = await ns.payload
            return {}

    data = {
        'name': 'John Doe',
        'age': 15,
        'birthdate': '2019-10-12'
    }
    await client.post_json('/apples/validation/', data)

    assert Payload.payload == data
