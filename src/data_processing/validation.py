"""Data validation module using Pydantic for configuration and constraints"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
import pandas as pd


class DataQualityThresholds(BaseModel):
    """Thresholds for data quality validation"""
    
    max_nan_wattage_pct: float = Field(
        default=10.0,
        ge=0.0,
        le=100.0,
        description="Maximum acceptable percentage of NaN values in wattage column"
    )
    
    max_outage_pct: float = Field(
        default=5.0,
        ge=0.0,
        le=100.0,
        description="Maximum acceptable percentage of outage rows"
    )
    
    min_pre_action_duration: float = Field(
        default=30.0,
        ge=0.0,
        description="Minimum required duration (seconds) of pre-action data"
    )
    
    min_post_action_duration: float = Field(
        default=60.0,
        ge=0.0,
        description="Minimum required duration (seconds) of post-action data"
    )
    
    required_power_change_threshold: float = Field(
        default=50.0,
        ge=0.0,
        description="Minimum power change (watts) expected at action time"
    )


class ColumnConstraints(BaseModel):
    """Constraints for individual columns"""
    
    min_seconds: Optional[float] = Field(
        default=-3600.0,
        description="Minimum acceptable value for seconds column"
    )
    
    max_seconds: Optional[float] = Field(
        default=3600.0,
        description="Maximum acceptable value for seconds column"
    )
    
    min_power: float = Field(
        default=0.0,
        ge=0.0,
        description="Minimum acceptable power value (watts)"
    )
    
    max_power: float = Field(
        default=5000.0,
        ge=0.0,
        description="Maximum acceptable power value (watts)"
    )
    
    min_temperature: float = Field(
        default=-40.0,
        description="Minimum acceptable temperature (°C)"
    )
    
    max_temperature: float = Field(
        default=150.0,
        description="Maximum acceptable temperature (°C)"
    )
    
    @field_validator('max_power')
    @classmethod
    def validate_max_power(cls, v: float, info) -> float:
        """Ensure max_power is greater than min_power"""
        min_power = info.data.get('min_power', 0.0)
        if v <= min_power:
            raise ValueError(f"max_power ({v}) must be greater than min_power ({min_power})")
        return v
    
    @field_validator('max_temperature')
    @classmethod
    def validate_max_temperature(cls, v: float, info) -> float:
        """Ensure max_temperature is greater than min_temperature"""
        min_temp = info.data.get('min_temperature', -40.0)
        if v <= min_temp:
            raise ValueError(f"max_temperature ({v}) must be greater than min_temperature ({min_temp})")
        return v


class ValidationConfig(BaseModel):
    """Complete validation configuration"""
    
    quality_thresholds: DataQualityThresholds = Field(
        default_factory=DataQualityThresholds
    )
    
    column_constraints: ColumnConstraints = Field(
        default_factory=ColumnConstraints
    )
    
    strict_mode: bool = Field(
        default=False,
        description="If True, raise errors for quality threshold violations; if False, only warn"
    )


class DataFrameValidator:
    """Validates pandas DataFrames against defined constraints"""
    
    def __init__(self, config: Optional[ValidationConfig] = None):
        """
        Initialize validator with configuration.
        
        Args:
            config: Validation configuration. If None, uses defaults.
        """
        self.config = config or ValidationConfig()
    
    def validate_data_quality(self, df: pd.DataFrame, warnings: List[str]) -> List[str]:
        """
        Validate data quality against thresholds.
        
        Args:
            df: DataFrame to validate
            warnings: Existing warnings list to append to
            
        Returns:
            Updated warnings list
            
        Raises:
            ValueError: If strict_mode is True and thresholds are exceeded
        """
        total_rows = len(df)
        issues = []
        
        # Check NaN wattage percentage
        if 'summary_wattage' in df.columns:
            nan_count = df['summary_wattage'].isna().sum()
            nan_pct = (nan_count / total_rows) * 100
            
            if nan_pct > self.config.quality_thresholds.max_nan_wattage_pct:
                msg = (
                    f"NaN wattage percentage ({nan_pct:.1f}%) exceeds threshold "
                    f"({self.config.quality_thresholds.max_nan_wattage_pct}%)"
                )
                issues.append(msg)
        
        # Check outage percentage
        if 'outage' in df.columns:
            outage_count = df['outage'].sum()
            outage_pct = (outage_count / total_rows) * 100
            
            if outage_pct > self.config.quality_thresholds.max_outage_pct:
                msg = (
                    f"Outage percentage ({outage_pct:.1f}%) exceeds threshold "
                    f"({self.config.quality_thresholds.max_outage_pct}%)"
                )
                issues.append(msg)
        
        # Handle issues based on strict mode
        if issues:
            if self.config.strict_mode:
                raise ValueError("Data quality validation failed:\n" + "\n".join(issues))
            else:
                warnings.extend(issues)
        
        return warnings
    
    def validate_column_ranges(self, df: pd.DataFrame) -> List[str]:
        """
        Validate that column values are within acceptable ranges.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            List of warnings for out-of-range values
        """
        warnings = []
        constraints = self.config.column_constraints
        
        # Validate seconds range
        if 'seconds' in df.columns:
            if constraints.min_seconds is not None:
                below_min = (df['seconds'] < constraints.min_seconds).sum()
                if below_min > 0:
                    warnings.append(
                        f"{below_min} rows have seconds below minimum ({constraints.min_seconds})"
                    )
            
            if constraints.max_seconds is not None:
                above_max = (df['seconds'] > constraints.max_seconds).sum()
                if above_max > 0:
                    warnings.append(
                        f"{above_max} rows have seconds above maximum ({constraints.max_seconds})"
                    )
        
        # Validate power ranges
        power_cols = ['mode_power', 'summary_wattage']
        for col in power_cols:
            if col in df.columns:
                valid_values = df[col].dropna()
                
                below_min = (valid_values < constraints.min_power).sum()
                if below_min > 0:
                    warnings.append(
                        f"{below_min} rows in '{col}' below minimum power ({constraints.min_power}W)"
                    )
                
                above_max = (valid_values > constraints.max_power).sum()
                if above_max > 0:
                    warnings.append(
                        f"{above_max} rows in '{col}' above maximum power ({constraints.max_power}W)"
                    )
        
        # Validate temperature ranges
        temp_cols = ['temp_hash_board_max', 'psu_temp_max']
        for col in temp_cols:
            if col in df.columns:
                valid_values = df[col].dropna()
                
                below_min = (valid_values < constraints.min_temperature).sum()
                if below_min > 0:
                    warnings.append(
                        f"{below_min} rows in '{col}' below minimum temp ({constraints.min_temperature}°C)"
                    )
                
                above_max = (valid_values > constraints.max_temperature).sum()
                if above_max > 0:
                    warnings.append(
                        f"{above_max} rows in '{col}' above maximum temp ({constraints.max_temperature}°C)"
                    )
        
        return warnings
    
    def validate_action_time_coverage(
        self,
        df: pd.DataFrame,
        action_idx: int
    ) -> List[str]:
        """
        Validate that there's sufficient data before and after action time.
        
        Args:
            df: DataFrame
            action_idx: Index of action time
            
        Returns:
            List of warnings for insufficient coverage
        """
        warnings = []
        thresholds = self.config.quality_thresholds
        
        if action_idx == 0:
            warnings.append("No pre-action data available")
            return warnings
        
        # Check pre-action duration
        pre_action_time = abs(df.at[0, 'seconds'])
        if pre_action_time < thresholds.min_pre_action_duration:
            warnings.append(
                f"Pre-action duration ({pre_action_time:.1f}s) is less than "
                f"minimum ({thresholds.min_pre_action_duration}s)"
            )
        
        # Check post-action duration
        if action_idx < len(df) - 1:
            post_action_time = df.at[len(df) - 1, 'seconds']
            if post_action_time < thresholds.min_post_action_duration:
                warnings.append(
                    f"Post-action duration ({post_action_time:.1f}s) is less than "
                    f"minimum ({thresholds.min_post_action_duration}s)"
                )
        else:
            warnings.append("No post-action data available")
        
        return warnings
