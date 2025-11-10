"""
Interactive Power Timeline Visualization.

This module creates Plotly-based interactive charts showing power consumption
over time with key thresholds, action markers, and zone overlays.
"""

import plotly.graph_objects as go
from plotly.offline import plot
from typing import Dict, Any, List, Optional
import logging
import pandas as pd

logger = logging.getLogger(__name__)


class PowerTimelinePlotter:
    """
    Creates interactive power timeline visualizations with zone overlays.
    
    This class handles the creation of time-series plots with:
    - Power consumption over time
    - Action time marker (t=0)
    - Band entry zone overlay
    - Setpoint zone overlay
    - Interactive hover tooltips
    """
    
    def __init__(self, raw_data: List[Dict[str, Any]], metrics: Dict[str, Any], metadata: Dict[str, Any]):
        """
        Initialize plotter with data and metrics from Phase 1 orchestrator.
        
        Args:
            raw_data: List of dictionaries containing preprocessed time-series data
            metrics: Dictionary of calculated metrics
            metadata: Processing metadata
        """
        self.raw_data = raw_data
        self.metrics = metrics
        self.metadata = metadata
        
        # Convert raw_data to DataFrame for easier manipulation
        self.df = pd.DataFrame(raw_data)
        
        # Validate required columns exist
        # Note: Column names are standardized by ingestion (miner. prefix removed)
        required_columns = ['seconds', 'summary_wattage']
        missing_columns = [col for col in required_columns if col not in self.df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        logger.debug(f"Initialized plotter with {len(self.df)} data points")
    
    def create_power_timeline(self) -> go.Figure:
        """
        Create interactive power timeline plot with all overlays and markers.
        
        Returns:
            Plotly Figure object with complete visualization
        """
        logger.info("Creating power timeline visualization")
        
        # Create base figure
        fig = go.Figure()
        
        # Add main power trace
        self._add_power_trace(fig)
        
        # Add miner mode (target power) trace
        self._add_mode_power_trace(fig)
        
        # Add zone overlays
        self._add_band_entry_zone(fig)
        self._add_setpoint_zone(fig)
        
        # Add action marker (t=0 vertical line)
        self._add_action_marker(fig)
        
        # Configure layout
        self._configure_layout(fig)
        
        logger.info("Power timeline visualization created successfully")
        return fig
    
    def _add_power_trace(self, fig: go.Figure) -> None:
        """Add the main power consumption time-series trace."""
        time_seconds = self.df['seconds'].tolist()
        power_watts = self.df['summary_wattage'].tolist()
        
        # Create hover text with additional information
        hover_text = []
        for idx, row in self.df.iterrows():
            text = (
                f"<b>Time:</b> {row['seconds']:.1f}s<br>"
                f"<b>Power:</b> {row['summary_wattage']:.1f}W<br>"
            )
            
            # Add temperature if available
            if 'temp_hash_board_max' in row and pd.notna(row['temp_hash_board_max']):
                text += f"<b>Hash Board Temp:</b> {row['temp_hash_board_max']:.1f}°C<br>"
            if 'psu_temp_max' in row and pd.notna(row['psu_temp_max']):
                text += f"<b>PSU Temp:</b> {row['psu_temp_max']:.1f}°C"
            
            hover_text.append(text)
        
        fig.add_trace(go.Scatter(
            x=time_seconds,
            y=power_watts,
            mode='lines',
            name='Actual Power',
            line=dict(color='#2E86DE', width=2),
            hovertext=hover_text,
            hoverinfo='text',
            showlegend=True
        ))
    
    def _add_mode_power_trace(self, fig: go.Figure) -> None:
        """Add miner mode power (target/commanded power) trace as light red line."""
        # Check if mode_power column exists
        if 'mode_power' not in self.df.columns:
            logger.warning("mode_power column not available, skipping mode power trace")
            return
        
        time_seconds = self.df['seconds'].tolist()
        mode_power = self.df['mode_power'].tolist()
        
        # Create hover text
        hover_text = []
        for idx, row in self.df.iterrows():
            if pd.notna(row['mode_power']):
                text = (
                    f"<b>Time:</b> {row['seconds']:.1f}s<br>"
                    f"<b>Target Power:</b> {row['mode_power']:.1f}W"
                )
                hover_text.append(text)
            else:
                hover_text.append("")
        
        fig.add_trace(go.Scatter(
            x=time_seconds,
            y=mode_power,
            mode='lines',
            name='Target Power (Mode)',
            line=dict(color='rgba(255, 99, 71, 0.6)', width=2),
            hovertext=hover_text,
            hoverinfo='text',
            showlegend=True
        ))
        
        logger.debug("Added miner mode power trace")
    
    def _add_band_entry_zone(self, fig: go.Figure) -> None:
        """Add band entry zone overlay (±5% of target power)."""
        # Get target power after action
        target_power_after = self.metrics.get('target_power', {}).get('after')
        
        if target_power_after is None:
            logger.warning("Target power not available, skipping band entry zone")
            return
        
        # Calculate ±5% band
        band_lower = target_power_after * 0.95
        band_upper = target_power_after * 1.05
        
        # Get time range
        time_min = self.df['seconds'].min()
        time_max = self.df['seconds'].max()
        
        # Add band zone as filled area
        fig.add_trace(go.Scatter(
            x=[time_min, time_max, time_max, time_min, time_min],
            y=[band_lower, band_lower, band_upper, band_upper, band_lower],
            fill='toself',
            fillcolor='rgba(255, 195, 0, 0.15)',
            line=dict(width=0),
            name='Band Entry Zone (±5%)',
            hoverinfo='skip',
            showlegend=True
        ))
        
        logger.debug(f"Added band entry zone: {band_lower:.1f}W - {band_upper:.1f}W")
    
    def _add_setpoint_zone(self, fig: go.Figure) -> None:
        """Add setpoint zone overlay (±2% of target power)."""
        # Get target power after action
        target_power_after = self.metrics.get('target_power', {}).get('after')
        
        if target_power_after is None:
            logger.warning("Target power not available, skipping setpoint zone")
            return
        
        # Calculate ±2% setpoint zone
        setpoint_lower = target_power_after * 0.98
        setpoint_upper = target_power_after * 1.02
        
        # Get time range
        time_min = self.df['seconds'].min()
        time_max = self.df['seconds'].max()
        
        # Add setpoint zone as filled area
        fig.add_trace(go.Scatter(
            x=[time_min, time_max, time_max, time_min, time_min],
            y=[setpoint_lower, setpoint_lower, setpoint_upper, setpoint_upper, setpoint_lower],
            fill='toself',
            fillcolor='rgba(46, 213, 115, 0.2)',
            line=dict(width=0),
            name='Setpoint Zone (±2%)',
            hoverinfo='skip',
            showlegend=True
        ))
        
        logger.debug(f"Added setpoint zone: {setpoint_lower:.1f}W - {setpoint_upper:.1f}W")
    
    def _add_action_marker(self, fig: go.Figure) -> None:
        """Add vertical line at t=0 marking the action time."""
        # Get y-axis range for vertical line
        power_values = self.df['summary_wattage']
        y_min = power_values.min()
        y_max = power_values.max()
        
        # Add some padding to y-axis range
        y_padding = (y_max - y_min) * 0.1
        y_min -= y_padding
        y_max += y_padding
        
        # Add vertical line at t=0
        fig.add_trace(go.Scatter(
            x=[0, 0],
            y=[y_min, y_max],
            mode='lines',
            line=dict(color='red', width=2, dash='dash'),
            name='Action Time (t=0)',
            hoverinfo='skip',
            showlegend=True
        ))
        
        logger.debug("Added action marker at t=0")
    
    def _configure_layout(self, fig: go.Figure) -> None:
        """Configure plot layout, axes, and styling."""
        # Get step direction for title
        step_direction = self.metrics.get('step_direction', {}).get('direction', 'Unknown')
        target_before = self.metrics.get('target_power', {}).get('before')
        target_after = self.metrics.get('target_power', {}).get('after')
        
        # Build title
        title = "Power Profile Timeline"
        if target_before and target_after:
            title += f" ({step_direction}: {target_before:.0f}W → {target_after:.0f}W)"
        
        fig.update_layout(
            title={
                'text': title,
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 18, 'color': '#2C3E50'}
            },
            xaxis_title="Time (seconds)",
            yaxis_title="Power (W)",
            xaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128, 128, 128, 0.2)',
                zeroline=True,
                zerolinewidth=2,
                zerolinecolor='rgba(128, 128, 128, 0.3)',
            ),
            yaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128, 128, 128, 0.2)',
            ),
            hovermode='closest',
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(family='Arial, sans-serif', size=12, color='#2C3E50'),
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1,
                bgcolor='rgba(255, 255, 255, 0.8)',
                bordercolor='rgba(128, 128, 128, 0.5)',
                borderwidth=1
            ),
            margin=dict(l=80, r=40, t=100, b=80),
        )


def create_power_timeline(
    raw_data: List[Dict[str, Any]],
    metrics: Dict[str, Any],
    metadata: Dict[str, Any]
) -> go.Figure:
    """
    Create an interactive power timeline visualization.
    
    This is the main entry point for creating power timeline plots.
    
    Args:
        raw_data: List of dictionaries containing preprocessed time-series data
        metrics: Dictionary of calculated metrics from Phase 1
        metadata: Processing metadata
    
    Returns:
        Plotly Figure object ready for display or HTML export
    
    Raises:
        ValueError: If required data or columns are missing
        
    Example:
        >>> from src.metrics.orchestrator import MetricOrchestrator
        >>> orchestrator = MetricOrchestrator()
        >>> result = orchestrator.process_file('data.csv')
        >>> fig = create_power_timeline(result['raw_data'], result['metrics'], result['metadata'])
    """
    plotter = PowerTimelinePlotter(raw_data, metrics, metadata)
    return plotter.create_power_timeline()


def figure_to_html(fig: go.Figure, include_plotlyjs: str = 'cdn') -> str:
    """
    Convert Plotly figure to self-contained HTML.
    
    Args:
        fig: Plotly Figure object to convert
        include_plotlyjs: How to include Plotly.js library:
            - 'cdn': Load from CDN (default, smallest file size)
            - True: Embed full library (self-contained, ~3MB)
            - False: Don't include library (requires external script)
    
    Returns:
        HTML string containing the complete plot
        
    Example:
        >>> fig = create_power_timeline(raw_data, metrics, metadata)
        >>> html = figure_to_html(fig, include_plotlyjs=True)  # Self-contained
        >>> with open('report.html', 'w') as f:
        ...     f.write(html)
    """
    logger.info(f"Converting figure to HTML (include_plotlyjs={include_plotlyjs})")
    
    # Convert figure to HTML div
    html = plot(
        fig,
        include_plotlyjs=include_plotlyjs,
        output_type='div',
        config={
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
            'toImageButtonOptions': {
                'format': 'png',
                'filename': 'power_timeline',
                'height': 800,
                'width': 1200,
                'scale': 2
            }
        }
    )
    
    logger.info("Figure converted to HTML successfully")
    return html

