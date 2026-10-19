"""Region settings contain no discontinued application groups."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bot.route_settings import TASHKENT_KEYS, destination, read_settings, settings_path, save_settings


class RouteSettingsTests(unittest.TestCase):
    def test_routes_and_legacy_settings(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'PERSIST_DIR': folder}):
            save_settings({'TASHKENT_DRIVER_GROUP_1': '-1001', 'TASHKENT_BRAND_GROUP': '-1002'})
            self.assertEqual(destination(TASHKENT_KEYS['brand']), '-1002')
            path = settings_path()
            path.write_text('{"TASHKENT_BRAND_GROUP":"-1002","TASHKENT_SPECTRE_GROUP":"-1003"}')
            self.assertEqual(read_settings(), {'TASHKENT_BRAND_GROUP': '-1002'})
            self.assertNotIn('spectre', TASHKENT_KEYS)
