"""Unit tests for data preprocessing module"""
import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from data_processing.preprocessing import DataPreprocessor


# Fixtures
@pytest.fixture
def sample_normal_data():
    """Sample data with normal power transition"""
    return pd.DataFrame({
        'seconds': [-60, -30, -10, 0, 10, 30, 60, 90],
        'mode_power': [3600, 3600, 3600, 1000, 1000, 1000, 1000, 1000],
        'summary_wattage': [3550, 3575, 3595, 3598, 2850, 1045, 1000, 1002],
        'temp_hash_board_max': [65, 66, 67, 68, 66, 64, 62, 60],
        'psu_temp_max': [45, 46, 47, 48, 47, 45, 44, 43],
        'outage': [False] * 8
    })


@pytest.fixture
def sample_data_with_nan():
    """Sample data with NaN segments"""
    return pd.DataFrame({
        'seconds': [-60, -30, 0, 10, 20, 30, 40, 50],
        'mode_power': [3600, 3600, 1000, 1000, 1000, 1000, 1000, 1000],
        'summary_wattage': [3550, None, 3598, 2850, None, None, None, 1000],
        'temp_hash_board_max': [65, 66, 67, 68, 66, 64, 62, 60],
        'psu_temp_max': [45, 46, 47, 48, 47, 45, 44, 43],
        'outage': [False] * 8
    })


@pytest.fixture
def sample_data_with_outages():
    """Sample data with outages"""
    return pd.DataFrame({
        'seconds': [-60, -30, 0, 10, 20, 30, 40, 50],
        'mode_power': [3600, 3600, 1000, 1000, 1000, 1000, 1000, 1000],
        'summary_wattage': [3550, 3575, 3598, 2850, 1045, 1000, 1002, 1005],
        'temp_hash_board_max': [65, 66, 67, 68, 66, 64, 62, 60],
        'psu_temp_max': [45, 46, 47, 48, 47, 45, 44, 43],
        'outage': [False, True, False, False, True, True, False, False]
    })


@pytest.fixture
def sample_data_with_gaps():
    """Sample data with large time gaps"""
    return pd.DataFrame({
        'seconds': [-60, -30, 0, 10, 25, 55, 85, 115],  # Gaps of 15, 30, 30 seconds
        'mode_power': [3600, 3600, 1000, 1000, 1000, 1000, 1000, 1000],
        'summary_wattage': [3550, 3575, 3598, 2850, 1045, 1000, 1002, 1005],
        'temp_hash_board_max': [65, 66, 67, 68, 66, 64, 62, 60],
        'psu_temp_max': [45, 46, 47, 48, 47, 45, 44, 43],
        'outage': [False] * 8
    })


class TestDataPreprocessorInit:
    """Test DataPreprocessor initialization"""
    
    def test_init_basic(self, sample_normal_data):
        """Test basic initialization"""
        preprocessor = DataPreprocessor(sample_normal_data, action_idx=3)
        
        assert len(preprocessor.df) == len(sample_normal_data)
        assert preprocessor.action_idx == 3
        assert 'action_index' in preprocessor.metadata
        assert 'action_time' in preprocessor.metadata
        assert preprocessor.metadata['action_index'] == 3
        assert preprocessor.metadata['action_time'] == 0
    
    def test_init_copies_dataframe(self, sample_normal_data):
        """Test that DataFrame is copied, not referenced"""
        preprocessor = DataPreprocessor(sample_normal_data, action_idx=3)
        
        # Modify preprocessor's df
        preprocessor.df.at[0, 'seconds'] = -999
        
        # Original should be unchanged
        assert sample_normal_data.at[0, 'seconds'] == -60


class TestDataPreprocessorPreprocess:
    """Test full preprocessing pipeline"""
    
    def test_preprocess_returns_tuple(self, sample_normal_data):
        """Test that preprocess returns (df, metadata) tuple"""
        preprocessor = DataPreprocessor(sample_normal_data, action_idx=3)
        result = preprocessor.preprocess()
        
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], pd.DataFrame)
        assert isinstance(result[1], dict)
    
    def test_preprocess_generates_metadata(self, sample_normal_data):
        """Test that preprocess populates comprehensive metadata"""
        preprocessor = DataPreprocessor(sample_normal_data, action_idx=3)
        df, metadata = preprocessor.preprocess()
        
        # Check required metadata fields
        assert 'action_index' in metadata
        assert 'action_time' in metadata
        assert 'total_rows' in metadata
        assert 'pre_action_duration' in metadata
        assert 'post_action_duration' in metadata
        assert 'pre_action_rows' in metadata
        assert 'post_action_rows' in metadata
        assert 'target_power_before' in metadata
        assert 'target_power_after' in metadata
        assert 'power_change' in metadata
        assert 'transition_direction' in metadata


class TestNaNSegmentIdentification:
    """Test NaN segment detection"""
    
    def test_no_nan_segments(self, sample_normal_data):
        """Test with data that has no NaN values"""
        preprocessor = DataPreprocessor(sample_normal_data, action_idx=3)
        preprocessor.preprocess()
        
        assert 'wattage_nan_segments' in preprocessor.metadata
        assert preprocessor.metadata['wattage_nan_segments'] == []
        assert preprocessor.metadata.get('nan_segment_count', 0) == 0
    
    def test_single_nan_segment(self, sample_data_with_nan):
        """Test identification of single NaN segment"""
        preprocessor = DataPreprocessor(sample_data_with_nan, action_idx=2)
        preprocessor.preprocess()
        
        segments = preprocessor.metadata['wattage_nan_segments']
        
        # Should find two segments: [1] and [4,5,6]
        assert len(segments) == 2
        assert (1, 1) in segments  # Single NaN at index 1
        assert (4, 6) in segments  # Three consecutive NaNs at indices 4,5,6
        assert preprocessor.metadata['nan_segment_count'] == 2
    
    def test_nan_segment_at_end(self):
        """Test NaN segment that extends to end of data"""
        df = pd.DataFrame({
            'seconds': [0, 10, 20, 30],
            'mode_power': [1000, 1000, 1000, 1000],
            'summary_wattage': [1000, 1005, None, None],
            'outage': [False] * 4
        })
        
        preprocessor = DataPreprocessor(df, action_idx=0)
        preprocessor.preprocess()
        
        segments = preprocessor.metadata['wattage_nan_segments']
        assert len(segments) == 1
        assert segments[0] == (2, 3)


class TestTimeGapDetection:
    """Test time gap detection"""
    
    def test_no_large_gaps(self):
        """Test with data that has consistent time intervals (< 10s gaps)"""
        # Create data with consistent 5-second intervals (no large gap)
        df = pd.DataFrame({
            'seconds': [-20, -15, -10, -5, 0, 5, 10, 15],
            'mode_power': [3600] * 4 + [1000] * 4,
            'summary_wattage': [3550, 3560, 3570, 3580, 3590, 2800, 1500, 1050],
            'temp_hash_board_max': [65] * 8,
            'psu_temp_max': [45] * 8,
            'outage': [False] * 8
        })
        
        preprocessor = DataPreprocessor(df, action_idx=4)
        preprocessor.preprocess()
        
        assert 'large_time_gaps' in preprocessor.metadata
        assert preprocessor.metadata['large_time_gaps'] == []
        assert 'max_time_gap' in preprocessor.metadata
        assert preprocessor.metadata['max_time_gap'] == 5.0
    
    def test_detect_large_gaps(self, sample_data_with_gaps):
        """Test detection of large time gaps"""
        preprocessor = DataPreprocessor(sample_data_with_gaps, action_idx=2)
        preprocessor.preprocess()
        
        large_gaps = preprocessor.metadata['large_time_gaps']
        
        # Should detect gaps > 10 seconds (15s, 30s, 30s)
        assert len(large_gaps) > 0
        
        # Check that gap values are reasonable
        for idx, gap in large_gaps:
            assert gap > 10
            assert isinstance(idx, int)
            assert isinstance(gap, float)
    
    def test_max_gap_recorded(self, sample_data_with_gaps):
        """Test that maximum gap is recorded"""
        preprocessor = DataPreprocessor(sample_data_with_gaps, action_idx=2)
        preprocessor.preprocess()
        
        max_gap = preprocessor.metadata['max_time_gap']
        assert max_gap == 30.0  # Largest gap in sample data


class TestDurationCalculation:
    """Test duration calculations"""
    
    def test_normal_durations(self, sample_normal_data):
        """Test duration calculation with normal data"""
        preprocessor = DataPreprocessor(sample_normal_data, action_idx=3)
        preprocessor.preprocess()
        
        # Pre-action: from -60 to 0 = 60 seconds
        assert preprocessor.metadata['pre_action_duration'] == 60.0
        # Post-action: from 0 to 90 = 90 seconds
        assert preprocessor.metadata['post_action_duration'] == 90.0
        
        # Row counts
        assert preprocessor.metadata['pre_action_rows'] == 3
        assert preprocessor.metadata['post_action_rows'] == 5  # From index 3 to end
    
    def test_no_pre_action_data(self):
        """Test with no pre-action data (action at index 0)"""
        df = pd.DataFrame({
            'seconds': [0, 10, 20, 30],
            'mode_power': [1000] * 4,
            'summary_wattage': [1000, 1005, 1010, 1008],
            'outage': [False] * 4
        })
        
        preprocessor = DataPreprocessor(df, action_idx=0)
        preprocessor.preprocess()
        
        assert preprocessor.metadata['pre_action_duration'] == 0.0
        assert preprocessor.metadata['pre_action_rows'] == 0
        assert preprocessor.metadata['post_action_duration'] > 0
    
    def test_no_post_action_data(self):
        """Test with no post-action data"""
        df = pd.DataFrame({
            'seconds': [-30, -20, -10],
            'mode_power': [3600] * 3,
            'summary_wattage': [3550, 3575, 3600],
            'outage': [False] * 3
        })
        
        preprocessor = DataPreprocessor(df, action_idx=2)
        preprocessor.preprocess()
        
        assert preprocessor.metadata['pre_action_duration'] > 0
        assert preprocessor.metadata['post_action_duration'] == 0.0


class TestPowerLevelIdentification:
    """Test power level identification"""
    
    def test_power_down_transition(self, sample_normal_data):
        """Test identification of power down transition"""
        preprocessor = DataPreprocessor(sample_normal_data, action_idx=3)
        preprocessor.preprocess()
        
        assert preprocessor.metadata['target_power_before'] == 3600
        assert preprocessor.metadata['target_power_after'] == 1000
        assert preprocessor.metadata['power_change'] == -2600
        assert preprocessor.metadata['transition_direction'] == 'down'
    
    def test_power_up_transition(self):
        """Test identification of power up transition"""
        df = pd.DataFrame({
            'seconds': [-30, -10, 0, 10, 30],
            'mode_power': [1000, 1000, 3600, 3600, 3600],
            'summary_wattage': [1000, 1005, 1010, 2500, 3550],
            'outage': [False] * 5
        })
        
        preprocessor = DataPreprocessor(df, action_idx=2)
        preprocessor.preprocess()
        
        assert preprocessor.metadata['target_power_before'] == 1000
        assert preprocessor.metadata['target_power_after'] == 3600
        assert preprocessor.metadata['power_change'] == 2600
        assert preprocessor.metadata['transition_direction'] == 'up'
    
    def test_no_power_change(self):
        """Test with no power change"""
        df = pd.DataFrame({
            'seconds': [-30, -10, 0, 10, 30],
            'mode_power': [1000] * 5,
            'summary_wattage': [1000, 1005, 1010, 1008, 1002],
            'outage': [False] * 5
        })
        
        preprocessor = DataPreprocessor(df, action_idx=2)
        preprocessor.preprocess()
        
        assert preprocessor.metadata['power_change'] == 0
        assert preprocessor.metadata['transition_direction'] == 'none'


class TestDataSegmentation:
    """Test data segmentation methods"""
    
    def test_get_pre_action_data(self, sample_normal_data):
        """Test getting pre-action data"""
        preprocessor = DataPreprocessor(sample_normal_data, action_idx=3)
        pre_data = preprocessor.get_pre_action_data()
        
        # Should get rows where seconds < 0
        assert len(pre_data) == 3
        assert all(pre_data['seconds'] < 0)
        assert pre_data.at[pre_data.index[0], 'seconds'] == -60
    
    def test_get_post_action_data(self, sample_normal_data):
        """Test getting post-action data"""
        preprocessor = DataPreprocessor(sample_normal_data, action_idx=3)
        post_data = preprocessor.get_post_action_data()
        
        # Should get rows where seconds >= 0
        assert len(post_data) == 5
        assert all(post_data['seconds'] >= 0)
        assert post_data.at[post_data.index[0], 'seconds'] == 0
    
    def test_exclude_outages(self, sample_data_with_outages):
        """Test filtering out outages"""
        preprocessor = DataPreprocessor(sample_data_with_outages, action_idx=2)
        
        # Get pre-action without outages
        pre_data = preprocessor.get_pre_action_data(exclude_outages=True)
        assert len(pre_data) == 1  # Only 1 row without outage before t=0
        
        # Get post-action without outages
        post_data = preprocessor.get_post_action_data(exclude_outages=True)
        assert len(post_data) == 4  # 4 rows without outage at/after t=0
    
    def test_get_time_window(self, sample_normal_data):
        """Test getting data in specific time window"""
        preprocessor = DataPreprocessor(sample_normal_data, action_idx=3)
        
        # Get window from -30 to 30
        window = preprocessor.get_time_window(-30, 30)
        
        # Rows at -30, -10, 0, 10, 30 = 5 rows
        assert len(window) == 5
        assert window['seconds'].min() == -30
        assert window['seconds'].max() == 30
    
    def test_get_valid_wattage_data(self, sample_data_with_nan):
        """Test getting only valid wattage data"""
        preprocessor = DataPreprocessor(sample_data_with_nan, action_idx=2)
        
        # Get data with valid wattage (no NaN)
        valid_data = preprocessor.get_valid_wattage_data(exclude_nan=True, exclude_outages=False)
        
        assert len(valid_data) == 4  # Only 4 rows have valid wattage
        assert valid_data['summary_wattage'].notna().all()


class TestMetadataSummary:
    """Test metadata summary generation"""
    
    def test_get_metadata_summary(self, sample_normal_data):
        """Test metadata summary string generation"""
        preprocessor = DataPreprocessor(sample_normal_data, action_idx=3)
        preprocessor.preprocess()
        
        summary = preprocessor.get_metadata_summary()
        
        assert isinstance(summary, str)
        assert 'Total rows' in summary
        assert 'Action index' in summary
        assert 'Power transition' in summary
        assert 'Pre-action' in summary
        assert 'Post-action' in summary
    
    def test_summary_with_nan_segments(self, sample_data_with_nan):
        """Test summary includes NaN segment information"""
        preprocessor = DataPreprocessor(sample_data_with_nan, action_idx=2)
        preprocessor.preprocess()
        
        summary = preprocessor.get_metadata_summary()
        
        assert 'NaN wattage' in summary
        assert 'NaN segments' in summary
    
    def test_summary_with_outages(self, sample_data_with_outages):
        """Test summary includes outage information"""
        preprocessor = DataPreprocessor(sample_data_with_outages, action_idx=2)
        preprocessor.preprocess()
        
        summary = preprocessor.get_metadata_summary()
        
        assert 'Outages' in summary
    
    def test_summary_with_gaps(self, sample_data_with_gaps):
        """Test summary includes time gap information"""
        preprocessor = DataPreprocessor(sample_data_with_gaps, action_idx=2)
        preprocessor.preprocess()
        
        summary = preprocessor.get_metadata_summary()
        
        assert 'Large time gaps' in summary or 'Max gap' in summary

