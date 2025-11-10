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
        start_data = metrics['start_power']
        median = start_data.get('median') or start_data.get('value')
        last_value = start_data.get('last_value')
        difference = start_data.get('difference')
        
        if median is not None:
            # Build expandable details
            details_parts = [
                f"<strong>Median:</strong> {median:.1f}W",
            ]
            if last_value is not None:
                details_parts.append(f"<strong>Last Value:</strong> {last_value:.1f}W")
            if difference is not None:
                details_parts.append(f"<strong>Difference:</strong> {difference:.1f}W")
            
            details_html = "<br>".join(details_parts)
            
            rows.append({
                'name': 'Start Power',
                'value': f"{median:.1f} W",
                'description': 'Average power in first 10 samples',
                'details': details_html
            })
    
    # Metric 2: Target Power
    if 'target_power' in metrics:
        target_data = metrics['target_power']
        before = target_data.get('before')
        after = target_data.get('after')
        change = target_data.get('change')
        
        if before is not None and after is not None:
            # Build expandable details
            details_parts = [
                f"<strong>Before:</strong> {before:.1f}W",
                f"<strong>After:</strong> {after:.1f}W",
            ]
            if change is not None:
                details_parts.append(f"<strong>Change:</strong> {change:.1f}W")
            
            details_html = "<br>".join(details_parts)
            
            rows.append({
                'name': 'Target Power',
                'value': f"{before:.0f} W → {after:.0f} W",
                'description': 'Power transition (before → after action)',
                'details': details_html
            })
    
    # Metric 3: Step Direction
    if 'step_direction' in metrics:
        step_data = metrics['step_direction']
        direction = step_data.get('direction')
        delta = step_data.get('delta') or step_data.get('magnitude')
        description_text = step_data.get('description')
        
        if direction and delta is not None:
            # Build expandable details
            details_parts = [
                f"<strong>Direction:</strong> {direction}",
                f"<strong>Delta:</strong> {delta:.1f}W",
            ]
            if description_text:
                details_parts.append(f"<strong>Description:</strong> {description_text}")
            
            details_html = "<br>".join(details_parts)
            
            rows.append({
                'name': 'Step Direction',
                'value': f"{direction} ({delta:+.0f} W)",
                'description': 'Direction and magnitude of power change',
                'details': details_html
            })
    
    # Metric 4: Temperature Ranges
    if 'temperature_ranges' in metrics:
        temp_data = metrics['temperature_ranges']
        # Phase 1 returns 'board' and 'psu', not 'hash_board_max' and 'psu_temp_max'
        board = temp_data.get('board', {})
        psu = temp_data.get('psu', {})
        
        temp_parts = []
        details_parts = []
        
        if board.get('min') is not None and board.get('max') is not None:
            temp_parts.append(f"Hash Board: {board['min']:.2f}°C - {board['max']:.2f}°C")
            details_parts.append(f"<strong>Hash Board:</strong> Min={board['min']:.2f}°C, Max={board['max']:.2f}°C, Range={board.get('range', 0):.2f}°C")
        
        if psu.get('min') is not None and psu.get('max') is not None:
            temp_parts.append(f"PSU: {psu['min']:.2f}°C - {psu['max']:.2f}°C")
            details_parts.append(f"<strong>PSU:</strong> Min={psu['min']:.2f}°C, Max={psu['max']:.2f}°C, Range={psu.get('range', 0):.2f}°C")
        
        if temp_parts:
            rows.append({
                'name': 'Temperature Ranges',
                'value': '<br>'.join(temp_parts),
                'description': 'Min-max temperature ranges during test',
                'details': "<br>".join(details_parts)
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
        percentage = band_data.get('percentage')
        band_limits = band_data.get('band_limits', {})
        entry_method = band_data.get('entry_method')
        
        if status == 'ENTERED' and time_val is not None:
            value_str = f"✓ Entered at t={time_val:.1f}s"
            if wattage:
                value_str += f" ({wattage:.0f}W)"
            
            # Build expandable details
            details_parts = [
                f"<strong>Status:</strong> {status}",
                f"<strong>Time:</strong> {time_val:.6f}s",
                f"<strong>Wattage:</strong> {wattage:.1f}W" if wattage else "",
            ]
            if percentage is not None:
                details_parts.append(f"<strong>Percentage:</strong> {percentage:.2f}%")
            if band_limits:
                lower = band_limits.get('lower', 0)
                upper = band_limits.get('upper', 0)
                tolerance = band_limits.get('tolerance', 0)
                details_parts.append(f"<strong>Band Limits:</strong> {lower:.1f}W - {upper:.1f}W (±{tolerance:.1f}W)")
            if entry_method:
                details_parts.append(f"<strong>Entry Method:</strong> {entry_method}")
            
            details_html = "<br>".join([p for p in details_parts if p])
        else:
            value_str = "✗ Never entered band"
            details_html = f"<strong>Status:</strong> {status or 'NEVER_ENTERED'}"
        
        rows.append({
            'name': 'Band Entry (±5%)',
            'value': value_str,
            'description': 'Time to enter ±5% band around target power',
            'details': details_html
        })
    
    # Metric 6: Setpoint Hit
    if 'setpoint_hit' in metrics:
        setpoint_data = metrics['setpoint_hit']
        # Phase 1 returns complex structure with 'summary' containing first_sustained_hit_time
        summary = setpoint_data.get('summary', {})
        never_hit = summary.get('never_sustained', True)
        first_hit_time = summary.get('first_sustained_hit_time')
        total_hits = summary.get('total_sustained_hits', 0)
        total_touches = summary.get('total_brief_touches', 0)
        brief_touches = setpoint_data.get('brief_touches', [])
        sustained_hits = setpoint_data.get('sustained_hits', [])
        
        if not never_hit and first_hit_time is not None:
            value_str = f"✓ Hit at t={first_hit_time:.1f}s"
            if total_hits > 1:
                value_str += f" ({total_hits} sustained hits)"
            
            # Build expandable details
            details_parts = [
                f"<strong>Sustained Hits:</strong> {total_hits}",
                f"<strong>Brief Touches:</strong> {total_touches}",
            ]
            
            # Add brief touch times
            if brief_touches:
                touch_times = ", ".join([f"t={t.get('time', 0):.6f}s" for t in brief_touches[:5]])
                if len(brief_touches) > 5:
                    touch_times += f", ... and {len(brief_touches) - 5} more"
                details_parts.append(f"<strong>Brief Touch Times:</strong> {touch_times}")
            
            # Add sustained hit details
            if sustained_hits:
                for idx, hit in enumerate(sustained_hits[:3], 1):
                    hit_time = hit.get('start_time')
                    duration = hit.get('duration')
                    if hit_time is not None and duration is not None:
                        # Time values use 6 decimals, durations use 2 decimals (per reference doc)
                        details_parts.append(f"<strong>Sustained Hit #{idx}:</strong> Time={hit_time:.6f}s, Duration={duration:.2f}s")
            
            details_html = "<br>".join(details_parts)
        else:
            value_str = "✗ Never hit setpoint"
            details_html = "<strong>Sustained Hits:</strong> 0<br><strong>Brief Touches:</strong> 0"
        
        rows.append({
            'name': 'Setpoint Hit (±2%)',
            'value': value_str,
            'description': 'Time to reach ±2% of target power',
            'details': details_html
        })
    
    # Metric 7: Stable Plateau
    if 'stable_plateau' in metrics:
        plateau_data = metrics['stable_plateau']
        # Phase 1 returns 'plateaus' list and 'summary' with counts
        plateaus = plateau_data.get('plateaus', [])
        summary = plateau_data.get('summary', {})
        plateau_count = summary.get('total_count', 0)
        longest_duration = summary.get('longest_duration', 0)
        total_stable_time = summary.get('total_stable_time', 0)
        
        if plateau_count > 0 and plateaus:
            first_plateau = plateaus[0]
            start_time = first_plateau.get('start_time')
            duration = first_plateau.get('duration')
            value_str = f"✓ Achieved at t={start_time:.1f}s"
            if duration:
                # Durations use 2 decimals per reference doc
                value_str += f" (duration: {duration:.2f}s)"
            
            # Build expandable details
            # Durations use 2 decimals per reference doc
            details_parts = [
                f"<strong>Total Plateaus:</strong> {plateau_count}",
                f"<strong>Longest Duration:</strong> {longest_duration:.2f}s",
                f"<strong>Total Stable Time:</strong> {total_stable_time:.2f}s",
            ]
            
            # Add plateau ranges
            if plateaus:
                plateau_ranges = []
                for p in plateaus[:5]:
                    start = p.get('start_time')
                    exit_time = p.get('exit_time')
                    if start is not None and exit_time is not None:
                        plateau_ranges.append(f"t={start:.1f}-{exit_time:.1f}s")
                if len(plateaus) > 5:
                    plateau_ranges.append(f"... and {len(plateaus) - 5} more")
                details_parts.append(f"<strong>Plateau Ranges:</strong> {' and '.join(plateau_ranges)}")
            
            details_html = "<br>".join(details_parts)
        else:
            value_str = "✗ No stable plateau detected"
            details_html = "<strong>Total Plateaus:</strong> 0<br><strong>Longest Duration:</strong> 0.0s<br><strong>Total Stable Time:</strong> 0.0s"
        
        rows.append({
            'name': 'Stable Plateau',
            'value': value_str,
            'description': '30s window with power within ±2% of target',
            'details': details_html
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
        drop_list = drops_data.get('sharp_drops', [])
        threshold = drops_data.get('threshold', 'N/A')
        
        value_str = f"{count} drop(s) detected"
        
        # Build expandable details
        details_parts = [
            f"<strong>Count:</strong> {count}",
            f"<strong>Threshold:</strong> {threshold}%" if isinstance(threshold, (int, float)) else f"<strong>Threshold:</strong> N/A%",
        ]
        
        if drop_list:
            drop_times = ", ".join([f"t={d.get('time', 0):.6f}s" for d in drop_list[:10]])
            if len(drop_list) > 10:
                drop_times += f", ... and {len(drop_list) - 10} more"
            details_parts.append(f"<strong>Times:</strong> {drop_times}")
        
        details_html = "<br>".join(details_parts)
        
        rows.append({
            'name': 'Sharp Drops',
            'value': value_str,
            'description': 'Power drops >200W in 5s window',
            'details': details_html
        })
    
    # Metric 9: Sharp Rises  
    if 'sharp_rises' in metrics:
        rises_data = metrics['sharp_rises']
        # Phase 1 returns 'summary' with 'count' and 'sharp_rises' list
        summary = rises_data.get('summary', {})
        count = summary.get('count', 0)
        rise_list = rises_data.get('sharp_rises', [])
        threshold = rises_data.get('threshold', 'N/A')
        
        value_str = f"{count} rise(s) detected"
        
        # Build expandable details
        details_parts = [
            f"<strong>Count:</strong> {count}",
            f"<strong>Threshold:</strong> {threshold}%" if isinstance(threshold, (int, float)) else f"<strong>Threshold:</strong> N/A%",
        ]
        
        if rise_list:
            rise_times = ", ".join([f"t={r.get('time', 0):.6f}s" for r in rise_list[:10]])
            if len(rise_list) > 10:
                rise_times += f", ... and {len(rise_list) - 10} more"
            details_parts.append(f"<strong>Times:</strong> {rise_times}")
        
        details_html = "<br>".join(details_parts)
        
        rows.append({
            'name': 'Sharp Rises',
            'value': value_str,
            'description': 'Power rises >200W in 5s window (excludes normal transitions)',
            'details': details_html
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
            
            # Build expandable details for overshoot
            details_html = f"<strong>Overshoot Occurred:</strong> {overshoot_occurred}"
        elif undershoot_occurred:
            value_str = "✓ Undershoot detected"
            time_val = undershoot.get('time')
            magnitude = undershoot.get('magnitude')
            if time_val is not None:
                value_str += f" at t={time_val:.1f}s"
            if magnitude is not None:
                value_str += f" ({magnitude:+.0f}W)"
            
            # Build expandable details for undershoot
            details_html = f"<strong>Undershoot Occurred:</strong> {undershoot_occurred}"
        else:
            value_str = "✗ No overshoot/undershoot"
            details_html = "<strong>Overshoot Occurred:</strong> False"
        
        rows.append({
            'name': 'Overshoot/Undershoot',
            'value': value_str,
            'description': 'Power exceeds band by >5% after initial transition',
            'details': details_html
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
            f'<td class="metric-description">',
            row["description"]
        ])
        
        # Add expandable details if present
        if 'details' in row and row['details']:
            html_parts.extend([
                '<details class="metric-details" style="margin-top: 8px;">',
                '<summary style="cursor: pointer; color: #3498db; font-weight: 500;">▶ View Details</summary>',
                f'<div class="details-content" style="margin-top: 8px; padding: 8px; background: #f8f9fa; border-left: 3px solid #3498db; font-size: 0.9em;">',
                row['details'],
                '</div>',
                '</details>'
            ])
        
        html_parts.extend([
            '</td>',
            '</tr>'
        ])
    
    html_parts.extend([
        '</tbody>',
        '</table>',
        '</div>'
    ])
    
    return '\n'.join(html_parts)

