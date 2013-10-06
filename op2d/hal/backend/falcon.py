
import RPi.GPIO as GPIO
import time

from application import log
from application.notification import IObserver, NotificationCenter
from application.python import Null
from sipsimple.configuration.settings import SIPSimpleSettings
from sipsimple.streams import AudioStream
from sipsimple.threading import run_in_thread, run_in_twisted_thread
from twisted.internet import reactor
from zope.interface import implements

from op2d import __version__ as op2_version
from op2d.hal.backend import IBackend
from op2d.hal.backend.pihelpers import mcp230xx
from op2d.hal.backend.pihelpers.lcd import CharLCD
from op2d.sessions import SessionManager

__all__ = ['Backend']


# These buttons are mapped to GPIO pins using BCM pinout,
# *not* BOARD pinout

ANSWER_BTN = 4
HANGUP_BTN = 25
INFO_BTN   = 24
SD1_BTN    = 23
SD2_BTN    = 22
SD3_BTN    = 27   # 21 if using a rev1 board

# Status LED (also uses the BCM pinout)
STATUS_LED = 18

# Use 200ms bounce time, seems to work fine

BTN_BOUNCETIME = 200

# LCD pins, note that LCD is connected to a MCP23017

LCD_PIN_RS    = 8
LCD_PIN_E     = 9
LCD_DATA_PINS = [0, 1, 2, 3]


class FalconBackend(object):
    implements(IBackend, IObserver)

    def __init__(self):
        self.current_session = None
        self.incoming_request = None
        self._lcd = None
        self._lcd_gpio = None

    def initialize(self):
        log.msg('Falcon HAL backend initialized')

        # Initialize LCD
        self._lcd_gpio = mcp230xx.GPIO(1, 0x20, 16)    # busnum, address, num gpios
        self._lcd = CharLCD(pin_rs=8, pin_e=9, pins_db=[0, 1, 2, 3], GPIO=self._lcd_gpio)
        self.lcd_output('OP^2 system\nversion %s' % op2_version)

        # Initialize GPIO
        GPIO.setmode(GPIO.BCM)

        # Initialize buttons, with a pull-down ressistor
        GPIO.setup(ANSWER_BTN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(HANGUP_BTN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(INFO_BTN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(SD1_BTN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(SD2_BTN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(SD3_BTN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

        # Status LED
        GPIO.setup(STATUS_LED, GPIO.OUT)

    def start(self):
        log.msg('Falcon HAL backend started')
        notification_center = NotificationCenter()
        notification_center.add_observer(self, name='IncomingRequestReceived')
        notification_center.add_observer(self, name='IncomingRequestAccepted')
        notification_center.add_observer(self, name='IncomingRequestRejected')
        notification_center.add_observer(self, name='SessionItemNewIncoming')
        notification_center.add_observer(self, name='SessionItemNewOutgoing')
        notification_center.add_observer(self, name='SessionItemDidChange')
        notification_center.add_observer(self, name='SessionItemDidEnd')

        # Register callbacks for button interrupts
        GPIO.add_event_detect(ANSWER_BTN, GPIO.RISING, callback=self.handle_button_press, bouncetime=BTN_BOUNCETIME)
        GPIO.add_event_detect(HANGUP_BTN, GPIO.RISING, callback=self.handle_button_press, bouncetime=BTN_BOUNCETIME)
        GPIO.add_event_detect(INFO_BTN, GPIO.RISING, callback=self.handle_button_press, bouncetime=BTN_BOUNCETIME)
        GPIO.add_event_detect(SD1_BTN, GPIO.RISING, callback=self.handle_button_press, bouncetime=BTN_BOUNCETIME)
        GPIO.add_event_detect(SD2_BTN, GPIO.RISING, callback=self.handle_button_press, bouncetime=BTN_BOUNCETIME)
        GPIO.add_event_detect(SD3_BTN, GPIO.RISING, callback=self.handle_button_press, bouncetime=BTN_BOUNCETIME)

        GPIO.output(STATUS_LED, 1)

    def stop(self):
        log.msg('Falcon HAL backend stopped')
        notification_center = NotificationCenter()
        notification_center.remove_observer(self, name='IncomingRequestReceived')
        notification_center.remove_observer(self, name='IncomingRequestAccepted')
        notification_center.remove_observer(self, name='IncomingRequestRejected')
        notification_center.remove_observer(self, name='SessionItemNewIncoming')
        notification_center.remove_observer(self, name='SessionItemNewOutgoing')
        notification_center.remove_observer(self, name='SessionItemDidChange')
        notification_center.remove_observer(self, name='SessionItemDidEnd')

        # Cleanup hardware stuff
        GPIO.cleanup()
        self._lcd.clear()
        self._lcd_gpio.cleanup()

    @run_in_thread('hal-io')
    def lcd_output(self, text, delay=0):
        # This function runs in a different thread because the LCD module
        # needs to call sleep() for brief amounts of time
        if self._lcd is None:
            return
        self._lcd.clear()
        if text:
            self._lcd.message(text)
        if delay:
            time.sleep(delay)

    @run_in_twisted_thread
    def handle_button_press(self, button):
        if button == ANSWER_BTN:
            self._EH_AnswerButtonPressed()
        elif button == HANGUP_BTN:
            self._EH_HangupButtonPressed()
        elif button == INFO_BTN:
            self._EH_InfoButtonPressed()
        elif button in (SD1_BTN, SD2_BTN, SD3_BTN):
            self._EH_SpeedDialButtonPressed(button)
        else:
            log.warn('Unknown button pressed: %s' % button)

    def _EH_AnswerButtonPressed(self):
        if self.current_session is not None or self.incoming_request is None:
            return
        log.msg('Answering incoming request...')
        self.incoming_request.accept(audio=True)

    def _EH_HangupButtonPressed(self):
        if self.incoming_request is not None:
            log.msg('Rejecting incoming request...')
            self.incoming_request.busy()
        elif self.current_session is not None:
            log.msg('Ending session...')
            self.current_session.end()

    def _EH_InfoButtonPressed(self):
        if self.incoming_request is None and self.current_session is None:
            # TODO: alternate some info on the LCD
            return
        if self.current_session is not None:
            if self.current_session.local_hold:
                self.current_session.unhold()
            else:
                self.current_session.hold()

    def _EH_SpeedDialButtonPressed(self, button):
        log.msg('SD button %s pressed' % button)
        if self.incoming_request is not None or self.current_session is not None:
            return
        settings = SIPSimpleSettings()
        speed_dialing = settings.op2.speed_dialing
        if not speed_dialing:
            return
        try:
            if button == SD1_BTN:
                entry = speed_dialing[0]
            elif button == SD2_BTN:
                entry = speed_dialing[1]
            elif button == SD3_BTN:
                entry = speed_dialing[2]
            else:
                return
        except IndexError:
            return
        if not entry.uri:
            return
        session_manager = SessionManager()
        session_manager.start_call(entry.name, entry.uri, [AudioStream()])

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
        name = request.session.remote_identity.display_name or request.session.remote_identity.uri.user
        self.lcd_output('Incoming call\n%s' % name)
        self.incoming_request = request

    def _NH_IncomingRequestAccepted(self, notification):
        log.msg('Incoming request accepted')
        self.lcd_output('')
        self.incoming_request = None

    def _NH_IncomingRequestRejected(self, notification):
        request = notification.sender
        if request is not self.incoming_request:
            return
        log.msg('Incoming request rejected')
        self.lcd_output('Call rejected', delay=2)
        self.lcd_output('')
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
        name = session.name or session.uri.user
        self.lcd_output('Outgoing call\n%s' % name)
        self.current_session = session

    def _NH_SessionItemDidChange(self, notification):
        if notification.sender is not self.current_session:
            return
        session = notification.sender
        name = session.name or session.uri.user
        line1 = session.status or name
        line2 = session.duration
        self.lcd_output('%s\n%s' % (line1, line2))

    def _NH_SessionItemDidEnd(self, notification):
        if notification.sender is self.current_session:
            log.msg('Session ended')
            self.lcd_output('Call ended', delay=2)
            self.lcd_output('')
            self.current_session = None


def Backend():
    return FalconBackend()

