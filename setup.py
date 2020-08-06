"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst')) as f:
    long_description = f.read()

setup(
    name='pylablib',
    version='0.4.2',
    description='Collection of Python code for using in lab environment (data acquisition, device communication, data analysis)',
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url='https://github.com/AlexShkarin/pyLabLib-v0',
    author='Alexey Shkarin',
    author_email='alex.shkarin@gmail.com',
    license='MIT',
    classifiers=[
    'Development Status :: 3 - Alpha',
    'Environment :: Win32 (MS Windows)',
    'Intended Audience :: Science/Research',
    'Topic :: Scientific/Engineering :: Physics',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Operating System :: Microsoft :: Windows'
    ],
    project_urls={
    'Documentation': 'https://pylablib-v0.readthedocs.io',
    'Source': 'https://github.com/AlexShkarin/pyLabLib-v0/',
    'Tracker': 'https://github.com/AlexShkarin/pyLabLib-v0/issues'
    },
    packages=find_packages(exclude=['docs']),
    install_requires=['future','numpy','scipy','matplotlib','pandas','numba','rpyc'],
    extras_require={
        'devio-basic':['pyft232','pyvisa','pyserial','pyusb','websocket-client'],
        'devio':['pyft232','pyvisa','pyserial','nidaqmx','pywinusb','websocket-client'],
        'gui':['pyqt5','sip','pyqtgraph'],
    }
)