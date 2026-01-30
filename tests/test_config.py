#!/usr/bin/env python3
"""
Test suite for config.py
TDD Phase 2: Configuration Module
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestConfig(unittest.TestCase):
    """Test suite for configuration module"""

    def setUp(self):
        """Set up test environment"""
        # Save original env var if exists
        self.original_key = os.environ.get('ANTHROPIC_API_KEY', None)

    def tearDown(self):
        """Clean up test environment"""
        # Restore original env var
        if self.original_key is not None:
            os.environ['ANTHROPIC_API_KEY'] = self.original_key
        elif 'ANTHROPIC_API_KEY' in os.environ:
            del os.environ['ANTHROPIC_API_KEY']

    def test_load_api_key_from_environment(self):
        """Test: Should load API key from environment variable"""
        # This test will FAIL until config.py is implemented
        os.environ['ANTHROPIC_API_KEY'] = 'sk-ant-test123456'

        import config
        api_key = config.get_api_key()

        self.assertEqual(api_key, 'sk-ant-test123456')

    def test_validate_api_key_format_standard(self):
        """Test: Should validate standard Anthropic API key format"""
        os.environ['ANTHROPIC_API_KEY'] = 'sk-ant-test123456'

        import config
        is_valid = config.validate_api_key_format()

        self.assertTrue(is_valid)

    def test_validate_api_key_format_ccswitch_proxy(self):
        """Test: Should accept ccswitch proxy API keys (any non-empty string)"""
        # ccswitch proxy keys may have different formats
        os.environ['ANTHROPIC_API_KEY'] = 'ccswitch-proxy-key-12345'

        import config
        is_valid = config.validate_api_key_format()

        self.assertTrue(is_valid)

    def test_reject_empty_api_key(self):
        """Test: Should reject empty API key"""
        os.environ['ANTHROPIC_API_KEY'] = ''

        import config
        is_valid = config.validate_api_key_format()

        self.assertFalse(is_valid)

    def test_raise_error_on_missing_api_key(self):
        """Test: Should raise clear error when API key is not set"""
        # Remove API key from environment
        if 'ANTHROPIC_API_KEY' in os.environ:
            del os.environ['ANTHROPIC_API_KEY']

        import config

        with self.assertRaises(RuntimeError) as context:
            config.get_api_key()

        self.assertIn('ANTHROPIC_API_KEY', str(context.exception))

    def test_default_model_constants(self):
        """Test: Should have correct default model constants"""
        import config

        self.assertEqual(config.DEFAULT_MODEL, 'claude-3-haiku-20240307')
        self.assertEqual(config.DEFAULT_MAX_TOKENS, 1024)

    def test_model_pricing_dictionary(self):
        """Test: Should have pricing for all Claude 3 models"""
        import config

        self.assertIn('claude-3-haiku-20240307', config.MODEL_PRICING)
        self.assertIn('claude-3-sonnet-20240229', config.MODEL_PRICING)
        self.assertIn('claude-3-opus-20240229', config.MODEL_PRICING)

    def test_calculate_cost_for_haiku(self):
        """Test: Should calculate cost correctly for Haiku"""
        import config

        cost = config.calculate_cost(
            'claude-3-haiku-20240307',
            1000,  # input tokens
            500    # output tokens
        )

        # Haiku: $0.25/1M input, $1.25/1M output
        # Expected: (1000/1M * 0.25) + (500/1M * 1.25)
        # = 0.00025 + 0.000625 = 0.000875
        expected_cost = 0.000875
        self.assertAlmostEqual(cost, expected_cost, places=6)

    def test_calculate_cost_for_sonnet(self):
        """Test: Should calculate cost correctly for Sonnet"""
        import config

        cost = config.calculate_cost(
            'claude-3-sonnet-20240229',
            1000,
            500
        )

        # Sonnet: $3/1M input, $15/1M output
        expected_cost = 0.0105  # 0.003 + 0.0075
        self.assertAlmostEqual(cost, expected_cost, places=6)

    def test_jitter_range_constant(self):
        """Test: Should define jitter range for status updates"""
        import config

        self.assertEqual(config.JITTER_RANGE, (0, 1))


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
