"""
Simple Power Profile Visualizer - Individual HTML files
Generates one HTML file per CSV for easy viewing
"""

import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

# Get all CSV files
data_dir = Path("tests/fixtures/real_data")
csv_files = sorted(data_dir.glob("*.csv"))

print(f"Found {len(csv_files)} CSV files")

# Create output directory
output_dir = Path("power_plots")
output_dir.mkdir(exist_ok=True)

# Process each file
for i, csv_file in enumerate(csv_files, 1):
    print(f"Processing {i}/{len(csv_files)}: {csv_file.name}")
    
    # Load data
    df = pd.read_csv(csv_file)
    
    # Rename columns
    df = df.rename(columns={
        'miner.seconds': 'seconds',
        'miner.mode.power': 'mode_power',
        'miner.summary.wattage': 'summary_wattage'
    })
    
    # Find action point
    action_idx = df[df['seconds'] >= 0].index[0] if len(df[df['seconds'] >= 0]) > 0 else None
    action_time = df.loc[action_idx, 'seconds'] if action_idx is not None else 0
    
    # Calculate targets
    if action_idx:
        pre_data = df[df['seconds'] < 0]['mode_power'].dropna()
        post_data = df[df['seconds'] >= 0]['mode_power'].dropna()
        target_before = pre_data.mode().iloc[0] if len(pre_data) > 0 and len(pre_data.mode()) > 0 else None
        target_after = post_data.mode().iloc[0] if len(post_data) > 0 and len(post_data.mode()) > 0 else None
    else:
        target_before = None
        target_after = None
    
    # Create figure
    fig = go.Figure()
    
    # Add zones if we have target_after
    if target_after and not pd.isna(target_after):
        # Band Entry zone (±5%)
        band_lower = target_after * 0.95
        band_upper = target_after * 1.05
        fig.add_hrect(
            y0=band_lower, y1=band_upper,
            fillcolor="green", opacity=0.15,
            layer="below", line_width=0,
            annotation_text="Band Entry Zone (±5%)",
            annotation_position="top left"
        )
        
        # Setpoint zone (±1%)
        setpoint_lower = target_after * 0.99
        setpoint_upper = target_after * 1.01
        fig.add_hrect(
            y0=setpoint_lower, y1=setpoint_upper,
            fillcolor="blue", opacity=0.15,
            layer="below", line_width=0,
            annotation_text="Setpoint Zone (±1%)",
            annotation_position="bottom left"
        )
    
    # Plot actual wattage (BLUE)
    fig.add_trace(go.Scatter(
        x=df['seconds'].values,
        y=df['summary_wattage'].values,
        mode='lines',
        name='Actual Wattage',
        line=dict(color='blue', width=2),
        hovertemplate='Time: %{x:.2f}s<br>Wattage: %{y:.0f}W<extra></extra>'
    ))
    
    # Plot mode power target (ORANGE)
    fig.add_trace(go.Scatter(
        x=df['seconds'].values,
        y=df['mode_power'].values,
        mode='lines',
        name='Target (Mode Power)',
        line=dict(color='orange', width=2, dash='dot'),
        hovertemplate='Time: %{x:.2f}s<br>Target: %{y:.0f}W<extra></extra>'
    ))
    
    # Add action point vertical line (RED DASHED)
    if action_idx is not None:
        fig.add_vline(
            x=action_time,
            line_width=2,
            line_dash="dash",
            line_color="red",
            annotation_text="Action Point",
            annotation_position="top"
        )
    
    # Add target annotations
    if target_before and not pd.isna(target_before):
        fig.add_annotation(
            x=df['seconds'].min() + 30,
            y=target_before,
            text=f"Target Before: {target_before:.0f}W",
            showarrow=True,
            arrowhead=2,
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="black",
            borderwidth=1
        )
    
    if target_after and not pd.isna(target_after):
        fig.add_annotation(
            x=df['seconds'].max() - 50,
            y=target_after,
            text=f"Target After: {target_after:.0f}W",
            showarrow=True,
            arrowhead=2,
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="black",
            borderwidth=1
        )
    
    # Update layout
    fig.update_layout(
        title=f"File {i}/30: {csv_file.name}",
        xaxis_title="Time (seconds)",
        yaxis_title="Power (Watts)",
        hovermode='x unified',
        width=1600,
        height=700,
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="black",
            borderwidth=1
        ),
        template="plotly_white"
    )
    
    # Save individual HTML
    output_file = output_dir / f"{i:02d}_{csv_file.stem}.html"
    fig.write_html(
        str(output_file),
        config={'displayModeBar': True, 'displaylogo': False}
    )

print(f"\nDone! Generated {len(csv_files)} HTML files in '{output_dir}' folder")
print("\nTo view:")
print(f"  1. Open the '{output_dir}' folder")
print(f"  2. Double-click any HTML file (they're numbered 01-30)")
print(f"  3. Navigate through them in order")

