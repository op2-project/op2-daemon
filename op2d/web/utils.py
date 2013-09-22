
from application.python import Null
from twisted.web.resource import Resource
from twisted.web.server import Site

__all__ = ['MySite', 'WSGIRootResource']


class MySite(Site):

    def __init__(self, resource):
        Site.__init__(self, resource, logPath='.')

    def _openLogFile(self, path):
        # We pass a fake path in __init__ so that this function will be called
        # and we can override the default logging with Null.
        # TODO: replace this with a facility to log to a file.
        return Null


# Copied from AutoBahn Python

class WSGIRootResource(Resource):
    """
    Root resource when you want a WSGI resource be the default serving
    resource for a Twisted Web site, but have subpaths served by
    different resources.

    This is a hack needed since
    `twisted.web.wsgi.WSGIResource <http://twistedmatrix.com/documents/current/api/twisted.web.wsgi.WSGIResource.html>`_.
    does not provide a `putChild()` method.

    See also:
       * `Autobahn Twisted Web WSGI example <https://github.com/tavendo/AutobahnPython/tree/master/examples/websocket/echo_wsgi>`_
       * `Original hack <http://blog.vrplumber.com/index.php?/archives/2426-Making-your-Twisted-resources-a-url-sub-tree-of-your-WSGI-resource....html>`_
    """

    def __init__(self, wsgiResource, children):
        """
        Creates a Twisted Web root resource.

        :param wsgiResource:
        :type wsgiResource: Instance of `twisted.web.wsgi.WSGIResource <http://twistedmatrix.com/documents/current/api/twisted.web.wsgi.WSGIResource.html>`_.
        :param children: A dictionary with string keys constituting URL subpaths, and Twisted Web resources as values.
        :type children: dict
        """
        Resource.__init__(self)
        self._wsgiResource = wsgiResource
        self.children = children

    def getChild(self, path, request):
        request.prepath.pop()
        request.postpath.insert(0, path)
        return self._wsgiResource

