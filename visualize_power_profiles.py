"""
Simple Power Profile Visualizer
- Press LEFT/RIGHT arrow keys or click buttons to navigate between files
- Shows wattage, mode power, action point, and zones
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

# Get all CSV files in the same order as validation report
data_dir = Path("tests/fixtures/real_data")
csv_files = sorted(data_dir.glob("*.csv"))

print(f"Found {len(csv_files)} CSV files")
print("Files will be displayed in this order:")
for i, f in enumerate(csv_files, 1):
    print(f"  {i}. {f.name}")

def create_plot(csv_file, file_index, total_files):
    """Create plot for a single CSV file"""
    
    # Load data
    df = pd.read_csv(csv_file)
    
    # Rename columns for easier access
    df = df.rename(columns={
        'miner.seconds': 'seconds',
        'miner.mode.power': 'mode_power',
        'miner.summary.wattage': 'summary_wattage'
    })
    
    # Find action point (where seconds crosses 0)
    action_idx = df[df['seconds'] >= 0].index[0] if len(df[df['seconds'] >= 0]) > 0 else None
    action_time = df.loc[action_idx, 'seconds'] if action_idx is not None else 0
    
    # Calculate target powers from mode_power
    if action_idx:
        target_before = df[df['seconds'] < 0]['mode_power'].mode().iloc[0] if len(df[df['seconds'] < 0]) > 0 else None
        target_after = df[df['seconds'] >= 0]['mode_power'].mode().iloc[0] if len(df[df['seconds'] >= 0]) > 0 else None
    else:
        target_before = None
        target_after = None
    
    # Create figure
    fig = go.Figure()
    
    # Add zones (faded rectangles) - Band Entry zone (±5% of target_after)
    if target_after and not pd.isna(target_after):
        band_lower = target_after * 0.95
        band_upper = target_after * 1.05
        
        fig.add_hrect(
            y0=band_lower, y1=band_upper,
            fillcolor="green", opacity=0.1,
            layer="below", line_width=0,
            annotation_text="Band Entry Zone (±5%)",
            annotation_position="top left"
        )
        
        # Setpoint zone (±1% of target_after)
        setpoint_lower = target_after * 0.99
        setpoint_upper = target_after * 1.01
        
        fig.add_hrect(
            y0=setpoint_lower, y1=setpoint_upper,
            fillcolor="blue", opacity=0.1,
            layer="below", line_width=0,
            annotation_text="Setpoint Zone (±1%)",
            annotation_position="bottom left"
        )
    
    # Plot actual wattage (blue line)
    fig.add_trace(go.Scatter(
        x=df['seconds'],
        y=df['summary_wattage'],
        mode='lines',
        name='Actual Wattage',
        line=dict(color='blue', width=2),
        hovertemplate='<b>Time:</b> %{x:.2f}s<br><b>Wattage:</b> %{y:.0f}W<extra></extra>'
    ))
    
    # Plot mode power target (orange dotted)
    fig.add_trace(go.Scatter(
        x=df['seconds'],
        y=df['mode_power'],
        mode='lines',
        name='Target (Mode Power)',
        line=dict(color='orange', width=2, dash='dot'),
        hovertemplate='<b>Time:</b> %{x:.2f}s<br><b>Target:</b> %{y:.0f}W<extra></extra>'
    ))
    
    # Add vertical line at action point (red dotted)
    if action_idx is not None:
        fig.add_vline(
            x=action_time,
            line_width=2,
            line_dash="dash",
            line_color="red",
            annotation_text="Action Point",
            annotation_position="top"
        )
    
    # Add target power annotations
    if target_before and not pd.isna(target_before):
        fig.add_annotation(
            x=df['seconds'].min() + 30,
            y=target_before,
            text=f"Target Before: {target_before:.0f}W",
            showarrow=True,
            arrowhead=2,
            bgcolor="white",
            opacity=0.8
        )
    
    if target_after and not pd.isna(target_after):
        fig.add_annotation(
            x=df['seconds'].max() - 30,
            y=target_after,
            text=f"Target After: {target_after:.0f}W",
            showarrow=True,
            arrowhead=2,
            bgcolor="white",
            opacity=0.8
        )
    
    # Layout
    fig.update_layout(
        title=f"File {file_index}/{total_files}: {csv_file.name}<br><sub>Use LEFT/RIGHT arrows to navigate</sub>",
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
            bgcolor="rgba(255,255,255,0.8)"
        ),
        # Add navigation buttons
        updatemenus=[
            dict(
                type="buttons",
                direction="left",
                x=0.5,
                y=1.15,
                xanchor="center",
                buttons=[
                    dict(
                        label="◄ Previous",
                        method="skip",
                        args=[None],
                    ),
                    dict(
                        label="Next ►",
                        method="skip",
                        args=[None],
                    )
                ]
            )
        ]
    )
    
    return fig

# Create HTML with all plots and navigation
html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Power Profile Viewer</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1650px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .controls {
            text-align: center;
            margin-bottom: 20px;
        }
        button {
            padding: 10px 30px;
            margin: 0 10px;
            font-size: 16px;
            cursor: pointer;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 5px;
        }
        button:hover {
            background-color: #45a049;
        }
        button:disabled {
            background-color: #cccccc;
            cursor: not-allowed;
        }
        .info {
            text-align: center;
            font-size: 18px;
            margin-bottom: 10px;
            color: #333;
        }
        #plot {
            margin-top: 20px;
        }
        .help {
            text-align: center;
            color: #666;
            font-size: 14px;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1 style="text-align: center;">Power Profile Visualizer</h1>
        
        <div class="info">
            <span id="fileInfo">Loading...</span>
        </div>
        
        <div class="controls">
            <button id="prevBtn" onclick="navigate(-1)">◄ Previous</button>
            <button id="nextBtn" onclick="navigate(1)">Next ►</button>
        </div>
        
        <div class="help">
            💡 Tip: Use LEFT/RIGHT arrow keys to navigate | Press 'f' for fullscreen
        </div>
        
        <div id="plot"></div>
    </div>
    
    <script>
        let currentIndex = 0;
        const plots = PLOTS_DATA;
        
        function updatePlot() {
            const plotData = plots[currentIndex];
            Plotly.newPlot('plot', plotData.data, plotData.layout, {responsive: true});
            
            document.getElementById('fileInfo').textContent = 
                `File ${currentIndex + 1} of ${plots.length}: ${plotData.filename}`;
            
            document.getElementById('prevBtn').disabled = currentIndex === 0;
            document.getElementById('nextBtn').disabled = currentIndex === plots.length - 1;
        }
        
        function navigate(direction) {
            const newIndex = currentIndex + direction;
            if (newIndex >= 0 && newIndex < plots.length) {
                currentIndex = newIndex;
                updatePlot();
            }
        }
        
        // Keyboard navigation
        document.addEventListener('keydown', function(event) {
            if (event.key === 'ArrowLeft') {
                navigate(-1);
            } else if (event.key === 'ArrowRight') {
                navigate(1);
            } else if (event.key === 'f' || event.key === 'F') {
                document.getElementById('plot').requestFullscreen();
            }
        });
        
        // Initialize
        updatePlot();
    </script>
</body>
</html>
"""

# Generate all plots
print("\nGenerating plots...")
plots_data = []

for i, csv_file in enumerate(csv_files, 1):
    print(f"  Processing {i}/{len(csv_files)}: {csv_file.name}")
    fig = create_plot(csv_file, i, len(csv_files))
    
    plots_data.append({
        'filename': csv_file.name,
        'data': fig.to_dict()['data'],
        'layout': fig.to_dict()['layout']
    })

# Replace placeholder in HTML
import json
import plotly.io as pio

# Convert to JSON-serializable format
json_plots = json.dumps(plots_data, default=lambda x: float(x) if hasattr(x, 'item') else str(x))
html_content = html_content.replace('PLOTS_DATA', json_plots)

# Save HTML file
output_file = "power_profile_viewer.html"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"\nDone! Open '{output_file}' in your browser")
print("\nControls:")
print("  - Click 'Previous' / 'Next' buttons")
print("  - Use LEFT/RIGHT arrow keys")
print("  - Press 'f' for fullscreen")
print("  - Hover over lines to see exact values")

