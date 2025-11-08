"""CSV data ingestion module with validation and preprocessing"""
import pandas as pd
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, List

logger = logging.getLogger(__name__)


class DataIngestionError(Exception):
    """Base exception for data ingestion errors"""
    pass


class MissingColumnsError(DataIngestionError):
    """Raised when required columns are missing from CSV"""
    pass


class DataValidationError(DataIngestionError):
    """Raised when data validation fails"""
    pass


class FileFormatError(DataIngestionError):
    """Raised when file format is invalid"""
    pass


class DataIngestion:
    """Handles CSV file loading, validation, and preprocessing for miner power profile data"""
    
    REQUIRED_COLUMNS = [
        'miner.seconds',
        'miner.mode.power',
        'miner.summary.wattage',
        'miner.temp.hash_board_max',
        'miner.psu.temp_max',
        'miner.outage'
    ]
    
    # Standardized column names (after renaming)
    STANDARD_COLUMNS = [
        'seconds',
        'mode_power',
        'summary_wattage',
        'temp_hash_board_max',
        'psu_temp_max',
        'outage'
    ]
    
    def __init__(self):
        """Initialize DataIngestion instance"""
        self.warnings: List[str] = []
    
    def load_csv(self, filepath: Path) -> Tuple[pd.DataFrame, int, List[str]]:
        """
        Load and validate CSV file with complete preprocessing.
        
        Args:
            filepath: Path to the CSV file
            
        Returns:
            Tuple of (dataframe, action_idx, warnings)
            - dataframe: Validated and sorted DataFrame with standardized columns
            - action_idx: Row index where time crosses 0
            - warnings: List of data quality warnings
            
        Raises:
            FileFormatError: If file cannot be read or is invalid format
            MissingColumnsError: If required columns are missing
            DataValidationError: If data validation fails
        """
        self.warnings = []
        
        try:
            logger.info(f"Loading CSV file: {filepath}")
            df = pd.read_csv(filepath)
            logger.info(f"Successfully loaded {len(df)} rows from CSV")
        except FileNotFoundError:
            error_msg = f"File not found: {filepath}"
            logger.error(error_msg)
            raise FileFormatError(error_msg)
        except pd.errors.EmptyDataError:
            error_msg = f"File is empty: {filepath}"
            logger.error(error_msg)
            raise FileFormatError(error_msg)
        except Exception as e:
            error_msg = f"Failed to read CSV file: {e}"
            logger.error(error_msg)
            raise FileFormatError(error_msg)
        
        # Validate columns
        self._validate_columns(df)
        
        # Standardize column names (do this before type validation)
        df = self._standardize_column_names(df)
        
        # Convert data types (with coercion for invalid values)
        df = self._convert_types(df)
        
        # Validate data types after conversion
        self._validate_converted_types(df)
        
        # Sort by time
        df = self._sort_by_time(df)
        
        # Find action time index
        action_idx = self._find_action_time(df)
        
        # Validate action characteristics
        self._validate_action_characteristics(df, action_idx)
        
        # Log data quality metrics
        self._log_data_quality(df)
        
        logger.info(f"Data ingestion complete. Action time at index {action_idx}")
        return df, action_idx, self.warnings
    
    def _validate_columns(self, df: pd.DataFrame) -> None:
        """
        Validate that all required columns are present.
        
        Raises:
            MissingColumnsError: If any required columns are missing
        """
        missing = set(self.REQUIRED_COLUMNS) - set(df.columns)
        if missing:
            error_msg = (
                f"Missing required columns: {sorted(missing)}\n"
                f"Required columns are: {self.REQUIRED_COLUMNS}"
            )
            logger.error(error_msg)
            raise MissingColumnsError(error_msg)
        
        logger.debug("All required columns present")
    
    def _validate_converted_types(self, df: pd.DataFrame) -> None:
        """
        Validate that columns have correct types after conversion.
        
        Raises:
            DataValidationError: If critical columns are entirely invalid
        """
        errors = []
        
        # Check that critical columns have some valid data
        critical_cols = ['seconds', 'mode_power']
        
        for col in critical_cols:
            if df[col].isna().all():
                errors.append(f"Column '{col}' has no valid numeric values")
        
        # Check outage column
        if df['outage'].dtype != 'bool':
            errors.append(f"Column 'outage' failed boolean conversion, got {df['outage'].dtype}")
        
        if errors:
            error_msg = "Data type validation failed after conversion:\n" + "\n".join(errors)
            logger.error(error_msg)
            raise DataValidationError(error_msg)
        
        logger.debug("Data type validation passed")
    
    def _standardize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Rename columns to standardized names for internal use.
        
        Args:
            df: DataFrame with original column names
            
        Returns:
            DataFrame with standardized column names
        """
        rename_map = {
            'miner.seconds': 'seconds',
            'miner.mode.power': 'mode_power',
            'miner.summary.wattage': 'summary_wattage',
            'miner.temp.hash_board_max': 'temp_hash_board_max',
            'miner.psu.temp_max': 'psu_temp_max',
            'miner.outage': 'outage'
        }
        
        df_renamed = df.rename(columns=rename_map)
        logger.debug("Column names standardized")
        return df_renamed
    
    def _convert_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert columns to appropriate data types with robust error handling.
        
        Args:
            df: DataFrame with standardized column names
            
        Returns:
            DataFrame with converted types
        """
        df = df.copy()
        
        # Convert numeric columns
        numeric_cols = ['seconds', 'mode_power', 'summary_wattage', 
                       'temp_hash_board_max', 'psu_temp_max']
        
        for col in numeric_cols:
            original_count = len(df)
            df[col] = pd.to_numeric(df[col], errors='coerce')
            nan_count = df[col].isna().sum()
            
            if nan_count > 0:
                warning = f"Converted {nan_count}/{original_count} values to NaN in '{col}' due to invalid numeric values"
                logger.warning(warning)
                self.warnings.append(warning)
        
        # Convert boolean column
        if df['outage'].dtype != 'bool':
            # Handle various boolean representations
            bool_map = {
                'true': True, 'True': True, 'TRUE': True, 1: True, '1': True,
                'false': False, 'False': False, 'FALSE': False, 0: False, '0': False
            }
            
            try:
                df['outage'] = df['outage'].map(lambda x: bool_map.get(x, bool(x)) if pd.notna(x) else False)
            except Exception as e:
                logger.warning(f"Failed to convert outage column to boolean: {e}. Defaulting to False.")
                df['outage'] = False
        
        logger.debug("Data type conversion complete")
        return df
    
    def _sort_by_time(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Sort DataFrame by time (seconds column).
        
        Args:
            df: DataFrame to sort
            
        Returns:
            Sorted DataFrame with reset index
        """
        df_sorted = df.sort_values('seconds').reset_index(drop=True)
        logger.debug(f"DataFrame sorted by time: {len(df_sorted)} rows")
        return df_sorted
    
    def _find_action_time(self, df: pd.DataFrame) -> int:
        """
        Find the action time index where time crosses from negative to non-negative.
        
        Args:
            df: Sorted DataFrame
            
        Returns:
            Integer index where seconds >= 0
            
        Raises:
            DataValidationError: If no action time is found
        """
        action_indices = df[df['seconds'] >= 0].index
        
        if len(action_indices) == 0:
            error_msg = "No action time found (no rows with seconds >= 0)"
            logger.error(error_msg)
            raise DataValidationError(error_msg)
        
        action_idx = action_indices[0]
        action_time = df.at[action_idx, 'seconds']
        
        logger.info(f"Action time found at index {action_idx}, t={action_time:.2f}s")
        return action_idx
    
    def _validate_action_characteristics(self, df: pd.DataFrame, action_idx: int) -> None:
        """
        Validate that power target changes at action time.
        
        Args:
            df: DataFrame
            action_idx: Action time index
        """
        if action_idx == 0:
            warning = "Action time is at first row, cannot validate power change"
            logger.warning(warning)
            self.warnings.append(warning)
            return
        
        target_before = df.at[action_idx - 1, 'mode_power']
        target_after = df.at[action_idx, 'mode_power']
        
        if pd.notna(target_before) and pd.notna(target_after):
            if abs(target_before - target_after) < 0.1:  # Allow small floating point differences
                warning = (
                    f"Target power did not change at action time: "
                    f"before={target_before:.1f}W, after={target_after:.1f}W"
                )
                logger.warning(warning)
                self.warnings.append(warning)
            else:
                logger.info(
                    f"Power transition detected: {target_before:.1f}W → {target_after:.1f}W"
                )
    
    def _log_data_quality(self, df: pd.DataFrame) -> None:
        """
        Log data quality metrics and add warnings for issues.
        
        Args:
            df: DataFrame to analyze
        """
        total_rows = len(df)
        
        # Count NaN values in key columns
        nan_wattage_count = df['summary_wattage'].isna().sum()
        nan_temp_hb_count = df['temp_hash_board_max'].isna().sum()
        nan_temp_psu_count = df['psu_temp_max'].isna().sum()
        
        # Count outages
        outage_count = df['outage'].sum()
        
        # Log and warn about data quality issues
        if nan_wattage_count > 0:
            pct = (nan_wattage_count / total_rows) * 100
            warning = f"{nan_wattage_count}/{total_rows} ({pct:.1f}%) rows have NaN wattage"
            logger.warning(warning)
            self.warnings.append(warning)
        
        if nan_temp_hb_count > 0:
            logger.info(f"{nan_temp_hb_count}/{total_rows} rows have NaN hash board temp")
        
        if nan_temp_psu_count > 0:
            logger.info(f"{nan_temp_psu_count}/{total_rows} rows have NaN PSU temp")
        
        if outage_count > 0:
            pct = (outage_count / total_rows) * 100
            info = f"{outage_count}/{total_rows} ({pct:.1f}%) rows marked as outage"
            logger.info(info)
        
        # Log summary
        logger.info(
            f"Data quality summary: {total_rows} total rows, "
            f"{nan_wattage_count} NaN wattage, {outage_count} outages"
        )
