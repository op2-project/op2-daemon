
from sipsimple.account import BonjourMSRPSettings, MessageSummarySettings, MSRPSettings, PresenceSettings, RTPSettings, SIPSettings, TLSSettings, XCAPSettings
from sipsimple.configuration import Setting, SettingsGroup, SettingsObjectExtension
from sipsimple.configuration.datatypes import AudioCodecList, MSRPConnectionModel, MSRPTransport, NonNegativeInteger, Path, SIPTransportList, SRTPEncryption
from sipsimple.util import user_info

from op2d.configuration.datatypes import ApplicationDataPath, CustomSoundFile, DefaultPath
from op2d.resources import Resources

__all__ = ['AccountExtension', 'BonjourAccountExtension']


class BonjourMSRPSettingsExtension(BonjourMSRPSettings):
    transport = Setting(type=MSRPTransport, default='tcp')


class BonjourSIPSettings(SettingsGroup):
    transport_order = Setting(type=SIPTransportList, default=SIPTransportList(['tcp', 'udp', 'tls']))


class BonjourPresenceSettingsExtension(PresenceSettings):
    enabled = Setting(type=bool, default=True)


class MessageSummarySettingsExtension(MessageSummarySettings):
    enabled = Setting(type=bool, default=True)


class MSRPSettingsExtension(MSRPSettings):
    connection_model = Setting(type=MSRPConnectionModel, default='relay')


class PresenceSettingsExtension(PresenceSettings):
    enabled = Setting(type=bool, default=False)


class PSTNSettings(SettingsGroup):
    idd_prefix = Setting(type=unicode, default=None, nillable=True)
    prefix = Setting(type=unicode, default=None, nillable=True)


class RTPSettingsExtension(RTPSettings):
    audio_codec_order = Setting(type=AudioCodecList, default=None, nillable=True)
    inband_dtmf = Setting(type=bool, default=False)
    srtp_encryption = Setting(type=SRTPEncryption, default='disabled')
    use_srtp_without_tls = Setting(type=bool, default=True)


class SIPSettingsExtension(SIPSettings):
    always_use_my_proxy = Setting(type=bool, default=True)
    register = Setting(type=bool, default=True)
    register_interval = Setting(type=NonNegativeInteger, default=600)
    subscribe_interval = Setting(type=NonNegativeInteger, default=600)
    publish_interval = Setting(type=NonNegativeInteger, default=600)


class SoundSettings(SettingsGroup):
    inbound_ringtone = Setting(type=CustomSoundFile, default=CustomSoundFile(DefaultPath), nillable=True)


class TLSSettingsExtension(TLSSettings):
    certificate = Setting(type=Path, default=Path(Resources.get('tls/default.crt')), nillable=True)


class XCAPSettingsExtension(XCAPSettings):
    enabled = Setting(type=bool, default=False)


class AccountExtension(SettingsObjectExtension):
    display_name = Setting(type=unicode, default=user_info.fullname, nillable=True)
    message_summary = MessageSummarySettingsExtension
    msrp = MSRPSettingsExtension
    pstn = PSTNSettings
    presence = PresenceSettingsExtension
    rtp = RTPSettingsExtension
    sip = SIPSettingsExtension
    sounds = SoundSettings
    tls = TLSSettingsExtension
    xcap = XCAPSettingsExtension


class BonjourAccountExtension(SettingsObjectExtension):
    msrp = BonjourMSRPSettingsExtension
    presence = BonjourPresenceSettingsExtension
    rtp = RTPSettingsExtension
    sip = BonjourSIPSettings
    sounds = SoundSettings


