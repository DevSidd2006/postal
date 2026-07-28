import unittest
from importlib.metadata import version

from click.testing import CliRunner

from main import main


class PostalCliTests(unittest.TestCase):
    def test_version_reports_installed_package_version(self):
        result = CliRunner().invoke(main, ["--version"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn(f"postal, version {version('postalcli')}", result.output)


if __name__ == "__main__":
    unittest.main()
