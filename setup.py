# coding=utf8

import glob
import os
import re

from distutils.core import setup


def get_version():
    return re.search(r"""__version__\s+=\s+(?P<quote>['"])(?P<version>.+?)(?P=quote)""", open('op2d/__init__.py').read()).group('version')

def find_packages(toplevel):
    return [directory.replace(os.path.sep, '.') for directory, subdirs, files in os.walk(toplevel) if '__init__.py' in files]

def list_resources(directory, destination_directory):
    return [(dir.replace(directory, destination_directory), [os.path.join(dir, file) for file in files]) for dir, subdirs, files in os.walk(directory)]

setup(name         = "op2d",
      version      = get_version(),
      author       = "Saúl Ibarra Corretgé",
      author_email = "saghul@gmail.com",
      url          = "https://github.com/op2-project/op2-daemon",
      description  = "Open Pi Phone daemon",
      classifiers  = [
            "Development Status :: 3 - Alpha",
            "License :: GNU General Public License 3",
            "Operating System :: OS Independent",
            "Programming Language :: Python"
                     ],
      packages     = find_packages('op2d'),
      data_files   = list_resources('resources', 'share/op2d'),
      scripts      = ['op2-daemon']
      )

