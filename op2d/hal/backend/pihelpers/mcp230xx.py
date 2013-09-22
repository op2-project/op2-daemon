
from .i2c import I2C

__all__ = ['MCP230XX', 'GPIO']


MCP23017_IODIRA = 0x00
MCP23017_IODIRB = 0x01
MCP23017_GPIOA  = 0x12
MCP23017_GPIOB  = 0x13
MCP23017_GPPUA  = 0x0C
MCP23017_GPPUB  = 0x0D
MCP23017_OLATA  = 0x14
MCP23017_OLATB  = 0x15

MCP23008_GPIOA  = 0x09
MCP23008_GPPUA  = 0x06
MCP23008_OLATA  = 0x0A


class MCP230XX(object):
    OUTPUT = 0
    INPUT  = 1

    def __init__(self, busnum, address, num_gpios):
        assert num_gpios in (8, 16), "Number of GPIOs must be 8 or 16"
        self._i2c = I2C(address=address, busnum=busnum)
        self.address = address
        self.num_gpios = num_gpios
        # set defaults
        self.reset()

    def _read_change_pin(self, port, pin, value, currvalue=None):
        assert pin >= 0 and pin < self.num_gpios, "Pin number %s is invalid, only 0-%s are valid" % (pin, self.num_gpios)
        assert value in (0, 1), "Value is %s, must be 1 or 0" % value
        if not currvalue:
            currvalue = self._i2c.read8(port)
        # swap current value
        if value == 0:
            newvalue = currvalue & ~(1 << pin)
        elif value == 1:
            newvalue = currvalue | (1 << pin)
        self._i2c.write8(port, newvalue)
        return newvalue

    def reset(self):
        if self.num_gpios == 8:
            self._i2c.write8(MCP23017_IODIRA, 0xFF)  # all inputs on port A
            self._direction = self._i2c.read8(MCP23017_IODIRA)
            self._i2c.write8(MCP23008_GPPUA, 0x00)
        elif self.num_gpios == 16:
            self._i2c.write8(MCP23017_IODIRA, 0xFF)  # all inputs on port A
            self._i2c.write8(MCP23017_IODIRB, 0xFF)  # all inputs on port B
            self._direction = self._i2c.read8(MCP23017_IODIRA)
            self._direction |= self._i2c.read8(MCP23017_IODIRB) << 8
            self._i2c.write8(MCP23017_GPPUA, 0x00)
            self._i2c.write8(MCP23017_GPPUB, 0x00)

    def pullup(self, pin, value):
        if self.num_gpios == 8:
            self._read_change_pin(MCP23008_GPPUA, pin, value)
        elif self.num_gpios == 16:
            if (pin < 8):
                self._read_change_pin(MCP23017_GPPUA, pin, value)
            else:
                self._read_change_pin(MCP23017_GPPUB, pin-8, value) << 8

    def config(self, pin, mode):
        if self.num_gpios == 8:
            self._direction = self._read_change_pin(MCP23017_IODIRA, pin, mode)
        elif self.num_gpios == 16:
            if (pin < 8):
                self._direction = self._read_change_pin(MCP23017_IODIRA, pin, mode)
            else:
                self._direction |= self._read_change_pin(MCP23017_IODIRB, pin-8, mode) << 8

    def output(self, pin, value):
        # TODO: check if pin is configured for this direction?
        if self.num_gpios == 8:
            self._read_change_pin(MCP23008_GPIOA, pin, value, self._i2c.read8(MCP23008_OLATA))
        if self.num_gpios == 16:
            if (pin < 8):
                self._read_change_pin(MCP23017_GPIOA, pin, value, self._i2c.read8(MCP23017_OLATA))
            else:
                self._read_change_pin(MCP23017_GPIOB, pin-8, value, self._i2c.read8(MCP23017_OLATB)) << 8

    def input(self, pin):
        # TODO: check if pin is configured for this direction?
        if self.num_gpios == 8:
            value = self._i2c.read8(MCP23008_GPIOA)
        elif self.num_gpios == 16:
            value = self._i2c.read8(MCP23017_GPIOA)
            value |= self._i2c.read8(MCP23017_GPIOB) << 8
        return value & (1 << pin)


class GPIO(object):
    """
    RPi.GPIO compatible interface for MCP23017 and MCP23008
    """

    OUT = 0
    IN = 1
    BCM = BOARD = 0

    def __init__(self, busnum, address, num_gpios):
        self._chip = MCP230XX(busnum, address, num_gpios)

    def setmode(self, mode):
        pass

    def setup(self, pin, mode):
        self._chip.config(pin, mode)

    def input(self, pin):
        return self._chip.input(pin)

    def output(self, pin, value):
        self._chip.output(pin, value)

    def pullup(self, pin, value):
        self._chip.pullup(pin, value)

    def cleanup(self):
        try:
            self._chip.reset()
        except Exception:
            pass

