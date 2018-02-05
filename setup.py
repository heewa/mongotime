from setuptools import setup
from os import path

here = path.abspath(path.dirname(__file__))

# Exec mongotime/version.py to load __version__ into global namespace. For
# reasons and alt, see:
# https://packaging.python.org/guides/single-sourcing-package-version/
exec(open(path.join(here, 'mongotime', 'version.py')).read())

LONG_DESC = '''
Mongotime is a sampling-based performance analysis tool for MongoDB that aims
to give you a deep view into how Mongo is spending its time by showing %
utilization of various activity types, and allowing you to add custom grouping
and filtering.

This approach is particularly useful if your DB is strained by a high volume of
fast queries, rather than a few slow ones. Besides optimizing slow queries, you
might want to understand and change general access patterns. For example, maybe
your DB is spending way too much time looking up a user's last login time, even
if each lookup is very fast because of indexing.
'''

setup(
    name='mongotime',
    version=__version__,  # noqa
    description=(
        'Sampling Profiler for Mongo DB - see what the DB spends time on'),
    url='http://github.com/heewa/mongotime',
    download_url='https://github.com/heewa/mongotime/archive/v0.1.0.tar.gz',
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
    tests_require=[
        'pytest',
        'tox',
    ],
    long_description=LONG_DESC)
