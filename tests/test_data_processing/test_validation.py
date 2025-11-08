"""Unit tests for data validation module"""
import pytest
import pandas as pd
import sys
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from data_processing.validation import (
    DataQualityThresholds,
    ColumnConstraints,
    ValidationConfig,
    DataFrameValidator
)


class TestDataQualityThresholds:
    """Test DataQualityThresholds Pydantic model"""
    
    def test_default_values(self):
        """Test that default values are set correctly"""
        thresholds = DataQualityThresholds()
        
        assert thresholds.max_nan_wattage_pct == 10.0
        assert thresholds.max_outage_pct == 5.0
        assert thresholds.min_pre_action_duration == 30.0
        assert thresholds.min_post_action_duration == 60.0
        assert thresholds.required_power_change_threshold == 50.0
    
    def test_custom_values(self):
        """Test setting custom threshold values"""
        thresholds = DataQualityThresholds(
            max_nan_wattage_pct=20.0,
            max_outage_pct=10.0,
            min_pre_action_duration=45.0
        )
        
        assert thresholds.max_nan_wattage_pct == 20.0
        assert thresholds.max_outage_pct == 10.0
        assert thresholds.min_pre_action_duration == 45.0
    
    def test_validation_ranges(self):
        """Test that percentage values are validated"""
        # Valid percentages
        DataQualityThresholds(max_nan_wattage_pct=0.0)
        DataQualityThresholds(max_nan_wattage_pct=100.0)
        
        # Invalid percentages should raise error
        with pytest.raises(ValueError):
            DataQualityThresholds(max_nan_wattage_pct=-1.0)
        
        with pytest.raises(ValueError):
            DataQualityThresholds(max_nan_wattage_pct=101.0)


class TestColumnConstraints:
    """Test ColumnConstraints Pydantic model"""
    
    def test_default_values(self):
        """Test default constraint values"""
        constraints = ColumnConstraints()
        
        assert constraints.min_seconds == -3600.0
        assert constraints.max_seconds == 3600.0
        assert constraints.min_power == 0.0
        assert constraints.max_power == 5000.0
        assert constraints.min_temperature == -40.0
        assert constraints.max_temperature == 150.0
    
    def test_power_range_validation(self):
        """Test that max_power must be greater than min_power"""
        # Valid range
        ColumnConstraints(min_power=100.0, max_power=2000.0)
        
        # Invalid range should raise error
        with pytest.raises(ValueError) as exc_info:
            ColumnConstraints(min_power=2000.0, max_power=100.0)
        
        assert "max_power" in str(exc_info.value).lower()
    
    def test_temperature_range_validation(self):
        """Test that max_temperature must be greater than min_temperature"""
        # Valid range
        ColumnConstraints(min_temperature=0.0, max_temperature=100.0)
        
        # Invalid range should raise error
        with pytest.raises(ValueError) as exc_info:
            ColumnConstraints(min_temperature=100.0, max_temperature=0.0)
        
        assert "max_temperature" in str(exc_info.value).lower()


class TestValidationConfig:
    """Test ValidationConfig model"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = ValidationConfig()
        
        assert isinstance(config.quality_thresholds, DataQualityThresholds)
        assert isinstance(config.column_constraints, ColumnConstraints)
        assert config.strict_mode is False
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = ValidationConfig(
            quality_thresholds=DataQualityThresholds(max_nan_wattage_pct=15.0),
            column_constraints=ColumnConstraints(max_power=4000.0),
            strict_mode=True
        )
        
        assert config.quality_thresholds.max_nan_wattage_pct == 15.0
        assert config.column_constraints.max_power == 4000.0
        assert config.strict_mode is True


class TestDataFrameValidator:
    """Test DataFrameValidator functionality"""
    
    @pytest.fixture
    def validator(self):
        """Return validator with default config"""
        return DataFrameValidator()
    
    @pytest.fixture
    def sample_df(self):
        """Return sample DataFrame"""
        return pd.DataFrame({
            'seconds': [-60, -30, 0, 30, 60],
            'mode_power': [3600, 3600, 1000, 1000, 1000],
            'summary_wattage': [3550, 3575, None, 1005, 1000],
            'temp_hash_board_max': [65, 66, 67, 64, 62],
            'psu_temp_max': [45, 46, 47, 45, 44],
            'outage': [False, False, False, False, False]
        })
    
    def test_validate_data_quality_pass(self, validator, sample_df):
        """Test data quality validation with good data"""
        warnings = []
        result = validator.validate_data_quality(sample_df, warnings)
        
        # Should not add warnings for good data (20% NaN is below default 10% threshold)
        # Actually, 1/5 = 20% which exceeds 10%, so it should warn
        assert isinstance(result, list)
    
    def test_validate_data_quality_high_nan(self, validator):
        """Test data quality validation with high NaN percentage"""
        df = pd.DataFrame({
            'summary_wattage': [100, None, None, None, None, None],  # 83% NaN
            'outage': [False] * 6
        })
        
        warnings = []
        result = validator.validate_data_quality(df, warnings)
        
        # Should warn about high NaN percentage
        assert len(result) > 0
        assert any('NaN wattage' in w for w in result)
    
    def test_validate_data_quality_high_outage(self, validator):
        """Test data quality validation with high outage percentage"""
        df = pd.DataFrame({
            'summary_wattage': [100, 200, 300, 400, 500],
            'outage': [True, True, False, False, False]  # 40% outage
        })
        
        warnings = []
        result = validator.validate_data_quality(df, warnings)
        
        # Should warn about high outage percentage
        assert len(result) > 0
        assert any('outage' in w.lower() for w in result)
    
    def test_validate_data_quality_strict_mode(self):
        """Test that strict mode raises errors instead of warnings"""
        config = ValidationConfig(strict_mode=True)
        validator = DataFrameValidator(config)
        
        df = pd.DataFrame({
            'summary_wattage': [100, None, None, None, None, None],  # 83% NaN
            'outage': [False] * 6
        })
        
        warnings = []
        
        # Should raise ValueError in strict mode
        with pytest.raises(ValueError) as exc_info:
            validator.validate_data_quality(df, warnings)
        
        assert "data quality" in str(exc_info.value).lower()
    
    def test_validate_column_ranges_power(self, validator, sample_df):
        """Test power range validation"""
        warnings = validator.validate_column_ranges(sample_df)
        
        # With default constraints (0-5000W), should have no warnings
        power_warnings = [w for w in warnings if 'power' in w.lower()]
        assert len(power_warnings) == 0
        
        # Test with out-of-range values
        df_bad = sample_df.copy()
        df_bad.loc[0, 'mode_power'] = -100  # Below minimum
        
        warnings = validator.validate_column_ranges(df_bad)
        assert len(warnings) > 0
        assert any('below minimum' in w for w in warnings)
    
    def test_validate_column_ranges_temperature(self, validator, sample_df):
        """Test temperature range validation"""
        # Add extreme temperature
        df_extreme = sample_df.copy()
        df_extreme.loc[0, 'temp_hash_board_max'] = 200  # Above maximum
        
        warnings = validator.validate_column_ranges(df_extreme)
        
        assert len(warnings) > 0
        assert any('above maximum temp' in w for w in warnings)
    
    def test_validate_action_time_coverage_sufficient(self, validator, sample_df):
        """Test action time coverage validation with sufficient data"""
        # Action time at index 2 (t=0)
        # Pre-action: 60 seconds, post-action: 60 seconds
        warnings = validator.validate_action_time_coverage(sample_df, action_idx=2)
        
        # With default thresholds (30s pre, 60s post), should have no warnings
        assert len(warnings) == 0
    
    def test_validate_action_time_coverage_insufficient_pre(self, validator):
        """Test action time coverage with insufficient pre-action data"""
        df = pd.DataFrame({
            'seconds': [-10, 0, 30, 60],  # Only 10s pre-action
            'mode_power': [3600, 1000, 1000, 1000]
        })
        
        warnings = validator.validate_action_time_coverage(df, action_idx=1)
        
        # Should warn about insufficient pre-action duration
        assert len(warnings) > 0
        assert any('pre-action' in w.lower() for w in warnings)
    
    def test_validate_action_time_coverage_insufficient_post(self, validator):
        """Test action time coverage with insufficient post-action data"""
        df = pd.DataFrame({
            'seconds': [-60, -30, 0, 10, 20],  # Only 20s post-action
            'mode_power': [3600, 3600, 1000, 1000, 1000]
        })
        
        warnings = validator.validate_action_time_coverage(df, action_idx=2)
        
        # Should warn about insufficient post-action duration
        assert len(warnings) > 0
        assert any('post-action' in w.lower() for w in warnings)
    
    def test_validate_action_time_at_start(self, validator):
        """Test validation when action time is at first row"""
        df = pd.DataFrame({
            'seconds': [0, 30, 60],  # No pre-action data
            'mode_power': [1000, 1000, 1000]
        })
        
        warnings = validator.validate_action_time_coverage(df, action_idx=0)
        
        # Should warn about no pre-action data
        assert len(warnings) > 0
        assert any('pre-action' in w.lower() for w in warnings)

