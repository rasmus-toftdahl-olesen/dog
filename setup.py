#!/usr/bin/env python

import sys
from setuptools import setup
from pathlib import Path
root_dir = Path(__file__).parent
readme = (root_dir / 'README.md').read_text()
import dog

setup(name='dog-rasmus.toftdahl.olesen',
      version=dog.VERSION,
      description='dog is a simple wrapper for docker run to make it simple to call tools residing inside docker containers',
      license='The Unlicense',
      long_description_content_type='text/markdown',
      long_description=readme,
      author='Rasmus Toftdahl Olesen',
      author_email='rasmus.toftdahl.olesen@gmail.com',
      url='https://github.com/rasmus-toftdahl-olesen/dog',
      py_modules=['dog'],
      scripts=['dog.py'],
      platforms='any',
      python_requires='>=3.6',
      classifiers=['Operating System :: OS Independent',
                   'License :: OSI Approved :: The Unlicense (Unlicense)',
                   'Environment :: Console',
                   'Topic :: Software Development :: Build Tools',
                   'Topic :: Software Development :: Embedded Systems',
                   'Programming Language :: Python :: 3',
      ],
)