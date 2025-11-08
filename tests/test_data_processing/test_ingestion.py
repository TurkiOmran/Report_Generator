"""Unit tests for data ingestion module"""
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from data_processing.ingestion import (
    DataIngestion,
    MissingColumnsError,
    DataValidationError,
    FileFormatError
)


# Fixtures
@pytest.fixture
def fixtures_dir():
    """Return path to fixtures directory"""
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def ingestion():
    """Return DataIngestion instance"""
    return DataIngestion()


class TestDataIngestionValidCases:
    """Test successful data ingestion scenarios"""
    
    def test_load_valid_csv(self, ingestion, fixtures_dir):
        """Test loading a valid CSV file"""
        filepath = fixtures_dir / "valid_power_profile.csv"
        df, action_idx, warnings = ingestion.load_csv(filepath)
        
        # Verify DataFrame structure
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        
        # Verify columns were standardized
        expected_cols = ['seconds', 'mode_power', 'summary_wattage',
                        'temp_hash_board_max', 'psu_temp_max', 'outage']
        assert all(col in df.columns for col in expected_cols)
        
        # Verify data types
        assert pd.api.types.is_numeric_dtype(df['seconds'])
        assert pd.api.types.is_numeric_dtype(df['mode_power'])
        assert pd.api.types.is_numeric_dtype(df['summary_wattage'])
        assert df['outage'].dtype == 'bool'
        
        # Verify action index is valid (can be int or numpy integer)
        assert isinstance(action_idx, (int, np.integer))
        assert 0 <= action_idx < len(df)
        assert df.at[action_idx, 'seconds'] >= 0
        
        # Verify sorted by time
        assert df['seconds'].is_monotonic_increasing
    
    def test_action_time_detection(self, ingestion, fixtures_dir):
        """Test that action time is correctly identified"""
        filepath = fixtures_dir / "valid_power_profile.csv"
        df, action_idx, warnings = ingestion.load_csv(filepath)
        
        # Action time should be where seconds crosses 0
        assert df.at[action_idx, 'seconds'] >= 0
        if action_idx > 0:
            assert df.at[action_idx - 1, 'seconds'] < 0
    
    def test_power_transition_detection(self, ingestion, fixtures_dir):
        """Test that power transition is detected at action time"""
        filepath = fixtures_dir / "valid_power_profile.csv"
        df, action_idx, warnings = ingestion.load_csv(filepath)
        
        # Should detect power change from 3600W to 1000W
        if action_idx > 0:
            power_before = df.at[action_idx - 1, 'mode_power']
            power_after = df.at[action_idx, 'mode_power']
            assert power_before != power_after
    
    def test_data_quality_logging(self, ingestion, fixtures_dir):
        """Test that data quality issues are logged"""
        filepath = fixtures_dir / "with_nan_values.csv"
        df, action_idx, warnings = ingestion.load_csv(filepath)
        
        # Should have warnings about NaN values
        assert isinstance(warnings, list)
        # Valid CSV with some NaN should still load successfully
        assert len(df) > 0


class TestDataIngestionErrors:
    """Test error handling scenarios"""
    
    def test_missing_file(self, ingestion):
        """Test error when file doesn't exist"""
        with pytest.raises(FileFormatError) as exc_info:
            ingestion.load_csv(Path("nonexistent_file.csv"))
        
        assert "not found" in str(exc_info.value).lower()
    
    def test_missing_columns(self, ingestion, fixtures_dir):
        """Test error when required columns are missing"""
        filepath = fixtures_dir / "missing_columns.csv"
        
        with pytest.raises(MissingColumnsError) as exc_info:
            ingestion.load_csv(filepath)
        
        error_msg = str(exc_info.value)
        assert "missing required columns" in error_msg.lower()
        # Should mention specific missing columns
        assert "temp" in error_msg.lower() or "outage" in error_msg.lower()
    
    def test_empty_file(self, ingestion, tmp_path):
        """Test error when file is empty"""
        empty_file = tmp_path / "empty.csv"
        empty_file.write_text("")
        
        with pytest.raises(FileFormatError) as exc_info:
            ingestion.load_csv(empty_file)
        
        assert "empty" in str(exc_info.value).lower()
    
    def test_no_action_time(self, ingestion, tmp_path):
        """Test error when no action time (t>=0) exists"""
        # Create CSV with only negative times
        csv_content = """miner.seconds,miner.mode.power,miner.summary.wattage,miner.temp.hash_board_max,miner.psu.temp_max,miner.outage
-60.0,3600,3550.5,65.2,45.3,false
-50.0,3600,3575.2,66.1,46.0,false
-40.0,3600,3562.8,65.8,45.8,false"""
        
        no_action_file = tmp_path / "no_action.csv"
        no_action_file.write_text(csv_content)
        
        with pytest.raises(DataValidationError) as exc_info:
            ingestion.load_csv(no_action_file)
        
        assert "action time" in str(exc_info.value).lower()


class TestDataIngestionTypeConversion:
    """Test type conversion and handling of malformed data"""
    
    def test_invalid_numeric_conversion(self, ingestion, fixtures_dir):
        """Test handling of invalid numeric values"""
        filepath = fixtures_dir / "invalid_types.csv"
        df, action_idx, warnings = ingestion.load_csv(filepath)
        
        # Should convert invalid values to NaN
        assert df['mode_power'].isna().sum() > 0
        assert df['summary_wattage'].isna().sum() > 0
        
        # Should have warnings about conversions
        assert len(warnings) > 0
        assert any("NaN" in w for w in warnings)
    
    def test_boolean_conversion(self, ingestion, fixtures_dir):
        """Test conversion of various boolean representations"""
        filepath = fixtures_dir / "with_nan_values.csv"
        df, action_idx, warnings = ingestion.load_csv(filepath)
        
        # Outage column should be boolean
        assert df['outage'].dtype == 'bool'
        # Should handle 0/1 representations
        assert df['outage'].isin([True, False]).all()
    
    def test_nan_handling(self, ingestion, fixtures_dir):
        """Test that NaN values are preserved appropriately"""
        filepath = fixtures_dir / "with_nan_values.csv"
        df, action_idx, warnings = ingestion.load_csv(filepath)
        
        # NaN values should be preserved in numeric columns
        assert df['summary_wattage'].isna().any()
        assert df['temp_hash_board_max'].isna().any()
        assert df['psu_temp_max'].isna().any()


class TestDataIngestionColumnValidation:
    """Test column validation logic"""
    
    def test_column_names_standardized(self, ingestion, fixtures_dir):
        """Test that column names are properly standardized"""
        filepath = fixtures_dir / "valid_power_profile.csv"
        df, action_idx, warnings = ingestion.load_csv(filepath)
        
        # Original names should be gone
        assert 'miner.seconds' not in df.columns
        assert 'miner.mode.power' not in df.columns
        
        # Standardized names should be present
        assert 'seconds' in df.columns
        assert 'mode_power' in df.columns
        assert 'summary_wattage' in df.columns
    
    def test_all_required_columns_validated(self, ingestion):
        """Test that all required columns are checked"""
        required = ingestion.REQUIRED_COLUMNS
        
        # Should have all 6 required columns
        assert len(required) == 6
        assert 'miner.seconds' in required
        assert 'miner.mode.power' in required
        assert 'miner.summary.wattage' in required
        assert 'miner.temp.hash_board_max' in required
        assert 'miner.psu.temp_max' in required
        assert 'miner.outage' in required


class TestDataIngestionSorting:
    """Test data sorting functionality"""
    
    def test_data_sorted_by_time(self, ingestion, tmp_path):
        """Test that data is sorted by seconds column"""
        # Create CSV with unsorted times
        csv_content = """miner.seconds,miner.mode.power,miner.summary.wattage,miner.temp.hash_board_max,miner.psu.temp_max,miner.outage
20.0,1000,1525.3,66.5,47.0,false
-60.0,3600,3550.5,65.2,45.3,false
10.0,1000,2850.5,68.0,48.5,false
-50.0,3600,3575.2,66.1,46.0,false
0.0,1000,3598.2,67.8,47.2,false"""
        
        unsorted_file = tmp_path / "unsorted.csv"
        unsorted_file.write_text(csv_content)
        
        df, action_idx, warnings = ingestion.load_csv(unsorted_file)
        
        # Should be sorted by time
        assert df['seconds'].is_monotonic_increasing
        
        # First row should have most negative time
        assert df.iloc[0]['seconds'] == -60.0
        # Last row should have most positive time
        assert df.iloc[-1]['seconds'] == 20.0

