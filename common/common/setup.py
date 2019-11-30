import sys
import re
from setuptools import setup, find_packages


def get_version():
    return "0.1.0"


def readme():
    ''' Returns README.rst contents as str '''
    return ""


install_requires = [
    'browsermob-proxy==0.8.0',
    'scrapy>=1.5.0',
    'selenium==3.141.0',
    'six>=1.4.1',
]

lint_requires = [
    'pep8',
    'pyflakes'
]

tests_require = [
    # 'mock==2.0.0',
    # 'testfixtures==4.13.5'
]

dependency_links = []
setup_requires = []
extras_require = {
    'test': tests_require,
    'all': install_requires + tests_require,
    'docs': ['sphinx'] + tests_require,
    'lint': lint_requires
}

if 'nosetests' in sys.argv[1:]:
    setup_requires.append('nose')

setup(
    name='common',
    version=get_version(),
    description='Knwldg common scripts',
    long_description=readme(),
    license='MIT',
    packages=find_packages(),
    package_data={},
    install_requires=install_requires,
    tests_require=tests_require,
    setup_requires=setup_requires,
    extras_require=extras_require,
    dependency_links=dependency_links,
    zip_safe=True,
    include_package_data=True,
)
