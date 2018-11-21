# -*- coding: utf-8 -*-
from quart_restplus.swagger import extract_path, extract_path_params, parse_docstring


class TestExtractPath(object):
    def test_extract_static_path(self):
        path = '/test'
        assert extract_path(path) == '/test'

    def test_extract_path_with_a_single_simple_parameter(self):
        path = '/test/<parameter>'
        assert extract_path(path) == '/test/{parameter}'

    def test_extract_path_with_a_single_typed_parameter(self):
        path = '/test/<string:parameter>'
        assert extract_path(path) == '/test/{parameter}'

    def test_extract_path_with_a_single_typed_parameter_with_arguments(self):
        path = '/test/<string(length=2):parameter>'
        assert extract_path(path) == '/test/{parameter}'

    def test_extract_path_with_multiple_parameters(self):
        path = '/test/<parameter>/<string:other>/'
        assert extract_path(path) == '/test/{parameter}/{other}/'


class TestExtractPathParams(object):
    async def test_extract_static_path(self, app):
        path = '/test'
        async with app.test_request_context():
            assert extract_path_params(path) == {}

    async def test_extract_single_simple_parameter(self, app):
        path = '/test/<parameter>'
        async with app.test_request_context():
            assert extract_path_params(path) == {
                'parameter': {
                    'name': 'parameter',
                    'type': 'string',
                    'in': 'path',
                    'required': True
                }
            }

    async def test_single_int_parameter(self, app):
        path = '/test/<int:parameter>'
        async with app.test_request_context():
            assert extract_path_params(path) == {
                'parameter': {
                    'name': 'parameter',
                    'type': 'integer',
                    'in': 'path',
                    'required': True
                }
            }

    async def test_single_float_parameter(self, app):
        path = '/test/<float:parameter>'
        async with app.test_request_context():
            assert extract_path_params(path) == {
                'parameter': {
                    'name': 'parameter',
                    'type': 'number',
                    'in': 'path',
                    'required': True
                }
            }

    async def test_extract_path_with_multiple_parameters(self, app):
        path = '/test/<parameter>/<int:other>/'
        async with app.test_request_context():
            assert extract_path_params(path) == {
                'parameter': {
                    'name': 'parameter',
                    'type': 'string',
                    'in': 'path',
                    'required': True
                },
                'other': {
                    'name': 'other',
                    'type': 'integer',
                    'in': 'path',
                    'required': True
                }
            }

    async def test_extract_parameter_with_arguments(self, app):
        path = '/test/<string(length=2):parameter>'
        async with app.test_request_context():
            assert extract_path_params(path) == {
                'parameter': {
                    'name': 'parameter',
                    'type': 'string',
                    'in': 'path',
                    'required': True
                }
            }


class TestParseDocstring(object):
    def test_empty(self):
        def without_doc():
            pass

        parsed = parse_docstring(without_doc)

        assert parsed['raw'] is None
        assert parsed['summary'] is None
        assert parsed['details'] is None
        assert parsed['returns'] is None
        assert parsed['raises'] == {}
        assert parsed['params'] == []

    def test_single_line(self):
        def func():
            """Some summary"""
            pass

        parsed = parse_docstring(func)

        assert parsed['raw'] == 'Some summary'
        assert parsed['summary'] == 'Some summary'
        assert parsed['details'] is None
        assert parsed['returns'] is None
        assert parsed['raises'] == {}
        assert parsed['params'] == []

    def test_multi_line(self):
        def func():
            """
            Some summary
            Some details
            """
            pass

        parsed = parse_docstring(func)

        assert parsed['raw'] == 'Some summary\nSome details'
        assert parsed['summary'] == 'Some summary'
        assert parsed['details'] == 'Some details'
        assert parsed['returns'] is None
        assert parsed['raises'] == {}
        assert parsed['params'] == []

    def test_multi_line_and_dot(self):
        def func():
            """
            Some summary. bla bla
            Some details
            """
            pass

        parsed = parse_docstring(func)

        assert parsed['raw'] == 'Some summary. bla bla\nSome details'
        assert parsed['summary'] == 'Some summary'
        assert parsed['details'] == 'bla bla\nSome details'
        assert parsed['returns'] is None
        assert parsed['raises'] == {}
        assert parsed['params'] == []

    def test_raises(self):
        def func():
            """
            Some summary.
            :raises SomeException: in case of something
            """
            pass

        parsed = parse_docstring(func)

        assert parsed['raw'] == 'Some summary.\n:raises SomeException: in case of something'
        assert parsed['summary'] == 'Some summary'
        assert parsed['details'] is None
        assert parsed['returns'] is None
        assert parsed['params'] == []
        assert parsed['raises'] == {
            'SomeException': 'in case of something'
        }
