
import smbus

__all__ = ['I2C']


class I2C(object):

    def __init__(self, address, busnum, debug=False):
        self._address = address
        self._bus = smbus.SMBus(busnum)
        self._debug = debug

    @property
    def address(self):
        return self._address

    def _log_debug(self, msg):
        print "I2C: %s" % msg

    def _log_error(self, msg):
        print "I2C: Error accessing 0x%02X: %s" % (self._address, msg)

    def write8(self, reg, value):
        """
        Writes an 8-bit value to the specified register/address
        """
        try:
            self._bus.write_byte_data(self._address, reg, value)
            if self._debug:
                self._log_debug("Wrote 0x%02X to register 0x%02X" % (value, reg))
        except IOError as e:
            self._log_error(e)

    def write16(self, reg, value):
        """
        Writes a 16-bit value to the specified register/address pair
        """
        try:
            self._bus.write_word_data(self._address, reg, value)
            if self._debug:
                self._log_debug("Wrote 0x%02X to register pair 0x%02X, 0x%02X" % (value, reg, reg+1))
        except IOError as e:
            self._log_error(e)

    def read8(self, reg):
        """
        Read an 8-bit value from the I2C device
        """
        try:
            result = self._bus.read_byte_data(self._address, reg)
            if self._debug:
                self._log_debug("Device 0x%02X returned 0x%02X from reg 0x%02X" % (self._address, result & 0xFF, reg))
            return result
        except IOError as e:
            self._log_error(e)

    def read16(self, reg):
        """
        Read a 16-bit value from the I2C device
        """
        try:
            result = self._bus.read_word_data(self._address, reg)
            if self._debug:
                self._log_debug("Device 0x%02X returned 0x%02X from reg 0x%02X" % (self._address, result & 0xFF, reg))
            return result
        except IOError as e:
            self._log_error(e)

