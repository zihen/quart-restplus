# -*- coding: utf-8 -*-
import decimal
import pytest

from io import BytesIO
from quart.exceptions import BadRequest
from quart.datastructures import FileStorage, MultiDict

from quart_restplus import Api, Model, fields, inputs
from quart_restplus.errors import SpecsError
from quart_restplus.reqparse import Argument, RequestParser, ParseResult

JSON_HEADERS = {
    'Content-Type': 'application/json'
}


class TestRequestParser:
    def test_api_shortcut(self, app):
        api = Api(app)
        parser = api.parser()
        assert isinstance(parser, RequestParser)

    async def test_parse_model(self, app):
        model = Model('Todo', {
            'task': fields.String(required=True)
        })

        parser = RequestParser()
        parser.add_argument('todo', type=model, required=True)

        data = {'todo': {'task': 'aaa'}}

        async with app.test_request_context(
            method='POST',
            data=data,
            headers=JSON_HEADERS
        ):
            args = await parser.parse_args()
            assert args['todo'] == {'task': 'aaa'}

    async def test_help(self, app, mocker):
        abort = mocker.patch('quart_restplus.reqparse.abort',
                             side_effect=BadRequest())
        parser = RequestParser()
        parser.add_argument('foo', choices=('one', 'two'), help='Bad choice.')
        req = mocker.Mock(['values'])
        req.values = MultiDict([('foo', 'three')])
        async with app.test_request_context():
            with pytest.raises(BadRequest):
                await parser.parse_args(req)
        expected = {'foo': 'Bad choice. The value \'three\' is not a valid choice for \'foo\'.'}
        abort.assert_called_with(400, 'Input payload validation failed', errors=expected)

    async def test_no_help(self, app, mocker):
        abort = mocker.patch('quart_restplus.reqparse.abort',
                             side_effect=BadRequest())
        parser = RequestParser()
        parser.add_argument('foo', choices=['one', 'two'])
        req = mocker.Mock(['values'])
        req.values = MultiDict([('foo', 'three')])
        async with app.test_request_context():
            with pytest.raises(BadRequest):
                await parser.parse_args(req)
        expected = {'foo': 'The value \'three\' is not a valid choice for \'foo\'.'}
        abort.assert_called_with(400, 'Input payload validation failed', errors=expected)

    async def test_viewargs(self, app, mocker):
        async with app.test_request_context() as ctx:
            req = ctx.request
            req.view_args = {'foo': 'bar'}
            parser = RequestParser()
            parser.add_argument('foo', location=['view_args'])
            args = await parser.parse_args(req)
            assert args['foo'] == 'bar'

            req = mocker.Mock()
            req.values = ()
            req.json = None
            req.view_args = {'foo': 'bar'}
            parser = RequestParser()
            parser.add_argument('foo', store_missing=True)
            args = await parser.parse_args(req)
            assert args['foo'] is None

    async def test_parse_unicode(self, app):
        async with app.test_request_context('/bubble?foo=barß') as ctx:
            parser = RequestParser()
            parser.add_argument('foo')

            args = await parser.parse_args(ctx.request)
            assert args['foo'] == 'barß'

    async def test_parse_unicode_app(self, app):
        parser = RequestParser()
        parser.add_argument('foo')

        async with app.test_request_context('/bubble?foo=barß'):
            args = await parser.parse_args()
            assert args['foo'] == 'barß'

    async def test_json_location(self, app):
        async with app.test_request_context('/bubble', method='POST'):
            parser = RequestParser()
            parser.add_argument('foo', location='json', store_missing=True)

            args = await parser.parse_args()
            assert args['foo'] is None

    async def test_get_json_location(self, app):
        async with app.test_request_context(
            '/bubble', method='post',
            data={'foo': 'bar'},
            headers={'Content-Type': 'application/json'}
        ):
            parser = RequestParser()
            parser.add_argument('foo', location='json')
            args = await parser.parse_args()
            assert args['foo'] == 'bar'

    async def test_parse_append_ignore(self, app):
        async with app.test_request_context('/bubble?foo=bar'):
            parser = RequestParser()
            parser.add_argument('foo', ignore=True, type=int, action='append',
                                store_missing=True),

            args = await parser.parse_args()
            assert args['foo'] is None

    async def test_parse_append_default(self, app):
        async with app.test_request_context('/bubble?'):
            parser = RequestParser()
            parser.add_argument('foo', action='append', store_missing=True),

            args = await parser.parse_args()
            assert args['foo'] is None

    async def test_parse_append(self, app):
        async with app.test_request_context('/bubble?foo=bar&foo=bat'):
            parser = RequestParser()
            parser.add_argument('foo', action='append'),

            args = await parser.parse_args()
            assert args['foo'] == ['bar', 'bat']

    async def test_parse_append_single(self, app):
        async with app.test_request_context('/bubble?foo=bar'):
            parser = RequestParser()
            parser.add_argument('foo', action='append'),

            args = await parser.parse_args()
            assert args['foo'] == ['bar']

    async def test_split_single(self, app):
        async with app.test_request_context('/bubble?foo=bar'):
            parser = RequestParser()
            parser.add_argument('foo', action='split'),

            args = await parser.parse_args()
            assert args['foo'] == ['bar']

    async def test_split_multiple(self, app):
        async with app.test_request_context('/bubble?foo=bar,bat'):
            parser = RequestParser()
            parser.add_argument('foo', action='split'),

            args = await parser.parse_args()
            assert args['foo'] == ['bar', 'bat']

    async def test_split_multiple_cast(self, app):
        async with app.test_request_context('/bubble?foo=1,2,3'):
            parser = RequestParser()
            parser.add_argument('foo', type=int, action='split')

            args = await parser.parse_args()
            assert args['foo'] == [1, 2, 3]

    async def test_parse_dest(self, app):
        async with app.test_request_context('/bubble?foo=bar'):
            parser = RequestParser()
            parser.add_argument('foo', dest='bat')

            args = await parser.parse_args()
            assert args['bat'] == 'bar'

    async def test_parse_gte_lte_eq(self, app):
        async with app.test_request_context('/bubble?foo>=bar&foo<=bat&foo=foo'):
            parser = RequestParser()
            parser.add_argument('foo', operators=['>=', '<=', '='], action='append'),

            args = await parser.parse_args()
            assert args['foo'] == ['bar', 'bat', 'foo']

    async def test_parse_gte(self, app):
        async with app.test_request_context('/bubble?foo>=bar'):
            parser = RequestParser()
            parser.add_argument('foo', operators=['>='])

            args = await parser.parse_args()
            assert args['foo'] == 'bar'

    async def test_parse_foo_operators_four_hunderd(self, app):
        async with app.test_request_context('/bubble?foo=bar'):
            parser = RequestParser()
            parser.add_argument('foo', type=int),
            with pytest.raises(BadRequest):
                await parser.parse_args()

    async def test_parse_foo_operators_ignore(self, app):
        async with app.test_request_context('/bubble'):
            parser = RequestParser()
            parser.add_argument('foo', ignore=True, store_missing=True)

            args = await parser.parse_args()
            assert args['foo'] is None

    async def test_parse_lte_gte_mock(self, app, mocker):
        async with app.test_request_context('/bubble?foo<=bar'):
            mock_type = mocker.Mock()

            parser = RequestParser()
            parser.add_argument('foo', type=mock_type, operators=['<='])

            await parser.parse_args()
            mock_type.assert_called_with('bar', 'foo', '<=')

    async def test_parse_lte_gte_append(self, app):
        async with app.test_request_context('/bubble?foo<=bar'):
            parser = RequestParser()
            parser.add_argument('foo', operators=['<=', '='], action='append')

            args = await parser.parse_args()
            assert args['foo'] == ['bar']

    async def test_parse_lte_gte_missing(self, app):
        async with app.test_request_context('/bubble?foo<=bar'):
            parser = RequestParser()
            parser.add_argument('foo', operators=['<=', '='])
            args = await parser.parse_args()
            assert args['foo'] == 'bar'

    async def test_parse_eq_other(self, app):
        async with app.test_request_context('/bubble?foo=bar&foo=bat'):
            parser = RequestParser()
            parser.add_argument('foo'),
            args = await parser.parse_args()
            assert args['foo'] == 'bar'

    async def test_parse_eq(self, app):
        async with app.test_request_context('/bubble?foo=bar'):
            parser = RequestParser()
            parser.add_argument('foo'),
            args = await parser.parse_args()
            assert args['foo'] == 'bar'

    async def test_parse_lte(self, app):
        async with app.test_request_context('/bubble?foo<=bar'):
            parser = RequestParser()
            parser.add_argument('foo', operators=['<='])

            args = await parser.parse_args()
            assert args['foo'] == 'bar'

    async def test_parse_required(self, app):
        async with app.test_request_context('/bubble'):
            parser = RequestParser()
            parser.add_argument('foo', required=True, location='values')

            expected = {
                'foo': 'Missing required parameter in the post body or the query string'
            }
            with pytest.raises(BadRequest) as cm:
                await parser.parse_args()

            assert cm.value.data['message'] == 'Input payload validation failed'
            assert cm.value.data['errors'] == expected

            parser = RequestParser()
            parser.add_argument('bar', required=True, location=['values', 'cookies'])

            expected = {
                'bar': ("Missing required parameter in the post body or the query "
                        "string or the request's cookies")
            }

            with pytest.raises(BadRequest) as cm:
                await parser.parse_args()
            assert cm.value.data['message'] == 'Input payload validation failed'
            assert cm.value.data['errors'] == expected

    @pytest.mark.config(bundle_errors=True)
    async def test_parse_error_bundling(self, app):
        async with app.test_request_context('/bubble'):
            parser = RequestParser()
            parser.add_argument('foo', required=True, location='values')
            parser.add_argument('bar', required=True, location=['values', 'cookies'])

            with pytest.raises(BadRequest) as cm:
                await parser.parse_args()

            assert cm.value.data['message'] == 'Input payload validation failed'
            assert cm.value.data['errors'] == {
                'foo': 'Missing required parameter in the post body or the query string',
                'bar': ("Missing required parameter in the post body or the query string "
                        "or the request's cookies")
            }

    @pytest.mark.config(bundle_errors=False)
    async def test_parse_error_bundling_w_parser_arg(self, app):
        async with app.test_request_context('/bubble'):
            parser = RequestParser(bundle_errors=True)
            parser.add_argument('foo', required=True, location='values')
            parser.add_argument('bar', required=True, location=['values', 'cookies'])

            with pytest.raises(BadRequest) as cm:
                await parser.parse_args()

            assert cm.value.data['message'] == 'Input payload validation failed'
            assert cm.value.data['errors'] == {
                'foo': 'Missing required parameter in the post body or the query string',
                'bar': ("Missing required parameter in the post body or the query string "
                        "or the request's cookies")
            }

    async def test_parse_default_append(self, app):
        async with app.test_request_context('/bubble'):
            parser = RequestParser()
            parser.add_argument('foo', default='bar', action='append',
                                store_missing=True)

            args = await parser.parse_args()

            assert args['foo'] == 'bar'

    async def test_parse_default(self, app):
        async with app.test_request_context('/bubble'):
            parser = RequestParser()
            parser.add_argument('foo', default='bar', store_missing=True)

            args = await parser.parse_args()
            assert args['foo'] == 'bar'

    async def test_parse_callable_default(self, app):
        async with app.test_request_context('/bubble'):
            parser = RequestParser()
            parser.add_argument('foo', default=lambda: 'bar', store_missing=True)

            args = await parser.parse_args()
            assert args['foo'] == 'bar'

    async def test_parse(self, app):
        async with app.test_request_context('/bubble?foo=bar'):
            parser = RequestParser()
            parser.add_argument('foo'),

            args = await parser.parse_args()
            assert args['foo'] == 'bar'

    async def test_parse_none(self, app):
        async with app.test_request_context('/bubble'):
            parser = RequestParser()
            parser.add_argument('foo')

            args = await parser.parse_args()
            assert args['foo'] is None

    async def test_parse_store_missing(self, app):
        async with app.test_request_context('/bubble') as ctx:
            req = ctx.request
            parser = RequestParser()
            parser.add_argument('foo', store_missing=False)

            args = await parser.parse_args(req)
            assert 'foo' not in args

    async def test_parse_choices_correct(self, app):
        async with app.test_request_context('/bubble?foo=bat') as ctx:
            req = ctx.request
            parser = RequestParser()
            parser.add_argument('foo', choices=['bat']),

            args = await parser.parse_args(req)
            assert args['foo'] == 'bat'

    async def test_parse_choices(self, app):
        async with app.test_request_context('/bubble?foo=bar') as ctx:
            req = ctx.request

            parser = RequestParser()
            parser.add_argument('foo', choices=['bat']),

            with pytest.raises(BadRequest):
                await parser.parse_args(req)

    async def test_parse_choices_sensitive(self, app):
        async with app.test_request_context('/bubble?foo=BAT') as ctx:
            req = ctx.request

            parser = RequestParser()
            parser.add_argument('foo', choices=['bat'], case_sensitive=True),

            with pytest.raises(BadRequest):
                await parser.parse_args(req)

    async def test_parse_choices_insensitive(self, app):
        async with app.test_request_context('/bubble?foo=BAT') as ctx:
            req = ctx.request

            parser = RequestParser()
            parser.add_argument('foo', choices=['bat'], case_sensitive=False),

            args = await parser.parse_args(req)
            assert 'bat' == args.get('foo')

        # both choices and args are case_insensitive
        async with app.test_request_context('/bubble?foo=bat') as ctx:
            req = ctx.request

            parser = RequestParser()
            parser.add_argument('foo', choices=['BAT'], case_sensitive=False),

            args = await parser.parse_args(req)
            assert 'bat' == args.get('foo')

    async def test_parse_ignore(self, app):
        async with app.test_request_context('/bubble?foo=bar') as ctx:
            req = ctx.request

            parser = RequestParser()
            parser.add_argument('foo', type=int, ignore=True, store_missing=True),

            args = await parser.parse_args(req)
            assert args['foo'] is None

    def test_chaining(self):
        parser = RequestParser()
        assert parser is parser.add_argument('foo')

    def test_result_existence(self):
        result = ParseResult()
        result.foo = 'bar'
        result['bar'] = 'baz'
        assert result['foo'] == 'bar'
        assert result.bar == 'baz'

    def test_result_missing(self):
        result = ParseResult()
        pytest.raises(AttributeError, lambda: result.spam)
        pytest.raises(KeyError, lambda: result['eggs'])

    async def test_result_configurability(self, app):
        async with app.test_request_context() as ctx:
            req = ctx.request
            assert isinstance(await RequestParser().parse_args(req), ParseResult)
            assert type(await RequestParser(result_class=dict).parse_args(req)) is dict

    async def test_none_argument(self, app):
        parser = RequestParser()
        parser.add_argument('foo', location='json')
        async with app.test_request_context('/bubble', method='post',
                                            data={'foo': None},
                                            headers=JSON_HEADERS):
            args = await parser.parse_args()
        assert args['foo'] is None

    async def test_type_callable(self, app):
        async with app.test_request_context('/bubble?foo=1') as ctx:
            req = ctx.request

            parser = RequestParser()
            parser.add_argument('foo', type=lambda x: x, required=False),

            args = await parser.parse_args(req)
            assert args['foo'] == '1'

    async def test_type_callable_none(self, app):
        parser = RequestParser()
        parser.add_argument('foo', type=lambda x: x, location='json', required=False),

        async with app.test_request_context('/bubble', method='post',
                                            data={'foo': None},
                                            headers=JSON_HEADERS):
            args = await parser.parse_args()
            assert args['foo'] is None

    async def test_type_decimal(self, app):
        parser = RequestParser()
        parser.add_argument('foo', type=decimal.Decimal, location='json')

        async with app.test_request_context('/bubble', method='post',
                                            data={'foo': '1.0025'},
                                            headers=JSON_HEADERS):
            args = await parser.parse_args()
            assert args['foo'] == decimal.Decimal('1.0025')

    async def test_type_filestorage(self, app):
        parser = RequestParser()
        parser.add_argument('foo', type=FileStorage, location='files')

        fdata = 'foo bar baz qux'.encode('utf-8')
        async with app.test_request_context('/bubble', method='POST',
                                            data={'foo': ('baz.txt', BytesIO(fdata))}):
            args = await parser.parse_args()
            assert args['foo'].name == 'foo'
            assert args['foo'].filename == 'baz.txt'
            assert args['foo'].read() == fdata

    async def test_filestorage_custom_type(self, app):
        def _custom_type(f):
            return FileStorage(stream=f.stream,
                               filename='{0}aaaa'.format(f.filename),
                               name='{0}aaaa'.format(f.name))

        parser = RequestParser()
        parser.add_argument('foo', type=_custom_type, location='files')

        fdata = 'foo bar baz qux'.encode('utf-8')
        async with app.test_request_context('/bubble', method='POST',
                                            data={'foo': ('baz.txt', BytesIO(fdata))}):
            args = await parser.parse_args()

            assert args['foo'].name == 'fooaaaa'
            assert args['foo'].filename == 'baz.txtaaaa'
            assert args['foo'].read() == fdata

    async def test_passing_arguments_object(self, app):
        async with app.test_request_context('/bubble?foo=bar') as ctx:
            req = ctx.request
            parser = RequestParser()
            parser.add_argument(Argument('foo'))

            args = await parser.parse_args(req)
            assert args['foo'] == 'bar'

    async def test_int_choice_types(self, app):
        parser = RequestParser()
        parser.add_argument('foo', type=int, choices=[1, 2, 3], location='json')

        async with app.test_request_context('/bubble', method='post',
                                            data={'foo': 5},
                                            headers=JSON_HEADERS):
            with pytest.raises(BadRequest):
                await parser.parse_args()

    async def test_int_range_choice_types(self, app):
        parser = RequestParser()
        parser.add_argument('foo', type=int, choices=range(100), location='json')

        async with app.test_request_context('/bubble', method='post',
                                            data={'foo': 101},
                                            headers=JSON_HEADERS):
            with pytest.raises(BadRequest):
                await parser.parse_args()

    async def test_request_parser_copy(self, app):
        async with app.test_request_context('/bubble?foo=101&bar=baz') as ctx:
            req = ctx.request
            parser = RequestParser()
            foo_arg = Argument('foo', type=int)
            parser.args[foo_arg.name] = foo_arg
            parser_copy = parser.copy()

            # Deepcopy should create a clone of the argument object instead of
            # copying a reference to the new args list
            assert foo_arg not in parser_copy.args.values()

            # Args added to new parser should not be added to the original
            bar_arg = Argument('bar')
            parser_copy.args[bar_arg.name] = bar_arg
            assert bar_arg not in parser.args.values()

            args = await parser_copy.parse_args(req)
            assert args['foo'] == 101
            assert args['bar'] == 'baz'

    async def test_request_parse_copy_including_settings(self):
        parser = RequestParser(trim=True, bundle_errors=True)
        parser_copy = parser.copy()

        assert parser.trim == parser_copy.trim
        assert parser.bundle_errors == parser_copy.bundle_errors

    async def test_request_parser_replace_argument(self, app):
        async with app.test_request_context('/bubble?foo=baz') as ctx:
            req = ctx.request
            parser = RequestParser()
            parser.add_argument('foo', type=int)
            parser_copy = parser.copy()
            parser_copy.replace_argument('foo')

            args = await parser_copy.parse_args(req)
            assert args['foo'] == 'baz'

    async def test_both_json_and_values_location(self, app):
        parser = RequestParser()
        parser.add_argument('foo', type=int)
        parser.add_argument('baz', type=int)
        async with app.test_request_context('/bubble?foo=1', method='post',
                                            data={'baz': 2},
                                            headers=JSON_HEADERS):
            args = await parser.parse_args()
            assert args['foo'] == 1
            assert args['baz'] == 2

    async def test_not_json_location_and_content_type_json(self, app):
        parser = RequestParser()
        parser.add_argument('foo', location='args')

        async with app.test_request_context('/bubble', method='get',
                                            headers=JSON_HEADERS):
            await parser.parse_args()  # Should not raise a 400: BadRequest

    async def test_request_parser_remove_argument(self, app):
        async with app.test_request_context('/bubble?foo=baz') as ctx:
            req = ctx.request
            parser = RequestParser()
            parser.add_argument('foo', type=int)
            parser_copy = parser.copy()
            parser_copy.remove_argument('foo')

            args = await parser_copy.parse_args(req)
            assert args == {}

    async def test_strict_parsing_off(self, app):
        async with app.test_request_context('/bubble?foo=baz') as ctx:
            req = ctx.request
            parser = RequestParser()
            args = await parser.parse_args(req)
            assert args == {}

    async def test_strict_parsing_on(self, app):
        async with app.test_request_context('/bubble?foo=baz') as ctx:
            req = ctx.request
            parser = RequestParser()
            with pytest.raises(BadRequest):
                await parser.parse_args(req, strict=True)

    async def test_strict_parsing_off_partial_hit(self, app):
        async with app.test_request_context('/bubble?foo=1&bar=bees&n=22') as ctx:
            req = ctx.request
            parser = RequestParser()
            parser.add_argument('foo', type=int)
            args = await parser.parse_args(req)
            assert args['foo'] == 1

    async def test_strict_parsing_on_partial_hit(self, app):
        async with app.test_request_context('/bubble?foo=1&bar=bees&n=22') as ctx:
            req = ctx.request
            parser = RequestParser()
            parser.add_argument('foo', type=int)
            with pytest.raises(BadRequest):
                await parser.parse_args(req, strict=True)

    async def test_trim_argument(self, app):
        async with app.test_request_context('/bubble?foo= 1 &bar=bees&n=22') as ctx:
            req = ctx.request
            parser = RequestParser()
            parser.add_argument('foo')
            args = await parser.parse_args(req)
            assert args['foo'] == ' 1 '

            parser = RequestParser()
            parser.add_argument('foo', trim=True)
            args = await parser.parse_args(req)
            assert args['foo'] == '1'

            parser = RequestParser()
            parser.add_argument('foo', trim=True, type=int)
            args = await parser.parse_args(req)
            assert args['foo'] == 1

    async def test_trim_request_parser(self, app):
        async with app.test_request_context('/bubble?foo= 1 &bar=bees&n=22') as ctx:
            req = ctx.request
            parser = RequestParser(trim=False)
            parser.add_argument('foo')
            args = await parser.parse_args(req)
            assert args['foo'] == ' 1 '

            parser = RequestParser(trim=True)
            parser.add_argument('foo')
            args = await parser.parse_args(req)
            assert args['foo'] == '1'

            parser = RequestParser(trim=True)
            parser.add_argument('foo', type=int)
            args = await parser.parse_args(req)
            assert args['foo'] == 1

    def test_trim_request_parser_override_by_argument(self):
        parser = RequestParser(trim=True)
        parser.add_argument('foo', trim=False)

        assert parser.args['foo'].trim is False

    async def test_trim_request_parser_json(self, app):
        parser = RequestParser(trim=True)
        parser.add_argument('foo', location='json')
        parser.add_argument('int1', location='json', type=int)
        parser.add_argument('int2', location='json', type=int)

        async with app.test_request_context('/bubble', method='post',
                                            data={'foo': ' bar ', 'int1': 1, 'int2': ' 2 '},
                                            headers=JSON_HEADERS):
            args = await parser.parse_args()
        assert args['foo'] == 'bar'
        assert args['int1'] == 1
        assert args['int2'] == 2


class TestArgument(object):
    def test_name(self):
        arg = Argument('foo')
        assert arg.name == 'foo'

    def test_dest(self):
        arg = Argument('foo', dest='foobar')
        assert arg.dest == 'foobar'

    def test_location_url(self):
        arg = Argument('foo', location='url')
        assert arg.location == 'url'

    def test_location_url_list(self):
        arg = Argument('foo', location=['url'])
        assert arg.location == ['url']

    def test_location_header(self):
        arg = Argument('foo', location='headers')
        assert arg.location == 'headers'

    def test_location_json(self):
        arg = Argument('foo', location='json')
        assert arg.location == 'json'

    def test_location_get_json(self):
        arg = Argument('foo', location='get_json')
        assert arg.location == 'get_json'

    def test_location_header_list(self):
        arg = Argument('foo', location=['headers'])
        assert arg.location == ['headers']

    def test_type(self):
        arg = Argument('foo', type=int)
        assert arg.type == int

    def test_default(self):
        arg = Argument('foo', default=True)
        assert arg.default is True

    def test_default_help(self):
        arg = Argument('foo')
        assert arg.help is None

    def test_required(self):
        arg = Argument('foo', required=True)
        assert arg.required is True

    def test_ignore(self):
        arg = Argument('foo', ignore=True)
        assert arg.ignore is True

    def test_operator(self):
        arg = Argument('foo', operators=['>=', '<=', '='])
        assert arg.operators == ['>=', '<=', '=']

    def test_action_filter(self):
        arg = Argument('foo', action='filter')
        assert arg.action == 'filter'

    def test_action(self):
        arg = Argument('foo', action='append')
        assert arg.action == 'append'

    def test_choices(self):
        arg = Argument('foo', choices=[1, 2])
        assert arg.choices == [1, 2]

    def test_default_dest(self):
        arg = Argument('foo')
        assert arg.dest is None

    def test_default_operators(self):
        arg = Argument('foo')
        assert arg.operators[0] == '='
        assert len(arg.operators) == 1

    def test_default_default(self):
        arg = Argument('foo')
        assert arg.default is None

    def test_required_default(self):
        arg = Argument('foo')
        assert arg.required is False

    def test_ignore_default(self):
        arg = Argument('foo')
        assert arg.ignore is False

    def test_action_default(self):
        arg = Argument('foo')
        assert arg.action == 'store'

    def test_choices_default(self):
        arg = Argument('foo')
        assert len(arg.choices) == 0

    async def test_source(self, mocker):
        req = mocker.Mock(['args', 'headers', 'values'])
        req.args = {'foo': 'bar'}
        req.headers = {'baz': 'bat'}
        arg = Argument('foo', location=['args'])
        assert (await arg.source(req)) == MultiDict(req.args)

        arg = Argument('foo', location=['headers'])
        assert (await arg.source(req)) == MultiDict(req.headers)

    def test_convert_default_type_with_null_input(self):
        arg = Argument('foo')
        assert arg.convert(None, None) is None

    def test_convert_with_null_input_when_not_nullable(self):
        arg = Argument('foo', nullable=False)
        pytest.raises(ValueError, lambda: arg.convert(None, None))

    async def test_source_bad_location(self, mocker):
        req = mocker.Mock(['values'])
        arg = Argument('foo', location=['foo'])
        assert len(await arg.source(req)) == 0  # yes, basically you don't find it

    async def test_source_default_location(self, mocker):
        req = mocker.Mock(['values'])
        req._get_child_mock = lambda **kwargs: MultiDict()
        arg = Argument('foo')
        assert (await arg.source(req)) == req.values

    def test_option_case_sensitive(self):
        arg = Argument('foo', choices=['bar', 'baz'], case_sensitive=True)
        assert arg.case_sensitive is True

        # Insensitive
        arg = Argument('foo', choices=['bar', 'baz'], case_sensitive=False)
        assert arg.case_sensitive is False

        # Default
        arg = Argument('foo', choices=['bar', 'baz'])
        assert arg.case_sensitive is True


class TestRequestParserSchema(object):
    def test_empty_parser(self):
        parser = RequestParser()
        assert parser.__schema__ == []

    def test_primitive_types(self):
        parser = RequestParser()
        parser.add_argument('int', type=int, help='Some integer')
        parser.add_argument('str', type=str, help='Some string')
        parser.add_argument('float', type=float, help='Some float')

        assert parser.__schema__ == [
            {
                "description": "Some integer",
                "type": "integer",
                "name": "int",
                "in": "query"
            }, {
                "description": "Some string",
                "type": "string",
                "name": "str",
                "in": "query"
            }, {
                "description": "Some float",
                "type": "number",
                "name": "float",
                "in": "query"
            }
        ]

    def test_unknown_type(self):
        parser = RequestParser()
        parser.add_argument('unknown', type=lambda v: v)
        assert parser.__schema__ == [{
            'name': 'unknown',
            'type': 'string',
            'in': 'query',
        }]

    def test_required(self):
        parser = RequestParser()
        parser.add_argument('int', type=int, required=True)
        assert parser.__schema__ == [{
            'name': 'int',
            'type': 'integer',
            'in': 'query',
            'required': True,
        }]

    def test_default(self):
        parser = RequestParser()
        parser.add_argument('int', type=int, default=5)
        assert parser.__schema__ == [{
            'name': 'int',
            'type': 'integer',
            'in': 'query',
            'default': 5,
        }]

    def test_default_as_false(self):
        parser = RequestParser()
        parser.add_argument('bool', type=inputs.boolean, default=False)
        assert parser.__schema__ == [{
            'name': 'bool',
            'type': 'boolean',
            'in': 'query',
            'default': False,
        }]

    def test_choices(self):
        parser = RequestParser()
        parser.add_argument('string', type=str, choices=['a', 'b'])
        assert parser.__schema__ == [{
            'name': 'string',
            'type': 'string',
            'in': 'query',
            'enum': ['a', 'b'],
            'collectionFormat': 'multi',
        }]

    def test_location(self):
        parser = RequestParser()
        parser.add_argument('default', type=int)
        parser.add_argument('in_values', type=int, location='values')
        parser.add_argument('in_query', type=int, location='args')
        parser.add_argument('in_headers', type=int, location='headers')
        parser.add_argument('in_cookie', type=int, location='cookie')
        assert parser.__schema__ == [{
            'name': 'default',
            'type': 'integer',
            'in': 'query',
        }, {
            'name': 'in_values',
            'type': 'integer',
            'in': 'query',
        }, {
            'name': 'in_query',
            'type': 'integer',
            'in': 'query',
        }, {
            'name': 'in_headers',
            'type': 'integer',
            'in': 'header',
        }]

    def test_location_json(self):
        parser = RequestParser()
        parser.add_argument('in_json', type=str, location='json')
        assert parser.__schema__ == [{
            'name': 'in_json',
            'type': 'string',
            'in': 'body',
        }]

    def test_location_form(self):
        parser = RequestParser()
        parser.add_argument('in_form', type=int, location='form')
        assert parser.__schema__ == [{
            'name': 'in_form',
            'type': 'integer',
            'in': 'formData',
        }]

    def test_location_files(self):
        parser = RequestParser()
        parser.add_argument('in_files', type=FileStorage, location='files')
        assert parser.__schema__ == [{
            'name': 'in_files',
            'type': 'file',
            'in': 'formData',
        }]

    def test_form_and_body_location(self):
        parser = RequestParser()
        parser.add_argument('default', type=int)
        parser.add_argument('in_form', type=int, location='form')
        parser.add_argument('in_json', type=str, location='json')
        with pytest.raises(SpecsError) as cm:
            _ = parser.__schema__

        assert cm.value.msg == "Can't use formData and body at the same time"

    def test_files_and_body_location(self):
        parser = RequestParser()
        parser.add_argument('default', type=int)
        parser.add_argument('in_files', type=FileStorage, location='files')
        parser.add_argument('in_json', type=str, location='json')
        with pytest.raises(SpecsError) as cm:
            _ = parser.__schema__

        assert cm.value.msg == "Can't use formData and body at the same time"

    def test_models(self):
        todo_fields = Model('Todo', {
            'task': fields.String(required=True, description='The task details')
        })
        parser = RequestParser()
        parser.add_argument('todo', type=todo_fields)
        assert parser.__schema__ == [{
            'name': 'todo',
            'type': 'Todo',
            'in': 'body',
        }]

    def test_lists(self):
        parser = RequestParser()
        parser.add_argument('int', type=int, action='append')
        assert parser.__schema__ == [{
            'name': 'int',
            'in': 'query',
            'type': 'array',
            'collectionFormat': 'multi',
            'items': {'type': 'integer'}
        }]

    def test_split_lists(self):
        parser = RequestParser()
        parser.add_argument('int', type=int, action='split')
        assert parser.__schema__ == [{
            'name': 'int',
            'in': 'query',
            'type': 'array',
            'collectionFormat': 'csv',
            'items': {'type': 'integer'}
        }]

    def test_schema_interface(self):
        def custom(value):
            pass

        custom.__schema__ = {
            'type': 'string',
            'format': 'custom-format',
        }

        parser = RequestParser()
        parser.add_argument('custom', type=custom)

        assert parser.__schema__ == [{
            'name': 'custom',
            'in': 'query',
            'type': 'string',
            'format': 'custom-format',
        }]

    def test_callable_default(self):
        parser = RequestParser()
        parser.add_argument('int', type=int, default=lambda: 5)
        assert parser.__schema__ == [{
            'name': 'int',
            'type': 'integer',
            'in': 'query',
            'default': 5,
        }]
