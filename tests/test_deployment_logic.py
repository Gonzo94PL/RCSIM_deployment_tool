# -*- coding: utf-8 -*-
import os
import unittest
from unittest.mock import MagicMock, patch

from core.deployment_logic import (create_project_archive,
                                      generate_mediamtx_config,
                                      get_setup_script,
                                      strip_ansi_codes)


class TestDeploymentLogic(unittest.TestCase):
    def test_strip_ansi_codes(self):
        text_with_ansi = "\x1b[31mError:\x1b[0m Something went wrong"
        expected = "Error: Something went wrong"
        self.assertEqual(strip_ansi_codes(text_with_ansi), expected)

    def test_generate_mediamtx_config(self):
        config = generate_mediamtx_config(
            width=1280, height=720, fps=60, bitrate=2000000
        )
        self.assertIn("rpiCameraWidth: 1280", config)
        self.assertIn("rpiCameraHeight: 720", config)
        self.assertIn("rpiCameraFPS: 60", config)
        self.assertIn("rpiCameraBitrate: 2000000", config)

    def test_get_setup_script(self):
        script = get_setup_script(
            user="pi", home="/home/pi", new_pass="secret", camera_port="cam1"
        )
        self.assertIn('USER_NAME="pi"', script)
        self.assertIn('NEW_SSH_PASS="secret"', script)
        self.assertIn('CAMERA_PORT="cam1"', script)
        self.assertIn("imx219,$CAMERA_PORT", script)

    @patch("shutil.rmtree")
    @patch("os.makedirs")
    @patch("shutil.copytree")
    @patch("shutil.make_archive")
    @patch("os.path.isdir")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=unittest.mock.mock_open, read_data="{}")
    def test_create_project_archive(
        self,
        mock_open,
        mock_exists,
        mock_isdir,
        mock_make_archive,
        mock_copytree,
        mock_makedirs,
        mock_rmtree,
    ):
        mock_isdir.return_value = True
        mock_exists.return_value = False  # config.json does not exist

        log_func = MagicMock()
        gettext_func = MagicMock(side_effect=lambda x: x)

        payload = {
            "hardware": {},
            "camera": {"resolution": [1920, 1080], "fps": 30, "bitrate": 5000000},
        }

        result = create_project_archive(
            log_func=log_func,
            gettext_func=gettext_func,
            project_source_dir="/source",
            pc_tailscale_ip="100.64.0.1",
            use_rtk=False,
            ntrip_user="",
            ntrip_pass="",
            ntrip_host="",
            ntrip_port="0",
            ntrip_mount="",
            full_config_payload=payload,
        )

        self.assertTrue(mock_make_archive.called)
        self.assertTrue(mock_copytree.called)
        # Check if config.json was written
        mock_open.assert_any_call(
            os.path.join("temp_deploy", "project_content", "config.json"),
            "w",
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
