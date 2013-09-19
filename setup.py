# coding=utf8

import glob
import os
import re

from distutils.core import setup


def get_version():
    return re.search(r"""__version__\s+=\s+(?P<quote>['"])(?P<version>.+?)(?P=quote)""", open('op2d/__init__.py').read()).group('version')

def find_packages(toplevel):
    return [directory.replace(os.path.sep, '.') for directory, subdirs, files in os.walk(toplevel) if '__init__.py' in files]

setup(name         = "op2d",
      version      = get_version(),
      author       = "Saúl Ibarra Corretgé",
      author_email = "saghul@gmail.com",
      url          = "TODO",
      description  = "Open Pi Phone daemon",
      classifiers  = [
            "Development Status :: 3 - Alpha",
            "License :: GNU General Public License 3",
            "Operating System :: OS Independent",
            "Programming Language :: Python"
                     ],
      packages     = find_packages('op2d'),
      package_data = {
          'op2d.web.frontend': ['templates/*']
      },
      scripts      = ['op2-daemon'],
      data_files   = [('/var/spool/op2d', []),
                      ('share/op2d/sounds', glob.glob(os.path.join('resources', 'sounds', '*.wav')))]
      )

