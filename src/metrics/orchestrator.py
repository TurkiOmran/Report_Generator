"""
Metric Orchestrator - Manages metric calculation with dependency management.

This module coordinates the execution of all metrics in proper dependency order,
aggregates results, and provides validation and error handling.
"""

import pandas as pd
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from src.data_processing.ingestion import DataIngestion
from src.data_processing.preprocessing import DataPreprocessor
from src.metrics.basic_metrics import BasicMetrics
from src.metrics.time_metrics import TimeMetrics
from src.metrics.anomaly_metrics import AnomalyMetrics

logger = logging.getLogger(__name__)


class MetricOrchestrator:
    """
    Orchestrates metric calculation with dependency management.
    
    This class manages the entire metric calculation pipeline:
    1. Data ingestion and preprocessing
    2. Metric calculation in dependency order
    3. Result aggregation and validation
    4. Error handling and metadata tracking
    """
    
    def __init__(self):
        """Initialize the orchestrator with empty result containers."""
        self.results: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}
        
        # Define execution order based on metric dependencies
        self.execution_order = [
            'start_power',           # METRIC 1 (independent)
            'target_power',          # METRIC 2 (independent)
            'step_direction',        # METRIC 3 (depends on target_power)
            'temperature_ranges',    # METRIC 4 (independent)
            'band_entry',            # METRIC 5 (depends on target_power)
            'setpoint_hit',          # METRIC 6 (depends on target_power)
            'stable_plateau',        # METRIC 7 (depends on target_power)
            'sharp_drops',           # METRIC 8 (independent)
            'spikes',                # METRIC 9 (independent)
            'overshoot_undershoot'   # METRIC 10 (depends on target_power, step_direction)
        ]
    
    def process_file(self, filepath: str) -> Dict[str, Any]:
        """
        Process a CSV file and calculate all metrics.
        
        Args:
            filepath: Path to the CSV file containing power profile data
            
        Returns:
            Dictionary containing:
                - success: Boolean indicating if processing succeeded
                - metrics: Dictionary of all calculated metrics
                - metadata: Processing metadata (timing, file info, etc.)
                - raw_data: Preprocessed dataframe as list of dicts (for visualization)
                - error: Error message (only if success=False)
                - error_type: Type of error (only if success=False)
        """
        start_time = datetime.now()
        
        try:
            # Step 1: Data ingestion
            logger.info(f"Loading file: {filepath}")
            ingestion = DataIngestion()
            df, action_idx, ingestion_warnings = ingestion.load_csv(filepath)
            
            # Step 2: Preprocessing
            logger.info("Preprocessing data")
            preprocessor = DataPreprocessor(df, action_idx)
            processed_df, preprocessing_metadata = preprocessor.preprocess()
            
            # Store preprocessing metadata
            self.metadata.update(preprocessing_metadata)
            self.metadata['filename'] = filepath
            self.metadata['total_rows'] = len(processed_df)
            self.metadata['start_time'] = start_time.isoformat()
            self.metadata['ingestion_warnings'] = ingestion_warnings
            
            # Step 3: Initialize metric calculators
            logger.info("Initializing metric calculators")
            basic_metrics = BasicMetrics(processed_df, action_idx)
            time_metrics = TimeMetrics(processed_df, action_idx)
            anomaly_metrics = AnomalyMetrics(processed_df, action_idx)
            
            # Step 4: Calculate metrics in dependency order
            logger.info("Calculating metrics in dependency order")
            self._calculate_metrics(basic_metrics, time_metrics, anomaly_metrics)
            
            # Step 5: Validate results
            logger.info("Validating metric results")
            validation_results = self.validate_results()
            
            # Step 6: Calculate processing time
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            # Step 7: Compile final results
            final_result = {
                'success': True,
                'metrics': self.results,
                'metadata': {
                    **self.metadata,
                    'processing_time_seconds': round(processing_time, 3),
                    'end_time': end_time.isoformat(),
                    'validation': validation_results
                },
                'raw_data': processed_df.to_dict('records')
            }
            
            logger.info(f"Processing completed successfully in {processing_time:.3f}s")
            return final_result
            
        except Exception as e:
            # Handle any errors during processing
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            error_result = {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'metadata': {
                    **self.metadata,
                    'processing_time_seconds': round(processing_time, 3),
                    'end_time': end_time.isoformat()
                }
            }
            
            logger.error(f"Error processing file: {e}", exc_info=True)
            return error_result
    
    def _calculate_metrics(
        self,
        basic_metrics: BasicMetrics,
        time_metrics: TimeMetrics,
        anomaly_metrics: AnomalyMetrics
    ) -> None:
        """
        Calculate all metrics in proper dependency order.
        
        Args:
            basic_metrics: BasicMetrics calculator instance
            time_metrics: TimeMetrics calculator instance
            anomaly_metrics: AnomalyMetrics calculator instance
        """
        # METRIC 1: Start Power (independent)
        logger.debug("Calculating METRIC 1: Start Power")
        self.results['start_power'] = basic_metrics.calculate_start_power()
        
        # METRIC 2: Target Power (independent)
        logger.debug("Calculating METRIC 2: Target Power")
        self.results['target_power'] = basic_metrics.calculate_target_power()
        
        # METRIC 3: Step Direction (depends on start_power, target_power)
        logger.debug("Calculating METRIC 3: Step Direction")
        self.results['step_direction'] = basic_metrics.calculate_step_direction(
            self.results['start_power'],
            self.results['target_power']
        )
        
        # METRIC 4: Temperature Ranges (independent)
        logger.debug("Calculating METRIC 4: Temperature Ranges")
        self.results['temperature_ranges'] = basic_metrics.calculate_temperature_ranges()
        
        # METRIC 5: Band Entry (depends on target_power, start_power, step_direction)
        logger.debug("Calculating METRIC 5: Band Entry")
        self.results['band_entry'] = time_metrics.calculate_band_entry(
            self.results['target_power'],
            self.results['start_power'],
            self.results['step_direction']
        )
        
        # METRIC 6: Setpoint Hit (depends on target_power)
        logger.debug("Calculating METRIC 6: Setpoint Hit")
        self.results['setpoint_hit'] = time_metrics.calculate_setpoint_hit(
            self.results['target_power']
        )
        
        # METRIC 7: Stable Plateau Duration (depends on target_power)
        logger.debug("Calculating METRIC 7: Stable Plateau Duration")
        self.results['stable_plateau'] = time_metrics.calculate_plateau_duration(
            self.results['target_power']
        )
        
        # METRIC 8: Sharp Drops (independent)
        logger.debug("Calculating METRIC 8: Sharp Drops")
        self.results['sharp_drops'] = anomaly_metrics.calculate_sharp_drops()
        
        # METRIC 9: Spikes (independent)
        logger.debug("Calculating METRIC 9: Spikes")
        self.results['spikes'] = anomaly_metrics.calculate_spikes()
        
        # METRIC 10: Overshoot/Undershoot (depends on target_power, step_direction)
        logger.debug("Calculating METRIC 10: Overshoot/Undershoot")
        self.results['overshoot_undershoot'] = anomaly_metrics.calculate_overshoot_undershoot(
            self.results['target_power'],
            self.results['step_direction']
        )
    
    def validate_results(self) -> Dict[str, Any]:
        """
        Validate calculated metrics for consistency and logical relationships.
        
        Returns:
            Dictionary containing:
                - warnings: List of warning messages
                - errors: List of error messages
                - valid: Boolean indicating if results are valid (no errors)
        """
        warnings: List[str] = []
        errors: List[str] = []
        
        # Check if all expected metrics were calculated
        for metric_name in self.execution_order:
            if metric_name not in self.results:
                errors.append(f"Missing metric: {metric_name}")
        
        # If essential metrics are missing, skip further validation
        if errors:
            return {
                'warnings': warnings,
                'errors': errors,
                'valid': False
            }
        
        # Validate metric relationships
        self._validate_power_metrics(warnings)
        self._validate_time_metrics(warnings)
        self._validate_step_direction(warnings)
        
        return {
            'warnings': warnings,
            'errors': errors,
            'valid': len(errors) == 0
        }
    
    def _validate_power_metrics(self, warnings: List[str]) -> None:
        """Validate power-related metrics for logical consistency."""
        start_power = self.results.get('start_power', {})
        target_power = self.results.get('target_power', {})
        
        start_median = start_power.get('median')
        target_before = target_power.get('before')
        target_after = target_power.get('after')
        
        # Check start power vs target before power
        if start_median and target_before:
            diff = abs(start_median - target_before)
            if diff > 100:
                warnings.append(
                    f"Large discrepancy between start power ({start_median:.0f}W) "
                    f"and target before ({target_before:.0f}W): {diff:.0f}W difference"
                )
        
        # Check if target power changed appropriately
        if target_before and target_after:
            if abs(target_after - target_before) < 50:
                warnings.append(
                    f"Small power change detected: {target_before:.0f}W → {target_after:.0f}W "
                    "(may be MINIMAL-STEP or data quality issue)"
                )
    
    def _validate_time_metrics(self, warnings: List[str]) -> None:
        """Validate time-based metrics for logical ordering."""
        band_entry = self.results.get('band_entry', {})
        setpoint_hit = self.results.get('setpoint_hit', {})
        
        band_time = band_entry.get('time_seconds')
        setpoint_time = setpoint_hit.get('time_seconds')
        
        # Band entry should generally happen before or at setpoint hit
        if band_time and setpoint_time:
            if setpoint_time < band_time:
                warnings.append(
                    f"Setpoint hit ({setpoint_time:.1f}s) occurred before "
                    f"band entry ({band_time:.1f}s) - unusual but possible with "
                    "tight convergence"
                )
    
    def _validate_step_direction(self, warnings: List[str]) -> None:
        """Validate step direction classification."""
        step_direction = self.results.get('step_direction', {})
        target_power = self.results.get('target_power', {})
        
        direction = step_direction.get('direction')
        delta = step_direction.get('delta')
        target_before = target_power.get('before')
        target_after = target_power.get('after')
        
        # Verify delta calculation
        if target_before and target_after and delta is not None:
            expected_delta = target_after - target_before
            if abs(expected_delta - delta) > 1:  # Allow 1W tolerance
                warnings.append(
                    f"Step direction delta mismatch: expected {expected_delta:.0f}W, "
                    f"got {delta:.0f}W"
                )
        
        # Check if MINIMAL-STEP has appropriate warning context
        if direction == 'MINIMAL-STEP' and delta is not None:
            if abs(delta) > 100:
                warnings.append(
                    f"Large delta ({delta:.0f}W) classified as MINIMAL-STEP - "
                    "verify classification logic"
                )
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a high-level summary of all calculated metrics.
        
        Returns:
            Dictionary with condensed metric information for quick review
        """
        if not self.results:
            return {'error': 'No metrics calculated yet'}
        
        summary = {
            'file': self.metadata.get('filename', 'Unknown'),
            'processing_time': self.metadata.get('processing_time_seconds'),
            'test_type': self.results.get('step_direction', {}).get('direction', 'Unknown'),
            'power_transition': {
                'start': self.results.get('start_power', {}).get('median'),
                'target_before': self.results.get('target_power', {}).get('before'),
                'target_after': self.results.get('target_power', {}).get('after'),
                'delta': self.results.get('step_direction', {}).get('delta')
            },
            'timing': {
                'band_entry': self.results.get('band_entry', {}).get('time_seconds'),
                'setpoint_hit': self.results.get('setpoint_hit', {}).get('time_seconds'),
                'stable_plateaus': self.results.get('stable_plateau', {}).get('summary', {}).get('total_count', 0)
            },
            'anomalies': {
                'sharp_drops': self.results.get('sharp_drops', {}).get('summary', {}).get('count', 0),
                'spikes': self.results.get('spikes', {}).get('summary', {}).get('count', 0),
                'overshoot': self.results.get('overshoot_undershoot', {}).get('overshoot', {}).get('occurred', False),
                'undershoot': self.results.get('overshoot_undershoot', {}).get('undershoot', {}).get('occurred', False)
            },
            'temperature': {
                'hash_board_max': self.results.get('temperature_ranges', {}).get('hash_board_max', {}).get('peak'),
                'psu_max': self.results.get('temperature_ranges', {}).get('psu_max', {}).get('peak')
            }
        }
        
        return summary

