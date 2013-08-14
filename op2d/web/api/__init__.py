
from flask import Flask
from werkzeug.wsgi import DispatcherMiddleware

from op2d.web.api import v1

__all__ = ['app']


# Empty app to  use with DispatcherMiddleware
_app = Flask('api')

@_app.route('/')
def index():
    return ''


# Support multiple API versions
app = DispatcherMiddleware(_app, {'/v1': v1.app})

