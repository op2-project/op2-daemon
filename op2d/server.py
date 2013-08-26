
from application import log
from application.notification import IObserver, NotificationCenter
from application.python import Null
from application.python.types import Singleton
from sipsimple.application import SIPApplication
from sipsimple.storage import FileStorage
from threading import Event
from zope.interface import implements

from op2d.accounts import AccountModel
from op2d.resources import ApplicationData
from op2d.web import WebHandler

__all__ = ['OP2Daemon']


class OP2Daemon(object):
    __metaclass__ = Singleton
    implements(IObserver)

    def __init__(self):
        self.application = SIPApplication()
        self.stop_event = Event()
        self.account_model = AccountModel()
        self.web_handler = None

    def start(self):
        self.account_model.start()
        notification_center = NotificationCenter()
        notification_center.add_observer(self, sender=self.application)
        self.application.start(FileStorage(ApplicationData.directory))

    def stop(self):
        self.account_model.stop()
        self.application.stop()
        self.application.thread.join()
        self.stop_event.set()

    def handle_notification(self, notification):
        handler = getattr(self, '_NH_%s' % notification.name, Null)
        handler(notification)

    def _NH_SIPApplicationDidStart(self, notification):
        log.msg('SIP application started')
        self.web_handler = WebHandler()
        self.web_handler.start()

    def _NH_SIPApplicationWillEnd(self, notification):
        if self.web_handler is not None:
            self.web_handler.stop()

    def _NH_SIPApplicationDidEnd(self, notification):
        log.msg('SIP application ended')

