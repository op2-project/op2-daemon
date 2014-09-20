
import platform
import sys

from sipsimple.configuration import Setting, SettingsGroup, SettingsObjectExtension
from sipsimple.configuration.datatypes import AudioCodecList, NonNegativeInteger, SampleRate
from sipsimple.configuration.settings import AudioSettings, EchoCancellerSettings, LogsSettings, RTPSettings, TLSSettings

from op2d import __version__
from op2d.configuration.datatypes import ApplicationDataPath, SoundFile, SpeedDialingList
from op2d.resources import Resources

__all__ = ['SIPSimpleSettingsExtension']


class EchoCancellerSettingsExtension(EchoCancellerSettings):
    enabled = Setting(type=bool, default=False)


class AudioSettingsExtension(AudioSettings):
    recordings_directory = Setting(type=ApplicationDataPath, default=ApplicationDataPath('recordings'))
    sample_rate = Setting(type=SampleRate, default=16000)
    echo_canceller = EchoCancellerSettingsExtension


class LogsSettingsExtension(LogsSettings):
    directory = Setting(type=ApplicationDataPath, default=ApplicationDataPath('logs'))
    trace_notifications = Setting(type=bool, default=False)


class OP2Settings(SettingsGroup):
    speed_dialing = Setting(type=SpeedDialingList, default=None, nillable=True)


class RTPSettingsExtension(RTPSettings):
    audio_codec_list = Setting(type=AudioCodecList, default=AudioCodecList(('G722', 'PCMU', 'PCMA')))
    timeout = Setting(type=NonNegativeInteger, default=0)


class SoundSettings(SettingsGroup):
    inbound_ringtone = Setting(type=SoundFile, default=SoundFile(Resources.get('sounds/inbound_ringtone.wav')), nillable=True)
    outbound_ringtone = Setting(type=SoundFile, default=SoundFile(Resources.get('sounds/outbound_ringtone.wav')), nillable=True)


class TLSSettingsExtension(TLSSettings):
    ca_list = Setting(type=ApplicationDataPath, default=None, nillable=True)


class SIPSimpleSettingsExtension(SettingsObjectExtension):
    audio = AudioSettingsExtension
    logs = LogsSettingsExtension
    op2 = OP2Settings
    rtp = RTPSettingsExtension
    sounds = SoundSettings
    tls = TLSSettingsExtension

    user_agent = Setting(type=str, default='OP2 Device %s (%s)' % (__version__, platform.system() if sys.platform!='darwin' else 'OSX'))

