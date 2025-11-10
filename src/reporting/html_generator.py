"""
HTML Report Generator - Assemble complete HTML documents.

This module creates complete, self-contained HTML reports with:
- Embedded CSS (no external dependencies)
- Responsive design for mobile/desktop
- Fixed section ordering
- Semantic HTML5 structure
"""

from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def generate_html_report(
    metrics: Dict[str, Any],
    metadata: Dict[str, Any],
    chart_html: str,
    analysis_text: Optional[str] = None
) -> str:
    """
    Generate complete HTML report with all sections.
    
    Creates a self-contained HTML document with:
    1. Header (title and timestamp)
    2. Metadata (file info, test details)
    3. Analysis (Claude-generated insights)
    4. Metrics (formatted tables)
    5. Chart (Plotly visualization)
    
    Args:
        metrics: Dictionary of calculated metrics
        metadata: Processing metadata (filename, test info, etc.)
        chart_html: Plotly chart as HTML div
        analysis_text: Optional Claude-generated analysis narrative
    
    Returns:
        Complete HTML document as string
        
    Example:
        >>> from src.metrics.orchestrator import MetricOrchestrator
        >>> orchestrator = MetricOrchestrator()
        >>> result = orchestrator.process_file('data.csv')
        >>> html = generate_html_report(
        ...     result['metrics'],
        ...     result['metadata'],
        ...     chart_html,
        ...     analysis_text
        ... )
    """
    logger.info("Generating HTML report")
    
    # Build HTML sections
    html_parts = [
        _get_html_header(),
        _get_embedded_css(),
        '</head>',
        '<body>',
        '<div class="container">',
        _generate_header_section(metadata),
        _generate_metadata_section(metadata),
    ]
    
    # Add analysis section if available
    if analysis_text:
        html_parts.append(_generate_analysis_section(analysis_text))
    
    # Add metrics section
    html_parts.append(_generate_metrics_section(metrics))
    
    # Add chart section
    html_parts.append(_generate_chart_section(chart_html))
    
    # Close document
    html_parts.extend([
        '</div>',  # Close container
        '</body>',
        '</html>'
    ])
    
    logger.info("HTML report generated successfully")
    return '\n'.join(html_parts)


def _get_html_header() -> str:
    """Generate HTML document header with meta tags."""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Power Profile Test Report">
    <title>Power Profile Report</title>'''


def _get_embedded_css() -> str:
    """Generate embedded CSS styles for the report."""
    return '''
    <style>
        /* Reset and Base Styles */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 
                         'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #2C3E50;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }
        
        /* Container */
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            overflow: hidden;
        }
        
        /* Header Section */
        .report-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        
        .report-header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 700;
        }
        
        .report-header .timestamp {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        /* Section Containers */
        .section {
            padding: 40px;
            border-bottom: 1px solid #ecf0f1;
        }
        
        .section:last-child {
            border-bottom: none;
        }
        
        .section-title {
            font-size: 1.8em;
            color: #2C3E50;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
            display: inline-block;
        }
        
        /* Metadata Section */
        .metadata-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .metadata-item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        
        .metadata-item .label {
            font-size: 0.9em;
            color: #7f8c8d;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 5px;
        }
        
        .metadata-item .value {
            font-size: 1.1em;
            font-weight: 600;
            color: #2C3E50;
        }
        
        /* Analysis Section */
        .analysis-content {
            background: #f8f9fa;
            padding: 25px;
            border-radius: 8px;
            border-left: 4px solid #3498db;
            line-height: 1.8;
            font-size: 1.05em;
        }
        
        .analysis-content p {
            margin-bottom: 15px;
        }
        
        .analysis-content p:last-child {
            margin-bottom: 0;
        }
        
        /* Metrics Section */
        .metrics-container {
            margin-top: 20px;
        }
        
        .metrics-category {
            margin-bottom: 40px;
        }
        
        .metrics-category:last-child {
            margin-bottom: 0;
        }
        
        .category-title {
            font-size: 1.4em;
            color: #667eea;
            margin-bottom: 15px;
            font-weight: 600;
        }
        
        .metrics-table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            border-radius: 8px;
            overflow: hidden;
        }
        
        .metrics-table thead {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .metrics-table th {
            padding: 15px;
            text-align: left;
            font-weight: 600;
            font-size: 0.95em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .metrics-table tbody tr {
            border-bottom: 1px solid #ecf0f1;
            transition: background-color 0.2s;
        }
        
        .metrics-table tbody tr:hover {
            background-color: #f8f9fa;
        }
        
        .metrics-table tbody tr:last-child {
            border-bottom: none;
        }
        
        .metrics-table td {
            padding: 15px;
        }
        
        .metrics-table .metric-name {
            font-weight: 600;
            color: #2C3E50;
            width: 25%;
        }
        
        .metrics-table .metric-value {
            font-family: 'Courier New', monospace;
            color: #27ae60;
            width: 35%;
        }
        
        .metrics-table .metric-description {
            color: #7f8c8d;
            font-size: 0.95em;
            width: 40%;
        }
        
        /* Anomaly Details */
        .anomaly-details {
            margin: 10px 0 0 20px;
            list-style-type: disc;
        }
        
        .anomaly-details li {
            color: #e74c3c;
            margin: 5px 0;
            font-size: 0.9em;
        }
        
        /* Chart Section */
        .chart-container {
            margin-top: 20px;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        
        /* No Data Message */
        .no-data {
            text-align: center;
            color: #7f8c8d;
            font-style: italic;
            padding: 20px;
        }
        
        /* Responsive Design */
        @media (max-width: 768px) {
            body {
                padding: 10px;
            }
            
            .report-header {
                padding: 25px;
            }
            
            .report-header h1 {
                font-size: 1.8em;
            }
            
            .section {
                padding: 25px;
            }
            
            .section-title {
                font-size: 1.4em;
            }
            
            .metadata-grid {
                grid-template-columns: 1fr;
            }
            
            .metrics-table {
                font-size: 0.9em;
            }
            
            .metrics-table th,
            .metrics-table td {
                padding: 10px;
            }
            
            /* Make table scrollable on mobile */
            .metrics-category {
                overflow-x: auto;
            }
        }
        
        @media print {
            body {
                background: white;
                padding: 0;
            }
            
            .container {
                box-shadow: none;
            }
            
            .section {
                page-break-inside: avoid;
            }
        }
    </style>'''


def _generate_header_section(metadata: Dict[str, Any]) -> str:
    """Generate report header with title and timestamp."""
    # Get test info from metadata
    test_id = metadata.get('test_id', 'Unknown Test')
    
    # Format current timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    return f'''
    <div class="report-header">
        <h1>Power Profile Test Report</h1>
        <p class="timestamp">Test ID: {test_id} | Generated: {timestamp}</p>
    </div>'''


def _generate_metadata_section(metadata: Dict[str, Any]) -> str:
    """Generate metadata section with file and test information."""
    # Extract metadata fields - Phase 1 returns different keys
    filename = metadata.get('filename', 'Unknown')
    test_id = metadata.get('test_id', 'N/A')
    miner_number = metadata.get('miner_number', 'N/A')
    timestamp = metadata.get('timestamp', 'N/A')
    
    # Phase 1 uses 'total_rows', not 'total_samples'
    total_samples = metadata.get('total_rows') or metadata.get('total_samples', 0)
    
    # Phase 1 uses 'processing_time_seconds', not 'duration_seconds'
    duration = metadata.get('processing_time_seconds') or metadata.get('duration_seconds', 0)
    
    # Phase 1 uses 'transition_direction', not 'step_direction'
    step_direction = metadata.get('transition_direction') or metadata.get('step_direction', 'N/A')
    
    return f'''
    <div class="section metadata-section">
        <h2 class="section-title">Test Information</h2>
        <div class="metadata-grid">
            <div class="metadata-item">
                <div class="label">Source File</div>
                <div class="value">{filename}</div>
            </div>
            <div class="metadata-item">
                <div class="label">Test ID</div>
                <div class="value">{test_id}</div>
            </div>
            <div class="metadata-item">
                <div class="label">Miner Number</div>
                <div class="value">{miner_number}</div>
            </div>
            <div class="metadata-item">
                <div class="label">Test Timestamp</div>
                <div class="value">{timestamp}</div>
            </div>
            <div class="metadata-item">
                <div class="label">Step Direction</div>
                <div class="value">{step_direction}</div>
            </div>
            <div class="metadata-item">
                <div class="label">Total Samples</div>
                <div class="value">{total_samples:,}</div>
            </div>
            <div class="metadata-item">
                <div class="label">Duration</div>
                <div class="value">{duration:.1f} seconds</div>
            </div>
        </div>
    </div>'''


def _generate_analysis_section(analysis_text: str) -> str:
    """Generate analysis section with Claude-generated insights."""
    # Split text into paragraphs for better formatting
    paragraphs = [p.strip() for p in analysis_text.split('\n\n') if p.strip()]
    
    paragraph_html = '\n'.join([f'<p>{p}</p>' for p in paragraphs])
    
    return f'''
    <div class="section analysis-section">
        <h2 class="section-title">AI Analysis</h2>
        <div class="analysis-content">
            {paragraph_html}
        </div>
    </div>'''


def _generate_metrics_section(metrics: Dict[str, Any]) -> str:
    """Generate metrics section with formatted tables."""
    from src.reporting.metrics_formatter import format_metrics_table
    
    metrics_html = format_metrics_table(metrics)
    
    return f'''
    <div class="section metrics-section">
        <h2 class="section-title">Performance Metrics</h2>
        {metrics_html}
    </div>'''


def _generate_chart_section(chart_html: str) -> str:
    """Generate chart section with Plotly visualization."""
    return f'''
    <div class="section chart-section">
        <h2 class="section-title">Power Timeline</h2>
        <div class="chart-container">
            {chart_html}
        </div>
    </div>'''

