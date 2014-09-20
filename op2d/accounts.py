
from application.notification import IObserver, NotificationCenter
from application.python import Null
from application.python.types import Singleton
from sipsimple.account import Account, AccountManager
from threading import RLock
from zope.interface import implements


class AccountInfo(object):

    def __init__(self, account):
        self.account = account
        self.registration_state = None
        self.registrar = None


class AccountModel(object):
    __metaclass__ = Singleton
    implements(IObserver)

    def __init__(self):
        self._lock = RLock()
        self._running = False
        self._accounts = {}

    def get_account(self, account_id):
        with self._lock:
            return self._accounts.get(account_id, None)

    def start(self):
        if self._running:
            return
        notification_center = NotificationCenter()
        notification_center.add_observer(self, name='CFGSettingsObjectDidChange')
        notification_center.add_observer(self, name='SIPAccountWillRegister')
        notification_center.add_observer(self, name='SIPAccountRegistrationDidSucceed')
        notification_center.add_observer(self, name='SIPAccountRegistrationDidFail')
        notification_center.add_observer(self, name='SIPAccountRegistrationDidEnd')
        notification_center.add_observer(self, name='BonjourAccountWillRegister')
        notification_center.add_observer(self, name='BonjourAccountRegistrationDidSucceed')
        notification_center.add_observer(self, name='BonjourAccountRegistrationDidFail')
        notification_center.add_observer(self, name='BonjourAccountRegistrationDidEnd')
        notification_center.add_observer(self, sender=AccountManager())
        self._running = True

    def stop(self):
        if not self._running:
            return
        self._running = False
        self._accounts.clear()
        notification_center = NotificationCenter()
        notification_center.remove_observer(self, name='SIPAccountWillRegister')
        notification_center.remove_observer(self, name='SIPAccountRegistrationDidSucceed')
        notification_center.remove_observer(self, name='SIPAccountRegistrationDidFail')
        notification_center.remove_observer(self, name='SIPAccountRegistrationDidEnd')
        notification_center.remove_observer(self, name='BonjourAccountWillRegister')
        notification_center.remove_observer(self, name='BonjourAccountRegistrationDidSucceed')
        notification_center.remove_observer(self, name='BonjourAccountRegistrationDidFail')
        notification_center.remove_observer(self, name='BonjourAccountRegistrationDidEnd')
        notification_center.remove_observer(self, sender=AccountManager())

    def handle_notification(self, notification):
        if not self._running:
            return
        with self._lock:
            handler = getattr(self, '_NH_%s' % notification.name, Null)
            handler(notification)

    def _NH_SIPAccountManagerDidAddAccount(self, notification):
        account = notification.data.account
        self._accounts[account.id] = AccountInfo(account)

    def _NH_SIPAccountManagerDidRemoveAccount(self, notification):
        account = notification.data.account
        del self._accounts[account.id]

    def _NH_SIPAccountWillRegister(self, notification):
        account = notification.sender
        try:
            info = self._accounts[account.id]
        except ValueError:
            return
        info.registration_state = 'started'
        info.registrar = None

    def _NH_SIPAccountRegistrationDidSucceed(self, notification):
        account = notification.sender
        try:
            info = self._accounts[account.id]
        except ValueError:
            return
        info.registration_state = 'succeeded'
        if isinstance(account, Account):
            route = notification.data.registrar
            info.registrar = '%s:%s:%d' % (route.transport, route.address, route.port)
        else:
            info.registrar = '<bonjour>'

    def _NH_SIPAccountRegistrationDidFail(self, notification):
        account = notification.sender
        try:
            info = self._accounts[account.id]
        except ValueError:
            return
        info.registration_state = 'failed'
        info.registrar = None

    def _NH_SIPAccountRegistrationDidEnd(self, notification):
        account = notification.sender
        try:
            info = self._accounts[account.id]
        except ValueError:
            return
        info.registration_state = 'ended'
        info.registrar = None

    _NH_BonjourAccountWillRegister = _NH_SIPAccountWillRegister
    _NH_BonjourAccountRegistrationDidSucceed = _NH_SIPAccountRegistrationDidSucceed
    _NH_BonjourAccountRegistrationDidFail = _NH_SIPAccountRegistrationDidFail
    _NH_BonjourAccountRegistrationDidEnd = _NH_SIPAccountRegistrationDidEnd

