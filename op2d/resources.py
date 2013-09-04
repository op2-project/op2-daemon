
import os
import sys

from application.process import process
from application.python.descriptor import classproperty

__all__ = ['ApplicationData', 'Resources']


class ApplicationData(object):
    """Provide access to user data"""

    _cached_directory = None

    @classproperty
    def directory(cls):
        if cls._cached_directory is None:
            cls._cached_directory = os.path.abspath(process.spool_directory)
        return cls._cached_directory

    @classmethod
    def get(cls, resource):
        return os.path.join(cls.directory, resource or u'')


class Resources(object):
    """Provide access to application resources"""

    _cached_directory = None

    @classproperty
    def directory(cls):
        if cls._cached_directory is None:
            script = sys.argv[0]
            if script == '':
                application_directory = os.path.realpath(script) # executed in interactive interpreter
            else:
                binary_directory = os.path.dirname(os.path.realpath(script))
                if os.path.basename(binary_directory) == 'bin':
                    application_directory = os.path.dirname(binary_directory)
                else:
                    application_directory = binary_directory
            if os.path.exists(os.path.join(application_directory, 'resources', '.op2d')):
                cls._cached_directory = os.path.join(application_directory, 'resources').decode(sys.getfilesystemencoding())
            else:
                cls._cached_directory = os.path.join(application_directory, 'share', 'op2-daemon').decode(sys.getfilesystemencoding())
        return cls._cached_directory

    @classmethod
    def get(cls, resource):
        return os.path.join(cls.directory, resource or u'')

