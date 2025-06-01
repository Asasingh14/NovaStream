"""
Unit tests for example scripts in the examples directory.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory to sys.path to allow importing from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestBasicUsageExample(unittest.TestCase):
    """Tests for the basic_usage.py example script."""
    
    @patch('src.run_download')
    def test_basic_usage_script(self, mock_run_download):
        """Test that the basic_usage.py example script calls run_download with the correct parameters."""
        # Import the example script's main function
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'examples')))
        from basic_usage import main
        
        # Run the main function
        main()
        
        # Assert that run_download was called with the correct parameters
        mock_run_download.assert_called_once_with(
            url="https://example.com/show",
            name_input="MyDrama",
            base_output="downloads",
            download_all=True,
            episode_list="",
            workers=4
        )