
import os
import sys

from collections import deque
from datetime import datetime
from pprint import pformat

from application import log
from application.notification import IObserver, NotificationCenter, ObserverWeakrefProxy
from application.python.queue import EventQueue
from application.python import Null
from application.python.types import Singleton
from application.system import makedirs
from sipsimple.configuration.settings import SIPSimpleSettings
from zope.interface import implements

from op2d.resources import ApplicationData

__all__ = ['TraceManager']


class NotificationQueue(object):
    implements(IObserver)

    def __init__(self):
        self.notifications = deque()
        NotificationCenter().add_observer(ObserverWeakrefProxy(self))

    def handle_notification(self, notification):
        self.notifications.append(notification)


class LogFile(object):
    def __init__(self, filename):
        self.filename = filename

    def _get_filename(self):
        return self.__dict__['filename']

    def _set_filename(self, filename):
        if filename == self.__dict__.get('filename'):
            return
        old_file = self.__dict__.pop('file', Null)
        old_file.close()
        self.__dict__['filename'] = filename

    filename = property(_get_filename, _set_filename)
    del _get_filename, _set_filename

    @property
    def file(self):
        if 'file' not in self.__dict__:
            directory = os.path.dirname(self.filename)
            makedirs(directory)
            self.__dict__['file'] = open(self.filename, 'a')
        return self.__dict__['file']

    def write(self, string):
        self.file.write(string)
        self.file.flush()

    def truncate(self):
        self.file.truncate(0)

    def close(self):
        file = self.__dict__.get('file', Null)
        file.close()


class TraceManager(object):
    __metaclass__ = Singleton

    implements(IObserver)

    def __init__(self):
        self.name = os.path.basename(sys.argv[0]).rsplit('.py', 1)[0]
        self.pid = os.getpid()
        self.msrp_level = log.level.INFO
        self.siptrace_file = Null
        self.msrptrace_file = Null
        self.pjsiptrace_file = Null
        self.notifications_file = Null
        self.event_queue = Null
        self.notification_queue = NotificationQueue()
        self._siptrace_start_time = None
        self._siptrace_packet_count = None

    def start(self):
        settings = SIPSimpleSettings()
        notification_center = NotificationCenter()
        notification_center.add_observer(self)
        self.siptrace_file = LogFile(os.path.join(ApplicationData.directory, 'logs', 'sip.log'))
        self.msrptrace_file = LogFile(os.path.join(ApplicationData.directory, 'logs', 'msrp.log'))
        self.pjsiptrace_file = LogFile(os.path.join(ApplicationData.directory, 'logs', 'pjsip.log'))
        self.notifications_file = LogFile(os.path.join(ApplicationData.directory, 'logs', 'notifications.log'))
        self._siptrace_start_time = datetime.now()
        self._siptrace_packet_count = 0
        self.event_queue = EventQueue(handler=self._process_notification, name='Log handling')
        self.event_queue.start()
        while settings.logs.trace_notifications and self.notification_queue and self.notification_queue.notifications:
            notification = self.notification_queue.notifications.popleft()
            self.handle_notification(notification)
        self.notification_queue = None

    def stop(self):
        notification_center = NotificationCenter()
        notification_center.remove_observer(self)

        self.event_queue.stop()
        self.event_queue.join()
        self.event_queue = Null

        self.siptrace_file = Null
        self.msrptrace_file = Null
        self.pjsiptrace_file = Null
        self.notifications_file = Null

    def handle_notification(self, notification):
        self.event_queue.put(notification)

    def _process_notification(self, notification):
        handler = getattr(self, '_NH_%s' % notification.name, Null)
        handler(notification)

        handler = getattr(self, '_LH_%s' % notification.name, Null)
        handler(notification)

        settings = SIPSimpleSettings()
        if notification.name not in ('SIPEngineLog', 'SIPEngineSIPTrace') and settings.logs.trace_notifications:
            message = 'Notification name=%s sender=%s data=%s' % (notification.name, notification.sender, pformat(notification.data))
            try:
                self.notifications_file.write('%s [%s %d]: %s\n' % (datetime.now(), self.name, self.pid, message))
            except Exception:
                pass

    def _LH_SIPEngineSIPTrace(self, notification):
        settings = SIPSimpleSettings()
        if not settings.logs.trace_sip:
            return
        self._siptrace_packet_count += 1
        if notification.data.received:
            direction = "RECEIVED"
        else:
            direction = "SENDING"
        buf = ["%s: Packet %d, +%s" % (direction, self._siptrace_packet_count, (notification.datetime - self._siptrace_start_time))]
        buf.append("%(source_ip)s:%(source_port)d -(SIP over %(transport)s)-> %(destination_ip)s:%(destination_port)d" % notification.data.__dict__)
        buf.append(notification.data.data)
        buf.append('--')
        message = '\n'.join(buf)
        try:
            self.siptrace_file.write('%s [%s %d]: %s\n' % (notification.datetime, self.name, self.pid, message))
        except Exception:
            pass

    def _LH_SIPEngineLog(self, notification):
        settings = SIPSimpleSettings()
        if not settings.logs.trace_pjsip:
            return
        message = "(%(level)d) %(message)s" % notification.data.__dict__
        try:
            self.pjsiptrace_file.write('[%s %d] %s\n' % (self.name, self.pid, message))
        except Exception:
            pass

    def _LH_DNSLookupTrace(self, notification):
        settings = SIPSimpleSettings()
        if not settings.logs.trace_sip:
            return
        message = 'DNS lookup %(query_type)s %(query_name)s' % notification.data.__dict__
        if notification.data.error is None:
            message += ' succeeded, ttl=%d: ' % notification.data.answer.ttl
            if notification.data.query_type == 'A':
                message += ", ".join(record.address for record in notification.data.answer)
            elif notification.data.query_type == 'SRV':
                message += ", ".join('%d %d %d %s' % (record.priority, record.weight, record.port, record.target) for record in notification.data.answer)
            elif notification.data.query_type == 'NAPTR':
                message += ", ".join('%d %d "%s" "%s" "%s" %s' % (record.order, record.preference, record.flags, record.service, record.regexp, record.replacement) for record in notification.data.answer)
        else:
            import dns.resolver
            message_map = {dns.resolver.NXDOMAIN: 'DNS record does not exist',
                           dns.resolver.NoAnswer: 'DNS response contains no answer',
                           dns.resolver.NoNameservers: 'no DNS name servers could be reached',
                           dns.resolver.Timeout: 'no DNS response received, the query has timed out'}
            message += ' failed: %s' % message_map.get(notification.data.error.__class__, '')
        try:
            self.siptrace_file.write('%s [%s %d]: %s\n' % (notification.datetime, self.name, self.pid, message))
        except Exception:
            pass

    def _LH_MSRPTransportTrace(self, notification):
        settings = SIPSimpleSettings()
        if not settings.logs.trace_msrp:
            return
        arrow = {'incoming': '<--', 'outgoing': '-->'}[notification.data.direction]
        local_address = notification.data.local_address
        local_address = '%s:%d' % (local_address.host, local_address.port)
        remote_address = notification.data.remote_address
        remote_address = '%s:%d' % (remote_address.host, remote_address.port)
        message = '%s %s %s\n' % (local_address, arrow, remote_address) + notification.data.data
        try:
            self.msrptrace_file.write('%s [%s %d]: %s\n' % (notification.datetime, self.name, self.pid, message))
        except Exception:
            pass

    def _LH_MSRPLibraryLog(self, notification):
        settings = SIPSimpleSettings()
        if not settings.logs.trace_msrp:
            return
        if notification.data.level < self.msrp_level:
            return
        message = '%s%s' % (notification.data.level.prefix, notification.data.message)
        try:
            self.msrptrace_file.write('%s [%s %d]: %s\n' % (notification.datetime, self.name, self.pid, message))
        except Exception:
            pass

