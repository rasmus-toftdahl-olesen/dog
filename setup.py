#!/usr/bin/env python

from pathlib import Path

from setuptools import setup

import dog

root_dir = Path(__file__).parent
readme = (root_dir / 'README.md').read_text()

setup(
    name='dog',
    version=dog.DOG_VERSION,
    description='dog is a simple wrapper for "docker run" to make it simple to call'
    ' tools residing inside docker containers',
    license='The Unlicense',
    long_description_content_type='text/markdown',
    long_description=readme,
    author='Rasmus Toftdahl Olesen',
    author_email='rasmus.toftdahl.olesen@gmail.com',
    url='https://github.com/rasmus-toftdahl-olesen/dog',
    py_modules=['dog'],
    entry_points={'console_scripts': ['dog=dog:setup_tools_main']},
    scripts=['dog.py'],
    platforms='any',
    python_requires='>=3.5',
    classifiers=[
        'Operating System :: OS Independent',
        'License :: OSI Approved :: The Unlicense (Unlicense)',
        'Environment :: Console',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Embedded Systems',
        'Programming Language :: Python :: 3',
    ],
)
