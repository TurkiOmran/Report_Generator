"""Data preprocessing utilities for metric calculations"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class DataPreprocessor:
    """
    Preprocessing utilities for preparing ingested data for metric calculations.
    
    This class provides analysis and segmentation methods for data that has
    already been loaded and validated by DataIngestion.
    """
    
    def __init__(self, df: pd.DataFrame, action_idx: int):
        """
        Initialize preprocessor with ingested data.
        
        Args:
            df: DataFrame from DataIngestion (already sorted, validated, standardized)
            action_idx: Action time index from DataIngestion
        """
        self.df = df.copy()
        self.action_idx = action_idx
        self.metadata: Dict[str, Any] = {
            'action_index': action_idx,
            'action_time': df.at[action_idx, 'seconds'] if action_idx < len(df) else None,
            'total_rows': len(df)
        }
    
    def preprocess(self) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Run full preprocessing pipeline.
        
        Returns:
            Tuple of (dataframe, metadata dict)
        """
        self._analyze_data_quality()
        self._identify_nan_segments()
        self._detect_time_gaps()
        self._calculate_durations()
        self._identify_power_levels()
        
        logger.info(f"Preprocessing complete. Action at index {self.action_idx}, t={self.metadata.get('action_time', 'N/A')}")
        return self.df, self.metadata
    
    def _analyze_data_quality(self) -> None:
        """Analyze data quality and store statistics in metadata."""
        # NaN counts per column
        nan_counts = self.df.isnull().sum()
        for col in nan_counts.index:
            if nan_counts[col] > 0:
                pct = (nan_counts[col] / len(self.df)) * 100
                self.metadata[f'{col}_nan_count'] = int(nan_counts[col])
                self.metadata[f'{col}_nan_pct'] = round(pct, 2)
                logger.debug(f"Column '{col}': {nan_counts[col]} NaN ({pct:.1f}%)")
        
        # Outage statistics
        if 'outage' in self.df.columns:
            outage_count = self.df['outage'].sum()
            outage_pct = (outage_count / len(self.df)) * 100
            self.metadata['outage_count'] = int(outage_count)
            self.metadata['outage_pct'] = round(outage_pct, 2)
            
            if outage_count > 0:
                logger.info(f"Outages detected: {outage_count} rows ({outage_pct:.1f}%)")
    
    def _identify_nan_segments(self) -> None:
        """
        Identify continuous segments of NaN values in wattage column.
        
        Stores list of (start_idx, end_idx) tuples in metadata.
        """
        if 'summary_wattage' not in self.df.columns:
            return
        
        wattage_nan_mask = self.df['summary_wattage'].isna()
        
        if not wattage_nan_mask.any():
            self.metadata['wattage_nan_segments'] = []
            return
        
        # Find continuous NaN segments
        segments = []
        in_segment = False
        start_idx = None
        
        for idx, is_nan in enumerate(wattage_nan_mask):
            if is_nan and not in_segment:
                # Start of new NaN segment
                start_idx = idx
                in_segment = True
            elif not is_nan and in_segment:
                # End of NaN segment
                segments.append((start_idx, idx - 1))
                in_segment = False
        
        # Handle segment that extends to end
        if in_segment:
            segments.append((start_idx, len(self.df) - 1))
        
        self.metadata['wattage_nan_segments'] = segments
        self.metadata['nan_segment_count'] = len(segments)
        
        if segments:
            total_nan_rows = sum(end - start + 1 for start, end in segments)
            logger.info(f"Found {len(segments)} NaN segments totaling {total_nan_rows} rows")
    
    def _detect_time_gaps(self) -> None:
        """Detect large gaps in time series data."""
        time_diffs = self.df['seconds'].diff()
        
        # Find maximum gap
        max_gap = time_diffs.max()
        max_gap_idx = time_diffs.idxmax()
        
        self.metadata['max_time_gap'] = float(max_gap)
        self.metadata['max_time_gap_at_index'] = int(max_gap_idx) if pd.notna(max_gap_idx) else None
        
        # Find gaps > threshold (10 seconds)
        gap_threshold = 10.0
        large_gaps = time_diffs[time_diffs > gap_threshold]
        
        if len(large_gaps) > 0:
            gap_locations = [(int(idx), float(gap)) for idx, gap in large_gaps.items()]
            self.metadata['large_time_gaps'] = gap_locations
            logger.warning(f"Detected {len(large_gaps)} time gaps > {gap_threshold}s (max: {max_gap:.1f}s)")
        else:
            self.metadata['large_time_gaps'] = []
    
    def _calculate_durations(self) -> None:
        """Calculate pre-action and post-action data durations."""
        if self.action_idx == 0:
            pre_duration = 0.0
        else:
            first_time = self.df.at[0, 'seconds']
            action_time = self.df.at[self.action_idx, 'seconds']
            pre_duration = abs(action_time - first_time)
        
        if self.action_idx >= len(self.df) - 1:
            post_duration = 0.0
        else:
            action_time = self.df.at[self.action_idx, 'seconds']
            last_time = self.df.at[len(self.df) - 1, 'seconds']
            post_duration = abs(last_time - action_time)
        
        self.metadata['pre_action_duration'] = round(pre_duration, 2)
        self.metadata['post_action_duration'] = round(post_duration, 2)
        self.metadata['pre_action_rows'] = self.action_idx
        self.metadata['post_action_rows'] = len(self.df) - self.action_idx
        
        logger.info(
            f"Durations - Pre: {pre_duration:.1f}s ({self.action_idx} rows), "
            f"Post: {post_duration:.1f}s ({len(self.df) - self.action_idx} rows)"
        )
    
    def _identify_power_levels(self) -> None:
        """Identify target power levels before and after action."""
        if 'mode_power' not in self.df.columns:
            return
        
        # Get power before action (if exists)
        if self.action_idx > 0:
            pre_action_power = self.df.at[self.action_idx - 1, 'mode_power']
            self.metadata['target_power_before'] = float(pre_action_power) if pd.notna(pre_action_power) else None
        else:
            self.metadata['target_power_before'] = None
        
        # Get power at/after action
        post_action_power = self.df.at[self.action_idx, 'mode_power']
        self.metadata['target_power_after'] = float(post_action_power) if pd.notna(post_action_power) else None
        
        # Calculate power change
        if self.metadata['target_power_before'] is not None and self.metadata['target_power_after'] is not None:
            power_change = self.metadata['target_power_after'] - self.metadata['target_power_before']
            self.metadata['power_change'] = round(power_change, 2)
            
            # Determine transition direction
            if power_change > 0:
                self.metadata['transition_direction'] = 'up'
                logger.info(f"Power up transition: {self.metadata['target_power_before']:.0f}W → {self.metadata['target_power_after']:.0f}W")
            elif power_change < 0:
                self.metadata['transition_direction'] = 'down'
                logger.info(f"Power down transition: {self.metadata['target_power_before']:.0f}W → {self.metadata['target_power_after']:.0f}W")
            else:
                self.metadata['transition_direction'] = 'none'
                logger.warning("No power change detected at transition")
        else:
            self.metadata['power_change'] = None
            self.metadata['transition_direction'] = 'unknown'
    
    def get_pre_action_data(self, exclude_outages: bool = False) -> pd.DataFrame:
        """
        Get data before action time (t < 0).
        
        Args:
            exclude_outages: If True, filter out rows where outage=True
            
        Returns:
            DataFrame with pre-action data
        """
        pre_data = self.df[self.df['seconds'] < 0].copy()
        
        if exclude_outages and 'outage' in pre_data.columns:
            original_len = len(pre_data)
            pre_data = pre_data[~pre_data['outage']].copy()
            filtered = original_len - len(pre_data)
            if filtered > 0:
                logger.debug(f"Filtered {filtered} outage rows from pre-action data")
        
        return pre_data
    
    def get_post_action_data(self, exclude_outages: bool = False) -> pd.DataFrame:
        """
        Get data at and after action time (t >= 0).
        
        Args:
            exclude_outages: If True, filter out rows where outage=True
            
        Returns:
            DataFrame with post-action data
        """
        post_data = self.df[self.df['seconds'] >= 0].copy()
        
        if exclude_outages and 'outage' in post_data.columns:
            original_len = len(post_data)
            post_data = post_data[~post_data['outage']].copy()
            filtered = original_len - len(post_data)
            if filtered > 0:
                logger.debug(f"Filtered {filtered} outage rows from post-action data")
        
        return post_data
    
    def get_time_window(
        self,
        start_time: float,
        end_time: float,
        exclude_outages: bool = False
    ) -> pd.DataFrame:
        """
        Get data within a specific time window.
        
        Args:
            start_time: Start time in seconds (inclusive)
            end_time: End time in seconds (inclusive)
            exclude_outages: If True, filter out rows where outage=True
            
        Returns:
            DataFrame with data in time window
        """
        window_mask = (self.df['seconds'] >= start_time) & (self.df['seconds'] <= end_time)
        window_data = self.df[window_mask].copy()
        
        if exclude_outages and 'outage' in window_data.columns:
            original_len = len(window_data)
            window_data = window_data[~window_data['outage']].copy()
            filtered = original_len - len(window_data)
            if filtered > 0:
                logger.debug(f"Filtered {filtered} outage rows from time window [{start_time}, {end_time}]")
        
        return window_data
    
    def get_valid_wattage_data(
        self,
        exclude_outages: bool = True,
        exclude_nan: bool = True
    ) -> pd.DataFrame:
        """
        Get data with valid wattage readings.
        
        Args:
            exclude_outages: If True, filter out outage rows
            exclude_nan: If True, filter out NaN wattage rows
            
        Returns:
            DataFrame with valid wattage data
        """
        data = self.df.copy()
        
        if exclude_nan and 'summary_wattage' in data.columns:
            original_len = len(data)
            data = data[data['summary_wattage'].notna()].copy()
            filtered = original_len - len(data)
            if filtered > 0:
                logger.debug(f"Filtered {filtered} NaN wattage rows")
        
        if exclude_outages and 'outage' in data.columns:
            original_len = len(data)
            data = data[~data['outage']].copy()
            filtered = original_len - len(data)
            if filtered > 0:
                logger.debug(f"Filtered {filtered} outage rows")
        
        return data
    
    def get_metadata_summary(self) -> str:
        """
        Get a human-readable summary of preprocessing metadata.
        
        Returns:
            Formatted string with key metadata
        """
        lines = [
            "=== Preprocessing Metadata Summary ===",
            f"Total rows: {self.metadata['total_rows']}",
            f"Action index: {self.metadata['action_index']}",
            f"Action time: {self.metadata.get('action_time', 'N/A')}s",
            f"",
            f"Pre-action: {self.metadata.get('pre_action_duration', 0):.1f}s ({self.metadata.get('pre_action_rows', 0)} rows)",
            f"Post-action: {self.metadata.get('post_action_duration', 0):.1f}s ({self.metadata.get('post_action_rows', 0)} rows)",
        ]
        
        # Power transition info
        if 'target_power_before' in self.metadata and 'target_power_after' in self.metadata:
            lines.extend([
                f"",
                f"Power transition: {self.metadata['target_power_before']}W → {self.metadata['target_power_after']}W",
                f"Direction: {self.metadata.get('transition_direction', 'unknown')}",
                f"Change: {self.metadata.get('power_change', 'N/A')}W"
            ])
        
        # Data quality info
        if 'summary_wattage_nan_count' in self.metadata:
            lines.extend([
                f"",
                f"NaN wattage: {self.metadata['summary_wattage_nan_count']} rows ({self.metadata['summary_wattage_nan_pct']}%)",
                f"NaN segments: {self.metadata.get('nan_segment_count', 0)}"
            ])
        
        if 'outage_count' in self.metadata:
            lines.append(f"Outages: {self.metadata['outage_count']} rows ({self.metadata['outage_pct']}%)")
        
        if 'large_time_gaps' in self.metadata and self.metadata['large_time_gaps']:
            lines.extend([
                f"",
                f"Large time gaps: {len(self.metadata['large_time_gaps'])}",
                f"Max gap: {self.metadata['max_time_gap']:.1f}s"
            ])
        
        return "\n".join(lines)

