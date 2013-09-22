
from application import log
from application.notification import IObserver, NotificationCenter
from application.python import Null
from application.python.types import Singleton
from importlib import import_module
from zope.interface import implements

from op2d.configuration import Configuration

__all__ = ['HardwareAbstractionLayer']


class HardwareAbstractionLayer(object):
    __metaclass__ = Singleton
    implements(IObserver)

    def __init__(self):
        self.backend = self._load_backend()
        self.backend.initialize()

    def _load_backend(self):
        backend_name = Configuration.hal_backend
        if backend_name:
            if '.' not in backend_name:
                backend_name = 'op2d.hal.backend.' + backend_name
            try:
                backend = import_module(backend_name)
                return backend.Backend()
            except Exception, e:
                log.error('Failed to load HAL backend: %s' % e)
        return Null

    def start(self):
        self.backend.start()
        notification_center = NotificationCenter()
        if self.backend is not Null:
            notification_center.add_observer(self, sender=self.backend)

    def stop(self):
        self.backend.stop()
        notification_center = NotificationCenter()
        if self.backend is not Null:
            notification_center.remove_observer(self, sender=self.backend)

    def handle_notification(self, notification):
        handler = getattr(self, '_NH_%s' % notification.name, Null)
        handler(notification)

