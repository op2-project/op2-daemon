
import os

from twisted.internet import reactor
from twisted.python.threadpool import ThreadPool
from twisted.web.static import File
from twisted.web.wsgi import WSGIResource
from werkzeug.wsgi import DispatcherMiddleware

from op2d.resources import Resources
from op2d.web import api, frontend
from op2d.web.utils import MySite, WSGIRootResource

__all__ = ['get_site']


# create thread pool used to serve WSGI requests
thread_pool = ThreadPool(maxthreads=5)
thread_pool.start()
reactor.addSystemEventTrigger('before', 'shutdown', thread_pool.stop)


def get_site():
    # WSGI application
    application = DispatcherMiddleware(frontend.app, {'/api': api.app})

    # resource for the WSGI application
    app_resource = WSGIResource(reactor, thread_pool, application)

    # resource for static assets
    static_resource = File(Resources.get('frontend/assets'))

    # root resource, aggregating the WSGI app and static assets
    root_resource = WSGIRootResource(app_resource, {'assets': static_resource})

    return MySite(root_resource)

