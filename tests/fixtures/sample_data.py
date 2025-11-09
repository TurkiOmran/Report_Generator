"""
Synthetic test data generators for comprehensive testing.

Creates realistic time-series data for various test scenarios including
UP-STEP, DOWN-STEP, edge cases, power drops, temperature variations, and outages.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any


def create_upstep_test_data(
    start_power: float = 2000.0,
    target_power: float = 3000.0,
    pre_duration: int = 300,
    post_duration: int = 600,
    noise_level: float = 10.0,
    add_overshoot: bool = True,
    overshoot_magnitude: float = 200.0
) -> pd.DataFrame:
    """
    Create sample data for UP-STEP test.
    
    Args:
        start_power: Initial power level (W)
        target_power: Target power after step (W)
        pre_duration: Duration of pre-action period (seconds)
        post_duration: Duration of post-action period (seconds)
        noise_level: Standard deviation of noise (W)
        add_overshoot: Whether to add overshoot transient
        overshoot_magnitude: Peak overshoot amount (W)
        
    Returns:
        DataFrame with realistic UP-STEP power profile
    """
    # Pre-action: stable at start_power
    pre_times = np.arange(-pre_duration, 0, 1)
    pre_power = np.random.normal(start_power, noise_level, len(pre_times))
    pre_mode = np.full(len(pre_times), start_power)
    
    # Post-action: step to target_power with transient response
    post_times = np.arange(0, post_duration, 1)
    post_power = np.zeros(len(post_times))
    
    # Transient response with ramp + optional overshoot
    ramp_duration = 10  # seconds to ramp up
    overshoot_duration = 10  # seconds for overshoot decay
    
    for i, t in enumerate(post_times):
        if t < ramp_duration:
            # Linear ramp
            post_power[i] = start_power + (target_power - start_power) * (t / ramp_duration)
        elif add_overshoot and t < (ramp_duration + overshoot_duration):
            # Exponential decay overshoot
            decay_time = t - ramp_duration
            overshoot = overshoot_magnitude * np.exp(-decay_time / 5)
            post_power[i] = target_power + overshoot + np.random.normal(0, noise_level)
        else:
            # Stable at target with noise
            post_power[i] = np.random.normal(target_power, noise_level)
    
    post_mode = np.full(len(post_times), target_power)
    
    # Temperature profiles (realistic thermal behavior)
    total_len = len(pre_times) + len(post_times)
    base_temp_hb = 65.0
    base_temp_psu = 55.0
    
    # Temperature rises with power
    temp_rise_hb = (target_power - start_power) / 1000.0 * 3  # ~3°C per kW
    temp_rise_psu = (target_power - start_power) / 1000.0 * 2  # ~2°C per kW
    
    hash_board_temp = np.concatenate([
        np.random.normal(base_temp_hb, 2, len(pre_times)),
        base_temp_hb + temp_rise_hb * np.minimum(post_times / 60, 1) + np.random.normal(0, 2, len(post_times))
    ])
    
    psu_temp = np.concatenate([
        np.random.normal(base_temp_psu, 1.5, len(pre_times)),
        base_temp_psu + temp_rise_psu * np.minimum(post_times / 60, 1) + np.random.normal(0, 1.5, len(post_times))
    ])
    
    # Combine data
    df = pd.DataFrame({
        'miner.seconds': np.concatenate([pre_times, post_times]),
        'miner.mode.power': np.concatenate([pre_mode, post_mode]),
        'miner.summary.wattage': np.concatenate([pre_power, post_power]),
        'miner.temp.hash_board_max': hash_board_temp,
        'miner.psu.temp_max': psu_temp,
        'miner.outage': np.zeros(total_len, dtype=bool)
    })
    
    return df


def create_downstep_test_data(
    start_power: float = 3000.0,
    target_power: float = 2000.0,
    pre_duration: int = 300,
    post_duration: int = 600,
    noise_level: float = 10.0,
    add_undershoot: bool = True,
    undershoot_magnitude: float = 150.0
) -> pd.DataFrame:
    """
    Create sample data for DOWN-STEP test.
    
    Args:
        start_power: Initial power level (W)
        target_power: Target power after step (W)
        pre_duration: Duration of pre-action period (seconds)
        post_duration: Duration of post-action period (seconds)
        noise_level: Standard deviation of noise (W)
        add_undershoot: Whether to add undershoot transient
        undershoot_magnitude: Depth of undershoot (W)
        
    Returns:
        DataFrame with realistic DOWN-STEP power profile
    """
    # Pre-action: stable at start_power
    pre_times = np.arange(-pre_duration, 0, 1)
    pre_power = np.random.normal(start_power, noise_level, len(pre_times))
    pre_mode = np.full(len(pre_times), start_power)
    
    # Post-action: step down to target_power
    post_times = np.arange(0, post_duration, 1)
    post_power = np.zeros(len(post_times))
    
    ramp_duration = 8  # Faster ramp down
    undershoot_duration = 12  # Longer undershoot recovery
    
    for i, t in enumerate(post_times):
        if t < ramp_duration:
            # Linear ramp down
            post_power[i] = start_power + (target_power - start_power) * (t / ramp_duration)
        elif add_undershoot and t < (ramp_duration + undershoot_duration):
            # Exponential recovery from undershoot
            decay_time = t - ramp_duration
            undershoot = undershoot_magnitude * np.exp(-decay_time / 6)
            post_power[i] = target_power - undershoot + np.random.normal(0, noise_level)
        else:
            # Stable at target with noise
            post_power[i] = np.random.normal(target_power, noise_level)
    
    post_mode = np.full(len(post_times), target_power)
    
    # Temperature profiles (cooling behavior)
    total_len = len(pre_times) + len(post_times)
    base_temp_hb = 68.0  # Start higher
    base_temp_psu = 58.0
    
    temp_drop_hb = (start_power - target_power) / 1000.0 * 3
    temp_drop_psu = (start_power - target_power) / 1000.0 * 2
    
    hash_board_temp = np.concatenate([
        np.random.normal(base_temp_hb, 2, len(pre_times)),
        base_temp_hb - temp_drop_hb * np.minimum(post_times / 90, 1) + np.random.normal(0, 2, len(post_times))
    ])
    
    psu_temp = np.concatenate([
        np.random.normal(base_temp_psu, 1.5, len(pre_times)),
        base_temp_psu - temp_drop_psu * np.minimum(post_times / 90, 1) + np.random.normal(0, 1.5, len(post_times))
    ])
    
    df = pd.DataFrame({
        'miner.seconds': np.concatenate([pre_times, post_times]),
        'miner.mode.power': np.concatenate([pre_mode, post_mode]),
        'miner.summary.wattage': np.concatenate([pre_power, post_power]),
        'miner.temp.hash_board_max': hash_board_temp,
        'miner.psu.temp_max': psu_temp,
        'miner.outage': np.zeros(total_len, dtype=bool)
    })
    
    return df


def create_data_with_drops(
    base_power: float = 3000.0,
    num_drops: int = 3,
    drop_duration: int = 5,
    pre_duration: int = 300,
    post_duration: int = 600
) -> pd.DataFrame:
    """
    Create data with sharp power drops (outages).
    
    Args:
        base_power: Baseline power level (W)
        num_drops: Number of drops to inject
        drop_duration: Duration of each drop (seconds)
        pre_duration: Duration of pre-action period (seconds)
        post_duration: Duration of post-action period (seconds)
        
    Returns:
        DataFrame with power drops marked as outages
    """
    # Start with stable power profile
    df = create_upstep_test_data(
        start_power=base_power,
        target_power=base_power,
        pre_duration=pre_duration,
        post_duration=post_duration,
        add_overshoot=False
    )
    
    # Inject drops at random post-action times
    post_action_mask = df['miner.seconds'] >= 0
    post_action_indices = df[post_action_mask].index.tolist()
    
    # Space drops evenly
    drop_spacing = len(post_action_indices) // (num_drops + 1)
    
    for i in range(num_drops):
        drop_start_idx = post_action_indices[drop_spacing * (i + 1)]
        drop_end_idx = min(drop_start_idx + drop_duration, len(df))
        
        # Mark as drop: zero power and outage flag
        df.loc[drop_start_idx:drop_end_idx, 'miner.summary.wattage'] = 0.0
        df.loc[drop_start_idx:drop_end_idx, 'miner.outage'] = True
    
    return df


def create_data_with_spikes(
    start_power: float = 2500.0,
    target_power: float = 3000.0,
    num_spikes: int = 2,
    spike_magnitude: float = 500.0,
    spike_duration: int = 3
) -> pd.DataFrame:
    """
    Create data with power spikes.
    
    Args:
        start_power: Initial power level (W)
        target_power: Target power after step (W)
        num_spikes: Number of spikes to inject
        spike_magnitude: Height of spikes above baseline (W)
        spike_duration: Duration of each spike (seconds)
        
    Returns:
        DataFrame with power spikes
    """
    df = create_upstep_test_data(
        start_power=start_power,
        target_power=target_power,
        add_overshoot=False
    )
    
    # Inject spikes in post-action period
    post_action_mask = df['miner.seconds'] >= 20  # After initial transient
    post_action_indices = df[post_action_mask].index.tolist()
    
    spike_spacing = len(post_action_indices) // (num_spikes + 1)
    
    for i in range(num_spikes):
        spike_start_idx = post_action_indices[spike_spacing * (i + 1)]
        spike_end_idx = min(spike_start_idx + spike_duration, len(df))
        
        # Add spike
        df.loc[spike_start_idx:spike_end_idx, 'miner.summary.wattage'] += spike_magnitude
    
    return df


def create_minimal_step_data(
    power_level: float = 3000.0,
    delta: float = 30.0,
    pre_duration: int = 300,
    post_duration: int = 600
) -> pd.DataFrame:
    """
    Create data with minimal power change (< 2% and < 50W).
    
    Args:
        power_level: Base power level (W)
        delta: Small power change (W)
        pre_duration: Duration of pre-action period (seconds)
        post_duration: Duration of post-action period (seconds)
        
    Returns:
        DataFrame with MINIMAL-STEP profile
    """
    return create_upstep_test_data(
        start_power=power_level,
        target_power=power_level + delta,
        pre_duration=pre_duration,
        post_duration=post_duration,
        noise_level=5.0,
        add_overshoot=False
    )


def create_high_noise_data(
    start_power: float = 2000.0,
    target_power: float = 3000.0,
    noise_level: float = 50.0
) -> pd.DataFrame:
    """
    Create data with high noise levels.
    
    Args:
        start_power: Initial power level (W)
        target_power: Target power after step (W)
        noise_level: High noise standard deviation (W)
        
    Returns:
        DataFrame with noisy power profile
    """
    return create_upstep_test_data(
        start_power=start_power,
        target_power=target_power,
        noise_level=noise_level,
        add_overshoot=False
    )


def create_data_with_nan_segments(
    start_power: float = 3000.0,
    target_power: float = 2000.0,
    nan_percentage: float = 0.1
) -> pd.DataFrame:
    """
    Create data with random NaN segments.
    
    Args:
        start_power: Initial power level (W)
        target_power: Target power after step (W)
        nan_percentage: Percentage of data to set as NaN (0-1)
        
    Returns:
        DataFrame with NaN values scattered throughout
    """
    df = create_downstep_test_data(
        start_power=start_power,
        target_power=target_power
    )
    
    # Randomly set some values to NaN
    total_rows = len(df)
    nan_count = int(total_rows * nan_percentage)
    nan_indices = np.random.choice(total_rows, nan_count, replace=False)
    
    # Set multiple columns to NaN for realism
    df.loc[nan_indices, 'miner.summary.wattage'] = np.nan
    df.loc[nan_indices[::2], 'miner.temp.hash_board_max'] = np.nan
    df.loc[nan_indices[::3], 'miner.psu.temp_max'] = np.nan
    
    return df


def save_test_fixtures(output_dir: str = None) -> Dict[str, str]:
    """
    Generate and save all test fixture CSV files.
    
    Args:
        output_dir: Directory to save fixtures (default: tests/fixtures/)
        
    Returns:
        Dictionary mapping scenario names to file paths
    """
    if output_dir is None:
        fixtures_dir = Path(__file__).parent
    else:
        fixtures_dir = Path(output_dir)
    
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    
    # Define scenarios
    scenarios = {
        'upstep_clean.csv': create_upstep_test_data(),
        'upstep_with_overshoot.csv': create_upstep_test_data(
            start_power=2000.0, target_power=3500.0, add_overshoot=True, overshoot_magnitude=300.0
        ),
        'downstep_clean.csv': create_downstep_test_data(),
        'downstep_with_undershoot.csv': create_downstep_test_data(
            start_power=3500.0, target_power=1000.0, add_undershoot=True, undershoot_magnitude=200.0
        ),
        'data_with_drops.csv': create_data_with_drops(base_power=3000.0, num_drops=3),
        'data_with_spikes.csv': create_data_with_spikes(
            start_power=2500.0, target_power=3000.0, num_spikes=2
        ),
        'minimal_step.csv': create_minimal_step_data(power_level=3000.0, delta=30.0),
        'high_noise.csv': create_high_noise_data(
            start_power=2000.0, target_power=3000.0, noise_level=50.0
        ),
        'with_nan_segments.csv': create_data_with_nan_segments(
            start_power=3500.0, target_power=2000.0, nan_percentage=0.15
        )
    }
    
    # Save all fixtures
    saved_files = {}
    for filename, df in scenarios.items():
        filepath = fixtures_dir / filename
        df.to_csv(filepath, index=False)
        saved_files[filename] = str(filepath)
        print(f"Created: {filepath}")
    
    return saved_files


if __name__ == "__main__":
    # Generate all test fixtures
    print("Generating synthetic test fixtures...")
    saved = save_test_fixtures()
    print(f"\nGenerated {len(saved)} test fixture files:")
    for name in sorted(saved.keys()):
        print(f"  - {name}")

