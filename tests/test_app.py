# pylint: disable=no-self-use

from unittest import TestCase

from click.testing import CliRunner

from mongotime.app import cli


class TestApp(TestCase):
    def invoke(self, args=None, **kwargs):
        runner = CliRunner()
        result = runner.invoke(cli, args, **kwargs)
        return result.exit_code, result.output

    def test_bare(self):
        exit_code, output = self.invoke()
        assert exit_code == 0
        assert 'Usage' in output
