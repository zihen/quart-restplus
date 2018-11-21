# -*- coding: utf-8 -*-
from quart import url_for, Blueprint, render_template
from quart.blueprints import BlueprintSetupState


class Apidoc(Blueprint):
    """
    Allow to know if the blueprint has already been registered
    until https://github.com/mitsuhiko/quart/pull/1301 is merged
    """

    def __init__(self, *args, **kwargs):
        super(Apidoc, self).__init__(*args, **kwargs)

        self.registered = False
        self.static_folder = kwargs.pop('static_folder', 'static')
        self.static_url_path = kwargs.pop('static_url_path', None)

        if self.has_static_folder:
            def add_static_url_rule(state: BlueprintSetupState):
                state.add_url_rule(
                    self.static_url_path + '/<path:filename>',
                    view_func=self.send_static_file, endpoint='static'
                )

            self.deferred_functions.append(add_static_url_rule)

    def register(self, *args, **kwargs):
        super(Apidoc, self).register(*args, **kwargs)
        self.registered = True


apidoc = Apidoc(
    'restplus_doc', __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/swaggerui',
)


@apidoc.add_app_template_global
def swagger_static(filename):
    return url_for('restplus_doc.static', filename=filename)


async def ui_for(api):
    """Render a SwaggerUI for a given API"""
    return await render_template('swagger-ui.html', title=api.title, specs_url=api.specs_url)
