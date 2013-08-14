
from application import log
from application.python.types import Singleton
from twisted.internet import reactor

from op2d.configuration import Configuration
from op2d.web.site import get_site


class WebHandler(object):
    __metaclass__ = Singleton

    def start(self):
        self._listener = reactor.listenTCP(Configuration.web_port, get_site())
        log.msg('Web services listening on: %s' % self._listener.getHost())

    def stop(self):
        self._listener.stopListening()

    @property
    def api_url(self):
        pass

    @property
    def configuration_url(self):
        pass

    @property
    def event_url(self):
        pass

