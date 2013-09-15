
import platform
import sys

from sipsimple.configuration import Setting, SettingsGroup, SettingsObjectExtension
from sipsimple.configuration.datatypes import AudioCodecList, Path, SampleRate
from sipsimple.configuration.settings import AudioSettings, ChatSettings, EchoCancellerSettings, FileTransferSettings, LogsSettings, RTPSettings, TLSSettings

from op2d import __version__
from op2d.configuration.datatypes import ApplicationDataPath, SoundFile
from op2d.resources import Resources

__all__ = ['SIPSimpleSettingsExtension']


class EchoCancellerSettingsExtension(EchoCancellerSettings):
    enabled = Setting(type=bool, default=False)


class AudioSettingsExtension(AudioSettings):
    recordings_directory = Setting(type=ApplicationDataPath, default=ApplicationDataPath('recordings'))
    sample_rate = Setting(type=SampleRate, default=16000)
    echo_canceller = EchoCancellerSettingsExtension


class ChatSettingsExtension(ChatSettings):
    auto_accept = Setting(type=bool, default=False)
    sms_replication = Setting(type=bool, default=True)
    history_directory = Setting(type=ApplicationDataPath, default=ApplicationDataPath('history'))


class FileTransferSettingsExtension(FileTransferSettings):
    auto_accept = Setting(type=bool, default=False)
    directory = Setting(type=Path, default=None, nillable=True)


class LogsSettingsExtension(LogsSettings):
    directory = Setting(type=ApplicationDataPath, default=ApplicationDataPath('logs'))
    trace_sip = Setting(type=bool, default=False)
    trace_pjsip = Setting(type=bool, default=False)
    trace_msrp = Setting(type=bool, default=False)
    trace_xcap = Setting(type=bool, default=False)
    trace_notifications = Setting(type=bool, default=False)


class RTPSettingsExtension(RTPSettings):
    audio_codec_list = Setting(type=AudioCodecList, default=AudioCodecList(('speex', 'G722', 'PCMU', 'PCMA')))


class SoundSettings(SettingsGroup):
    inbound_ringtone = Setting(type=SoundFile, default=SoundFile(Resources.get('sounds/inbound_ringtone.wav')), nillable=True)
    outbound_ringtone = Setting(type=SoundFile, default=SoundFile(Resources.get('sounds/outbound_ringtone.wav')), nillable=True)
    message_received = Setting(type=SoundFile, default=SoundFile(Resources.get('sounds/message_received.wav')), nillable=True)
    message_sent = Setting(type=SoundFile, default=SoundFile(Resources.get('sounds/message_sent.wav')), nillable=True)
    file_received = Setting(type=SoundFile, default=SoundFile(Resources.get('sounds/file_received.wav')), nillable=True)
    file_sent = Setting(type=SoundFile, default=SoundFile(Resources.get('sounds/file_sent.wav')), nillable=True)
    play_message_alerts = Setting(type=bool, default=True)
    play_file_alerts = Setting(type=bool, default=True)


class TLSSettingsExtension(TLSSettings):
    ca_list = Setting(type=ApplicationDataPath, default=None, nillable=True)


class SIPSimpleSettingsExtension(SettingsObjectExtension):
    audio = AudioSettingsExtension
    chat = ChatSettingsExtension
    file_transfer = FileTransferSettingsExtension
    logs = LogsSettingsExtension
    rtp = RTPSettingsExtension
    sounds = SoundSettings
    tls = TLSSettingsExtension

    user_agent = Setting(type=str, default='OP2 Device %s (%s)' % (__version__, platform.system() if sys.platform!='darwin' else 'OSX'))

