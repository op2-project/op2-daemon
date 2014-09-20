
from application import log
from application.notification import IObserver, NotificationCenter
from application.python import Null
from application.python.types import Singleton
from sipsimple.account import Account, BonjourAccount
from sipsimple.application import SIPApplication
from sipsimple.configuration.settings import SIPSimpleSettings
from sipsimple.storage import FileStorage
from threading import Event
from zope.interface import implements

from op2d.accounts import AccountModel
from op2d.bonjour import BonjourServices
from op2d.configuration.account import AccountExtension, BonjourAccountExtension
from op2d.configuration.settings import SIPSimpleSettingsExtension
from op2d.hal import HardwareAbstractionLayer
from op2d.resources import ApplicationData
from op2d.sessions import SessionManager
from op2d.web import WebHandler

__all__ = ['OP2Daemon']


class OP2Daemon(object):
    __metaclass__ = Singleton
    implements(IObserver)

    def __init__(self):
        self.application = SIPApplication()
        self.stopping = False
        self.stopping_event = Event()
        self.stop_event = Event()

        Account.register_extension(AccountExtension)
        BonjourAccount.register_extension(BonjourAccountExtension)
        SIPSimpleSettings.register_extension(SIPSimpleSettingsExtension)

        self.account_model = AccountModel()
        self.bonjour_services = BonjourServices()
        self.hal = HardwareAbstractionLayer()
        self.session_manager = SessionManager()
        self.web_handler = WebHandler()

    def start(self):
        self.account_model.start()
        self.bonjour_services.start()
        self.hal.start()
        self.session_manager.start()

        notification_center = NotificationCenter()
        notification_center.add_observer(self, sender=self.application)
        self.application.start(FileStorage(ApplicationData.directory))

    def stop(self):
        if self.stopping:
            return
        self.stopping = True
        self.session_manager.stop()
        self.hal.stop()
        self.bonjour_services.stop()
        self.account_model.stop()
        self.application.stop()

    def handle_notification(self, notification):
        handler = getattr(self, '_NH_%s' % notification.name, Null)
        handler(notification)

    def _NH_SIPApplicationDidStart(self, notification):
        log.msg('SIP application started')
        self.web_handler.start()

    def _NH_SIPApplicationWillEnd(self, notification):
        self.web_handler.stop()
        self.stopping_event.set()

    def _NH_SIPApplicationDidEnd(self, notification):
        log.msg('SIP application ended')
        if not self.stopping_event.is_set():
            log.warning('SIP application ended without stopping all subsystems')
            self.stopping_event.set()
        self.stop_event.set()

