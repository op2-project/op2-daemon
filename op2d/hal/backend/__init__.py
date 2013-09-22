
from zope.interface import Interface

__all__ = ['IBackend']


class IBackend(Interface):
    """
    Interface to be implemented by different HAL backends.

    * initialize: called very early, right when the HAL has
      loaded the backend.
    * start: called when the HAL has started it's processing
    * stop: called when the HAL has stopped it's processing.
    """

    def initialize(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass

