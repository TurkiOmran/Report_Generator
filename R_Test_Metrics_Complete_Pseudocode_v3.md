# R Test Metrics - Complete Pseudocode Specification

**Version:** 3.0  
**Document Purpose:** Technical specification for deterministic metric calculation  
**Target Audience:** Task generation system (Taskmaster) and implementation teams  
**Test Type:** R Tests (Ramp Tests - Power Up/Down transitions)

---

## Overview

This document provides complete algorithmic specifications for 10 deterministic metrics that analyze miner power profile behavior during R tests. These metrics replace LLM-computed values with consistent, reproducible calculations.

**Metric Categories:**
- Basic Metrics (1-4): Foundational measurements
- Time-Based Metrics (5-7): Behavioral timing analysis
- Anomaly Detection (3-10): Instability and failure detection

---

## Data Preprocessing

All metrics require preprocessing of the input CSV data.

### **Input CSV Structure**

Required columns:
- `miner.seconds` (float): Time in seconds, negative before action, positive after
- `miner.mode.power` (float): Target power setting in watts
- `miner.summary.wattage` (float): Actual measured power in watts (may contain NaN)
- `miner.temp.hash_board_max` (float): Hash board temperature in °C
- `miner.psu.temp_max` (float): PSU temperature in °C
- `miner.outage` (bool): True when miner is offline

### **Preprocessing Function**

```
FUNCTION: preprocess_dataframe(df)

INPUT: Raw DataFrame loaded from CSV

PROCESS:
1. Validate required columns exist
   required = ['miner.seconds', 'miner.mode.power', 'miner.summary.wattage',
               'miner.temp.hash_board_max', 'miner.psu.temp_max', 'miner.outage']
   missing = [col for col in required if col not in df.columns]
   
   IF missing is not empty:
      RAISE ERROR "Missing required columns: {missing}"

2. Validate data types
   df['miner.seconds'] → must be numeric
   df['miner.mode.power'] → must be numeric
   df['miner.summary.wattage'] → numeric (NaN allowed)
   df['miner.temp.hash_board_max'] → numeric (NaN allowed)
   df['miner.psu.temp_max'] → numeric (NaN allowed)
   df['miner.outage'] → boolean

3. Sort by time
   df = df.sort_values('miner.seconds').reset_index(drop=True)

4. Find action time (t=0)
   action_idx = first index where df['miner.seconds'] >= 0
   
   IF no such index exists:
      RAISE ERROR "No action time found (no positive miner.seconds values)"

5. Validate action time characteristics
   target_before = df.at[action_idx - 1, 'miner.mode.power']
   target_after = df.at[action_idx, 'miner.mode.power']
   
   IF target_before == target_after:
      LOG WARNING "Target power did not change at action time"

6. Count and log data quality issues
   total_rows = len(df)
   nan_wattage_count = df['miner.summary.wattage'].isna().sum()
   outage_count = df['miner.outage'].sum()
   
   IF nan_wattage_count > 0:
      LOG WARNING f"{nan_wattage_count}/{total_rows} rows have NaN wattage"
   
   IF outage_count > 0:
      LOG INFO f"{outage_count}/{total_rows} rows marked as outage"

OUTPUT:
- df: Validated and sorted DataFrame
- action_idx: Integer row index where t crosses 0
- warnings: List of data quality warnings
```

---

## METRIC 1: Start Power

### **Purpose**
Establish baseline power consumption before the action is taken.

### **Definition**
Median of actual wattage during the pre-action period (t < 0), typically spanning approximately 60 seconds before action time.

### **Dependencies**
- Preprocessing (action_idx)

### **Inputs**
- df: Preprocessed DataFrame
- action_idx: Row index where t crosses 0

### **Pseudocode**

```
FUNCTION: calculate_start_power(df, action_idx)

1. Extract pre-action data
   pre_action_mask = df['miner.seconds'] < 0
   pre_action_data = df[pre_action_mask]
   
   IF pre_action_data is empty:
      RAISE ERROR "No pre-action data available (all times >= 0)"

2. Extract wattage values
   wattage_series = pre_action_data['miner.summary.wattage']

3. Filter valid (non-NaN) values
   valid_wattage = wattage_series.dropna()
   
   IF valid_wattage is empty:
      RAISE ERROR "All pre-action wattage values are NaN"

4. Calculate median
   median_power = MEDIAN(valid_wattage)

5. Get last value before action
   last_row_idx = action_idx - 1
   last_value = df.at[last_row_idx, 'miner.summary.wattage']

6. Compare median vs last value
   IF last_value is NaN:
      difference = NaN
      note = "Last value unavailable (NaN)"
   ELSE:
      difference = ABS(last_value - median_power)
      
      IF difference > 50:
         note = f"Last value ({last_value:.0f}W) differs from median by {difference:.0f}W"
      ELSE:
         note = None

RETURN:
{
  'median': median_power,      # float, primary value for calculations
  'last_value': last_value,    # float or NaN, actual value at t≈0
  'difference': difference,    # float or NaN, absolute difference
  'note': note                 # string or None, warning if significant difference
}
```

### **Edge Cases**
- Empty pre-action period → Error (cannot compute)
- All NaN in pre-action → Error (data quality issue)
- Last value is NaN → Return median with note
- Large difference (>50W) → Flag in note but return both values
- Very short pre-action period (<10s) → Warn but compute

### **Output Format**
```python
{
  "median": 3458.0,
  "last_value": 3460.0,
  "difference": 2.0,
  "note": None
}
```

### **Validation**
- Median should be positive
- Median should be within reasonable range (500-8000W typical)
- If note is present, difference should indeed be >50W
- Last value (if not NaN) should be close to median for stable tests

---

## METRIC 2: Target Power

### **Purpose**
Extract the target power setting before and after the action to determine the intended power transition.

### **Definition**
Value of miner.mode.power immediately before action (last negative time) and immediately after action (first non-negative time).

### **Dependencies**
- Preprocessing (action_idx)

### **Inputs**
- df: Preprocessed DataFrame
- action_idx: Row index where t crosses 0

### **Pseudocode**

```
FUNCTION: calculate_target_power(df, action_idx)

1. Get target before action
   before_idx = action_idx - 1
   target_before = df.at[before_idx, 'miner.mode.power']

2. Get target after action
   target_after = df.at[action_idx, 'miner.mode.power']

3. Calculate change
   change = target_after - target_before

4. Validate target changed
   IF change == 0:
      LOG WARNING "Target power did not change at action time"

5. Validate target remains constant after action
   post_action_mask = df.index >= action_idx
   post_action_targets = df[post_action_mask]['miner.mode.power']
   unique_targets = post_action_targets.unique()
   
   IF len(unique_targets) > 1:
      LOG WARNING f"Target changed during test: {unique_targets}"
      # Use first target (at action time) as canonical

6. Validate values are reasonable
   IF target_before < 0 OR target_after < 0:
      LOG WARNING "Negative target power detected"
   
   IF target_before > 10000 OR target_after > 10000:
      LOG WARNING "Unusually high target power detected"

RETURN:
{
  'before': target_before,  # float, target in watts before action
  'after': target_after,    # float, target in watts after action
  'change': change          # float, signed change in watts
}
```

### **Edge Cases**
- Target unchanged (change = 0) → Warn but return values
- Target changes mid-test → Warn and use first post-action target
- Negative or unreasonably high targets → Warn but return values
- NaN target values → Error (data corruption)

### **Output Format**
```python
{
  "before": 3500.0,
  "after": 3400.0,
  "change": -100.0
}
```

### **Validation**
- Both values should be positive
- Both values should be in typical range (500-8000W)
- Change should match expected test behavior
- Before value should approximately match METRIC 1 start power (within ~5%)

---

## METRIC 3: Step Direction

### **Purpose**
Classify the type of power transition being tested.

### **Definition**
Classification of power change direction based on the difference between target after action and start power median. Uses 50W threshold to distinguish minimal changes.

### **Dependencies**
- METRIC 1 (start_power)
- METRIC 2 (target_power)

### **Inputs**
- start_power: Dictionary from METRIC 1
- target_power: Dictionary from METRIC 2

### **Pseudocode**

```
FUNCTION: calculate_step_direction(start_power, target_power)

1. Extract relevant values
   start_median = start_power['median']
   target_after = target_power['after']

2. Calculate delta
   delta = target_after - start_median

3. Classify direction
   threshold_minimal = 50  # watts
   
   IF delta > threshold_minimal:
      direction = "UP-STEP"
      description = f"Ramping up {delta:.0f}W"
   
   ELSE IF delta < -threshold_minimal:
      direction = "DOWN-STEP"
      description = f"Ramping down {abs(delta):.0f}W"
   
   ELSE:  # -50 <= delta <= 50
      direction = "MINIMAL-STEP"
      description = f"Minimal change ({delta:+.0f}W)"
      LOG WARNING "Step change is very small, test may not be meaningful"

RETURN:
{
  'direction': direction,     # string: "UP-STEP", "DOWN-STEP", or "MINIMAL-STEP"
  'delta': delta,            # float, signed change in watts
  'description': description  # string, human-readable description
}
```

### **Edge Cases**
- Delta exactly 0 → Classify as MINIMAL-STEP, warn
- Delta exactly ±50W → Follows threshold rules (>50 = UP, <-50 = DOWN)
- Very large delta (>2000W) → Log info but proceed normally
- Start or target missing → Error (cannot compute)

### **Output Format**
```python
{
  "direction": "DOWN-STEP",
  "delta": -100.0,
  "description": "Ramping down 100W"
}
```

### **Validation**
- Direction label should match sign of delta
- Delta should match target_power['change'] approximately
- Description string should be consistent with direction
- Absolute delta should be >= 0

---

## METRIC 4: Temperature Ranges

### **Purpose**
Track thermal behavior throughout the test by recording temperature extremes.

### **Definition**
Minimum and maximum temperatures for PSU and hash board across the entire test duration, including both pre-action and post-action periods.

### **Dependencies**
None (independent metric)

### **Inputs**
- df: Preprocessed DataFrame

### **Pseudocode**

```
FUNCTION: calculate_temperature_ranges(df)

1. Extract PSU temperatures
   psu_temps = df['miner.psu.temp_max']
   valid_psu = psu_temps.dropna()
   
   IF valid_psu is empty:
      psu_min = None
      psu_max = None
      psu_range = None
      LOG WARNING "All PSU temperature values are NaN"
   ELSE:
      psu_min = MIN(valid_psu)
      psu_max = MAX(valid_psu)
      psu_range = psu_max - psu_min

2. Extract hash board temperatures
   board_temps = df['miner.temp.hash_board_max']
   valid_board = board_temps.dropna()
   
   IF valid_board is empty:
      board_min = None
      board_max = None
      board_range = None
      LOG WARNING "All hash board temperature values are NaN"
   ELSE:
      board_min = MIN(valid_board)
      board_max = MAX(valid_board)
      board_range = board_max - board_min

3. Validate temperature ranges
   FOR temp_value in [psu_min, psu_max, board_min, board_max]:
      IF temp_value is not None:
         IF temp_value < 0 OR temp_value > 100:
            LOG WARNING f"Temperature {temp_value}°C outside typical range"

RETURN:
{
  'psu': {
    'min': psu_min,      # float or None, minimum PSU temp in °C
    'max': psu_max,      # float or None, maximum PSU temp in °C
    'range': psu_range   # float or None, temperature range in °C
  },
  'board': {
    'min': board_min,    # float or None, minimum board temp in °C
    'max': board_max,    # float or None, maximum board temp in °C
    'range': board_range # float or None, temperature range in °C
  }
}
```

### **Edge Cases**
- All temperatures NaN for one sensor → Return None for that sensor, warn
- Partial NaN values → Compute min/max from available values
- Temperatures outside typical range (0-100°C) → Warn but include
- Zero range (constant temperature) → Valid, indicates stable thermal environment
- Negative temperatures → Warn (sensor error) but include

### **Output Format**
```python
{
  "psu": {
    "min": 31.0,
    "max": 35.0,
    "range": 4.0
  },
  "board": {
    "min": 41.0,
    "max": 46.5,
    "range": 5.5
  }
}
```

### **Validation**
- If not None, max >= min for each sensor
- If not None, range = max - min
- Temperature values typically in range 20-80°C
- Board temperatures typically higher than PSU temperatures

---

## METRIC 5: Band Entry

### **Purpose**
Identify when the miner first achieves and maintains operation near the target power level.

### **Definition**
First time actual wattage enters and remains within an adaptive tolerance band around the target for at least 15 consecutive seconds. Band tolerance is the minimum of 5% of target or 50% of step magnitude, preventing unreasonably wide bands for small power changes.

### **Dependencies**
- Preprocessing (action_idx)
- METRIC 1 (start_power) - for adaptive band calculation
- METRIC 2 (target_power)
- METRIC 3 (step_direction) - optional for entry method classification

### **Inputs**
- df: Preprocessed DataFrame
- target_power: Dictionary from METRIC 2
- start_power: Dictionary from METRIC 1
- action_idx: Row index where t crosses 0
- step_direction: Dictionary from METRIC 3 (optional)

### **Pseudocode**

```
FUNCTION: calculate_band_entry(df, target_power, start_power, action_idx, step_direction=None)

1. Calculate adaptive band tolerance
   target = target_power['after']
   start_median = start_power['median']
   step_magnitude = ABS(target - start_median)
   
   # Adaptive tolerance: smaller of 5% target or 50% step
   tolerance_5pct = target * 0.05
   tolerance_step = step_magnitude * 0.5
   tolerance = MIN(tolerance_5pct, tolerance_step)
   
   lower_bound = target - tolerance
   upper_bound = target + tolerance

2. Extract post-action data
   post_action_mask = df.index >= action_idx
   post_action = df[post_action_mask].copy()
   
   IF post_action is empty:
      RAISE ERROR "No post-action data available"

3. Create in-band boolean mask
   wattage = post_action['miner.summary.wattage']
   
   # NaN is treated as out-of-band
   in_band = (wattage >= lower_bound) & (wattage <= upper_bound)
   in_band = in_band.fillna(False)

4. Find continuous in-band segments
   segments = []
   current_segment_start = None
   current_segment_start_idx = None
   
   FOR idx, row in post_action.iterrows():
      time = row['miner.seconds']
      is_in_band = in_band.loc[idx]
      
      IF is_in_band AND current_segment_start is None:
         # Entering band
         current_segment_start = time
         current_segment_start_idx = idx
      
      ELSE IF NOT is_in_band AND current_segment_start is not None:
         # Exiting band
         segment_duration = time - current_segment_start
         start_wattage = post_action.loc[current_segment_start_idx, 'miner.summary.wattage']
         
         segments.append({
            'start_time': current_segment_start,
            'start_wattage': start_wattage,
            'duration': segment_duration
         })
         
         current_segment_start = None
         current_segment_start_idx = None
   
   # Handle case where test ends while in-band
   IF current_segment_start is not None:
      last_idx = post_action.index[-1]
      last_time = post_action.loc[last_idx, 'miner.seconds']
      segment_duration = last_time - current_segment_start
      start_wattage = post_action.loc[current_segment_start_idx, 'miner.summary.wattage']
      
      segments.append({
         'start_time': current_segment_start,
         'start_wattage': start_wattage,
         'duration': segment_duration
      })

5. Find first sustained entry (≥15 seconds)
   min_dwell = 15.0  # seconds
   
   FOR segment in segments:
      IF segment['duration'] >= min_dwell:
         # Found first sustained entry
         entry_time = segment['start_time']
         entry_wattage = segment['start_wattage']
         entry_percentage = (entry_wattage / target) * 100
         
         # Optional: Determine entry method
         entry_method = None
         IF step_direction is not None:
            delta = step_direction['delta']
            IF delta > 0 AND entry_wattage > target:
               entry_method = "via_overshoot"
            ELSE IF delta < 0 AND entry_wattage < target:
               entry_method = "via_undershoot"
            ELSE:
               entry_method = "normal"
         
         RETURN {
            'status': 'ENTERED',
            'time': entry_time,
            'wattage': entry_wattage,
            'percentage': entry_percentage,
            'band_limits': {
               'lower': lower_bound,
               'upper': upper_bound,
               'tolerance': tolerance
            },
            'entry_method': entry_method
         }

6. Handle failure cases
   
   # Case A: Started in-band at t=0
   IF segments AND segments[0]['start_time'] < 1.0:
      first_segment = segments[0]
      
      IF first_segment['duration'] >= min_dwell:
         RETURN {
            'status': 'INITIALLY_IN_BAND',
            'time': 0.0,
            'wattage': first_segment['start_wattage'],
            'percentage': (first_segment['start_wattage'] / target) * 100,
            'band_limits': {
               'lower': lower_bound,
               'upper': upper_bound,
               'tolerance': tolerance
            },
            'entry_method': 'initially_in_band'
         }
      ELSE:
         RETURN {
            'status': 'BRIEFLY_IN_BAND_AT_START',
            'time': 0.0,
            'wattage': first_segment['start_wattage'],
            'left_at': first_segment['start_time'] + first_segment['duration'],
            'duration': first_segment['duration'],
            'band_limits': {
               'lower': lower_bound,
               'upper': upper_bound,
               'tolerance': tolerance
            }
         }
   
   # Case B: Brief entries only (all < 15s)
   IF segments:
      longest_segment = MAX(segments, key=lambda s: s['duration'])
      
      RETURN {
         'status': 'BRIEF_ENTRY_NOT_SUSTAINED',
         'time': longest_segment['start_time'],
         'wattage': longest_segment['start_wattage'],
         'duration': longest_segment['duration'],
         'band_limits': {
            'lower': lower_bound,
            'upper': upper_bound,
            'tolerance': tolerance
         }
      }
   
   # Case C: Never entered band
   # Find closest approach
   valid_wattage = post_action['miner.summary.wattage'].dropna()
   
   IF valid_wattage.empty:
      RETURN {
         'status': 'NO_VALID_DATA',
         'band_limits': {
            'lower': lower_bound,
            'upper': upper_bound,
            'tolerance': tolerance
         }
      }
   
   distances = ABS(valid_wattage - target)
   closest_idx = distances.idxmin()
   closest_wattage = valid_wattage.loc[closest_idx]
   closest_time = post_action.loc[closest_idx, 'miner.seconds']
   
   RETURN {
      'status': 'NOT_ENTERED',
      'closest_approach': {
         'time': closest_time,
         'wattage': closest_wattage,
         'distance': ABS(closest_wattage - target)
      },
      'band_limits': {
         'lower': lower_bound,
         'upper': upper_bound,
         'tolerance': tolerance
      }
   }
```

### **Edge Cases**
- Step magnitude = 0 → Use 5% tolerance only
- Very small step (<100W) → Adaptive tolerance prevents band > step
- Started in-band at t=0 → Classify as INITIALLY_IN_BAND
- NaN interrupts segment → Segment breaks, must restart counting
- Multiple entries → Return only first sustained entry
- All wattage values NaN → Return NO_VALID_DATA status

### **Output Format**
```python
# Success case
{
  "status": "ENTERED",
  "time": 45.3,
  "wattage": 3315.0,
  "percentage": 97.5,
  "band_limits": {
    "lower": 3371.0,
    "upper": 3429.0,
    "tolerance": 29.0
  },
  "entry_method": "normal"
}

# Failure case
{
  "status": "NOT_ENTERED",
  "closest_approach": {
    "time": 120.5,
    "wattage": 3220.0,
    "distance": 180.0
  },
  "band_limits": {
    "lower": 3371.0,
    "upper": 3429.0,
    "tolerance": 29.0
  }
}
```

### **Validation**
- Entry time should be >= 0 (post-action)
- Entry wattage should be within band_limits by definition
- Tolerance should be <= 5% of target
- Tolerance should be <= 50% of step magnitude
- Band limits should be symmetric around target
- If status = ENTERED, time should be the first occurrence

---

## METRIC 6: Setpoint Hit

### **Purpose**
Provide complete event history of all attempts to reach and maintain target power, enabling analysis of stabilization patterns and control behavior.

### **Definition**
Records all periods when actual wattage enters ±30W band around target. Distinguishes between brief touches (<25 seconds) and sustained hits (≥25 seconds). The 25-second threshold filters out transient drift-through behavior while accepting natural electrical variation.

### **Dependencies**
- Preprocessing (action_idx)
- METRIC 2 (target_power)

### **Inputs**
- df: Preprocessed DataFrame
- target_power: Dictionary from METRIC 2
- action_idx: Row index where t crosses 0

### **Pseudocode**

```
FUNCTION: calculate_setpoint_hit(df, target_power, action_idx)

1. Define setpoint criteria
   tolerance = 30  # watts (±30W band)
   min_sustained_duration = 25  # seconds

2. Calculate setpoint band
   target = target_power['after']
   lower_bound = target - tolerance
   upper_bound = target + tolerance

3. Extract post-action data
   post_action_mask = df.index >= action_idx
   post_action = df[post_action_mask].copy()
   
   IF post_action is empty:
      RAISE ERROR "No post-action data available"

4. Create in-band boolean mask
   wattage = post_action['miner.summary.wattage']
   
   # NaN is treated as out-of-band
   in_band = (wattage >= lower_bound) & (wattage <= upper_bound)
   in_band = in_band.fillna(False)

5. Find ALL continuous in-band segments
   segments = []
   current_segment_start = None
   current_segment_start_idx = None
   
   FOR idx, row in post_action.iterrows():
      time = row['miner.seconds']
      is_in_band = in_band.loc[idx]
      current_wattage = row['miner.summary.wattage']
      
      IF is_in_band AND current_segment_start is None:
         # Entering band
         current_segment_start = time
         current_segment_start_idx = idx
      
      ELSE IF NOT is_in_band AND current_segment_start is not None:
         # Exiting band - determine exit reason
         exit_time = time
         
         IF current_wattage < lower_bound:
            exit_reason = "dropped_below"
         ELSE IF current_wattage > upper_bound:
            exit_reason = "exceeded_above"
         ELSE:
            exit_reason = "unknown"
         
         segment_duration = exit_time - current_segment_start
         start_wattage = post_action.loc[current_segment_start_idx, 'miner.summary.wattage']
         
         # Calculate average wattage during segment
         segment_mask = (post_action['miner.seconds'] >= current_segment_start) & \
                       (post_action['miner.seconds'] < exit_time)
         segment_wattages = post_action.loc[segment_mask, 'miner.summary.wattage'].dropna()
         avg_wattage = MEAN(segment_wattages) if not segment_wattages.empty else start_wattage
         
         segments.append({
            'start_time': current_segment_start,
            'start_wattage': start_wattage,
            'duration': segment_duration,
            'avg_wattage': avg_wattage,
            'exit_time': exit_time,
            'exit_reason': exit_reason
         })
         
         current_segment_start = None
         current_segment_start_idx = None
   
   # Handle case where test ends while in-band
   IF current_segment_start is not None:
      last_idx = post_action.index[-1]
      last_time = post_action.loc[last_idx, 'miner.seconds']
      segment_duration = last_time - current_segment_start
      start_wattage = post_action.loc[current_segment_start_idx, 'miner.summary.wattage']
      
      # Calculate average wattage during segment
      segment_mask = post_action['miner.seconds'] >= current_segment_start
      segment_wattages = post_action.loc[segment_mask, 'miner.summary.wattage'].dropna()
      avg_wattage = MEAN(segment_wattages) if not segment_wattages.empty else start_wattage
      
      segments.append({
         'start_time': current_segment_start,
         'start_wattage': start_wattage,
         'duration': segment_duration,
         'avg_wattage': avg_wattage,
         'exit_time': last_time,
         'exit_reason': 'test_ended'
      })

6. Classify segments as brief touches or sustained hits
   brief_touches = []
   sustained_hits = []
   
   FOR segment in segments:
      IF segment['duration'] < min_sustained_duration:
         # Brief touch
         brief_touches.append({
            'time': segment['start_time'],
            'wattage': segment['start_wattage'],
            'duration': segment['duration'],
            'exit_reason': segment['exit_reason']
         })
      ELSE:
         # Sustained hit
         sustained_hits.append({
            'time': segment['start_time'],
            'wattage': segment['start_wattage'],
            'duration': segment['duration'],
            'avg_wattage': segment['avg_wattage'],
            'exit_time': segment['exit_time'],
            'exit_reason': segment['exit_reason']
         })

7. Create summary
   first_sustained_hit_time = None
   never_sustained = True
   
   IF sustained_hits:
      first_sustained_hit_time = sustained_hits[0]['time']
      never_sustained = False

RETURN:
{
  'brief_touches': brief_touches,
  'sustained_hits': sustained_hits,
  'summary': {
    'total_brief_touches': len(brief_touches),
    'total_sustained_hits': len(sustained_hits),
    'first_sustained_hit_time': first_sustained_hit_time,
    'never_sustained': never_sustained
  }
}
```

### **Edge Cases**
- Entry at t=0 → Valid, classify based on duration
- NaN interrupts segment → Segment breaks, new entry/exit logged
- Test ends while in band → exit_reason = "test_ended"
- Zero segments → Return empty lists with never_sustained = true
- Multiple sustained hits → All recorded in order
- Very brief touches (<1s) → Still recorded for completeness

### **Output Format**
```python
{
  "brief_touches": [
    {
      "time": 20.5,
      "wattage": 3485.0,
      "duration": 8.3,
      "exit_reason": "dropped_below"
    },
    {
      "time": 45.0,
      "wattage": 3472.0,
      "duration": 18.0,
      "exit_reason": "dropped_below"
    }
  ],
  "sustained_hits": [
    {
      "time": 80.0,
      "wattage": 3475.0,
      "duration": 370.0,
      "avg_wattage": 3478.5,
      "exit_time": 450.0,
      "exit_reason": "test_ended"
    }
  ],
  "summary": {
    "total_brief_touches": 2,
    "total_sustained_hits": 1,
    "first_sustained_hit_time": 80.0,
    "never_sustained": false
  }
}
```

### **Validation**
- All times should be >= 0 (post-action)
- All start wattages should be within ±30W of target at entry
- Brief touch durations should be < 25s
- Sustained hit durations should be >= 25s
- Exit times should be > entry times
- Sum of all durations should not exceed test duration
- Exit reasons should be valid: "dropped_below", "exceeded_above", or "test_ended"

---

## METRIC 7: Stable Plateau Duration

### **Purpose**
Identify and measure all periods of sustained stable operation near target, providing insight into control quality and system stability.

### **Definition**
Records all continuous periods where actual wattage remains within ±20W of target for at least 30 consecutive seconds. This tighter tolerance (compared to METRIC 6) identifies truly stable operation while accepting natural electrical variation. No slope check is required, allowing for gentle drift within the tolerance band.

### **Dependencies**
- Preprocessing (action_idx)
- METRIC 2 (target_power)

### **Inputs**
- df: Preprocessed DataFrame
- target_power: Dictionary from METRIC 2
- action_idx: Row index where t crosses 0

### **Pseudocode**

```
FUNCTION: calculate_plateau_duration(df, target_power, action_idx)

1. Define plateau criteria
   tolerance = 20  # watts (±20W band, tighter than setpoint hit)
   min_plateau_duration = 30  # seconds

2. Calculate plateau band
   target = target_power['after']
   lower_bound = target - tolerance
   upper_bound = target + tolerance

3. Extract post-action data
   post_action_mask = df.index >= action_idx
   post_action = df[post_action_mask].copy()
   
   IF post_action is empty:
      RAISE ERROR "No post-action data available"

4. Create in-band boolean mask
   wattage = post_action['miner.summary.wattage']
   
   # NaN is treated as out-of-band
   in_band = (wattage >= lower_bound) & (wattage <= upper_bound)
   in_band = in_band.fillna(False)

5. Find ALL continuous in-band segments
   segments = []
   current_segment_start = None
   current_segment_start_idx = None
   
   FOR idx, row in post_action.iterrows():
      time = row['miner.seconds']
      is_in_band = in_band.loc[idx]
      current_wattage = row['miner.summary.wattage']
      
      IF is_in_band AND current_segment_start is None:
         # Entering plateau band
         current_segment_start = time
         current_segment_start_idx = idx
      
      ELSE IF NOT is_in_band AND current_segment_start is not None:
         # Exiting plateau band - determine exit reason
         exit_time = time
         
         IF current_wattage < lower_bound:
            exit_reason = "dropped_below"
         ELSE IF current_wattage > upper_bound:
            exit_reason = "exceeded_above"
         ELSE:
            exit_reason = "unknown"
         
         segment_duration = exit_time - current_segment_start
         
         # Calculate average wattage during segment
         segment_mask = (post_action['miner.seconds'] >= current_segment_start) & \
                       (post_action['miner.seconds'] < exit_time)
         segment_wattages = post_action.loc[segment_mask, 'miner.summary.wattage'].dropna()
         
         IF not segment_wattages.empty:
            avg_wattage = MEAN(segment_wattages)
         ELSE:
            avg_wattage = post_action.loc[current_segment_start_idx, 'miner.summary.wattage']
         
         segments.append({
            'start_time': current_segment_start,
            'duration': segment_duration,
            'avg_wattage': avg_wattage,
            'exit_time': exit_time,
            'exit_reason': exit_reason
         })
         
         current_segment_start = None
         current_segment_start_idx = None
   
   # Handle case where test ends while in plateau
   IF current_segment_start is not None:
      last_idx = post_action.index[-1]
      last_time = post_action.loc[last_idx, 'miner.seconds']
      segment_duration = last_time - current_segment_start
      
      # Calculate average wattage during segment
      segment_mask = post_action['miner.seconds'] >= current_segment_start
      segment_wattages = post_action.loc[segment_mask, 'miner.summary.wattage'].dropna()
      
      IF not segment_wattages.empty:
         avg_wattage = MEAN(segment_wattages)
      ELSE:
         avg_wattage = post_action.loc[current_segment_start_idx, 'miner.summary.wattage']
      
      segments.append({
         'start_time': current_segment_start,
         'duration': segment_duration,
         'avg_wattage': avg_wattage,
         'exit_time': last_time,
         'exit_reason': 'test_ended'
      })

6. Filter for qualifying plateaus (≥30 seconds)
   plateaus = []
   
   FOR segment in segments:
      IF segment['duration'] >= min_plateau_duration:
         plateaus.append(segment)

7. Calculate summary statistics
   IF plateaus:
      longest_plateau = MAX(plateaus, key=lambda p: p['duration'])
      total_stable_time = SUM(p['duration'] for p in plateaus)
      
      RETURN {
         'plateaus': plateaus,
         'summary': {
            'total_count': len(plateaus),
            'longest_duration': longest_plateau['duration'],
            'total_stable_time': total_stable_time
         }
      }
   ELSE:
      RETURN {
         'plateaus': [],
         'summary': {
            'total_count': 0,
            'longest_duration': 0.0,
            'total_stable_time': 0.0
         }
      }
```

### **Edge Cases**
- No qualifying plateaus → Return empty list with zero summary stats
- NaN interrupts plateau → Segment breaks, multiple plateaus possible
- Test ends during plateau → exit_reason = "test_ended"
- Multiple plateaus of equal duration → All recorded
- Very short segments (<30s) → Filtered out, not included in results
- Entire test within ±20W → Single plateau for full duration

### **Output Format**
```python
{
  "plateaus": [
    {
      "start_time": 80.0,
      "duration": 35.0,
      "avg_wattage": 3395.0,
      "exit_time": 115.0,
      "exit_reason": "dropped_below"
    },
    {
      "start_time": 200.0,
      "duration": 380.0,
      "avg_wattage": 3402.0,
      "exit_time": 580.0,
      "exit_reason": "test_ended"
    }
  ],
  "summary": {
    "total_count": 2,
    "longest_duration": 380.0,
    "total_stable_time": 415.0
  }
}
```

### **Validation**
- All plateau durations should be >= 30s
- All average wattages should be within ±20W of target
- Exit times should be > start times
- Longest duration should equal max of all plateau durations
- Total stable time should equal sum of all plateau durations
- Summary counts should match length of plateaus list

---

## METRIC 8: Sharp Drops

### **Purpose**
Detect sudden, significant decreases in power that indicate instability, control failures, or equipment issues.

### **Definition**
A sharp drop occurs when actual wattage decreases by 15% or more of the current power level within a 5-second window. Uses rolling 5-second windows to detect rapid power loss events. The percentage-based threshold ensures sensitivity scales appropriately across different power levels.

### **Dependencies**
- Preprocessing (action_idx)

### **Inputs**
- df: Preprocessed DataFrame
- action_idx: Row index where t crosses 0

### **Pseudocode**

```
FUNCTION: calculate_sharp_drops(df, action_idx)

1. Define detection criteria
   drop_threshold_pct = 0.15  # 15% of current power
   detection_window = 5.0  # seconds

2. Extract post-action data
   post_action_mask = df.index >= action_idx
   post_action = df[post_action_mask].copy()
   
   IF post_action is empty:
      RAISE ERROR "No post-action data available"

3. Get valid wattage data
   times = post_action['miner.seconds'].values
   wattages = post_action['miner.summary.wattage'].values
   
   # Filter out NaN values
   valid_mask = ~np.isnan(wattages)
   valid_times = times[valid_mask]
   valid_wattages = wattages[valid_mask]
   
   IF len(valid_wattages) < 2:
      RETURN {
         'sharp_drops': [],
         'summary': {
            'count': 0,
            'worst_magnitude': None,
            'worst_rate': None
         }
      }

4. Scan for sharp drops using rolling window
   sharp_drops = []
   processed_times = set()  # Avoid duplicate detection
   
   FOR i FROM 0 TO len(valid_times) - 1:
      current_time = valid_times[i]
      current_wattage = valid_wattages[i]
      
      # Skip if this time already processed in a previous drop
      IF current_time in processed_times:
         CONTINUE
      
      # Define search window
      window_end_time = current_time + detection_window
      
      # Find all points within window
      window_mask = (valid_times > current_time) & (valid_times <= window_end_time)
      window_times = valid_times[window_mask]
      window_wattages = valid_wattages[window_mask]
      
      IF len(window_wattages) == 0:
         CONTINUE
      
      # Find minimum wattage in window
      min_wattage = MIN(window_wattages)
      min_idx = np.argmin(window_wattages)
      min_time = window_times[min_idx]
      
      # Calculate drop
      drop_magnitude = current_wattage - min_wattage
      drop_percentage = drop_magnitude / current_wattage
      
      # Check if drop exceeds threshold
      IF drop_percentage >= drop_threshold_pct:
         # Sharp drop detected
         drop_duration = min_time - current_time
         drop_rate = -drop_magnitude / drop_duration if drop_duration > 0 else 0
         
         sharp_drops.append({
            'time': current_time,
            'start_wattage': current_wattage,
            'end_wattage': min_wattage,
            'magnitude': drop_magnitude,
            'duration': drop_duration,
            'rate': drop_rate
         })
         
         # Mark all times in this drop as processed
         FOR t in window_times[:min_idx + 1]:
            processed_times.add(t)

5. Calculate summary statistics
   IF sharp_drops:
      worst_magnitude = MAX(d['magnitude'] for d in sharp_drops)
      worst_rate = MIN(d['rate'] for d in sharp_drops)  # Most negative
   ELSE:
      worst_magnitude = None
      worst_rate = None

RETURN:
{
  'sharp_drops': sharp_drops,
  'summary': {
    'count': len(sharp_drops),
    'worst_magnitude': worst_magnitude,
    'worst_rate': worst_rate
  }
}
```

### **Edge Cases**
- All wattage NaN → Return empty results with count = 0
- Single data point → Cannot compute drops
- Drop at end of test with limited window → Use available data
- Multiple overlapping drops → Processed_times prevents double-counting
- Drop magnitude = 0 → Skip (not a drop)
- Infinite rate (zero duration) → Set rate to 0 or very large negative number

### **Output Format**
```python
{
  "sharp_drops": [
    {
      "time": 35.0,
      "start_wattage": 3500.0,
      "end_wattage": 2950.0,
      "magnitude": 550.0,
      "duration": 3.5,
      "rate": -157.14
    }
  ],
  "summary": {
    "count": 1,
    "worst_magnitude": 550.0,
    "worst_rate": -157.14
  }
}
```

### **Validation**
- All drop times should be >= 0 (post-action)
- All magnitudes should be positive
- All rates should be negative
- end_wattage should be < start_wattage
- magnitude should equal start_wattage - end_wattage
- duration should be > 0 and <= 5 seconds
- Drop percentage (magnitude / start_wattage) should be >= 15%

---

## METRIC 9: Spikes

### **Purpose**
Detect sudden, significant increases in power that indicate instability, overshoot, or control anomalies.

### **Definition**
A spike occurs when actual wattage increases by 15% or more of the current power level within a 5-second window. Uses rolling 5-second windows to detect rapid power rise events. The percentage-based threshold ensures sensitivity scales appropriately across different power levels. All spikes are recorded, including expected initial ramp-up behavior.

### **Dependencies**
- Preprocessing (action_idx)

### **Inputs**
- df: Preprocessed DataFrame
- action_idx: Row index where t crosses 0

### **Pseudocode**

```
FUNCTION: calculate_spikes(df, action_idx)

1. Define detection criteria
   spike_threshold_pct = 0.15  # 15% of current power
   detection_window = 5.0  # seconds

2. Extract post-action data
   post_action_mask = df.index >= action_idx
   post_action = df[post_action_mask].copy()
   
   IF post_action is empty:
      RAISE ERROR "No post-action data available"

3. Get valid wattage data
   times = post_action['miner.seconds'].values
   wattages = post_action['miner.summary.wattage'].values
   
   # Filter out NaN values
   valid_mask = ~np.isnan(wattages)
   valid_times = times[valid_mask]
   valid_wattages = wattages[valid_mask]
   
   IF len(valid_wattages) < 2:
      RETURN {
         'spikes': [],
         'summary': {
            'count': 0,
            'worst_magnitude': None,
            'worst_rate': None
         }
      }

4. Scan for spikes using rolling window
   spikes = []
   processed_times = set()  # Avoid duplicate detection
   
   FOR i FROM 0 TO len(valid_times) - 1:
      current_time = valid_times[i]
      current_wattage = valid_wattages[i]
      
      # Skip if this time already processed in a previous spike
      IF current_time in processed_times:
         CONTINUE
      
      # Define search window
      window_end_time = current_time + detection_window
      
      # Find all points within window
      window_mask = (valid_times > current_time) & (valid_times <= window_end_time)
      window_times = valid_times[window_mask]
      window_wattages = valid_wattages[window_mask]
      
      IF len(window_wattages) == 0:
         CONTINUE
      
      # Find maximum wattage in window
      max_wattage = MAX(window_wattages)
      max_idx = np.argmax(window_wattages)
      max_time = window_times[max_idx]
      
      # Calculate rise
      rise_magnitude = max_wattage - current_wattage
      rise_percentage = rise_magnitude / current_wattage
      
      # Check if rise exceeds threshold
      IF rise_percentage >= spike_threshold_pct:
         # Spike detected
         spike_duration = max_time - current_time
         spike_rate = rise_magnitude / spike_duration if spike_duration > 0 else 0
         
         spikes.append({
            'time': current_time,
            'start_wattage': current_wattage,
            'end_wattage': max_wattage,
            'magnitude': rise_magnitude,
            'duration': spike_duration,
            'rate': spike_rate
         })
         
         # Mark all times in this spike as processed
         FOR t in window_times[:max_idx + 1]:
            processed_times.add(t)

5. Calculate summary statistics
   IF spikes:
      worst_magnitude = MAX(s['magnitude'] for s in spikes)
      worst_rate = MAX(s['rate'] for s in spikes)  # Most positive
   ELSE:
      worst_magnitude = None
      worst_rate = None

RETURN:
{
  'spikes': spikes,
  'summary': {
    'count': len(spikes),
    'worst_magnitude': worst_magnitude,
    'worst_rate': worst_rate
  }
}
```

### **Edge Cases**
- All wattage NaN → Return empty results with count = 0
- Single data point → Cannot compute spikes
- Spike at end of test with limited window → Use available data
- Multiple overlapping spikes → Processed_times prevents double-counting
- Rise magnitude = 0 → Skip (not a spike)
- Initial ramp-up counted as spike → Expected behavior, recorded
- Infinite rate (zero duration) → Set rate to 0 or very large positive number

### **Output Format**
```python
{
  "spikes": [
    {
      "time": 120.0,
      "start_wattage": 3200.0,
      "end_wattage": 3750.0,
      "magnitude": 550.0,
      "duration": 4.0,
      "rate": 137.5
    }
  ],
  "summary": {
    "count": 1,
    "worst_magnitude": 550.0,
    "worst_rate": 137.5
  }
}
```

### **Validation**
- All spike times should be >= 0 (post-action)
- All magnitudes should be positive
- All rates should be positive
- end_wattage should be > start_wattage
- magnitude should equal end_wattage - start_wattage
- duration should be > 0 and <= 5 seconds
- Rise percentage (magnitude / start_wattage) should be >= 15%

---

## METRIC 10: Overshoot/Undershoot

### **Purpose**
Detect when the miner crosses beyond the target power level during stabilization, indicating control tuning issues or aggressive response characteristics.

### **Definition**
For increasing power tests (UP-STEP), overshoot occurs when wattage exceeds target by more than MAX(200W, 4% of target). For decreasing power tests (DOWN-STEP), undershoot occurs when wattage falls below target by more than MAX(200W, 4% of target). Detection is direction-specific based on the sign of the power change.

### **Dependencies**
- Preprocessing (action_idx)
- METRIC 2 (target_power)
- METRIC 3 (step_direction)

### **Inputs**
- df: Preprocessed DataFrame
- target_power: Dictionary from METRIC 2
- step_direction: Dictionary from METRIC 3
- action_idx: Row index where t crosses 0

### **Pseudocode**

```
FUNCTION: calculate_overshoot_undershoot(df, target_power, step_direction, action_idx)

1. Extract parameters
   target = target_power['after']
   delta = step_direction['delta']

2. Calculate threshold
   threshold_absolute = 200  # watts
   threshold_percentage = 0.04  # 4%
   threshold = MAX(threshold_absolute, target * threshold_percentage)

3. Extract post-action data
   post_action_mask = df.index >= action_idx
   post_action = df[post_action_mask].copy()
   
   IF post_action is empty:
      RAISE ERROR "No post-action data available"

4. Determine which anomaly to check based on direction
   check_overshoot = (delta > 0)  # Increasing power
   check_undershoot = (delta < 0)  # Decreasing power

5. Check for overshoot (if applicable)
   overshoot_result = None
   
   IF check_overshoot:
      upper_threshold = target + threshold
      wattage = post_action['miner.summary.wattage']
      
      # Find where wattage exceeds upper threshold
      overshoot_mask = wattage > upper_threshold
      
      IF overshoot_mask.any():
         # Overshoot detected
         overshoot_data = post_action[overshoot_mask]
         
         # Find peak overshoot
         peak_idx = wattage.idxmax()
         peak_wattage = wattage.loc[peak_idx]
         peak_time = post_action.loc[peak_idx, 'miner.seconds']
         
         # Find when first crossed threshold
         first_cross_idx = overshoot_mask.idxmax()
         first_cross_time = post_action.loc[first_cross_idx, 'miner.seconds']
         
         # Calculate duration above threshold
         # Find when it drops back below threshold (if it does)
         post_peak_mask = post_action.index > peak_idx
         post_peak_data = post_action[post_peak_mask]
         
         IF not post_peak_data.empty:
            below_threshold_mask = post_peak_data['miner.summary.wattage'] <= upper_threshold
            
            IF below_threshold_mask.any():
               return_idx = post_peak_data[below_threshold_mask].index[0]
               return_time = post_peak_data.loc[return_idx, 'miner.seconds']
               duration = return_time - first_cross_time
            ELSE:
               # Never returned below threshold
               duration = post_action['miner.seconds'].iloc[-1] - first_cross_time
         ELSE:
            # Peaked at end of test
            duration = peak_time - first_cross_time
         
         magnitude = peak_wattage - target
         
         overshoot_result = {
            'occurred': True,
            'time': first_cross_time,
            'peak_wattage': peak_wattage,
            'peak_time': peak_time,
            'magnitude': magnitude,
            'duration': duration
         }
      ELSE:
         overshoot_result = {
            'occurred': False
         }

6. Check for undershoot (if applicable)
   undershoot_result = None
   
   IF check_undershoot:
      lower_threshold = target - threshold
      wattage = post_action['miner.summary.wattage']
      
      # Find where wattage drops below lower threshold
      undershoot_mask = wattage < lower_threshold
      
      IF undershoot_mask.any():
         # Undershoot detected
         undershoot_data = post_action[undershoot_mask]
         
         # Find lowest point
         lowest_idx = wattage.idxmin()
         lowest_wattage = wattage.loc[lowest_idx]
         lowest_time = post_action.loc[lowest_idx, 'miner.seconds']
         
         # Find when first crossed threshold
         first_cross_idx = undershoot_mask.idxmax()
         first_cross_time = post_action.loc[first_cross_idx, 'miner.seconds']
         
         # Calculate duration below threshold
         # Find when it rises back above threshold (if it does)
         post_lowest_mask = post_action.index > lowest_idx
         post_lowest_data = post_action[post_lowest_mask]
         
         IF not post_lowest_data.empty:
            above_threshold_mask = post_lowest_data['miner.summary.wattage'] >= lower_threshold
            
            IF above_threshold_mask.any():
               return_idx = post_lowest_data[above_threshold_mask].index[0]
               return_time = post_lowest_data.loc[return_idx, 'miner.seconds']
               duration = return_time - first_cross_time
            ELSE:
               # Never returned above threshold
               duration = post_action['miner.seconds'].iloc[-1] - first_cross_time
         ELSE:
            # Bottomed at end of test
            duration = lowest_time - first_cross_time
         
         magnitude = target - lowest_wattage
         
         undershoot_result = {
            'occurred': True,
            'time': first_cross_time,
            'lowest_wattage': lowest_wattage,
            'lowest_time': lowest_time,
            'magnitude': magnitude,
            'duration': duration
         }
      ELSE:
         undershoot_result = {
            'occurred': False
         }

7. Return appropriate result based on test direction
   IF check_overshoot:
      RETURN {
         'overshoot': overshoot_result,
         'threshold': threshold
      }
   ELSE:
      RETURN {
         'undershoot': undershoot_result,
         'threshold': threshold
      }
```

### **Edge Cases**
- MINIMAL-STEP → Check direction based on sign of delta
- Crosses threshold multiple times → Record first crossing and peak/lowest
- Never returns to target side → Duration extends to end of test
- Crosses at end of test → Calculate duration with available data
- All wattage NaN → Return occurred = False
- Target exactly at threshold boundary → Use > and < (not >=, <=)

### **Output Format**
```python
# Overshoot (UP-STEP)
{
  "overshoot": {
    "occurred": true,
    "time": 65.0,
    "peak_wattage": 3650.0,
    "peak_time": 68.0,
    "magnitude": 150.0,
    "duration": 12.0
  },
  "threshold": 200.0
}

# Undershoot (DOWN-STEP)
{
  "undershoot": {
    "occurred": true,
    "time": 30.0,
    "lowest_wattage": 3200.0,
    "lowest_time": 32.5,
    "magnitude": 200.0,
    "duration": 8.0
  },
  "threshold": 200.0
}

# No anomaly
{
  "overshoot": {
    "occurred": false
  },
  "threshold": 200.0
}
```

### **Validation**
- If occurred = true, all fields should be present
- Time should be >= 0 (post-action)
- Peak/lowest time should be >= initial crossing time
- Magnitude should be > threshold
- Duration should be > 0
- For overshoot: peak_wattage > target + threshold
- For undershoot: lowest_wattage < target - threshold
- Only one of overshoot or undershoot should be present in output

---

## Dependencies Summary

```
Preprocessing (required for all)
  ↓
├─→ METRIC 1: Start Power
├─→ METRIC 2: Target Power
├─→ METRIC 4: Temperature Ranges (independent)
│
├─→ METRIC 3: Step Direction
│     ↓ (requires METRIC 1, 2)
│
├─→ METRIC 5: Band Entry
│     ↓ (requires METRIC 1, 2, 3 optional)
│
├─→ METRIC 6: Setpoint Hit
│     ↓ (requires METRIC 2)
│
├─→ METRIC 7: Stable Plateau
│     ↓ (requires METRIC 2)
│
├─→ METRIC 8: Sharp Drops
│     ↓ (requires preprocessing only)
│
├─→ METRIC 9: Spikes
│     ↓ (requires preprocessing only)
│
└─→ METRIC 10: Overshoot/Undershoot
      ↓ (requires METRIC 2, 3)
```

---

## Implementation Notes

### Execution Order
Metrics should be calculated in the following order to satisfy dependencies:
1. Preprocessing
2. METRIC 1, 2, 4 (parallel - no dependencies)
3. METRIC 3 (requires 1, 2)
4. METRIC 5, 6, 7, 8, 9 (parallel - independent of each other)
5. METRIC 10 (requires 2, 3)

### Error Handling
All metrics should:
- Raise clear errors for missing required inputs
- Log warnings for data quality issues
- Continue processing when possible despite warnings
- Return None or empty structures for uncomputable values

### Performance Considerations
- Preprocessing should be done once and shared across all metrics
- Metrics 5, 6, 7 have similar segment-finding logic that could be optimized
- Large datasets (>10000 rows) may benefit from vectorized operations
- NaN filtering should be done efficiently using pandas/numpy built-ins

### Testing Strategy
Each metric should be validated with:
- Normal operation tests (clean data)
- Edge cases (NaN, outages, extreme values)
- Boundary conditions (at thresholds)
- Visual comparison with plotted data

---

**End of Pseudocode Specification**
