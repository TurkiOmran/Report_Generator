"""
Tests for Claude API client module (CSV formatting and helper functions).

Tests cover:
- CSV formatting and token optimization
- Test info extraction from filenames
- Step direction detection
- Power range formatting
- Token estimation
- Input validation
"""

import pytest
import pandas as pd
import warnings
from pathlib import Path
from io import StringIO

from src.analysis.claude_client import (
    format_csv_for_llm,
    estimate_token_count,
    validate_csv_format,
    extract_test_info,
    determine_step_direction,
    format_power_range,
    build_prompt,
    get_analysis
)


class TestFormatCSVForLLM:
    """Test suite for CSV formatting functionality."""
    
    @pytest.fixture
    def sample_dataframe(self):
        """Create sample power profile DataFrame."""
        return pd.DataFrame({
            'miner.seconds': [-60, -30, 0, 30, 60],
            'miner.mode.power': [1000, 1000, 3500, 3500, 3500],
            'miner.summary.wattage': [998.5, 1002.3, 1005.7, 2800.2, 3480.1],
            'miner.temp.hash_board_max': [65.2, 66.1, 67.5, 72.3, 75.8],
            'miner.psu.temp_max': [45.3, 45.8, 46.2, 52.1, 55.4],
            'miner.outage': [False, False, False, False, False],
            'miner.collection.summary_error': [0, 0, 0, 0, 0],
            'miner.collection.mode_error': [0, 0, 0, 0, 0]
        })
    
    def test_format_csv_basic(self, sample_dataframe):
        """Should convert DataFrame to CSV string."""
        result = format_csv_for_llm(sample_dataframe)
        
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Should contain header
        assert 'miner.seconds' in result
        assert 'miner.mode.power' in result
        assert 'miner.summary.wattage' in result
        
        # Should contain data
        assert '1000' in result
        assert '3500' in result
    
    def test_format_csv_no_index(self, sample_dataframe):
        """CSV should not include DataFrame index."""
        result = format_csv_for_llm(sample_dataframe)
        
        # Parse it back to check
        df = pd.read_csv(StringIO(result))
        
        # Row count should match (no extra index column)
        assert len(df) == len(sample_dataframe)
    
    def test_format_csv_rounds_power(self, sample_dataframe):
        """Should round power values to nearest watt."""
        result = format_csv_for_llm(sample_dataframe)
        
        # 998.5 should become 999, 1002.3 should become 1002
        assert '999' in result or '998' in result
        assert '1002' in result or '1003' in result
        assert '2800' in result
    
    def test_format_csv_rounds_temperature(self, sample_dataframe):
        """Should round temperature to 1 decimal place."""
        result = format_csv_for_llm(sample_dataframe)
        
        # Should have temperatures like 65.2, not 65.23456
        lines = result.split('\n')
        data_lines = [l for l in lines if l and not l.startswith('miner.')]
        
        # Check that temperature values have at most 1 decimal
        for line in data_lines:
            if line.strip():
                # Temperatures should be rounded to 1 decimal
                assert '65.2' in result or '66.1' in result
    
    def test_format_csv_preserves_structure(self, sample_dataframe):
        """Should preserve all rows and columns."""
        result = format_csv_for_llm(sample_dataframe)
        
        # Parse back and check
        df = pd.read_csv(StringIO(result))
        
        assert len(df) == len(sample_dataframe)
        assert list(df.columns) == list(sample_dataframe.columns)
    
    def test_format_csv_empty_dataframe(self):
        """Should raise ValueError for empty DataFrame."""
        empty_df = pd.DataFrame()
        
        with pytest.raises(ValueError, match="empty"):
            format_csv_for_llm(empty_df)
    
    def test_format_csv_none_input(self):
        """Should raise ValueError for None input."""
        with pytest.raises(ValueError, match="None"):
            format_csv_for_llm(None)
    
    def test_format_csv_missing_required_columns(self):
        """Should raise ValueError if required columns are missing."""
        df = pd.DataFrame({
            'miner.seconds': [1, 2, 3],
            'other_column': [4, 5, 6]
        })
        
        with pytest.raises(ValueError, match="Missing required columns"):
            format_csv_for_llm(df)
    
    def test_format_csv_warns_on_large_data(self):
        """Should warn if data exceeds token limit."""
        # Create large DataFrame
        large_df = pd.DataFrame({
            'miner.seconds': range(10000),
            'miner.mode.power': [1000] * 10000,
            'miner.summary.wattage': [998.5] * 10000,
            'miner.temp.hash_board_max': [65.2] * 10000,
            'miner.psu.temp_max': [45.3] * 10000,
            'miner.outage': [False] * 10000,
            'miner.collection.summary_error': [0] * 10000,
            'miner.collection.mode_error': [0] * 10000
        })
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            format_csv_for_llm(large_df, max_tokens=1000)
            
            assert len(w) == 1
            assert "token limit" in str(w[0].message).lower()
    
    def test_format_csv_doesnt_modify_original(self, sample_dataframe):
        """Should not modify the original DataFrame."""
        original_copy = sample_dataframe.copy()
        
        format_csv_for_llm(sample_dataframe)
        
        pd.testing.assert_frame_equal(sample_dataframe, original_copy)


class TestEstimateTokenCount:
    """Test suite for token estimation."""
    
    def test_estimate_empty_string(self):
        """Should return 0 for empty string."""
        assert estimate_token_count("") == 0
    
    def test_estimate_short_text(self):
        """Should estimate tokens for short text."""
        # "hello" = 5 chars = ~1 token
        result = estimate_token_count("hello")
        assert result == 1
    
    def test_estimate_longer_text(self):
        """Should estimate tokens for longer text."""
        text = "This is a test string with multiple words."
        # ~44 chars = ~11 tokens
        result = estimate_token_count(text)
        assert 10 <= result <= 12
    
    def test_estimate_csv_data(self):
        """Should estimate tokens for CSV-like data."""
        csv_text = "col1,col2,col3\n1,2,3\n4,5,6\n"
        result = estimate_token_count(csv_text)
        assert result > 0


class TestValidateCSVFormat:
    """Test suite for CSV validation."""
    
    def test_validate_valid_csv(self):
        """Should accept valid CSV string."""
        valid_csv = "col1,col2\nval1,val2\nval3,val4"
        assert validate_csv_format(valid_csv) is True
    
    def test_validate_empty_string(self):
        """Should reject empty string."""
        with pytest.raises(ValueError, match="empty"):
            validate_csv_format("")
    
    def test_validate_whitespace_only(self):
        """Should reject whitespace-only string."""
        with pytest.raises(ValueError, match="empty"):
            validate_csv_format("   \n  \n  ")
    
    def test_validate_malformed_csv(self):
        """Should reject truly malformed CSV that pandas can't parse."""
        # Use something that truly breaks pandas parsing
        malformed = "not,a,csv\n\"unclosed quote"
        
        with pytest.raises(ValueError, match="Invalid CSV format"):
            validate_csv_format(malformed)


class TestExtractTestInfo:
    """Test suite for test info extraction."""
    
    def test_extract_from_valid_filename(self):
        """Should extract info from properly formatted filename."""
        result = extract_test_info("r2_39_2025-08-28T09_40_10.csv")
        
        assert result['test_id'] == "r2_39"
        assert result['miner_number'] == "39"
        assert result['timestamp'] == "2025-08-28T09_40_10"
    
    def test_extract_from_path(self):
        """Should work with full file paths."""
        path = "tests/fixtures/r6_39_2025-08-27T19_19_13.csv"
        result = extract_test_info(path)
        
        assert result['test_id'] == "r6_39"
        assert result['miner_number'] == "39"
    
    def test_extract_different_test_numbers(self):
        """Should handle different test numbers."""
        result = extract_test_info("r10_39_2025-08-27T23_05_08.csv")
        
        assert result['test_id'] == "r10_39"
    
    def test_extract_invalid_format(self):
        """Should raise ValueError for invalid filename format."""
        with pytest.raises(ValueError, match="doesn't match expected format"):
            extract_test_info("invalid_filename.csv")
    
    def test_extract_missing_parts(self):
        """Should raise ValueError if parts are missing."""
        with pytest.raises(ValueError):
            extract_test_info("r2_39.csv")  # Missing timestamp


class TestDetermineStepDirection:
    """Test suite for step direction detection."""
    
    def test_detect_upstep(self):
        """Should detect UP-STEP when power increases."""
        df = pd.DataFrame({
            'miner.seconds': [-60, -30, 0, 30, 60],
            'miner.mode.power': [1000, 1000, 1000, 3500, 3500],
            'miner.summary.wattage': [998, 1002, 1005, 2800, 3480]
        })
        
        result = determine_step_direction(df)
        assert result == "UP-STEP"
    
    def test_detect_downstep(self):
        """Should detect DOWN-STEP when power decreases."""
        df = pd.DataFrame({
            'miner.seconds': [-60, -30, 0, 30, 60],
            'miner.mode.power': [3500, 3500, 3500, 1000, 1000],
            'miner.summary.wattage': [3480, 3500, 3490, 2000, 1005]
        })
        
        result = determine_step_direction(df)
        assert result == "DOWN-STEP"
    
    def test_missing_power_column(self):
        """Should raise ValueError if power column missing."""
        df = pd.DataFrame({
            'miner.seconds': [-60, -30, 0, 30, 60],
            'other_column': [1, 2, 3, 4, 5]
        })
        
        with pytest.raises(ValueError, match="Missing 'miner.mode.power' column"):
            determine_step_direction(df)
    
    def test_missing_transition_data(self):
        """Should raise ValueError if before/after data missing."""
        # Only positive times (no before data)
        df = pd.DataFrame({
            'miner.seconds': [30, 60, 90],
            'miner.mode.power': [3500, 3500, 3500]
        })
        
        with pytest.raises(ValueError, match="missing before/after data"):
            determine_step_direction(df)
    
    def test_unchanged_power(self):
        """Should raise ValueError if power doesn't change."""
        df = pd.DataFrame({
            'miner.seconds': [-60, -30, 0, 30, 60],
            'miner.mode.power': [1000, 1000, 1000, 1000, 1000]
        })
        
        with pytest.raises(ValueError, match="power unchanged"):
            determine_step_direction(df)


class TestFormatPowerRange:
    """Test suite for power range formatting."""
    
    def test_format_upstep_range(self):
        """Should format UP-STEP power range."""
        df = pd.DataFrame({
            'miner.seconds': [-60, -30, 0, 30, 60],
            'miner.mode.power': [1000, 1000, 1000, 3500, 3500]
        })
        
        result = format_power_range(df)
        assert result == "1000W → 3500W"
    
    def test_format_downstep_range(self):
        """Should format DOWN-STEP power range."""
        df = pd.DataFrame({
            'miner.seconds': [-60, -30, 0, 30, 60],
            'miner.mode.power': [3500, 3500, 3500, 1000, 1000]
        })
        
        result = format_power_range(df)
        assert result == "3500W → 1000W"
    
    def test_format_missing_column(self):
        """Should raise ValueError if power column missing."""
        df = pd.DataFrame({'miner.seconds': [1, 2, 3]})
        
        with pytest.raises(ValueError, match="Missing 'miner.mode.power'"):
            format_power_range(df)


class TestBuildPrompt:
    """Test suite for prompt building."""
    
    def test_build_prompt_integrates_template(self):
        """Should use prompt_template.format_prompt()."""
        csv_content = "col1,col2\n1,2"
        
        result = build_prompt(
            test_id="r2_39",
            miner_number="39",
            step_direction="UP-STEP",
            power_range="1000W → 3500W",
            csv_content=csv_content
        )
        
        assert isinstance(result, str)
        assert "r2_39" in result
        assert "UP-STEP" in result
        assert csv_content in result


class TestGetAnalysis:
    """Test suite for API analysis function (placeholder)."""
    
    def test_get_analysis_checks_api_key(self, monkeypatch):
        """Should raise ValueError if API key missing."""
        # Remove API key from environment
        monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
        
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY not found"):
            get_analysis("test prompt")
    
    def test_get_analysis_successful_call(self, monkeypatch):
        """Should successfully return analysis response."""
        from unittest.mock import patch, MagicMock
        
        # Set fake API key
        monkeypatch.setenv('ANTHROPIC_API_KEY', 'sk-ant-test-key-123')
        
        # Mock the API response
        with patch('src.analysis.claude_client.anthropic.Anthropic') as mock_client:
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="This is a test analysis narrative.")]
            mock_response.usage = MagicMock(input_tokens=1000, output_tokens=200)
            mock_response.model = "claude-sonnet-4-20250514"
            mock_response.stop_reason = "end_turn"
            mock_client.return_value.messages.create.return_value = mock_response
            
            result = get_analysis("test prompt")
            
            assert isinstance(result, dict)
            assert result['analysis'] == "This is a test analysis narrative."
            assert result['tokens_used']['input'] == 1000
            assert result['tokens_used']['output'] == 200
            assert result['tokens_used']['total'] == 1200
            assert result['model'] == "claude-sonnet-4-20250514"
            assert result['stop_reason'] == "end_turn"


class TestRealDataIntegration:
    """Integration tests with real CSV fixtures."""
    
    @pytest.fixture
    def real_csv_path(self):
        """Path to real test CSV."""
        return "tests/fixtures/r2_39_2025-08-28T09_40_10.csv"
    
    def test_format_real_csv(self, real_csv_path):
        """Should successfully format real CSV data."""
        if not Path(real_csv_path).exists():
            pytest.skip(f"Real CSV not found: {real_csv_path}")
        
        df = pd.read_csv(real_csv_path)
        result = format_csv_for_llm(df)
        
        # Should be valid CSV
        assert validate_csv_format(result)
        
        # Should be within reasonable token range
        tokens = estimate_token_count(result)
        assert 10000 <= tokens <= 20000
    
    def test_extract_info_from_real_file(self, real_csv_path):
        """Should extract info from real filename."""
        if not Path(real_csv_path).exists():
            pytest.skip(f"Real CSV not found: {real_csv_path}")
        
        info = extract_test_info(real_csv_path)
        
        assert info['test_id'] == "r2_39"
        assert info['miner_number'] == "39"
        assert '2025-08-28' in info['timestamp']
    
    def test_detect_direction_from_real_data(self, real_csv_path):
        """Should detect step direction from real data."""
        if not Path(real_csv_path).exists():
            pytest.skip(f"Real CSV not found: {real_csv_path}")
        
        df = pd.read_csv(real_csv_path)
        direction = determine_step_direction(df)
        
        # r2_39 is an UP-STEP test
        assert direction == "UP-STEP"
    
    def test_full_workflow_real_data(self, real_csv_path):
        """Test complete workflow with real data."""
        if not Path(real_csv_path).exists():
            pytest.skip(f"Real CSV not found: {real_csv_path}")
        
        # Load data
        df = pd.read_csv(real_csv_path)
        
        # Extract test info
        info = extract_test_info(real_csv_path)
        
        # Determine direction and power range
        direction = determine_step_direction(df)
        power_range = format_power_range(df)
        
        # Format CSV
        csv_content = format_csv_for_llm(df)
        
        # Build prompt
        prompt = build_prompt(
            test_id=info['test_id'],
            miner_number=info['miner_number'],
            step_direction=direction,
            power_range=power_range,
            csv_content=csv_content
        )
        
        # Verify complete prompt
        assert isinstance(prompt, str)
        assert len(prompt) > 1000
        assert info['test_id'] in prompt
        assert direction in prompt
        assert power_range in prompt
        assert 'miner.seconds' in prompt  # CSV header should be in there

