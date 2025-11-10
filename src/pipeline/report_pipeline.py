"""
Report Pipeline - End-to-End Orchestration

This module coordinates all components to generate complete HTML reports
from CSV power profile data:
1. Data ingestion and metrics calculation (Phase 1)
2. Power timeline visualization (Task 12)
3. Claude API analysis generation (Task 13)
4. HTML report assembly and export (Task 14)
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from src.metrics.orchestrator import MetricOrchestrator
from src.visualization.plotter import create_power_timeline, figure_to_html
from src.analysis.claude_client import (
    format_csv_for_llm,
    extract_test_info,
    build_prompt,
    get_analysis
)
from src.reporting import generate_html_report, save_report


# Custom exceptions for pipeline-specific errors
class PipelineError(Exception):
    """Base exception for pipeline errors."""
    pass


class ValidationError(PipelineError):
    """Raised when input validation fails."""
    pass


class MetricsCalculationError(PipelineError):
    """Raised when metrics calculation fails."""
    pass


class VisualizationError(PipelineError):
    """Raised when visualization generation fails."""
    pass


class AnalysisError(PipelineError):
    """Raised when Claude API analysis fails."""
    pass


class ReportGenerationError(PipelineError):
    """Raised when HTML report generation fails."""
    pass


class ReportPipeline:
    """
    End-to-end pipeline for generating HTML reports from CSV files.
    
    This class orchestrates all components of the report generation process,
    from raw CSV data to final HTML report with metrics, visualizations,
    and AI-generated analysis.
    
    Example:
        >>> pipeline = ReportPipeline(output_dir='reports')
        >>> result = pipeline.generate_report('data.csv')
        >>> print(f"Report saved to: {result['report_path']}")
    """
    
    def __init__(
        self,
        output_dir: str = 'reports',
        enable_analysis: bool = True,
        log_level: str = 'INFO',
        include_plotlyjs: str = 'cdn'
    ):
        """
        Initialize the report pipeline.
        
        Args:
            output_dir: Directory for saving generated reports (default: 'reports')
            enable_analysis: Whether to generate Claude AI analysis (default: True)
            log_level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR')
            include_plotlyjs: How to include Plotly.js ('cdn', True, False)
        
        Raises:
            ValueError: If configuration parameters are invalid
        """
        # Validate configuration
        self._validate_config(output_dir, enable_analysis, log_level, include_plotlyjs)
        
        # Store configuration
        self.output_dir = Path(output_dir)
        self.enable_analysis = enable_analysis
        self.include_plotlyjs = include_plotlyjs
        
        # Initialize logger
        self.logger = self._setup_logger(log_level)
        
        # Create output directory
        self._ensure_output_directory()
        
        # Initialize component trackers
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        self.logger.info(
            f"ReportPipeline initialized: output_dir={self.output_dir}, "
            f"enable_analysis={self.enable_analysis}"
        )
    
    def _validate_config(
        self,
        output_dir: str,
        enable_analysis: bool,
        log_level: str,
        include_plotlyjs: str
    ) -> None:
        """Validate configuration parameters."""
        if not output_dir or not isinstance(output_dir, str):
            raise ValueError("output_dir must be a non-empty string")
        
        if not isinstance(enable_analysis, bool):
            raise ValueError("enable_analysis must be a boolean")
        
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if log_level.upper() not in valid_log_levels:
            raise ValueError(
                f"log_level must be one of {valid_log_levels}, got '{log_level}'"
            )
        
        valid_plotlyjs_options = ['cdn', True, False]
        if include_plotlyjs not in valid_plotlyjs_options:
            raise ValueError(
                f"include_plotlyjs must be one of {valid_plotlyjs_options}, "
                f"got '{include_plotlyjs}'"
            )
    
    def _setup_logger(self, log_level: str) -> logging.Logger:
        """Set up logger with proper formatting."""
        logger = logging.getLogger(__name__)
        logger.setLevel(getattr(logging, log_level.upper()))
        
        # Only add handler if none exists (avoid duplicate handlers)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _ensure_output_directory(self) -> None:
        """Create output directory if it doesn't exist."""
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Output directory ensured: {self.output_dir.absolute()}")
        except PermissionError as e:
            raise PipelineError(
                f"Permission denied creating output directory '{self.output_dir}': {e}"
            ) from e
        except OSError as e:
            raise PipelineError(
                f"Failed to create output directory '{self.output_dir}': {e}"
            ) from e
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get pipeline statistics.
        
        Returns:
            Dictionary with processing statistics
            
        Example:
            >>> stats = pipeline.get_stats()
            >>> print(f"Success rate: {stats['successful']}/{stats['total_processed']}")
        """
        return {
            'total_processed': self.stats['total_processed'],
            'successful': self.stats['successful'],
            'failed': self.stats['failed'],
            'success_rate': (
                self.stats['successful'] / self.stats['total_processed']
                if self.stats['total_processed'] > 0 else 0
            ),
            'errors': self.stats['errors'].copy()
        }
    
    def reset_stats(self) -> None:
        """Reset pipeline statistics."""
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        self.logger.debug("Pipeline statistics reset")
    
    def generate_report(
        self,
        csv_filepath: str,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate complete HTML report from CSV file.
        
        Orchestrates the entire pipeline:
        1. Validates input file
        2. Calculates metrics (Phase 1 - MetricOrchestrator)
        3. Generates visualization (Task 12)
        4. Generates AI analysis (Task 13, optional)
        5. Assembles HTML report (Task 14)
        6. Saves to disk
        
        Args:
            csv_filepath: Path to input CSV file
            output_dir: Optional custom output directory (overrides default)
        
        Returns:
            Dictionary with generation results:
                - 'success': bool
                - 'report_path': str (path to generated report)
                - 'metrics': dict (calculated metrics)
                - 'metadata': dict (file metadata)
                - 'analysis_included': bool
                - 'error': str (if failed)
        
        Raises:
            ValidationError: If input file is invalid
            PipelineError: If any stage fails critically
            
        Example:
            >>> pipeline = ReportPipeline()
            >>> result = pipeline.generate_report('data.csv')
            >>> if result['success']:
            ...     print(f"Report saved: {result['report_path']}")
        """
        start_time = datetime.now()
        self.stats['total_processed'] += 1
        
        self.logger.info(f"Starting report generation for: {csv_filepath}")
        
        try:
            # Stage 1: Validate input file
            self.logger.info("Stage 1/5: Validating input file...")
            self._validate_input_file(csv_filepath)
            
            # Stage 2: Calculate metrics (Phase 1)
            self.logger.info("Stage 2/5: Calculating metrics...")
            orchestrator_result = self._calculate_metrics(csv_filepath)
            
            # Stage 3: Generate visualization (Task 12)
            self.logger.info("Stage 3/5: Generating visualization...")
            chart_html = self._generate_visualization(orchestrator_result)
            
            # Stage 4: Generate AI analysis (Task 13, optional)
            analysis_text = None
            if self.enable_analysis:
                self.logger.info("Stage 4/5: Generating AI analysis...")
                analysis_text = self._generate_analysis(orchestrator_result, csv_filepath)
            else:
                self.logger.info("Stage 4/5: Skipping AI analysis (disabled)")
            
            # Stage 5: Assemble and save report (Task 14)
            self.logger.info("Stage 5/5: Assembling and saving report...")
            report_path = self._save_report(
                orchestrator_result,
                chart_html,
                analysis_text,
                output_dir or str(self.output_dir)
            )
            
            # Success!
            duration = (datetime.now() - start_time).total_seconds()
            self.stats['successful'] += 1
            
            self.logger.info(
                f"Report generated successfully in {duration:.2f}s: {report_path}"
            )
            
            return {
                'success': True,
                'report_path': report_path,
                'metrics': orchestrator_result['metrics'],
                'metadata': orchestrator_result['metadata'],
                'analysis_included': analysis_text is not None,
                'duration_seconds': duration
            }
            
        except Exception as e:
            # Handle any errors
            duration = (datetime.now() - start_time).total_seconds()
            self.stats['failed'] += 1
            error_msg = f"{type(e).__name__}: {str(e)}"
            self.stats['errors'].append({
                'file': csv_filepath,
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            })
            
            self.logger.error(
                f"Report generation failed after {duration:.2f}s: {error_msg}"
            )
            
            return {
                'success': False,
                'error': error_msg,
                'file': csv_filepath,
                'duration_seconds': duration
            }
    
    def _validate_input_file(self, filepath: str) -> None:
        """Validate input CSV file exists and is readable."""
        if not filepath:
            raise ValidationError("File path cannot be empty")
        
        file_path = Path(filepath)
        
        if not file_path.exists():
            raise ValidationError(f"File not found: {filepath}")
        
        if not file_path.is_file():
            raise ValidationError(f"Path is not a file: {filepath}")
        
        if not filepath.lower().endswith('.csv'):
            raise ValidationError(f"File must be a CSV file: {filepath}")
        
        # Check if file is readable
        try:
            with open(file_path, 'r') as f:
                f.read(1)
        except PermissionError:
            raise ValidationError(f"Permission denied reading file: {filepath}")
        except Exception as e:
            raise ValidationError(f"Cannot read file: {filepath} - {e}")
        
        self.logger.debug(f"Input file validated: {filepath}")
    
    def _calculate_metrics(self, filepath: str) -> Dict[str, Any]:
        """Calculate metrics using Phase 1 MetricOrchestrator."""
        try:
            orchestrator = MetricOrchestrator()
            result = orchestrator.process_file(filepath)
            
            self.logger.debug(
                f"Metrics calculated: {len(result['metrics'])} metrics, "
                f"{len(result['raw_data'])} data points"
            )
            
            return result
            
        except Exception as e:
            raise MetricsCalculationError(
                f"Failed to calculate metrics: {e}"
            ) from e
    
    def _generate_visualization(self, orchestrator_result: Dict[str, Any]) -> str:
        """Generate Plotly visualization using Task 12 components."""
        try:
            # Create power timeline figure
            fig = create_power_timeline(
                raw_data=orchestrator_result['raw_data'],
                metrics=orchestrator_result['metrics'],
                metadata=orchestrator_result['metadata']
            )
            
            # Convert to HTML
            chart_html = figure_to_html(fig, include_plotlyjs=self.include_plotlyjs)
            
            self.logger.debug("Visualization generated successfully")
            
            return chart_html
            
        except Exception as e:
            raise VisualizationError(
                f"Failed to generate visualization: {e}"
            ) from e
    
    def _generate_analysis(
        self,
        orchestrator_result: Dict[str, Any],
        filepath: str
    ) -> Optional[str]:
        """Generate AI analysis using Task 13 Claude API integration."""
        try:
            # Read raw CSV data
            import pandas as pd
            raw_df = pd.read_csv(filepath)
            
            # Format CSV for LLM
            csv_content = format_csv_for_llm(raw_df)
            
            # Extract test info
            test_info = extract_test_info(filepath)
            
            # Determine step direction
            step_direction = orchestrator_result['metrics'].get('step_direction', {}).get('direction', 'UNKNOWN')
            
            # Format power range
            target_power = orchestrator_result['metrics'].get('target_power', {})
            power_before = target_power.get('before', 0)
            power_after = target_power.get('after', 0)
            power_range = f"{power_before:.0f}W → {power_after:.0f}W"
            
            # Build prompt
            prompt = build_prompt(
                test_id=test_info['test_id'],
                miner_number=test_info['miner_number'],
                step_direction=step_direction,
                power_range=power_range,
                csv_content=csv_content
            )
            
            # Get analysis from Claude
            analysis_result = get_analysis(prompt)
            
            self.logger.debug(
                f"Analysis generated: {analysis_result['tokens_used']['total']} tokens used"
            )
            
            return analysis_result['analysis']
            
        except Exception as e:
            # Log warning but don't fail the entire pipeline
            self.logger.warning(f"Failed to generate analysis: {e}")
            return None
    
    def _save_report(
        self,
        orchestrator_result: Dict[str, Any],
        chart_html: str,
        analysis_text: Optional[str],
        output_dir: str
    ) -> str:
        """Assemble and save HTML report using Task 14 components."""
        try:
            # Generate HTML report
            html_content = generate_html_report(
                metrics=orchestrator_result['metrics'],
                metadata=orchestrator_result['metadata'],
                chart_html=chart_html,
                analysis_text=analysis_text
            )
            
            # Save to disk
            report_path = save_report(
                html_content=html_content,
                output_dir=output_dir,
                metadata=orchestrator_result['metadata']
            )
            
            self.logger.debug(f"Report saved: {report_path}")
            
            return report_path
            
        except Exception as e:
            raise ReportGenerationError(
                f"Failed to generate/save report: {e}"
            ) from e
    
    def generate_batch(
        self,
        input_directory: str,
        output_dir: Optional[str] = None,
        pattern: str = '*.csv',
        continue_on_error: bool = True
    ) -> Dict[str, Any]:
        """
        Generate reports for multiple CSV files in batch.
        
        Args:
            input_directory: Directory containing CSV files to process
            output_dir: Optional custom output directory (overrides default)
            pattern: Glob pattern for finding CSV files (default: '*.csv')
            continue_on_error: Continue processing if individual files fail
        
        Returns:
            Dictionary with batch results:
                - 'total_files': int (number of files found)
                - 'successful': int (number of successfully processed files)
                - 'failed': int (number of failed files)
                - 'reports': list (paths to generated reports)
                - 'errors': list (error details for failed files)
                - 'duration_seconds': float (total processing time)
        
        Example:
            >>> pipeline = ReportPipeline()
            >>> result = pipeline.generate_batch('data/csv_files/')
            >>> print(f"Processed {result['successful']}/{result['total_files']} files")
        """
        start_time = datetime.now()
        
        # Validate input directory
        input_path = Path(input_directory)
        if not input_path.exists():
            raise ValidationError(f"Input directory not found: {input_directory}")
        if not input_path.is_dir():
            raise ValidationError(f"Path is not a directory: {input_directory}")
        
        # Discover CSV files
        csv_files = sorted(input_path.glob(pattern))
        
        if not csv_files:
            self.logger.warning(f"No files matching '{pattern}' found in {input_directory}")
            return {
                'total_files': 0,
                'successful': 0,
                'failed': 0,
                'reports': [],
                'errors': [],
                'duration_seconds': 0
            }
        
        self.logger.info(f"Starting batch processing of {len(csv_files)} files")
        
        # Track batch results
        batch_results = {
            'total_files': len(csv_files),
            'successful': 0,
            'failed': 0,
            'reports': [],
            'errors': [],
            'duration_seconds': 0
        }
        
        # Process each file
        for idx, csv_file in enumerate(csv_files, 1):
            self.logger.info(f"Processing file {idx}/{len(csv_files)}: {csv_file.name}")
            
            try:
                result = self.generate_report(
                    csv_filepath=str(csv_file),
                    output_dir=output_dir
                )
                
                if result['success']:
                    batch_results['successful'] += 1
                    batch_results['reports'].append(result['report_path'])
                    self.logger.info(f"✓ Success: {csv_file.name}")
                else:
                    batch_results['failed'] += 1
                    batch_results['errors'].append({
                        'file': str(csv_file),
                        'error': result.get('error', 'Unknown error')
                    })
                    self.logger.error(f"✗ Failed: {csv_file.name}")
                    
                    if not continue_on_error:
                        break
            
            except Exception as e:
                batch_results['failed'] += 1
                error_msg = f"{type(e).__name__}: {str(e)}"
                batch_results['errors'].append({
                    'file': str(csv_file),
                    'error': error_msg
                })
                self.logger.error(f"✗ Exception processing {csv_file.name}: {error_msg}")
                
                if not continue_on_error:
                    break
        
        # Calculate total duration
        duration = (datetime.now() - start_time).total_seconds()
        batch_results['duration_seconds'] = duration
        
        # Log summary
        success_rate = (
            batch_results['successful'] / batch_results['total_files'] * 100
            if batch_results['total_files'] > 0 else 0
        )
        
        self.logger.info(
            f"Batch processing complete: {batch_results['successful']}/{batch_results['total_files']} "
            f"successful ({success_rate:.1f}%) in {duration:.2f}s"
        )
        
        return batch_results

