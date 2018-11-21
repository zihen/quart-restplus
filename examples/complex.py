from quart import Quart
from zoo import api

app = Quart(__name__)
api.init_app(app)

app.run(debug=True)
