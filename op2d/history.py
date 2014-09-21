
import bisect
import cPickle as pickle
import re

from application.notification import IObserver, NotificationCenter
from application.python import Null
from application.python.types import Singleton
from datetime import date, datetime
from sipsimple.account import BonjourAccount
from sipsimple.threading import run_in_thread
from zope.interface import implements

from op2d.resources import ApplicationData

__all__ = ['HistoryManager']


class HistoryManager(object):
    __metaclass__ = Singleton
    implements(IObserver)

    history_size = 20

    def start(self):
        try:
            data = pickle.load(open(ApplicationData.get('calls_history')))
            if not isinstance(data, list) or not all(isinstance(item, HistoryEntry) and item.text for item in data):
                raise ValueError("invalid save data")
        except Exception:
            self.calls = []
        else:
            self.calls = data[-self.history_size:]
        notification_center = NotificationCenter()
        notification_center.add_observer(self, name='SIPSessionDidEnd')
        notification_center.add_observer(self, name='SIPSessionDidFail')

    def stop(self):
        notification_center = NotificationCenter()
        notification_center.remove_observer(self, name='SIPSessionDidEnd')
        notification_center.remove_observer(self, name='SIPSessionDidFail')

    @run_in_thread('file-io')
    def save(self):
        with open(ApplicationData.get('calls_history'), 'wb+') as history_file:
            pickle.dump(self.calls, history_file)

    def handle_notification(self, notification):
        handler = getattr(self, '_NH_%s' % notification.name, Null)
        handler(notification)

    def _NH_SIPSessionDidEnd(self, notification):
        if notification.sender.account is BonjourAccount():
            return
        session = notification.sender
        entry = HistoryEntry.from_session(session)
        bisect.insort(self.calls, entry)
        self.calls = self.calls[-self.history_size:]
        self.save()

    def _NH_SIPSessionDidFail(self, notification):
        if notification.sender.account is BonjourAccount():
            return
        session = notification.sender
        entry = HistoryEntry.from_session(session)
        if session.direction == 'incoming':
            if notification.data.code != 487 or notification.data.failure_reason != 'Call completed elsewhere':
                entry.failed = True
        else:
            if notification.data.code == 0:
                entry.reason = 'Internal Error'
            elif notification.data.code == 487:
                entry.reason = 'Cancelled'
            else:
                entry.reason = notification.data.reason or notification.data.failure_reason
            entry.failed = True
        bisect.insort(self.calls, entry)
        self.calls = self.calls[-self.history_size:]
        self.save()


class HistoryEntry(object):
    phone_number_re = re.compile(r'^(?P<number>(0|00|\+)[1-9]\d{7,14})@')

    def __init__(self, direction, name, uri, account_id, call_time, duration, failed=False, reason=None):
        self.direction = direction
        self.name = name
        self.uri = uri
        self.account_id = account_id
        self.call_time = call_time
        self.duration = duration
        self.failed = failed
        self.reason = reason
        self.text = self._generate_text()

    def __reduce__(self):
        return (self.__class__, (self.direction, self.name, self.uri, self.account_id, self.call_time, self.duration, self.failed, self.reason))

    def __eq__(self, other):
        return self is other

    def __ne__(self, other):
        return self is not other

    def __lt__(self, other):
        return self.call_time < other.call_time

    def __le__(self, other):
        return self.call_time <= other.call_time

    def __gt__(self, other):
        return self.call_time > other.call_time

    def __ge__(self, other):
        return self.call_time >= other.call_time

    def _generate_text(self):
        result = unicode(self.name or self.uri)
        if self.call_time:
            call_date = self.call_time.date()
            today = date.today()
            days = (today - call_date).days
            if call_date == today:
                result += self.call_time.strftime(" at %H:%M")
            elif days == 1:
                result += self.call_time.strftime(" Yesterday at %H:%M")
            elif days < 7:
                result += self.call_time.strftime(" on %A")
            elif call_date.year == today.year:
                result += self.call_time.strftime(" on %B %d")
            else:
                result += self.call_time.strftime(" on %Y-%m-%d")
        if self.duration:
            seconds = int(self.duration.total_seconds())
            if seconds >= 3600:
                result += """ (%dh%02d'%02d")""" % (seconds / 3600, (seconds % 3600) / 60, seconds % 60)
            else:
                result += """ (%d'%02d")""" % (seconds / 60, seconds % 60)
        elif self.reason:
            result += ' (%s)' % self.reason.title()
        return result

    @classmethod
    def from_session(cls, session):
        if session.start_time is None and session.end_time is not None:
            # Session may have anded before it fully started
            session.start_time = session.end_time
        call_time = session.start_time or datetime.now()
        if session.start_time and session.end_time:
            duration = session.end_time - session.start_time
        else:
            duration = None
        remote_uri = '%s@%s' % (session.remote_identity.uri.user, session.remote_identity.uri.host)
        match = cls.phone_number_re.match(remote_uri)
        if match:
            remote_uri = match.group('number')
        display_name = session.remote_identity.display_name
        return cls(session.direction, display_name, remote_uri, unicode(session.account.id), call_time, duration)

