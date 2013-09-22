
from twisted.web.resource import Resource

__all__ = ['WSGIRootResource']


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

