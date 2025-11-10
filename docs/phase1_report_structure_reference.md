# Phase 1 Report Structure Reference

This document contains the exact structure of the metrics report generated in Phase 1, to be used as a template for Phase 2 HTML report generation.

## Example Complete Metrics Report

**File:** r10_39_2025-08-27T23_05_08.csv

---

### 📊 Complete Metrics Report

**METRIC 1: Start Power**
- Median: 2462.0W
- Last Value: 2446.0W
- Difference: 16.0W

**METRIC 2: Target Power**
- Before: 2500.0W
- After: 3500.0W
- Change: 1000.0W

**METRIC 3: Step Direction**
- Direction: UP-STEP
- Delta: 1038.0W
- Description: Ramping up 1038W

**METRIC 4: Temperature Ranges**
- Hash Board: Min=46.25°C, Max=51.875°C, Range=5.625°C
- PSU: Min=37.0°C, Max=42.0°C, Range=5.0°C

**METRIC 5: Band Entry**
- Status: ENTERED
- Time: 92.471895s
- Wattage: 3326.0W
- Percentage: 95.02857142857142%
- Band Limits: 3325.0W - 3675.0W (±175.0W)
- Entry Method: normal

**METRIC 6: Setpoint Hit**
- Sustained Hits: 2
- Brief Touches: 2
- Brief Touch Times: t=196.437062s, t=382.61004s
- First Sustained Hit: Time=440.330625s, Duration=28.200931000000026s

**METRIC 7: Stable Plateau**
- Total Plateaus: 0
- Longest Duration: 0.0s
- Total Stable Time: 0.0s
- Plateau Ranges: (none)

**METRIC 8: Sharp Drops**
- Count: 1
- Threshold: N/A%
- Times: t=0.027482s

**METRIC 9: Sharp Rises**
- Count: 1
- Threshold: N/A%
- Times: t=13.849154s

**METRIC 10: Overshoot/Undershoot**
- Overshoot Occurred: False

---

### 📋 Metadata

- Total Rows: 1307
- Action Index: 119
- Action Time: 0.027482s
- Valid Metrics: 0/0
- Warnings: 1
  - Step direction delta mismatch: expected 1000W, got 1038W

---

## Report Structure Notes for Phase 2

### Section Order:
1. **Header** - File identification and test type
2. **Basic Metrics** (1-4) - Power and temperature baseline
3. **Time-Based Metrics** (5-7) - Timing measurements
4. **Anomaly Detection** (8-10) - Drops, rises, overshoot/undershoot
5. **Metadata** - Processing information and warnings

### Display Patterns:

#### Time Values:
- Format: `t=XXX.XXXXXXs` (6 decimal places)
- Use for: Band Entry, Setpoint Hit touches, Sharp Drops/Rises, Plateaus

#### Power Values:
- Format: `XXXXW` or `XXXX.XW` (0-1 decimal places)
- Always include unit "W"

#### Temperature Values:
- Format: `XX.XX°C` (2 decimal places)
- Always include unit "°C"

#### Percentages:
- Format: `XX.XX%` (2 decimal places)
- Use for: Band Entry percentage of target

#### Durations:
- Format: `XXX.XXs` (2 decimal places for display)
- Use for: Setpoint Hit duration, Plateau duration

#### Lists of Times:
- Format: `t=XX.XXs, t=YY.YYs, t=ZZ.ZZs`
- Comma-separated, each with "t=" prefix

#### Ranges:
- Format: `t=START-END and t=START-END...`
- Use "and" to separate multiple ranges
- Examples: `t=100.5-130.2s and t=340.1-380.7s`

### Conditional Display Rules:

#### Overshoot/Undershoot (METRIC 10):
- **UP-STEP**: Show only overshoot section
- **DOWN-STEP**: Show only undershoot section
- Never show both in the same report

#### Stable Plateau (METRIC 7):
- If `total_count > 0`: Show plateau ranges
- If `total_count == 0`: Show "(none)" or omit ranges line

#### Brief Touches (METRIC 6):
- If touches exist: Show times list
- If no touches: Omit times line

#### Sharp Drops/Rises (METRIC 8/9):
- Always show count
- If count > 0: Show times list
- If count == 0: Omit times line

### Data Mapping from Orchestrator Output:

```python
# METRIC 1: Start Power
metrics['start_power']['median']
metrics['start_power']['last_value']
metrics['start_power']['difference']

# METRIC 2: Target Power
metrics['target_power']['before']
metrics['target_power']['after']
metrics['target_power']['change']

# METRIC 3: Step Direction
metrics['step_direction']['direction']
metrics['step_direction']['delta']
metrics['step_direction']['description']

# METRIC 4: Temperature Ranges
metrics['temperature_ranges']['board']['min']
metrics['temperature_ranges']['board']['max']
metrics['temperature_ranges']['board']['range']
metrics['temperature_ranges']['psu']['min']
metrics['temperature_ranges']['psu']['max']
metrics['temperature_ranges']['psu']['range']

# METRIC 5: Band Entry
metrics['band_entry']['status']
metrics['band_entry']['time']
metrics['band_entry']['wattage']
metrics['band_entry']['percentage']
metrics['band_entry']['band_limits']['lower']
metrics['band_entry']['band_limits']['upper']
metrics['band_entry']['band_limits']['tolerance']
metrics['band_entry']['entry_method']

# METRIC 6: Setpoint Hit
metrics['setpoint_hit']['summary']['total_sustained_hits']
metrics['setpoint_hit']['summary']['total_brief_touches']
metrics['setpoint_hit']['brief_touches'] # List[Dict]
metrics['setpoint_hit']['sustained_hits'] # List[Dict]
metrics['setpoint_hit']['summary']['first_sustained_hit_time']

# METRIC 7: Stable Plateau
metrics['stable_plateau']['summary']['total_count']
metrics['stable_plateau']['summary']['longest_duration']
metrics['stable_plateau']['summary']['total_stable_time']
metrics['stable_plateau']['plateaus'] # List[Dict] with start_time, exit_time

# METRIC 8: Sharp Drops
metrics['sharp_drops']['summary']['count']
metrics['sharp_drops']['sharp_drops'] # List[Dict] with time

# METRIC 9: Sharp Rises
metrics['sharp_rises']['summary']['count']
metrics['sharp_rises']['sharp_rises'] # List[Dict] with time

# METRIC 10: Overshoot/Undershoot
metrics['overshoot_undershoot']['overshoot'] # Dict or None
metrics['overshoot_undershoot']['undershoot'] # Dict or None
metrics['overshoot_undershoot']['threshold']

# Metadata
metadata['total_rows']
metadata['action_index']
metadata['action_time']
metadata['validation']['warnings']
metadata['validation']['errors']
```

### Phase 2 Implementation Tasks:

1. **HTML Template Creation**
   - Convert markdown structure to HTML
   - Add CSS styling for professional appearance
   - Implement responsive design

2. **LLM Integration**
   - Pass complete metrics dictionary to Claude
   - Request narrative analysis (no recalculation)
   - Insert LLM response in descriptive section

3. **Plotly Visualization**
   - Use raw_data for time-series plot
   - Annotate events from metrics (band entry, setpoint hit, etc.)
   - Add interactive hover information

4. **Report Assembly**
   - Combine all sections in proper order
   - Format values according to display patterns
   - Apply conditional display rules

5. **Export Functionality**
   - Save as standalone HTML file
   - Include embedded CSS and JavaScript
   - Ensure portability (no external dependencies)

---

## Important Notes

- All metric values come from the orchestrator output (deterministic)
- LLM only provides narrative analysis, never recalculates metrics
- Report structure is fixed to maintain consistency
- Time precision varies by metric (see display patterns)
- Conditional sections prevent information overload

This structure was validated against 30 real test files in Phase 1 validation.

