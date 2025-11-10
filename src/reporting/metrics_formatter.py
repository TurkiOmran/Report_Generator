"""
Metrics Formatter - Convert metrics dictionaries to HTML tables.

This module formats calculated metrics into structured HTML tables with:
- Category grouping (Basic, Time-Based, Anomaly)
- Proper numeric formatting with units
- Nested tables for detailed lists
- CSS classes for styling
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


def format_metrics_table(metrics: Dict[str, Any]) -> str:
    """
    Convert metrics dictionary to structured HTML table.
    
    Groups metrics by category and formats values with appropriate
    precision and units. Handles detailed lists as nested structures.
    
    Args:
        metrics: Dictionary containing all calculated metrics
    
    Returns:
        HTML string containing formatted metrics table
        
    Example:
        >>> metrics = {
        ...     'start_power': {'value': 1000.5},
        ...     'target_power': {'before': 1000, 'after': 3500},
        ...     'band_entry': {'entered': True, 'time': 12.5}
        ... }
        >>> html = format_metrics_table(metrics)
    """
    if not metrics:
        logger.warning("Empty metrics dictionary provided")
        return "<p class='no-data'>No metrics available</p>"
    
    # Group metrics by category
    basic_metrics = _extract_basic_metrics(metrics)
    time_metrics = _extract_time_metrics(metrics)
    anomaly_metrics = _extract_anomaly_metrics(metrics)
    
    # Build HTML sections
    html_parts = ['<div class="metrics-container">']
    
    if basic_metrics:
        html_parts.append(_format_category_section('Basic Metrics', basic_metrics))
    
    if time_metrics:
        html_parts.append(_format_category_section('Time-Based Metrics', time_metrics))
    
    if anomaly_metrics:
        html_parts.append(_format_category_section('Anomaly Detection', anomaly_metrics))
    
    html_parts.append('</div>')
    
    return '\n'.join(html_parts)


def _extract_basic_metrics(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract and format basic metrics (1-4)."""
    rows = []
    
    # Metric 1: Start Power
    if 'start_power' in metrics:
        # Phase 1 returns 'median', not 'value'
        value = metrics['start_power'].get('median') or metrics['start_power'].get('value')
        if value is not None:
            rows.append({
                'name': 'Start Power',
                'value': f"{value:.1f} W",
                'description': 'Average power in first 10 samples'
            })
    
    # Metric 2: Target Power
    if 'target_power' in metrics:
        before = metrics['target_power'].get('before')
        after = metrics['target_power'].get('after')
        if before is not None and after is not None:
            rows.append({
                'name': 'Target Power',
                'value': f"{before:.0f} W → {after:.0f} W",
                'description': 'Power transition (before → after action)'
            })
    
    # Metric 3: Step Direction
    if 'step_direction' in metrics:
        direction = metrics['step_direction'].get('direction')
        # Phase 1 returns 'delta', not 'magnitude'
        magnitude = metrics['step_direction'].get('delta') or metrics['step_direction'].get('magnitude')
        if direction and magnitude is not None:
            rows.append({
                'name': 'Step Direction',
                'value': f"{direction} ({magnitude:+.0f} W)",
                'description': 'Direction and magnitude of power change'
            })
    
    # Metric 4: Temperature Ranges
    if 'temperature_ranges' in metrics:
        temp_data = metrics['temperature_ranges']
        hash_board = temp_data.get('hash_board_max', {})
        psu = temp_data.get('psu_temp_max', {})
        
        temp_parts = []
        if hash_board.get('min') is not None and hash_board.get('max') is not None:
            temp_parts.append(f"Hash Board: {hash_board['min']:.1f}°C - {hash_board['max']:.1f}°C")
        if psu.get('min') is not None and psu.get('max') is not None:
            temp_parts.append(f"PSU: {psu['min']:.1f}°C - {psu['max']:.1f}°C")
        
        if temp_parts:
            rows.append({
                'name': 'Temperature Ranges',
                'value': '<br>'.join(temp_parts),
                'description': 'Min-max temperature ranges during test'
            })
    
    return rows


def _extract_time_metrics(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract and format time-based metrics (5-7)."""
    rows = []
    
    # Metric 5: Band Entry
    if 'band_entry' in metrics:
        band_data = metrics['band_entry']
        # Phase 1 returns 'status' with values like 'ENTERED', 'NEVER_ENTERED'
        status = band_data.get('status', '')
        time_val = band_data.get('time')
        wattage = band_data.get('wattage')
        
        if status == 'ENTERED' and time_val is not None:
            value_str = f"✓ Entered at t={time_val:.1f}s"
            if wattage:
                value_str += f" ({wattage:.0f}W)"
        else:
            value_str = "✗ Never entered band"
        
        rows.append({
            'name': 'Band Entry (±5%)',
            'value': value_str,
            'description': 'Time to enter ±5% band around target power'
        })
    
    # Metric 6: Setpoint Hit
    if 'setpoint_hit' in metrics:
        setpoint_data = metrics['setpoint_hit']
        # Phase 1 returns complex structure with 'summary' containing first_sustained_hit_time
        summary = setpoint_data.get('summary', {})
        never_hit = summary.get('never_sustained', True)
        first_hit_time = summary.get('first_sustained_hit_time')
        total_hits = summary.get('total_sustained_hits', 0)
        
        if not never_hit and first_hit_time is not None:
            value_str = f"✓ Hit at t={first_hit_time:.1f}s"
            if total_hits > 1:
                value_str += f" ({total_hits} sustained hits)"
        else:
            value_str = "✗ Never hit setpoint"
        
        rows.append({
            'name': 'Setpoint Hit (±2%)',
            'value': value_str,
            'description': 'Time to reach ±2% of target power'
        })
    
    # Metric 7: Stable Plateau
    if 'stable_plateau' in metrics:
        plateau_data = metrics['stable_plateau']
        # Phase 1 returns 'plateaus' list and 'summary' with counts
        plateaus = plateau_data.get('plateaus', [])
        summary = plateau_data.get('summary', {})
        plateau_count = summary.get('total_count', 0)
        
        if plateau_count > 0 and plateaus:
            first_plateau = plateaus[0]
            start_time = first_plateau.get('start_time')
            duration = first_plateau.get('duration')
            value_str = f"✓ Achieved at t={start_time:.1f}s"
            if duration:
                value_str += f" (duration: {duration:.1f}s)"
        else:
            value_str = "✗ No stable plateau detected"
        
        rows.append({
            'name': 'Stable Plateau',
            'value': value_str,
            'description': '30s window with power within ±2% of target'
        })
    
    return rows


def _extract_anomaly_metrics(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract and format anomaly detection metrics (8-10)."""
    rows = []
    
    # Metric 8: Sharp Drops
    if 'sharp_drops' in metrics:
        drops_data = metrics['sharp_drops']
        # Phase 1 returns 'summary' with 'count' and 'sharp_drops' list
        summary = drops_data.get('summary', {})
        count = summary.get('count', 0)
        details = drops_data.get('sharp_drops', [])
        
        value_str = f"{count} drop(s) detected"
        if details:
            value_str += _format_anomaly_details(details, 'drop')
        
        rows.append({
            'name': 'Sharp Drops',
            'value': value_str,
            'description': 'Power drops >200W in 5s window'
        })
    
    # Metric 9: Sharp Rises  
    if 'sharp_rises' in metrics:
        rises_data = metrics['sharp_rises']
        # Phase 1 returns 'summary' with 'count' and 'sharp_rises' list
        summary = rises_data.get('summary', {})
        count = summary.get('count', 0)
        details = rises_data.get('sharp_rises', [])
        
        value_str = f"{count} rise(s) detected"
        if details:
            value_str += _format_anomaly_details(details, 'rise')
        
        rows.append({
            'name': 'Sharp Rises',
            'value': value_str,
            'description': 'Power rises >200W in 5s window (excludes normal transitions)'
        })
    
    # Metric 10: Overshoot/Undershoot
    if 'overshoot_undershoot' in metrics:
        overshoot_data = metrics['overshoot_undershoot']
        # Phase 1 returns nested 'overshoot' and 'undershoot' objects
        overshoot = overshoot_data.get('overshoot', {})
        undershoot = overshoot_data.get('undershoot', {})
        
        overshoot_occurred = overshoot.get('occurred', False)
        undershoot_occurred = undershoot.get('occurred', False) if undershoot else False
        
        if overshoot_occurred:
            value_str = "✓ Overshoot detected"
            time_val = overshoot.get('time')
            magnitude = overshoot.get('magnitude')
            if time_val is not None:
                value_str += f" at t={time_val:.1f}s"
            if magnitude is not None:
                value_str += f" ({magnitude:+.0f}W)"
        elif undershoot_occurred:
            value_str = "✓ Undershoot detected"
            time_val = undershoot.get('time')
            magnitude = undershoot.get('magnitude')
            if time_val is not None:
                value_str += f" at t={time_val:.1f}s"
            if magnitude is not None:
                value_str += f" ({magnitude:+.0f}W)"
        else:
            value_str = "✗ No overshoot/undershoot"
        
        rows.append({
            'name': 'Overshoot/Undershoot',
            'value': value_str,
            'description': 'Power exceeds band by >5% after initial transition'
        })
    
    return rows


def _format_anomaly_details(details: List[Dict[str, Any]], event_type: str) -> str:
    """Format anomaly details as nested HTML list."""
    if not details:
        return ""
    
    html_parts = ['<ul class="anomaly-details">']
    
    for detail in details[:10]:  # Limit to first 10 events
        time_val = detail.get('time', 'N/A')
        magnitude = detail.get('magnitude', 0)
        
        if time_val != 'N/A':
            html_parts.append(
                f'<li>t={time_val:.1f}s: {magnitude:+.0f}W {event_type}</li>'
            )
    
    if len(details) > 10:
        html_parts.append(f'<li><em>... and {len(details) - 10} more</em></li>')
    
    html_parts.append('</ul>')
    
    return '\n'.join(html_parts)


def _format_category_section(title: str, rows: List[Dict[str, Any]]) -> str:
    """Format a category section with title and metrics table."""
    if not rows:
        return ""
    
    html_parts = [
        f'<div class="metrics-category">',
        f'<h3 class="category-title">{title}</h3>',
        '<table class="metrics-table">',
        '<thead>',
        '<tr>',
        '<th class="metric-name">Metric</th>',
        '<th class="metric-value">Value</th>',
        '<th class="metric-description">Description</th>',
        '</tr>',
        '</thead>',
        '<tbody>'
    ]
    
    for row in rows:
        html_parts.extend([
            '<tr>',
            f'<td class="metric-name">{row["name"]}</td>',
            f'<td class="metric-value">{row["value"]}</td>',
            f'<td class="metric-description">{row["description"]}</td>',
            '</tr>'
        ])
    
    html_parts.extend([
        '</tbody>',
        '</table>',
        '</div>'
    ])
    
    return '\n'.join(html_parts)

