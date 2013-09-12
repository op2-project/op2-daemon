
from application.notification import IObserver, NotificationCenter
from application.python import Null
from application.python.types import Singleton
from datetime import timedelta
from sipsimple.account import Account, AccountManager
from sipsimple.application import SIPApplication
from sipsimple.audio import WavePlayer
from sipsimple.configuration.settings import SIPSimpleSettings
from sipsimple.core import SIPURI, ToHeader
from sipsimple.lookup import DNSLookup
from sipsimple.session import Session
from threading import RLock
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from zope.interface import implements

from op2d.configuration.datatypes import DefaultPath
from op2d.resources import Resources

__all__ = ['SessionManager']

# TODO
# - Support streams other than audio
# - Add Ability to mute sessions
# - Add ability to record sessions
# - Separate statistics per stream type


class IncomingProposalHandler(object):

    def __init__(self, session, streams, new_session=True):
        self.session = session
        self.streams = streams
        self.new_session = new_session

        self.accepted_streams = None
        self.reject_mode = None

    @property
    def proposed_streams(self):
        return [stream.type for stream in self.streams]

    @property
    def ringtone(self):
        if 'ringtone' not in self.__dict__:
            if set(self.proposed_streams).intersection(['audio', 'video', 'desktop-sharing']):
                sound_file = self.session.account.sounds.inbound_ringtone
                if sound_file is not None and sound_file.path is DefaultPath:
                    settings = SIPSimpleSettings()
                    sound_file = settings.sounds.inbound_ringtone
                ringtone = WavePlayer(SIPApplication.alert_audio_mixer, sound_file.path, volume=sound_file.volume, loop_count=0, pause_time=2.7) if sound_file is not None else Null
                ringtone.bridge = SIPApplication.alert_audio_bridge
            else:
                ringtone = WavePlayer(SIPApplication.alert_audio_mixer, Resources.get('sounds/beeping_ringtone.wav'), volume=70, loop_count=0, pause_time=5)
                ringtone.bridge = SIPApplication.alert_audio_bridge
            self.__dict__['ringtone'] = ringtone
        return self.__dict__['ringtone']

    def accept(self, audio=False, video=False, chat=False, desktopsharing=False, filetransfer=False):
        if self.accepted_streams is not None:
            return
        streams = []
        if audio:
            streams.append(next(stream for stream in streams if stream.type=='audio'))
        if video:
            streams.append(next(stream for stream in streams if stream.type=='video'))
        if chat:
            streams.append(next(stream for stream in streams if stream.type=='chat'))
        if desktopsharing:
            streams.append(next(stream for stream in streams if stream.type=='desktop-sharing'))
        if filetransfer:
            streams.append(next(stream for stream in streams if stream.type=='file-transfer'))
        self.accepted_streams = streams
        notification_center = NotificationCenter()
        notification_center.post_notification('IncomingProposalAccepted', sender=self)

    def reject(self):
        if self.accepted_streams is not None:
            return
        self.reject_mode = 'reject'
        notification_center = NotificationCenter()
        notification_center.post_notification('IncomingProposalRejected', sender=self)

    def busy(self):
        if self.accepted_streams is not None:
            return
        self.reject_mode = 'busy'
        notification_center = NotificationCenter()
        notification_center.post_notification('IncomingProposalRejected', sender=self)


class SessionItem(object):
    implements(IObserver)

    def __init__(self, name, uri, session, streams):
        self.name = name
        self.uri = uri
        self.session = session

        self.timer = LoopingCall(self._timer_fired)
        self.outbound_ringtone = Null
        self.offer_in_progress = False
        self.local_hold = False
        self.remote_hold = False

        self._active = False
        self._codec_info = u''
        self._tls = False
        self._srtp = False
        self._duration = timedelta(0)
        self._latency = 0
        self._packet_loss = 0
        self._status = None

        self._streams = {}
        for stream in streams:
            self._set_stream(stream.type, stream)

        notification_center = NotificationCenter()
        notification_center.add_observer(self, sender=session)

    def _set_stream(self, stream_type, stream):
        notification_center = NotificationCenter()
        old_stream = self._streams.get(stream_type, None)
        self._streams[stream_type] = stream
        if old_stream is not None:
            notification_center.remove_observer(self, sender=old_stream)
            if stream_type == 'audio':
                self.hold_tone = Null
        if stream is not None:
            notification_center.add_observer(self, sender=stream)
            if stream_type == 'audio':
                self.hold_tone = WavePlayer(stream.bridge.mixer, Resources.get('sounds/hold_tone.wav'), loop_count=0, pause_time=45, volume=30)
                stream.bridge.add(self.hold_tone)

    @property
    def audio_stream(self):
        return self._streams.get('audio', None)

    @property
    def video_stream(self):
        return self._streams.get('video', None)

    @property
    def codec_info(self):
        return self._codec_info

    @property
    def tls(self):
        return self._tls

    @property
    def srtp(self):
        return self._srtp

    @property
    def duration(self):
        return self._duration

    @property
    def latency(self):
        return self._latency

    @property
    def packet_loss(self):
        return self._packet_loss

    @property
    def status(self):
        return self._status

    @property
    def pending_removal(self):
        return not bool(self._streams.values())

    def _get_active(self):
        return self._active
    def _set_active(self, value):
        value = bool(value)
        if self._active == value:
            return
        self._active = value
        if self.audio_stream:
            self.audio_stream.device.output_muted = not value
        notification_center = NotificationCenter()
        if value:
            self.unhold()
            notification_center.post_notification('SessionItemDidActivate', sender=self)
        else:
            self.hold()
            notification_center.post_notification('SessionItemDidDeactivate', sender=self)
    active = property(_get_active, _set_active)
    del _get_active, _set_active

    def connect(self):
        self.offer_in_progress = True
        account = self.session.account
        settings = SIPSimpleSettings()
        if isinstance(account, Account):
            if account.sip.outbound_proxy is not None:
                proxy = account.sip.outbound_proxy
                uri = SIPURI(host=proxy.host, port=proxy.port, parameters={'transport': proxy.transport})
            elif account.sip.always_use_my_proxy:
                uri = SIPURI(host=account.id.domain)
            else:
                uri = self.uri
        else:
            uri = self.uri
        self._status = u'Looking up destination'
        lookup = DNSLookup()
        notification_center = NotificationCenter()
        notification_center.add_observer(self, sender=lookup)
        lookup.lookup_sip_proxy(uri, settings.sip.transport_list)

    def hold(self):
        if not self.pending_removal and not self.local_hold:
            self.local_hold = True
            self.session.hold()
            self.hold_tone.start()
            if not self.offer_in_progress:
                self._status = u'On hold'

    def unhold(self):
        if not self.pending_removal and self.local_hold:
            self.local_hold = False
            self.session.unhold()

    def send_dtmf(self, digit):
        if self.audio_stream is not None:
            try:
                self.audio_stream.send_dtmf(digit)
            except RuntimeError:
                pass
            else:
                digit_map = {'*': 'star'}
                filename = 'sounds/dtmf_%s_tone.wav' % digit_map.get(digit, digit)
                player = WavePlayer(SIPApplication.voice_audio_bridge.mixer, Resources.get(filename))
                notification_center = NotificationCenter()
                notification_center.add_observer(self, sender=player)
                if self.session.account.rtp.inband_dtmf:
                    self.audio_stream.bridge.add(player)
                SIPApplication.voice_audio_bridge.add(player)
                player.start()

    def end(self):
        if self.session.state is None:
            del self._streams[:]
            self.status = u'Call canceled'
            self._cleanup()
        else:
            self.session.end()

    def _cleanup(self):
        self.timer.stop()

        notification_center = NotificationCenter()
        notification_center.remove_observer(self, sender=self.session)

        player = WavePlayer(SIPApplication.voice_audio_bridge.mixer, Resources.get('sounds/hangup_tone.wav'), volume=60)
        notification_center.add_observer(self, sender=player)
        SIPApplication.voice_audio_bridge.add(player)
        player.start()

        notification_center.post_notification('SessionItemDidEnd', sender=self)

    def _reset_status(self):
        if self.pending_removal or self.offer_in_progress:
            return
        if self.local_hold:
            self._status = u'On hold'
        elif self.remote_hold:
            self._status = u'Hold by remote'
        else:
            self._status = None

    def _set_codec_info(self):
        codecs = []
        if self.video_stream is not None:
            desc = 'HD Video' if self.video_stream.bit_rate/1024 >= 512 else 'Video'
            codecs.append('[%s] %s %dkbit' % (desc, self.video_stream.codec, self.video_stream.bit_rate/1024))
        if self.audio_stream is not None:
            desc = 'HD Audio' if self.audio_stream.sample_rate/1000 >= 16 else 'Audio'
            codecs.append('[%s] %s %dkHz' % (desc, self.audio_stream.codec, self.audio_stream.sample_rate/1000))
        self._codec_info = ', '.join(codecs)

    def _timer_fired(self):
        if self.audio_stream is not None:
            stats = self.audio_stream.statistics
            if stats is not None:
                self._latency = stats['rtt']['avg'] / 1000
                self._packet_loss = int(stats['rx']['packets_lost']*100.0/stats['rx']['packets']) if stats['rx']['packets'] else 0
        self._duration += timedelta(seconds=1)

    def handle_notification(self, notification):
        handler = getattr(self, '_NH_%s' % notification.name, Null)
        handler(notification)

    def _NH_AudioStreamICENegotiationStateDidChange(self, notification):
        if notification.data.state == 'GATHERING':
            self._status = u'Gathering ICE candidates'
        elif notification.data.state == 'NEGOTIATING':
            self._status = u'Negotiating ICE'
        elif notification.data.state == 'RUNNING':
            self._status = u'Connecting...'
        elif notification.data.state == 'FAILED':
            self._status = u'ICE failed'

    def _NH_AudioStreamGotDTMF(self, notification):
        digit_map = {'*': 'star'}
        filename = 'sounds/dtmf_%s_tone.wav' % digit_map.get(notification.data.digit, notification.data.digit)
        player = WavePlayer(SIPApplication.voice_audio_bridge.mixer, Resources.get(filename))
        notification.center.add_observer(self, sender=player)
        SIPApplication.voice_audio_bridge.add(player)
        player.start()

    def _NH_AudioStreamDidStartRecordingAudio(self, notification):
        self._recording = True

    def _NH_AudioStreamWillStopRecordingAudio(self, notification):
        self._recording = False

    def _NH_DNSLookupDidSucceed(self, notification):
        settings = SIPSimpleSettings()
        notification.center.remove_observer(self, sender=notification.sender)
        if self.pending_removal:
            return
        if self.audio_stream:
            outbound_ringtone = settings.sounds.outbound_ringtone
            print "XXX",outbound_ringtone
            if outbound_ringtone:
                self.outbound_ringtone = WavePlayer(self.audio_stream.mixer, outbound_ringtone.path, outbound_ringtone.volume, loop_count=0, pause_time=5)
                self.audio_stream.bridge.add(self.outbound_ringtone)
        routes = notification.data.result
        self._tls = routes[0].transport=='tls' if routes else False
        self._status = u'Connecting...'
        self.session.connect(ToHeader(self.uri), routes, self._streams.values())

    def _NH_DNSLookupDidFail(self, notification):
        notification.center.remove_observer(self, sender=notification.sender)
        if self.pending_removal:
            return
        del self._streams[:]
        self._status = u'Destination not found'
        self._cleanup()

    def _NH_MediaStreamDidStart(self, notification):
        pass

    def _NH_SIPSessionGotRingIndication(self, notification):
        self._status = u'Ringing...'
        self.outbound_ringtone.start()

    def _NH_SIPSessionWillStart(self, notification):
        self.outbound_ringtone.stop()

    def _NH_SIPSessionDidStart(self, notification):
        if self.audio_stream not in notification.data.streams:
            self._set_stream('audio', None)
        if self.video_stream not in notification.data.streams:
            self._set_stream('video', None)
        if not self.local_hold:
            self.offer_in_progress = False
        if not self.pending_removal:
            self.timer.start(1)
            self._set_codec_info()
            self._status = u'Connected'
            self._srtp = all(stream.srtp_active for stream in (self.audio_stream, self.video_stream) if stream is not None)
            self._tls = self.session.transport == 'tls'
            reactor.callLater(1, self._reset_status)
        else:
            self._status = u'Ending...'
            self._cleanup()

    def _NH_SIPSessionDidFail(self, notification):
        del self._streams[:]
        self.offer_in_progress = False
        if notification.data.failure_reason == 'user request':
            if notification.data.code == 487:
                reason = 'Call canceled'
            else:
                reason = notification.data.reason
        else:
            reason = notification.data.failure_reason
        self._status = reason
        self.outbound_ringtone.stop()
        self._cleanup()

    def _NH_SIPSessionDidEnd(self, notification):
        del self._streams[:]
        self.offer_in_progress = False
        self._status = u'Call ended' if notification.data.originator=='local' else u'Call ended by remote'
        self._cleanup()

    def _NH_SIPSessionDidChangeHoldState(self, notification):
        if notification.data.originator == 'remote':
            self.remote_hold = notification.data.on_hold
        if self.local_hold:
            if not self.offer_in_progress:
                self._status = u'On hold'
        elif self.remote_hold:
            if not self.offer_in_progress:
                self._status = u'Hold by remote'
            self.hold_tone.start()
        else:
            self._status = None
            self.hold_tone.stop()
        self.offer_in_progress = False

    def _NH_SIPSessionGotAcceptProposal(self, notification):
        if self.audio_stream not in notification.data.proposed_streams and self.video_stream not in notification.data.proposed_streams:
            return
        if self.audio_stream in notification.data.proposed_streams and self.audio_stream not in notification.data.streams:
            self._set_stream('audio', None)
        if self.video_stream in notification.data.proposed_streams and self.video_stream not in notification.data.streams:
            self._set_stream('video', None)
        self.offer_in_progress = False
        if not self.pending_removal:
            self._set_codec_info()
            self._status = u'Connected'
            reactor.callLater(1, self._reset_status)
        else:
            self._status = u'Ending...'
            self._cleanup()

    def _NH_SIPSessionGotRejectProposal(self, notification):
        if self.audio_stream not in notification.data.streams and self.video_stream not in notification.data.streams:
            return
        if self.audio_stream in notification.data.streams:
            self._set_stream('audio', None)
        if self.video_stream in notification.data.streams:
            self._set_stream('video', None)
        self.offer_in_progress = False
        self._status = u'Stream refused'
        if not self.pending_removal:
            self._set_codec_info()
            reactor.callLater(1, self._reset_status)
        else:
            self._cleanup()

    def _NH_SIPSessionDidRenegotiateStreams(self, notification):
        if notification.data.action != 'remove':
            return
        if self.audio_stream not in notification.data.streams and self.video_stream not in notification.data.streams:
            return
        if self.audio_stream in notification.data.streams:
            self._set_stream('audio', None)
        if self.video_stream in notification.data.streams:
            self._set_stream('video', None)
        self.offer_in_progress = False
        self._status = u'Stream removed'
        if not self.pending_removal:
            self._set_codec_info()
            reactor.callLater(1, self._reset_status)
        else:
            self._cleanup()

    def _NH_WavePlayerDidFail(self, notification):
        notification.center.remove_observer(self, sender=notification.sender)

    def _NH_WavePlayerDidEnd(self, notification):
        notification.center.remove_observer(self, sender=notification.sender)


class SessionManager(object):
    __metaclass__ = Singleton
    implements(IObserver)

    def __init__(self):
        self._lock = RLock()
        self._active_session = None
        self._incoming_proposals = []
        self._sessions = []

        self.current_ringtone = Null
        self.last_dialed_uri = None

    @classmethod
    def create_uri(cls, account, address):
        if not address.startswith(('sip:', 'sips:')):
            address = 'sip:' + address
        username, separator, domain = address.partition('@')
        if not domain and isinstance(account, Account):
            domain = account.id.domain
        elif '.' not in domain and isinstance(account, Account):
            domain += '.' + account.id.domain
        elif not domain:
            raise ValueError('SIP address without domain')
        address = username + '@' + domain
        return SIPURI.parse(str(address))

    def start(self):
        notification_center = NotificationCenter()
        notification_center.add_observer(self, name='SIPSessionNewIncoming')
        notification_center.add_observer(self, name='SIPSessionGotProposal')
        notification_center.add_observer(self, name='SIPSessionDidFail')
        notification_center.add_observer(self, name='SIPSessionGotRejectProposal')
        notification_center.add_observer(self, name='SIPSessionDidRenegotiateStreams')

    def stop(self):
        notification_center = NotificationCenter()
        notification_center.remove_observer(self, name='SIPSessionNewIncoming')
        notification_center.remove_observer(self, name='SIPSessionGotProposal')
        notification_center.remove_observer(self, name='SIPSessionDidFail')
        notification_center.remove_observer(self, name='SIPSessionGotRejectProposal')
        notification_center.remove_observer(self, name='SIPSessionDidRenegotiateStreams')

    def _get_active_session(self):
        return self._active_session
    def _set_active_session(self, value):
        old_active_session = self._active_session
        if old_active_session == value:
            return
        if old_active_session is not None:
            old_active_session.active = False
        if value is not None:
            value.active = True
        self._active_session = value
    active_session = property(_get_active_session, _set_active_session)
    del _get_active_session, _set_active_session

    @property
    def sessions(self):
        return [session for session in self._sessions if not session.pending_removal]

    def start_call(self, name, address, streams, account=None):
        account_manager = AccountManager()
        account = account or account_manager.default_account
        if account is None or not account.enabled:
            raise ValueError('Invalid account')
        try:
            remote_uri = self.create_uri(account, address)
        except Exception, e:
            raise ValueError('Invalid URI: %s' % e)
        else:
            self.last_dialed_uri = remote_uri
            session = Session(account)
            session_item = SessionItem(name, remote_uri, session, streams)
            self._sessions.append(session_item)
            notification_center = NotificationCenter()
            notification_center.add_observer(self, sender=session_item)
            self.active_session = session_item
            session_item.connect()

    def update_ringtone(self):
        if not self._incoming_proposals:
            self.current_ringtone = Null
        elif self.sessions:
            self.current_ringtone = self.beeping_ringtone
        else:
            self.current_ringtone = self._incoming_proposals[0].ringtone

    @property
    def beeping_ringtone(self):
        if 'beeping_ringtone' not in self.__dict__:
            ringtone = WavePlayer(SIPApplication.voice_audio_mixer, Resources.get('sounds/beeping_ringtone.wav'), volume=70, loop_count=0, pause_time=10)
            ringtone.bridge = SIPApplication.voice_audio_bridge
            self.__dict__['beeping_ringtone'] = ringtone
        return self.__dict__['beeping_ringtone']

    def _get_current_ringtone(self):
        return self.__dict__['current_ringtone']
    def _set_current_ringtone(self, ringtone):
        old_ringtone = self.__dict__.get('current_ringtone', Null)
        if ringtone is not Null and ringtone is old_ringtone:
            return
        old_ringtone.stop()
        old_ringtone.bridge.remove(old_ringtone)
        ringtone.bridge.add(ringtone)
        ringtone.start()
        self.__dict__['current_ringtone'] = ringtone
    current_ringtone = property(_get_current_ringtone, _set_current_ringtone)
    del _get_current_ringtone, _set_current_ringtone

    def handle_notification(self, notification):
        handler = getattr(self, '_NH_%s' % notification.name, Null)
        handler(notification)

    def _NH_SIPSessionNewIncoming(self, notification):
        session = notification.sender
        audio_streams = [stream for stream in notification.data.streams if stream.type=='audio']
        video_streams = [stream for stream in notification.data.streams if stream.type=='video']
        chat_streams = [stream for stream in notification.data.streams if stream.type=='chat']
        desktopsharing_streams = [stream for stream in notification.data.streams if stream.type=='desktop-sharing']
        filetransfer_streams = [stream for stream in notification.data.streams if stream.type=='file-transfer']
        if not audio_streams and not video_streams and not chat_streams and not desktopsharing_streams and not filetransfer_streams:
            session.reject(488)
            return
        if filetransfer_streams and (audio_streams or video_streams or chat_streams or desktopsharing_streams):
            session.reject(488)
            return
        if video_streams and desktopsharing_streams:
            session.reject(488)
            return
        session.send_ring_indication()
        streams = []
        if audio_streams:
            streams.append(audio_streams[0])
        if video_streams:
            streams.append(video_streams[0])
        if chat_streams:
            streams.append(chat_streams[0])
        if desktopsharing_streams:
            streams.append(desktopsharing_streams[0])
        if filetransfer_streams:
            streams.append(filetransfer_streams[0])
        incoming_proposal = IncomingProposalHandler(session, streams, new_session=False)
        notification.center.add_observer(self, sender=incoming_proposal)
        self.update_ringtone()

    def _NH_SIPSessionGotProposal(self, notification):
        session = notification.sender
        audio_streams = [stream for stream in notification.data.streams if stream.type=='audio']
        video_streams = [stream for stream in notification.data.streams if stream.type=='video']
        chat_streams = [stream for stream in notification.data.streams if stream.type=='chat']
        desktopsharing_streams = [stream for stream in notification.data.streams if stream.type=='desktop-sharing']
        filetransfer_streams = [stream for stream in notification.data.streams if stream.type=='file-transfer']
        if not audio_streams and not video_streams and not chat_streams and not desktopsharing_streams and not filetransfer_streams:
            session.reject_proposal(488)
            return
        if filetransfer_streams and (audio_streams or video_streams or chat_streams or desktopsharing_streams):
            session.reject_proposal(488)
            return
        if video_streams and desktopsharing_streams:
            session.reject_proposal(488)
            return
        session.send_ring_indication()
        streams = []
        if audio_streams:
            streams.append(audio_streams[0])
        if video_streams:
            streams.append(video_streams[0])
        if chat_streams:
            streams.append(chat_streams[0])
        if desktopsharing_streams:
            streams.append(desktopsharing_streams[0])
        if filetransfer_streams:
            streams.append(filetransfer_streams[0])
        incoming_proposal = IncomingProposalHandler(session, streams, new_session=False)
        notification.center.add_observer(self, sender=incoming_proposal)
        self.update_ringtone()

    def _NH_SIPSessionDidFail(self, notification):
        if notification.data.code != 487:
            return
        try:
            incoming_session = next(incoming_session for incoming_session in self.incoming_sessions if incoming_session.session is notification.sender)
        except StopIteration:
            pass
        else:
            self.incoming_sessions.remove(incoming_session)
            self.update_ringtone()

    def _NH_SIPSessionGotRejectProposal(self, notification):
        if notification.data.code != 487:
            return
        try:
            incoming_session = next(incoming_session for incoming_session in self.incoming_sessions if incoming_session.session is notification.sender)
        except StopIteration:
            pass
        else:
            self.incoming_sessions.remove(incoming_session)
            self.update_ringtone()

    # SessionItem notifications

    def _NH_SessionItemDidEnd(self, notification):
        session = notification.sender
        self._sessions.remove(session)
        notification.center.remove_observer(self, sender=session)
        if session is self.active_session:
            self.active_session = None

    # IncomingProposalHandler notifications

    def _NH_IncomingProposalAccepted(self, notification):
        incoming_proposal = notification.sender
        self._incoming_proposals.remove(incoming_proposal)
        self.update_ringtone()
        session = incoming_proposal.session
        #streams = incoming_proposal.accepted_streams.copy()
        # TODO: enable other streams when support for them is implemented
        streams = [s for s in incoming_proposal.accepted_streams if s.type=='audio']
        if not streams:
            if incoming_proposal.new_session:
                session.reject(488)
            else:
                session.reject_proposal(488)
            notification.center.remove_observer(self, sender=incoming_proposal)
            return
        try:
            session_item = next(session_item for session_item in self.sessions if session_item.session is session)
            for stream in streams:
                session_item._set_stream(stream.type, stream)
        except StopIteration:
            session_item = SessionItem(session.remote_identity.display_name, session.remote_identity.uri, session, streams)
            notification.center.add_observer(self, sender=session_item)
        if incoming_proposal.new_session:
            session.accept(streams)
        else:
            session.accept_proposal(streams)
        notification.center.remove_observer(self, sender=incoming_proposal)

    def _NH_IncomingProposalRejected(self, notification):
        incoming_proposal = notification.sender
        self._incoming_proposals.remove(incoming_proposal)
        self.update_ringtone()
        session = incoming_proposal.session
        if not incoming_proposal.new_session:
            session.reject(486)
        elif incoming_proposal.reject_mode == 'reject':
            session.reject(603)
        elif incoming_proposal.reject_mode == 'busy':
            session.reject(486)
        notification.center.remove_observer(self, sender=incoming_proposal)

