"""
Basic Metrics Module

Implements METRIC 1 (Start Power) and METRIC 2 (Target Power)
following the pseudocode specification in R_Test_Metrics_Complete_Pseudocode_v3.md
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BasicMetrics:
    """
    Calculates basic foundational metrics for power profile analysis.
    
    Metrics:
    - METRIC 1: Start Power - Baseline power consumption before action
    - METRIC 2: Target Power - Target power settings before/after action
    """
    
    def __init__(self, df: pd.DataFrame, action_idx: int):
        """
        Initialize BasicMetrics calculator.
        
        Args:
            df: Preprocessed DataFrame with required columns
            action_idx: Row index where t crosses 0
        """
        self.df = df
        self.action_idx = action_idx
    
    def calculate_start_power(self) -> Dict[str, Any]:
        """
        METRIC 1: Start Power
        
        Calculate baseline power consumption before action time.
        Returns median of actual wattage during pre-action period (t < 0).
        
        Implementation follows pseudocode from:
        R_Test_Metrics_Complete_Pseudocode_v3.md - Lines 94-180
        
        Returns:
            Dictionary containing:
            - median: float, primary value for calculations
            - last_value: float or None, actual value at t≈0
            - difference: float or None, absolute difference
            - note: string or None, warning if significant difference
        
        Raises:
            ValueError: If no pre-action data or all values are NaN
        """
        # Step 1: Extract pre-action data
        pre_action_mask = self.df['seconds'] < 0
        pre_action_data = self.df[pre_action_mask]
        
        if pre_action_data.empty:
            raise ValueError("No pre-action data available (all times >= 0)")
        
        # Step 2: Extract wattage values
        wattage_series = pre_action_data['summary_wattage']
        
        # Step 3: Filter valid (non-NaN) values
        valid_wattage = wattage_series.dropna()
        
        if valid_wattage.empty:
            raise ValueError("All pre-action wattage values are NaN")
        
        # Step 4: Calculate median
        median_power = valid_wattage.median()
        
        # Step 5: Get last value before action
        last_row_idx = self.action_idx - 1
        last_value = self.df.at[last_row_idx, 'summary_wattage']
        
        # Step 6: Compare median vs last value
        if pd.isna(last_value):
            difference = None
            note = "Last value unavailable (NaN)"
        else:
            difference = abs(last_value - median_power)
            
            if difference > 50:
                note = f"Last value ({last_value:.0f}W) differs from median by {difference:.0f}W"
            else:
                note = None
        
        return {
            'median': float(median_power),
            'last_value': float(last_value) if pd.notna(last_value) else None,
            'difference': float(difference) if difference is not None else None,
            'note': note
        }
    
    def calculate_target_power(self) -> Dict[str, Any]:
        """
        METRIC 2: Target Power
        
        Extract target power setting before and after action to determine
        the intended power transition.
        
        Implementation follows pseudocode from:
        R_Test_Metrics_Complete_Pseudocode_v3.md - Lines 183-261
        
        Returns:
            Dictionary containing:
            - before: float, target in watts before action
            - after: float, target in watts after action
            - change: float, signed change in watts
        
        Raises:
            ValueError: If target values are NaN (data corruption)
        """
        # Step 1: Get target before action
        before_idx = self.action_idx - 1
        target_before = self.df.at[before_idx, 'mode_power']
        
        # Step 2: Get target after action
        target_after = self.df.at[self.action_idx, 'mode_power']
        
        # Validate targets are not NaN
        if pd.isna(target_before) or pd.isna(target_after):
            raise ValueError("Target power values are NaN (data corruption)")
        
        # Step 3: Calculate change
        change = target_after - target_before
        
        # Step 4: Validate target changed
        if change == 0:
            logger.warning("Target power did not change at action time")
        
        # Step 5: Validate target remains constant after action
        post_action_mask = self.df.index >= self.action_idx
        post_action_targets = self.df[post_action_mask]['mode_power']
        unique_targets = post_action_targets.dropna().unique()
        
        if len(unique_targets) > 1:
            logger.warning(f"Target changed during test: {unique_targets}")
            # Use first target (at action time) as canonical
        
        # Step 6: Validate values are reasonable
        if target_before < 0 or target_after < 0:
            logger.warning("Negative target power detected")
        
        if target_before > 10000 or target_after > 10000:
            logger.warning("Unusually high target power detected")
        
        return {
            'before': float(target_before),
            'after': float(target_after),
            'change': float(change)
        }
    
    def calculate_step_direction(self, start_power: Dict[str, Any], target_power: Dict[str, Any]) -> Dict[str, Any]:
        """
        METRIC 3: Step Direction
        
        Classify the type of power transition being tested based on the
        difference between target after action and start power median.
        
        Implementation follows pseudocode from:
        R_Test_Metrics_Complete_Pseudocode_v3.md - Lines 264-336
        
        Args:
            start_power: Dictionary from METRIC 1
            target_power: Dictionary from METRIC 2
        
        Returns:
            Dictionary containing:
            - direction: string, "UP-STEP", "DOWN-STEP", or "MINIMAL-STEP"
            - delta: float, signed change in watts
            - description: string, human-readable description
        
        Raises:
            ValueError: If start or target values are missing
        """
        # Step 1: Extract relevant values
        start_median = start_power['median']
        target_after = target_power['after']
        
        if start_median is None or target_after is None:
            raise ValueError("Cannot compute step direction - missing start or target power")
        
        # Step 2: Calculate delta
        delta = target_after - start_median
        
        # Step 3: Classify direction
        threshold_minimal = 50  # watts
        
        if delta > threshold_minimal:
            direction = "UP-STEP"
            description = f"Ramping up {delta:.0f}W"
        elif delta < -threshold_minimal:
            direction = "DOWN-STEP"
            description = f"Ramping down {abs(delta):.0f}W"
        else:  # -50 <= delta <= 50
            direction = "MINIMAL-STEP"
            description = f"Minimal change ({delta:+.0f}W)"
            logger.warning("Step change is very small, test may not be meaningful")
        
        # Log info for very large deltas
        if abs(delta) > 2000:
            logger.info(f"Very large power step detected: {delta:.0f}W")
        
        return {
            'direction': direction,
            'delta': float(delta),
            'description': description
        }
    
    def calculate_temperature_ranges(self) -> Dict[str, Any]:
        """
        METRIC 4: Temperature Ranges
        
        Track thermal behavior throughout the test by recording temperature
        extremes for both PSU and hash board sensors.
        
        Implementation follows pseudocode from:
        R_Test_Metrics_Complete_Pseudocode_v3.md - Lines 339-435
        
        Returns:
            Dictionary containing:
            - psu: dict with min, max, range (or None if no data)
            - board: dict with min, max, range (or None if no data)
        """
        # Step 1: Extract PSU temperatures
        psu_temps = self.df['psu_temp_max']
        valid_psu = psu_temps.dropna()
        
        if valid_psu.empty:
            psu_min = None
            psu_max = None
            psu_range = None
            logger.warning("All PSU temperature values are NaN")
        else:
            psu_min = float(valid_psu.min())
            psu_max = float(valid_psu.max())
            psu_range = float(psu_max - psu_min)
        
        # Step 2: Extract hash board temperatures
        board_temps = self.df['temp_hash_board_max']
        valid_board = board_temps.dropna()
        
        if valid_board.empty:
            board_min = None
            board_max = None
            board_range = None
            logger.warning("All hash board temperature values are NaN")
        else:
            board_min = float(valid_board.min())
            board_max = float(valid_board.max())
            board_range = float(board_max - board_min)
        
        # Step 3: Validate temperature ranges
        for temp_name, temp_value in [
            ('PSU min', psu_min), ('PSU max', psu_max),
            ('Board min', board_min), ('Board max', board_max)
        ]:
            if temp_value is not None:
                if temp_value < 0 or temp_value > 100:
                    logger.warning(f"Temperature {temp_value}°C ({temp_name}) outside typical range")
        
        return {
            'psu': {
                'min': psu_min,
                'max': psu_max,
                'range': psu_range
            },
            'board': {
                'min': board_min,
                'max': board_max,
                'range': board_range
            }
        }
