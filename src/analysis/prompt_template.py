"""
Prompt Template for LLM-Based Power Profile Analysis

This module contains the hardcoded prompt template used to generate narrative
analysis of miner power profile tests using Claude API.

The template is designed to:
- Accept raw CSV data (not pre-calculated metrics)
- Generate observational narratives about power behavior
- Adapt to different test scenarios (UP-STEP vs DOWN-STEP)
- Provide context about power ranges

Template placeholders:
- {test_id}: Test identifier
- {miner_number}: Miner unit number
- {step_direction}: UP-STEP or DOWN-STEP
- {power_range}: Power transition range (e.g., "1000W → 3500W")
- {csv_content}: Raw CSV data as compact string
"""

# Hardcoded prompt template with required placeholders
ANALYSIS_PROMPT_TEMPLATE = """You are analyzing a cryptocurrency miner power profile test. The test measures how the miner responds when its power target changes.

Test Information:
- Test: {test_id}
- Miner: {miner_number}
- Test Type: {step_direction}
- Power Transition: {power_range}

Raw Test Data (CSV):
{csv_content}

Column Definitions:
- miner.seconds: Time in seconds (negative = before action, positive = after action, 0 = transition moment)
- miner.mode.power: Target power setting commanded to the miner (in watts)
- miner.summary.wattage: Actual power consumption measured (in watts)
- miner.temp.hash_board_max: Hash board temperature (°C)
- miner.psu.temp_max: PSU temperature (°C)
- miner.outage: Whether miner is offline

Task:
Write a brief narrative describing what happened during this test. Focus on the power profile behavior:
- How stable was power before the transition?
- What happened at the transition (t=0)?
- How did power respond after the transition?
- Were there any anomalies, drops, spikes, or instabilities?

Be concise and observational. Describe what you see in the data timeline. Avoid calculations or technical jargon - just tell the story of what the miner did."""


def get_required_placeholders() -> set[str]:
    """
    Returns the set of required placeholder names in the template.
    
    Returns:
        Set of placeholder names (without braces)
    """
    return {
        'test_id',
        'miner_number',
        'step_direction',
        'power_range',
        'csv_content'
    }


def validate_template() -> bool:
    """
    Validates that the template contains all required placeholders.
    
    Returns:
        True if template is valid, raises ValueError otherwise
    
    Raises:
        ValueError: If required placeholders are missing
    """
    required = get_required_placeholders()
    
    # Extract placeholders from template
    import re
    found_placeholders = set(re.findall(r'\{(\w+)\}', ANALYSIS_PROMPT_TEMPLATE))
    
    # Check for missing placeholders
    missing = required - found_placeholders
    if missing:
        raise ValueError(
            f"Template is missing required placeholders: {', '.join(sorted(missing))}"
        )
    
    # Check for extra placeholders (not necessarily an error, but worth noting)
    extra = found_placeholders - required
    if extra:
        import warnings
        warnings.warn(
            f"Template contains unexpected placeholders: {', '.join(sorted(extra))}"
        )
    
    return True


def format_prompt(
    test_id: str,
    miner_number: str,
    step_direction: str,
    power_range: str,
    csv_content: str
) -> str:
    """
    Format the prompt template with provided values.
    
    Args:
        test_id: Test identifier (e.g., "r2_39")
        miner_number: Miner unit number (e.g., "39")
        step_direction: UP-STEP or DOWN-STEP
        power_range: Power transition range (e.g., "1000W → 3500W")
        csv_content: Raw CSV data as compact string
    
    Returns:
        Formatted prompt ready for LLM
    
    Raises:
        ValueError: If step_direction is invalid
    """
    # Validate step_direction
    valid_directions = {'UP-STEP', 'DOWN-STEP'}
    if step_direction not in valid_directions:
        raise ValueError(
            f"Invalid step_direction: {step_direction}. "
            f"Must be one of: {', '.join(sorted(valid_directions))}"
        )
    
    # Validate power_range format (basic check)
    if '→' not in power_range and '->' not in power_range:
        import warnings
        warnings.warn(
            f"power_range '{power_range}' may not be properly formatted. "
            "Expected format: 'X → Y' or 'X -> Y'"
        )
    
    # Format the template
    return ANALYSIS_PROMPT_TEMPLATE.format(
        test_id=test_id,
        miner_number=miner_number,
        step_direction=step_direction,
        power_range=power_range,
        csv_content=csv_content
    )


# Validate template on module import
validate_template()

