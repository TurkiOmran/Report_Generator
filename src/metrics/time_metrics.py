"""
Time-Based Metrics Module

Implements METRIC 5 (Band Entry) and METRIC 6 (Setpoint Hit) following the
pseudocode specification in R_Test_Metrics_Complete_Pseudocode_v3.md
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class TimeMetrics:
    """
    Time-based metrics for power profile analysis.
    
    Implements:
    - METRIC 5: Band Entry (adaptive tolerance band with 15s dwell time)
    - METRIC 6: Setpoint Hit (±30W tolerance with event tracking)
    """
    
    def __init__(self, df: pd.DataFrame, action_idx: int):
        """
        Initialize TimeMetrics calculator.
        
        Args:
            df: Preprocessed DataFrame with required columns
            action_idx: Row index where time crosses 0
        """
        self.df = df
        self.action_idx = action_idx
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def calculate_band_entry(
        self, 
        target_power: Dict[str, Any], 
        start_power: Dict[str, Any],
        step_direction: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        METRIC 5: Band Entry
        
        Identify when the miner first achieves and maintains operation near
        the target power level.
        
        Implementation follows pseudocode from:
        R_Test_Metrics_Complete_Pseudocode_v3.md - Lines 438-696
        
        Args:
            target_power: Dictionary from METRIC 2
            start_power: Dictionary from METRIC 1
            step_direction: Optional dictionary from METRIC 3
            
        Returns:
            Dictionary with status, time, wattage, band limits, and entry method
        """
        # 1. Calculate adaptive band tolerance
        target = target_power['after']
        start_median = start_power['median']
        step_magnitude = abs(target - start_median)
        
        # Adaptive tolerance: smaller of 5% target or 50% step
        tolerance_5pct = target * 0.05
        tolerance_step = step_magnitude * 0.5
        tolerance = min(tolerance_5pct, tolerance_step)
        
        # CRITICAL FIX: Band Entry must be wider than Setpoint Hit (±30W)
        # Ensure minimum tolerance of 50W to maintain meaningful distinction
        min_tolerance = 50  # watts
        tolerance = max(tolerance, min_tolerance)
        
        lower_bound = target - tolerance
        upper_bound = target + tolerance
        
        # 2. Extract post-action data
        post_action_mask = self.df.index >= self.action_idx
        post_action = self.df[post_action_mask].copy()
        
        if post_action.empty:
            raise ValueError("No post-action data available")
        
        # 3. Create in-band boolean mask (NaN treated as out-of-band)
        wattage = post_action['summary_wattage']
        in_band = (wattage >= lower_bound) & (wattage <= upper_bound)
        in_band = in_band.fillna(False)
        
        # 4. Find continuous in-band segments
        segments = []
        current_segment_start = None
        current_segment_start_idx = None
        
        for idx, row in post_action.iterrows():
            time = row['seconds']
            is_in_band = in_band.loc[idx]
            
            if is_in_band and current_segment_start is None:
                # Entering band
                current_segment_start = time
                current_segment_start_idx = idx
            
            elif not is_in_band and current_segment_start is not None:
                # Exiting band
                segment_duration = time - current_segment_start
                start_wattage = post_action.loc[current_segment_start_idx, 'summary_wattage']
                
                segments.append({
                    'start_time': current_segment_start,
                    'start_wattage': start_wattage,
                    'duration': segment_duration
                })
                
                current_segment_start = None
                current_segment_start_idx = None
        
        # Handle case where test ends while in-band
        if current_segment_start is not None:
            last_idx = post_action.index[-1]
            last_time = post_action.loc[last_idx, 'seconds']
            segment_duration = last_time - current_segment_start
            start_wattage = post_action.loc[current_segment_start_idx, 'summary_wattage']
            
            segments.append({
                'start_time': current_segment_start,
                'start_wattage': start_wattage,
                'duration': segment_duration
            })
        
        # 5. Find first sustained entry (≥15 seconds)
        min_dwell = 15.0  # seconds
        
        for segment in segments:
            if segment['duration'] >= min_dwell:
                # Found first sustained entry
                entry_time = segment['start_time']
                entry_wattage = segment['start_wattage']
                entry_percentage = (entry_wattage / target) * 100
                
                # Optional: Determine entry method
                entry_method = None
                if step_direction is not None:
                    delta = step_direction['delta']
                    if delta > 0 and entry_wattage > target:
                        entry_method = "via_overshoot"
                    elif delta < 0 and entry_wattage < target:
                        entry_method = "via_undershoot"
                    else:
                        entry_method = "normal"
                
                return {
                    'status': 'ENTERED',
                    'time': float(entry_time),
                    'wattage': float(entry_wattage),
                    'percentage': float(entry_percentage),
                    'band_limits': {
                        'lower': float(lower_bound),
                        'upper': float(upper_bound),
                        'tolerance': float(tolerance)
                    },
                    'entry_method': entry_method
                }
        
        # 6. Handle failure cases
        
        # Case A: Started in-band at t=0
        if segments and segments[0]['start_time'] < 1.0:
            first_segment = segments[0]
            
            if first_segment['duration'] >= min_dwell:
                return {
                    'status': 'INITIALLY_IN_BAND',
                    'time': 0.0,
                    'wattage': float(first_segment['start_wattage']),
                    'percentage': float((first_segment['start_wattage'] / target) * 100),
                    'band_limits': {
                        'lower': float(lower_bound),
                        'upper': float(upper_bound),
                        'tolerance': float(tolerance)
                    },
                    'entry_method': 'initially_in_band'
                }
            else:
                return {
                    'status': 'BRIEFLY_IN_BAND_AT_START',
                    'time': 0.0,
                    'wattage': float(first_segment['start_wattage']),
                    'left_at': float(first_segment['start_time'] + first_segment['duration']),
                    'duration': float(first_segment['duration']),
                    'band_limits': {
                        'lower': float(lower_bound),
                        'upper': float(upper_bound),
                        'tolerance': float(tolerance)
                    }
                }
        
        # Case B: Brief entries only (all < 15s)
        if segments:
            longest_segment = max(segments, key=lambda s: s['duration'])
            
            return {
                'status': 'BRIEF_ENTRY_NOT_SUSTAINED',
                'time': float(longest_segment['start_time']),
                'wattage': float(longest_segment['start_wattage']),
                'duration': float(longest_segment['duration']),
                'band_limits': {
                    'lower': float(lower_bound),
                    'upper': float(upper_bound),
                    'tolerance': float(tolerance)
                }
            }
        
        # Case C: Never entered band - find closest approach
        valid_wattage = post_action['summary_wattage'].dropna()
        
        if valid_wattage.empty:
            return {
                'status': 'NO_VALID_DATA',
                'band_limits': {
                    'lower': float(lower_bound),
                    'upper': float(upper_bound),
                    'tolerance': float(tolerance)
                }
            }
        
        distances = abs(valid_wattage - target)
        closest_idx = distances.idxmin()
        closest_wattage = valid_wattage.loc[closest_idx]
        closest_time = post_action.loc[closest_idx, 'seconds']
        
        return {
            'status': 'NOT_ENTERED',
            'closest_approach': {
                'time': float(closest_time),
                'wattage': float(closest_wattage),
                'distance': float(abs(closest_wattage - target))
            },
            'band_limits': {
                'lower': float(lower_bound),
                'upper': float(upper_bound),
                'tolerance': float(tolerance)
            }
        }
    
    def calculate_setpoint_hit(self, target_power: Dict[str, Any]) -> Dict[str, Any]:
        """
        METRIC 6: Setpoint Hit
        
        Provide complete event history of all attempts to reach and maintain
        target power, enabling analysis of stabilization patterns.
        
        Implementation follows pseudocode from:
        R_Test_Metrics_Complete_Pseudocode_v3.md - Lines 699-909
        
        Args:
            target_power: Dictionary from METRIC 2
            
        Returns:
            Dictionary with brief_touches, sustained_hits, and summary
        """
        # 1. Define setpoint criteria
        tolerance = 30  # watts (±30W band)
        min_sustained_duration = 25  # seconds
        
        # 2. Calculate setpoint band
        target = target_power['after']
        lower_bound = target - tolerance
        upper_bound = target + tolerance
        
        # 3. Extract post-action data
        post_action_mask = self.df.index >= self.action_idx
        post_action = self.df[post_action_mask].copy()
        
        if post_action.empty:
            raise ValueError("No post-action data available")
        
        # 4. Create in-band boolean mask (NaN treated as out-of-band)
        wattage = post_action['summary_wattage']
        in_band = (wattage >= lower_bound) & (wattage <= upper_bound)
        in_band = in_band.fillna(False)
        
        # 5. Find ALL continuous in-band segments
        segments = []
        current_segment_start = None
        current_segment_start_idx = None
        
        for idx, row in post_action.iterrows():
            time = row['seconds']
            is_in_band = in_band.loc[idx]
            current_wattage = row['summary_wattage']
            
            if is_in_band and current_segment_start is None:
                # Entering band
                current_segment_start = time
                current_segment_start_idx = idx
            
            elif not is_in_band and current_segment_start is not None:
                # Exiting band - determine exit reason
                exit_time = time
                
                if pd.notna(current_wattage):
                    if current_wattage < lower_bound:
                        exit_reason = "dropped_below"
                    elif current_wattage > upper_bound:
                        exit_reason = "exceeded_above"
                    else:
                        exit_reason = "unknown"
                else:
                    exit_reason = "unknown"
                
                segment_duration = exit_time - current_segment_start
                start_wattage = post_action.loc[current_segment_start_idx, 'summary_wattage']
                
                # Calculate average wattage during segment
                segment_mask = (post_action['seconds'] >= current_segment_start) & \
                              (post_action['seconds'] < exit_time)
                segment_wattages = post_action.loc[segment_mask, 'summary_wattage'].dropna()
                avg_wattage = segment_wattages.mean() if not segment_wattages.empty else start_wattage
                
                segments.append({
                    'start_time': current_segment_start,
                    'start_wattage': start_wattage,
                    'duration': segment_duration,
                    'avg_wattage': avg_wattage,
                    'exit_time': exit_time,
                    'exit_reason': exit_reason
                })
                
                current_segment_start = None
                current_segment_start_idx = None
        
        # Handle case where test ends while in-band
        if current_segment_start is not None:
            last_idx = post_action.index[-1]
            last_time = post_action.loc[last_idx, 'seconds']
            segment_duration = last_time - current_segment_start
            start_wattage = post_action.loc[current_segment_start_idx, 'summary_wattage']
            
            # Calculate average wattage during segment
            segment_mask = post_action['seconds'] >= current_segment_start
            segment_wattages = post_action.loc[segment_mask, 'summary_wattage'].dropna()
            avg_wattage = segment_wattages.mean() if not segment_wattages.empty else start_wattage
            
            segments.append({
                'start_time': current_segment_start,
                'start_wattage': start_wattage,
                'duration': segment_duration,
                'avg_wattage': avg_wattage,
                'exit_time': last_time,
                'exit_reason': 'test_ended'
            })
        
        # 6. Classify segments as brief touches or sustained hits
        brief_touches = []
        sustained_hits = []
        
        for segment in segments:
            if segment['duration'] < min_sustained_duration:
                # Brief touch
                brief_touches.append({
                    'time': float(segment['start_time']),
                    'wattage': float(segment['start_wattage']),
                    'duration': float(segment['duration']),
                    'exit_reason': segment['exit_reason']
                })
            else:
                # Sustained hit
                sustained_hits.append({
                    'time': float(segment['start_time']),
                    'wattage': float(segment['start_wattage']),
                    'duration': float(segment['duration']),
                    'avg_wattage': float(segment['avg_wattage']),
                    'exit_time': float(segment['exit_time']),
                    'exit_reason': segment['exit_reason']
                })
        
        # 7. Create summary
        first_sustained_hit_time = None
        never_sustained = True
        
        if sustained_hits:
            first_sustained_hit_time = sustained_hits[0]['time']
            never_sustained = False
        
        return {
            'brief_touches': brief_touches,
            'sustained_hits': sustained_hits,
            'summary': {
                'total_brief_touches': len(brief_touches),
                'total_sustained_hits': len(sustained_hits),
                'first_sustained_hit_time': first_sustained_hit_time,
                'never_sustained': never_sustained
            }
        }
    
    def calculate_plateau_duration(self, target_power: Dict[str, Any]) -> Dict[str, Any]:
        """
        METRIC 7: Stable Plateau Duration
        
        Identify and measure all periods of sustained stable operation near target,
        providing insight into control quality and system stability.
        
        Implementation follows pseudocode from:
        R_Test_Metrics_Complete_Pseudocode_v3.md - Lines 912-1102
        
        Args:
            target_power: Dictionary from METRIC 2
            
        Returns:
            Dictionary with plateaus list and summary statistics
        """
        # 1. Define plateau criteria
        tolerance = 20  # watts (±20W band, tighter than setpoint hit)
        min_plateau_duration = 30  # seconds
        
        # 2. Calculate plateau band
        target = target_power['after']
        lower_bound = target - tolerance
        upper_bound = target + tolerance
        
        # 3. Extract post-action data
        post_action_mask = self.df.index >= self.action_idx
        post_action = self.df[post_action_mask].copy()
        
        if post_action.empty:
            raise ValueError("No post-action data available")
        
        # 4. Create in-band boolean mask (NaN treated as out-of-band)
        wattage = post_action['summary_wattage']
        in_band = (wattage >= lower_bound) & (wattage <= upper_bound)
        in_band = in_band.fillna(False)
        
        # 5. Find ALL continuous in-band segments
        segments = []
        current_segment_start = None
        current_segment_start_idx = None
        
        for idx, row in post_action.iterrows():
            time = row['seconds']
            is_in_band = in_band.loc[idx]
            current_wattage = row['summary_wattage']
            
            if is_in_band and current_segment_start is None:
                # Entering plateau band
                current_segment_start = time
                current_segment_start_idx = idx
            
            elif not is_in_band and current_segment_start is not None:
                # Exiting plateau band - determine exit reason
                exit_time = time
                
                if pd.notna(current_wattage):
                    if current_wattage < lower_bound:
                        exit_reason = "dropped_below"
                    elif current_wattage > upper_bound:
                        exit_reason = "exceeded_above"
                    else:
                        exit_reason = "unknown"
                else:
                    exit_reason = "unknown"
                
                segment_duration = exit_time - current_segment_start
                
                # Calculate average wattage during segment
                segment_mask = (post_action['seconds'] >= current_segment_start) & \
                              (post_action['seconds'] < exit_time)
                segment_wattages = post_action.loc[segment_mask, 'summary_wattage'].dropna()
                
                if not segment_wattages.empty:
                    avg_wattage = segment_wattages.mean()
                else:
                    avg_wattage = post_action.loc[current_segment_start_idx, 'summary_wattage']
                
                segments.append({
                    'start_time': current_segment_start,
                    'duration': segment_duration,
                    'avg_wattage': avg_wattage,
                    'exit_time': exit_time,
                    'exit_reason': exit_reason
                })
                
                current_segment_start = None
                current_segment_start_idx = None
        
        # Handle case where test ends while in plateau
        if current_segment_start is not None:
            last_idx = post_action.index[-1]
            last_time = post_action.loc[last_idx, 'seconds']
            segment_duration = last_time - current_segment_start
            
            # Calculate average wattage during segment
            segment_mask = post_action['seconds'] >= current_segment_start
            segment_wattages = post_action.loc[segment_mask, 'summary_wattage'].dropna()
            
            if not segment_wattages.empty:
                avg_wattage = segment_wattages.mean()
            else:
                avg_wattage = post_action.loc[current_segment_start_idx, 'summary_wattage']
            
            segments.append({
                'start_time': current_segment_start,
                'duration': segment_duration,
                'avg_wattage': avg_wattage,
                'exit_time': last_time,
                'exit_reason': 'test_ended'
            })
        
        # 6. Filter for qualifying plateaus (≥30 seconds)
        plateaus = []
        
        for segment in segments:
            if segment['duration'] >= min_plateau_duration:
                plateaus.append({
                    'start_time': float(segment['start_time']),
                    'duration': float(segment['duration']),
                    'avg_wattage': float(segment['avg_wattage']),
                    'exit_time': float(segment['exit_time']),
                    'exit_reason': segment['exit_reason']
                })
        
        # 7. Calculate summary statistics
        if plateaus:
            longest_plateau = max(plateaus, key=lambda p: p['duration'])
            total_stable_time = sum(p['duration'] for p in plateaus)
            
            return {
                'plateaus': plateaus,
                'summary': {
                    'total_count': len(plateaus),
                    'longest_duration': float(longest_plateau['duration']),
                    'total_stable_time': float(total_stable_time)
                }
            }
        else:
            return {
                'plateaus': [],
                'summary': {
                    'total_count': 0,
                    'longest_duration': 0.0,
                    'total_stable_time': 0.0
                }
            }
