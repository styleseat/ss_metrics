#!/usr/bin/env python


from setuptools import setup


setup(
    name='ss_metrics',
    version='0.1.0',
    author='StyleSeat',
    description='Custom reporters for AppMetrics',
    url='https://github.com/styleseat/ss_metrics',
    packages=['ss_metrics'],
    install_requires=[
        'AppMetrics>=0.5.0',
        'librato-metrics>=0.8.6',
    ],
    platforms='Platform Independent',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Topic :: Internet',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
)
