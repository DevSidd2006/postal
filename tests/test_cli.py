import tempfile
import unittest
from importlib.metadata import version
from pathlib import Path
from unittest.mock import patch

from config.loader import save_model_name

from click.testing import CliRunner

from main import main


class PostalCliTests(unittest.TestCase):
    def test_version_reports_installed_package_version(self):
        result = CliRunner().invoke(main, ["--version"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn(f"postal, version {version('postalcli')}", result.output)


class ModelConfigPersistenceTests(unittest.TestCase):
    def test_save_model_name_updates_existing_model_section(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text("max_turns = 5\n\n[model]\nname = \"old/model\"\ntemperature = 1\n", encoding="utf-8")

            with patch("config.loader.get_system_config_path", return_value=path), patch(
                "config.loader._get_project_config", return_value=None
            ):
                save_model_name("new/model")

            self.assertIn('name = "new/model"', path.read_text(encoding="utf-8"))
            self.assertIn("temperature = 1", path.read_text(encoding="utf-8"))

    def test_save_model_name_creates_missing_config(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "config.toml"

            with patch("config.loader.get_system_config_path", return_value=path), patch(
                "config.loader._get_project_config", return_value=None
            ):
                save_model_name("new/model")

            self.assertIn('[model]\nname = "new/model"', path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
