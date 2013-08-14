
import os

from application.process import process
from application.python.descriptor import classproperty


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

