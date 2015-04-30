import sys

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', 'Arguments to pass to py.test')]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        sys.exit(pytest.main(self.pytest_args))


setup(
    name='alho-py',
    version='0.1',
    packages=find_packages(exclude=['tests', 'env']),
    test_suite='tests',
    install_requires=[
    ],
    tests_require=[
        'pytest>=2.6.1',
    ],
    cmdclass={'test': PyTest},
)
