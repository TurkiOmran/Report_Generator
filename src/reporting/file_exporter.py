"""
File Exporter - Save HTML reports to disk.

This module handles:
- Output directory creation
- Filename formatting (report_r{run}_{step}_{timestamp}.html)
- UTF-8 encoding
- Error handling (permissions, disk space)
- Single-file portability validation
"""

import os
from pathlib import Path
from typing import Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def save_report(
    html_content: str,
    output_dir: str = "reports",
    filename: Optional[str] = None,
    metadata: Optional[dict] = None
) -> str:
    """
    Save HTML report to disk with proper directory and filename management.
    
    Creates output directory if it doesn't exist and saves the HTML report
    with UTF-8 encoding. Generates filename from metadata if not provided.
    
    Args:
        html_content: Complete HTML document as string
        output_dir: Directory to save report (default: 'reports')
        filename: Optional custom filename (without extension)
        metadata: Optional metadata dict for auto-generating filename
    
    Returns:
        Full path to saved report file
        
    Raises:
        OSError: If directory creation or file writing fails
        ValueError: If html_content is empty or invalid
        PermissionError: If lacking write permissions
        
    Example:
        >>> html = generate_html_report(metrics, metadata, chart_html)
        >>> path = save_report(html, metadata=metadata)
        >>> print(f"Report saved to: {path}")
    """
    # Validate input
    if not html_content or not html_content.strip():
        raise ValueError("html_content cannot be empty")
    
    # Create output directory
    output_path = Path(output_dir)
    try:
        output_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory ensured: {output_path.absolute()}")
    except PermissionError as e:
        raise PermissionError(
            f"Permission denied creating directory '{output_dir}': {str(e)}"
        ) from e
    except OSError as e:
        raise OSError(
            f"Failed to create output directory '{output_dir}': {str(e)}"
        ) from e
    
    # Generate filename if not provided
    if filename is None:
        filename = generate_filename(metadata)
    
    # Ensure .html extension
    if not filename.endswith('.html'):
        filename += '.html'
    
    # Full file path
    file_path = output_path / filename
    
    # Save file with UTF-8 encoding
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Report saved successfully: {file_path.absolute()}")
        return str(file_path.absolute())
        
    except PermissionError as e:
        raise PermissionError(
            f"Permission denied writing to '{file_path}': {str(e)}"
        ) from e
    except OSError as e:
        # Handle disk full, invalid filename, etc.
        raise OSError(
            f"Failed to save report to '{file_path}': {str(e)}"
        ) from e


def generate_filename(metadata: Optional[dict] = None) -> str:
    """
    Generate report filename from metadata.
    
    Format: report_r{run}_{step}_{timestamp}.html
    Example: report_r2_39_2025-08-28T09_40_10.html
    
    If metadata is incomplete, generates: report_{current_timestamp}.html
    
    Args:
        metadata: Dictionary with 'test_id' and 'timestamp' keys
    
    Returns:
        Generated filename (without .html extension)
        
    Example:
        >>> metadata = {'test_id': 'r2_39', 'timestamp': '2025-08-28T09:40:10'}
        >>> filename = generate_filename(metadata)
        >>> print(filename)
        'report_r2_39_2025-08-28T09_40_10'
    """
    if metadata and 'test_id' in metadata and 'timestamp' in metadata:
        test_id = metadata['test_id']
        timestamp = metadata['timestamp']
        
        # Clean timestamp (replace colons with underscores for filename safety)
        timestamp_clean = timestamp.replace(':', '_')
        
        return f"report_{test_id}_{timestamp_clean}"
    else:
        # Fallback to current timestamp
        current_time = datetime.now().strftime('%Y-%m-%dT%H_%M_%S')
        return f"report_{current_time}"


def validate_single_file_portability(file_path: str) -> bool:
    """
    Validate that HTML report is a single portable file.
    
    Checks that:
    - File exists
    - File is readable
    - HTML content doesn't reference external files (except CDN for Plotly)
    
    Args:
        file_path: Path to HTML file to validate
    
    Returns:
        True if file is portable, False otherwise
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Report file not found: {file_path}")
    
    if not path.is_file():
        logger.error(f"Path is not a file: {file_path}")
        return False
    
    try:
        # Read file and check for external references
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for problematic external references
        external_patterns = [
            '<link rel="stylesheet"',  # External CSS
            '@import url(',  # CSS imports
            '<script src="http',  # External scripts (except CDN)
            '<img src="http',  # External images (should be data URLs)
        ]
        
        issues = []
        for pattern in external_patterns:
            if pattern in content:
                # Allow Plotly CDN
                if 'plotly' in content[content.find(pattern):content.find(pattern) + 200].lower():
                    continue
                issues.append(pattern)
        
        if issues:
            logger.warning(
                f"File may have external dependencies: {', '.join(issues)}"
            )
            return False
        
        logger.info(f"File validated as portable: {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error validating file portability: {str(e)}")
        return False


def cleanup_old_reports(
    output_dir: str = "reports",
    max_age_days: int = 30,
    dry_run: bool = False
) -> int:
    """
    Remove old report files from output directory.
    
    Args:
        output_dir: Directory containing reports
        max_age_days: Maximum age in days (files older will be deleted)
        dry_run: If True, only list files without deleting
    
    Returns:
        Number of files deleted (or would be deleted in dry_run mode)
        
    Example:
        >>> # Delete reports older than 30 days
        >>> count = cleanup_old_reports(max_age_days=30)
        >>> print(f"Deleted {count} old reports")
    """
    output_path = Path(output_dir)
    
    if not output_path.exists():
        logger.warning(f"Output directory does not exist: {output_dir}")
        return 0
    
    current_time = datetime.now().timestamp()
    max_age_seconds = max_age_days * 24 * 60 * 60
    
    deleted_count = 0
    
    for file_path in output_path.glob('report_*.html'):
        try:
            file_age = current_time - file_path.stat().st_mtime
            
            if file_age > max_age_seconds:
                if dry_run:
                    logger.info(f"Would delete old report: {file_path.name}")
                    deleted_count += 1
                else:
                    file_path.unlink()
                    logger.info(f"Deleted old report: {file_path.name}")
                    deleted_count += 1
                    
        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {str(e)}")
            continue
    
    action = "Would delete" if dry_run else "Deleted"
    logger.info(f"{action} {deleted_count} old reports from {output_dir}")
    return deleted_count


def get_report_list(output_dir: str = "reports") -> list:
    """
    Get list of all reports in output directory.
    
    Args:
        output_dir: Directory containing reports
    
    Returns:
        List of dictionaries with report info (filename, path, size, modified_time)
        
    Example:
        >>> reports = get_report_list()
        >>> for report in reports:
        ...     print(f"{report['filename']}: {report['size']} bytes")
    """
    output_path = Path(output_dir)
    
    if not output_path.exists():
        logger.warning(f"Output directory does not exist: {output_dir}")
        return []
    
    reports = []
    
    for file_path in sorted(output_path.glob('report_*.html'), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            stat = file_path.stat()
            reports.append({
                'filename': file_path.name,
                'path': str(file_path.absolute()),
                'size': stat.st_size,
                'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        except Exception as e:
            logger.error(f"Error reading {file_path.name}: {str(e)}")
            continue
    
    return reports

