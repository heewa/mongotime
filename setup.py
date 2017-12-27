from setuptools import setup
from os import path

here = path.abspath(path.dirname(__file__))

# Exec mongotime/version.py to load __version__ into global namespace. For
# reasons and alt, see:
# https://packaging.python.org/guides/single-sourcing-package-version/
exec(open(path.join(here, 'mongotime', 'version.py')).read())

setup(
    name='mongotime',
    version=__version__,  # noqa
    description=(
        'Sampling Profiler for Mongo DB - see what the DB spends time on'),
    url='http://github.com/heewa/mongotime',
    author='Heewa Barfchin',
    author_email='heewa.b@gmail.com',
    license='MIT',
    packages=['mongotime'],
    entry_points={
        'console_scripts': [
            'mongotime=mongotime.app:run',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',

        'Programming Language :: Python :: 2.7',

        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',

        'License :: OSI Approved :: MIT License',

        'Environment :: Console',

        'Topic :: Database',
        'Topic :: System',
        'Topic :: System :: Benchmark',
        'Topic :: System :: Monitoring',
    ],
    keywords='mongo mongodb database db perf performance profile profiler',
    install_requires=[
        'click>=6.7,<7',
        'pymongo>=3.6.0,<4',
    ],
    long_description='TODO')
