
from application import log
from application.python import Null
from application.python.types import Singleton
from importlib import import_module

from op2d.configuration import Configuration

__all__ = ['HardwareAbstractionLayer']


def load_backend(backend_name):
    if backend_name:
        mods = [backend_name]
        if '.' not in backend_name:
            mods.insert(0, 'op2d.hal.backend.' + backend_name)
        excs = []
        for mod in mods:
            try:
                backend = import_module(mod)
                return backend.Backend()
            except Exception, e:
                excs.append(e)
        log.error('Failed to load HAL backend: %s' % ' | '.join(str(e) for e in excs))
    return Null


class HardwareAbstractionLayer(object):
    __metaclass__ = Singleton

    def __init__(self):
        self._backend = load_backend(Configuration.hal_backend)
        self._backend.initialize()

    def start(self):
        self._backend.start()

    def stop(self):
        self._backend.stop()

