
from application import log
from application.notification import IObserver, NotificationCenter
from application.python import Null
from sipsimple.threading import run_in_twisted_thread
from twisted.internet import reactor
from zope.interface import implements

from op2d.hal.backend import IBackend

__all__ = ['Backend']

# Example and testing backend.
# It accepts calls after waiting 5 seconds and terminated them after 30 seconds.
# Output is logged to syslog / stdout


class NullBackend(object):
    implements(IBackend, IObserver)

    def __init__(self):
        self.current_session = None
        self.incoming_request = None

    def initialize(self):
        log.msg('Null HAL backend initialized')

    def start(self):
        log.msg('Null HAL backend started')
        notification_center = NotificationCenter()
        notification_center.add_observer(self, name='IncomingRequestReceived')
        notification_center.add_observer(self, name='IncomingRequestAccepted')
        notification_center.add_observer(self, name='IncomingRequestRejected')
        notification_center.add_observer(self, name='IncomingRequestCancelled')
        notification_center.add_observer(self, name='SessionItemNewIncoming')
        notification_center.add_observer(self, name='SessionItemNewOutgoing')
        notification_center.add_observer(self, name='SessionItemDidChange')
        notification_center.add_observer(self, name='SessionItemDidEnd')

    def stop(self):
        log.msg('Null HAL backend stopped')
        notification_center = NotificationCenter()
        notification_center.remove_observer(self, name='IncomingRequestReceived')
        notification_center.remove_observer(self, name='IncomingRequestAccepted')
        notification_center.remove_observer(self, name='IncomingRequestRejected')
        notification_center.remove_observer(self, name='IncomingRequestCancelled')
        notification_center.remove_observer(self, name='SessionItemNewIncoming')
        notification_center.remove_observer(self, name='SessionItemNewOutgoing')
        notification_center.remove_observer(self, name='SessionItemDidChange')
        notification_center.remove_observer(self, name='SessionItemDidEnd')

    def _accept_incoming_request(self):
        if self.incoming_request is not None:
            self.incoming_request.accept()

    def _end_current_session(self):
        if self.current_session is not None:
            self.current_session.end()

    @run_in_twisted_thread
    def handle_notification(self, notification):
        handler = getattr(self, '_NH_%s' % notification.name, Null)
        handler(notification)

    def _NH_IncomingRequestReceived(self, notification):
        request = notification.sender
        if not request.new_session:
            request.reject()
            return
        if self.current_session is not None:
            request.busy()
            return
        if self.incoming_request is not None:
            request.busy()
            return
        log.msg('Received incoming request from %s' % request.session.remote_identity)
        self.incoming_request = request
        reactor.callLater(5, self._accept_incoming_request)

    def _NH_IncomingRequestAccepted(self, notification):
        log.msg('Incoming request accepted')
        self.incoming_request = None

    def _NH_IncomingRequestRejected(self, notification):
        request = notification.sender
        if request is not self.incoming_request:
            return
        log.msg('Incoming request rejected')
        self.incoming_request = None
        reactor.callLater(30, self._end_current_session)

    def _NH_IncomingRequestCancelled(self, notification):
        request = notification.sender
        if request is not self.incoming_request:
            return
        log.msg('Incoming request cancelled')
        self.incoming_request = None

    def _NH_SessionItemNewIncoming(self, notification):
        assert self.current_session is None
        session = notification.sender
        log.msg('Incoming session from %s' % session.session.remote_identity)
        self.current_session = session

    def _NH_SessionItemNewOutgoing(self, notification):
        session = notification.sender
        if self.current_session is not None:
            reactor.callLater(0, session.end)
            self.current_session.active = True
            return
        log.msg('Outgoing session to %s' % session.uri)
        self.current_session = session
        reactor.callLater(30, self._end_current_session)

    def _NH_SessionItemDidChange(self, notification):
        if notification.sender is not self.current_session:
            return
        session = notification.sender
        name = session.name or session.uri.user
        log.msg('%s' % (session.status or name))
        log.msg('%s' % session.duration)

    def _NH_SessionItemDidEnd(self, notification):
        if notification.sender is self.current_session:
            log.msg('Session ended')
            self.current_session = None


def Backend():
    return NullBackend()

