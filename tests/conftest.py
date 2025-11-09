"""
Pytest configuration and shared fixtures for testing.

This module provides reusable fixtures for all test modules.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple

# Import test data generators
from tests.fixtures.sample_data import (
    create_upstep_test_data,
    create_downstep_test_data,
    create_data_with_drops,
    create_data_with_spikes,
    create_minimal_step_data,
    create_high_noise_data,
    create_data_with_nan_segments
)


# ============================================================================
# DataFrame Fixtures
# ============================================================================

@pytest.fixture
def sample_upstep_df() -> pd.DataFrame:
    """Provide sample UP-STEP dataframe."""
    return create_upstep_test_data(
        start_power=2000.0,
        target_power=3000.0,
        pre_duration=300,
        post_duration=600
    )


@pytest.fixture
def sample_downstep_df() -> pd.DataFrame:
    """Provide sample DOWN-STEP dataframe."""
    return create_downstep_test_data(
        start_power=3000.0,
        target_power=2000.0,
        pre_duration=300,
        post_duration=600
    )


@pytest.fixture
def sample_upstep_with_overshoot_df() -> pd.DataFrame:
    """Provide UP-STEP dataframe with overshoot transient."""
    return create_upstep_test_data(
        start_power=2000.0,
        target_power=3500.0,
        add_overshoot=True,
        overshoot_magnitude=300.0
    )


@pytest.fixture
def sample_downstep_with_undershoot_df() -> pd.DataFrame:
    """Provide DOWN-STEP dataframe with undershoot transient."""
    return create_downstep_test_data(
        start_power=3500.0,
        target_power=1000.0,
        add_undershoot=True,
        undershoot_magnitude=250.0
    )


@pytest.fixture
def sample_minimal_step_df() -> pd.DataFrame:
    """Provide dataframe with minimal power change (MINIMAL-STEP)."""
    return create_minimal_step_data(power_level=3000.0, delta=30.0)


@pytest.fixture
def sample_with_drops_df() -> pd.DataFrame:
    """Provide dataframe with power drops (sharp drops)."""
    return create_data_with_drops(base_power=3000.0, num_drops=3)


@pytest.fixture
def sample_with_spikes_df() -> pd.DataFrame:
    """Provide dataframe with power spikes."""
    return create_data_with_spikes(
        start_power=2500.0,
        target_power=3000.0,
        num_spikes=2,
        spike_magnitude=500.0
    )


@pytest.fixture
def sample_high_noise_df() -> pd.DataFrame:
    """Provide dataframe with high noise levels."""
    return create_high_noise_data(
        start_power=2000.0,
        target_power=3000.0,
        noise_level=50.0
    )


@pytest.fixture
def sample_with_nan_df() -> pd.DataFrame:
    """Provide dataframe with NaN segments."""
    return create_data_with_nan_segments(
        start_power=3500.0,
        target_power=2000.0,
        nan_percentage=0.15
    )


# ============================================================================
# Processed DataFrame Fixtures (with action_idx)
# ============================================================================

@pytest.fixture
def upstep_with_action_idx(sample_upstep_df) -> Tuple[pd.DataFrame, int]:
    """
    Provide UP-STEP dataframe with computed action index.
    
    Returns:
        Tuple of (dataframe, action_idx)
    """
    # Standardize column names (simulate ingestion)
    df = sample_upstep_df.copy()
    df.columns = [col.replace('miner.', '').replace('.', '_') for col in df.columns]
    
    # Find action index where seconds crosses 0
    action_idx = df[df['seconds'] >= 0].index[0]
    
    return df, action_idx


@pytest.fixture
def downstep_with_action_idx(sample_downstep_df) -> Tuple[pd.DataFrame, int]:
    """
    Provide DOWN-STEP dataframe with computed action index.
    
    Returns:
        Tuple of (dataframe, action_idx)
    """
    df = sample_downstep_df.copy()
    df.columns = [col.replace('miner.', '').replace('.', '_') for col in df.columns]
    action_idx = df[df['seconds'] >= 0].index[0]
    return df, action_idx


# ============================================================================
# CSV File Fixtures
# ============================================================================

@pytest.fixture
def temp_csv_file(tmp_path, sample_upstep_df) -> str:
    """
    Create temporary CSV file for testing file I/O.
    
    Args:
        tmp_path: pytest's temporary directory fixture
        sample_upstep_df: Dataframe to save
        
    Returns:
        Path to temporary CSV file
    """
    csv_path = tmp_path / "test_data.csv"
    sample_upstep_df.to_csv(csv_path, index=False)
    return str(csv_path)


@pytest.fixture
def temp_upstep_csv(tmp_path, sample_upstep_df) -> str:
    """Create temporary UP-STEP CSV file."""
    csv_path = tmp_path / "upstep_test.csv"
    sample_upstep_df.to_csv(csv_path, index=False)
    return str(csv_path)


@pytest.fixture
def temp_downstep_csv(tmp_path, sample_downstep_df) -> str:
    """Create temporary DOWN-STEP CSV file."""
    csv_path = tmp_path / "downstep_test.csv"
    sample_downstep_df.to_csv(csv_path, index=False)
    return str(csv_path)


@pytest.fixture
def temp_with_drops_csv(tmp_path, sample_with_drops_df) -> str:
    """Create temporary CSV with drops."""
    csv_path = tmp_path / "with_drops_test.csv"
    sample_with_drops_df.to_csv(csv_path, index=False)
    return str(csv_path)


# ============================================================================
# Edge Case Fixtures
# ============================================================================

@pytest.fixture
def empty_df() -> pd.DataFrame:
    """Provide empty dataframe with correct columns."""
    return pd.DataFrame(columns=[
        'miner.seconds', 'miner.mode.power', 'miner.summary.wattage',
        'miner.temp.hash_board_max', 'miner.psu.temp_max', 'miner.outage'
    ])


@pytest.fixture
def no_pre_action_df() -> pd.DataFrame:
    """Provide dataframe with no pre-action data (all times >= 0)."""
    times = np.arange(0, 100, 1)
    return pd.DataFrame({
        'miner.seconds': times,
        'miner.mode.power': np.full(len(times), 3000.0),
        'miner.summary.wattage': np.random.normal(3000, 10, len(times)),
        'miner.temp.hash_board_max': np.random.normal(65, 2, len(times)),
        'miner.psu.temp_max': np.random.normal(55, 2, len(times)),
        'miner.outage': np.zeros(len(times), dtype=bool)
    })


@pytest.fixture
def all_nan_wattage_df() -> pd.DataFrame:
    """Provide dataframe where all wattage values are NaN."""
    times = np.arange(-100, 100, 1)
    return pd.DataFrame({
        'miner.seconds': times,
        'miner.mode.power': np.full(len(times), 3000.0),
        'miner.summary.wattage': np.full(len(times), np.nan),
        'miner.temp.hash_board_max': np.random.normal(65, 2, len(times)),
        'miner.psu.temp_max': np.random.normal(55, 2, len(times)),
        'miner.outage': np.zeros(len(times), dtype=bool)
    })


# ============================================================================
# Real Fixture File Paths
# ============================================================================

@pytest.fixture
def real_fixtures_dir() -> Path:
    """Provide path to real CSV fixtures directory."""
    return Path(__file__).parent / 'fixtures'


@pytest.fixture
def real_upstep_csv(real_fixtures_dir) -> str:
    """Provide path to real UP-STEP fixture."""
    # Use r10_39 (UP-STEP: 2500W -> 3500W)
    return str(real_fixtures_dir / 'r10_39_2025-08-27T23_05_08.csv')


@pytest.fixture
def real_downstep_csv(real_fixtures_dir) -> str:
    """Provide path to real DOWN-STEP fixture."""
    # Use r9_39 (DOWN-STEP: 3500W -> 2500W)
    return str(real_fixtures_dir / 'r9_39_2025-08-27T22_53_07.csv')


@pytest.fixture
def real_valid_profile_csv(real_fixtures_dir) -> str:
    """Provide path to valid power profile fixture."""
    return str(real_fixtures_dir / 'valid_power_profile.csv')


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "edge_case: marks tests for edge cases"
    )

