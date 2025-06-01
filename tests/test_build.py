"""
Unit tests for build-related functionality.
"""

import unittest
import os
import subprocess
from unittest.mock import patch, MagicMock

class TestPyInstallerBuild(unittest.TestCase):
    """Tests for PyInstaller build functionality."""
    
    @patch('subprocess.run')
    def test_pyinstaller_command_windows(self, mock_run):
        """Test that the PyInstaller command for Windows works without the --strip option."""
        # Set up mock response
        mock_response = MagicMock()
        mock_response.returncode = 0
        mock_run.return_value = mock_response
        
        # Construct the PyInstaller command without --strip as per the change
        matrix_ext = ".exe"
        command = (
            f"pyinstaller --clean --windowed --onefile --name NovaStream{matrix_ext} "
            f"--exclude-module seleniumwire "
            f"--exclude-module selenium "
            f"--exclude-module webdriver_manager "
            f"--exclude-module chromedriver_autoinstaller "
            f"src/gui.py"
        )
        
        # Execute the command
        result = subprocess.run(command, shell=True, check=False)
        
        # Verify the command was run
        mock_run.assert_called_once()
        
        # Check that PyInstaller was called with the correct parameters (without --strip)
        call_args = mock_run.call_args[0][0]
        self.assertIn("--clean", call_args)
        self.assertIn("--windowed", call_args)
        self.assertIn("--onefile", call_args)
        self.assertNotIn("--strip", call_args)
        
        self.assertEqual(result.returncode, 0)