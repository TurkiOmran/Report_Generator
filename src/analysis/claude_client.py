"""
Claude API Client for Power Profile Analysis

This module provides functions to:
- Format CSV data for optimal LLM token consumption (~13,500 tokens)
- Build analysis prompts with test context
- Call Claude API for narrative generation
- Handle errors, timeouts, and token tracking

Dependencies:
- anthropic>=0.34.0
- pandas
- python-dotenv
"""

import os
import warnings
from typing import Optional, Dict, Any
from io import StringIO

import pandas as pd
from dotenv import load_dotenv

# Anthropic imports (for type hints and error handling)
try:
    import anthropic
    from anthropic import APIError, APIConnectionError, APITimeoutError, RateLimitError
except ImportError:
    # anthropic package not installed yet
    anthropic = None
    APIError = Exception
    APIConnectionError = Exception  
    APITimeoutError = Exception
    RateLimitError = Exception

# Load environment variables
load_dotenv()


def format_csv_for_llm(
    raw_data: pd.DataFrame,
    max_tokens: int = 14000
) -> str:
    """
    Convert DataFrame to compact CSV string optimized for LLM token consumption.
    
    This function formats the raw power profile data into a compact CSV string
    suitable for sending to Claude API. It optimizes for token efficiency while
    preserving all critical information.
    
    Token estimation: ~4 characters = 1 token (rough approximation)
    
    Args:
        raw_data: DataFrame containing power profile data with columns:
                  - miner.seconds
                  - miner.mode.power
                  - miner.summary.wattage
                  - miner.temp.hash_board_max
                  - miner.psu.temp_max
                  - miner.outage
                  - miner.collection.summary_error
                  - miner.collection.mode_error
        max_tokens: Maximum token count target (default: 14000)
    
    Returns:
        Compact CSV string representation
    
    Raises:
        ValueError: If required columns are missing or DataFrame is empty
    """
    # Validate input
    if raw_data is None or raw_data.empty:
        raise ValueError("raw_data cannot be None or empty")
    
    # Check for required columns
    required_columns = [
        'miner.seconds',
        'miner.mode.power',
        'miner.summary.wattage'
    ]
    
    missing_cols = [col for col in required_columns if col not in raw_data.columns]
    if missing_cols:
        raise ValueError(
            f"Missing required columns: {', '.join(missing_cols)}"
        )
    
    # Create a copy to avoid modifying original
    df = raw_data.copy()
    
    # Round numeric columns to reduce precision (saves tokens without losing meaning)
    numeric_cols = df.select_dtypes(include=['float64', 'float32']).columns
    for col in numeric_cols:
        if 'seconds' in col.lower():
            # Keep seconds as integers (they're already integers)
            df[col] = df[col].round(0).astype('Int64')
        elif 'wattage' in col.lower() or 'power' in col.lower():
            # Round power to nearest watt
            df[col] = df[col].round(0).astype('Int64')
        elif 'temp' in col.lower():
            # Round temperature to 1 decimal
            df[col] = df[col].round(1)
        else:
            # Other numeric fields: 2 decimals
            df[col] = df[col].round(2)
    
    # Convert to CSV string without index
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False, lineterminator='\n')
    csv_string = csv_buffer.getvalue()
    
    # Estimate token count (rough: 4 chars = 1 token)
    estimated_tokens = len(csv_string) // 4
    
    # Warn if exceeding target
    if estimated_tokens > max_tokens:
        warnings.warn(
            f"CSV data may exceed token limit: ~{estimated_tokens:,} tokens "
            f"(target: {max_tokens:,}). Consider sampling or reducing columns."
        )
    
    return csv_string


def estimate_token_count(text: str) -> int:
    """
    Rough estimation of token count from text.
    
    Uses approximation: 4 characters ≈ 1 token
    
    Args:
        text: Input text to estimate
    
    Returns:
        Estimated token count
    """
    return len(text) // 4


def validate_csv_format(csv_string: str) -> bool:
    """
    Validate that CSV string is properly formatted and readable.
    
    Args:
        csv_string: CSV string to validate
    
    Returns:
        True if valid, raises ValueError otherwise
    
    Raises:
        ValueError: If CSV is malformed or empty
    """
    if not csv_string or not csv_string.strip():
        raise ValueError("CSV string is empty")
    
    # Try to parse it back
    try:
        df = pd.read_csv(StringIO(csv_string))
        if df.empty:
            raise ValueError("CSV parses to empty DataFrame")
        return True
    except Exception as e:
        raise ValueError(f"Invalid CSV format: {str(e)}")


def extract_test_info(file_path: str) -> Dict[str, str]:
    """
    Extract test information from CSV filename.
    
    Expected format: r{test_num}_{miner}_{timestamp}.csv
    Example: r2_39_2025-08-28T09_40_10.csv
    
    Args:
        file_path: Path to CSV file
    
    Returns:
        Dictionary with 'test_id', 'miner_number', 'timestamp'
    
    Raises:
        ValueError: If filename doesn't match expected format
    """
    import re
    from pathlib import Path
    
    filename = Path(file_path).stem  # Get filename without extension
    
    # Pattern: r{test_num}_{miner}_{timestamp}
    pattern = r'^r(\d+)_(\d+)_(.+)$'
    match = re.match(pattern, filename)
    
    if not match:
        raise ValueError(
            f"Filename '{filename}' doesn't match expected format: "
            "r{{test_num}}_{{miner}}_{{timestamp}}.csv"
        )
    
    test_num, miner, timestamp = match.groups()
    
    return {
        'test_id': f"r{test_num}_{miner}",
        'miner_number': miner,
        'timestamp': timestamp
    }


def determine_step_direction(raw_data: pd.DataFrame) -> str:
    """
    Determine if test is UP-STEP or DOWN-STEP by analyzing mode.power changes.
    
    Args:
        raw_data: DataFrame with 'miner.mode.power' column
    
    Returns:
        'UP-STEP' or 'DOWN-STEP'
    
    Raises:
        ValueError: If step direction cannot be determined
    """
    if 'miner.mode.power' not in raw_data.columns:
        raise ValueError("Missing 'miner.mode.power' column")
    
    # Get power values before and after transition (t=0)
    before_transition = raw_data[raw_data['miner.seconds'] < 0]['miner.mode.power']
    after_transition = raw_data[raw_data['miner.seconds'] > 0]['miner.mode.power']
    
    if before_transition.empty or after_transition.empty:
        raise ValueError("Cannot determine step direction: missing before/after data")
    
    # Get typical values (use mode or most common value)
    power_before = before_transition.mode().iloc[0] if not before_transition.mode().empty else before_transition.mean()
    power_after = after_transition.mode().iloc[0] if not after_transition.mode().empty else after_transition.mean()
    
    if power_after > power_before:
        return "UP-STEP"
    elif power_after < power_before:
        return "DOWN-STEP"
    else:
        raise ValueError(
            f"Cannot determine step direction: power unchanged "
            f"(before={power_before:.0f}W, after={power_after:.0f}W)"
        )


def format_power_range(raw_data: pd.DataFrame) -> str:
    """
    Extract and format power transition range from data.
    
    Args:
        raw_data: DataFrame with 'miner.mode.power' column
    
    Returns:
        Formatted string like "1000W → 3500W"
    """
    if 'miner.mode.power' not in raw_data.columns:
        raise ValueError("Missing 'miner.mode.power' column")
    
    before_transition = raw_data[raw_data['miner.seconds'] < 0]['miner.mode.power']
    after_transition = raw_data[raw_data['miner.seconds'] > 0]['miner.mode.power']
    
    power_before = before_transition.mode().iloc[0] if not before_transition.mode().empty else before_transition.mean()
    power_after = after_transition.mode().iloc[0] if not after_transition.mode().empty else after_transition.mean()
    
    return f"{power_before:.0f}W → {power_after:.0f}W"


# Placeholder for future API functions
def build_prompt(
    test_id: str,
    miner_number: str,
    step_direction: str,
    power_range: str,
    csv_content: str
) -> str:
    """
    Build complete analysis prompt using template and test context.
    
    Args:
        test_id: Test identifier
        miner_number: Miner unit number
        step_direction: UP-STEP or DOWN-STEP
        power_range: Power transition range
        csv_content: Formatted CSV data
    
    Returns:
        Complete prompt ready for Claude API
    """
    from src.analysis.prompt_template import format_prompt
    
    return format_prompt(
        test_id=test_id,
        miner_number=miner_number,
        step_direction=step_direction,
        power_range=power_range,
        csv_content=csv_content
    )


def get_analysis(
    prompt: str,
    model: str = "claude-sonnet-4-20250514",
    timeout: int = 60,
    max_tokens: int = 2000
) -> Dict[str, Any]:
    """
    Call Claude API to get narrative analysis.
    
    Args:
        prompt: Complete analysis prompt
        model: Claude model to use (default: claude-sonnet-4-20250514)
        timeout: Request timeout in seconds (default: 60)
        max_tokens: Maximum tokens in response (default: 2000)
    
    Returns:
        Dictionary with:
            - 'analysis': Generated narrative text
            - 'tokens_used': Dict with 'input' and 'output' token counts
            - 'model': Model used for generation
            - 'stop_reason': Why the model stopped generating
    
    Raises:
        ValueError: If API key is missing or invalid
        TimeoutError: If request exceeds timeout
        RuntimeError: For API errors (rate limits, invalid request, etc.)
    """
    # Check if anthropic package is available
    if anthropic is None:
        raise ImportError(
            "anthropic package is not installed. "
            "Install it with: pip install anthropic"
        )
    
    # Validate API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if api_key:
        api_key = api_key.strip()
    
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY not found in environment. "
            "Please set it in .env file or environment variables."
        )
    
    # Validate model name format
    if not model or not isinstance(model, str):
        raise ValueError(f"Invalid model name: {model}")
    
    try:
        # Initialize client
        client = anthropic.Anthropic(
            api_key=api_key,
            timeout=timeout
        )
        
        # Make API call
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        # Extract response text
        if not response.content or len(response.content) == 0:
            raise RuntimeError("Claude API returned empty response")
        
        # Get text from first content block
        analysis_text = response.content[0].text if hasattr(response.content[0], 'text') else str(response.content[0])
        
        # Return structured response
        return {
            'analysis': analysis_text,
            'tokens_used': {
                'input': response.usage.input_tokens,
                'output': response.usage.output_tokens,
                'total': response.usage.input_tokens + response.usage.output_tokens
            },
            'model': response.model,
            'stop_reason': response.stop_reason
        }
    
    except APITimeoutError as e:
        raise TimeoutError(
            f"Claude API request timed out after {timeout} seconds. "
            "Try increasing the timeout parameter or check your network connection."
        ) from e
    
    except RateLimitError as e:
        raise RuntimeError(
            "Claude API rate limit exceeded. Please wait a moment and try again, "
            "or upgrade your Anthropic account for higher limits."
        ) from e
    
    except APIConnectionError as e:
        raise RuntimeError(
            f"Failed to connect to Claude API: {str(e)}. "
            "Check your internet connection and try again."
        ) from e
    
    except APIError as e:
        # Handle various API errors
        error_msg = str(e)
        if 'invalid' in error_msg.lower() and 'api' in error_msg.lower() and 'key' in error_msg.lower():
            raise ValueError(
                "Invalid ANTHROPIC_API_KEY. Please check your API key in .env file. "
                "Get a valid key from https://console.anthropic.com/"
            ) from e
        else:
            raise RuntimeError(
                f"Claude API error: {error_msg}"
            ) from e
    
    except Exception as e:
        # Catch any other unexpected errors
        raise RuntimeError(
            f"Unexpected error calling Claude API: {type(e).__name__}: {str(e)}"
        ) from e

