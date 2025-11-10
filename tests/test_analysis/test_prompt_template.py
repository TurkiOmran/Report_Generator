"""
Tests for prompt template module.

Tests cover:
- Template validation and placeholder detection
- Prompt formatting with various inputs
- Error handling for invalid inputs
- Edge cases and warnings
"""

import pytest
import warnings
from src.analysis.prompt_template import (
    ANALYSIS_PROMPT_TEMPLATE,
    get_required_placeholders,
    validate_template,
    format_prompt
)


class TestPromptTemplate:
    """Test suite for prompt template functionality."""
    
    def test_template_exists(self):
        """Template should be a non-empty string."""
        assert isinstance(ANALYSIS_PROMPT_TEMPLATE, str)
        assert len(ANALYSIS_PROMPT_TEMPLATE) > 0
    
    def test_template_contains_instructions(self):
        """Template should contain key instructions for analysis."""
        assert "power profile test" in ANALYSIS_PROMPT_TEMPLATE.lower()
        assert "narrative" in ANALYSIS_PROMPT_TEMPLATE.lower()
        assert "csv" in ANALYSIS_PROMPT_TEMPLATE.lower()
    
    def test_get_required_placeholders(self):
        """Should return all required placeholder names."""
        placeholders = get_required_placeholders()
        
        assert isinstance(placeholders, set)
        assert 'test_id' in placeholders
        assert 'miner_number' in placeholders
        assert 'step_direction' in placeholders
        assert 'power_range' in placeholders
        assert 'csv_content' in placeholders
    
    def test_validate_template_success(self):
        """Template validation should succeed with all placeholders present."""
        # Should not raise any exception
        assert validate_template() is True
    
    def test_template_has_all_placeholders(self):
        """Template should contain all required placeholders."""
        required = get_required_placeholders()
        
        for placeholder in required:
            assert f"{{{placeholder}}}" in ANALYSIS_PROMPT_TEMPLATE, \
                f"Missing placeholder: {{{placeholder}}}"


class TestFormatPrompt:
    """Test suite for prompt formatting functionality."""
    
    @pytest.fixture
    def sample_csv_content(self):
        """Sample CSV content for testing."""
        return """miner.seconds,miner.mode.power,miner.summary.wattage
-60,1000,998
-30,1000,1002
0,3500,1005
30,3500,2800
60,3500,3480"""
    
    def test_format_prompt_upstep(self, sample_csv_content):
        """Should format prompt correctly for UP-STEP scenario."""
        result = format_prompt(
            test_id="r2_39",
            miner_number="39",
            step_direction="UP-STEP",
            power_range="1000W → 3500W",
            csv_content=sample_csv_content
        )
        
        assert isinstance(result, str)
        assert "r2_39" in result
        assert "39" in result
        assert "UP-STEP" in result
        assert "1000W → 3500W" in result
        assert sample_csv_content in result
        
        # Should not contain any placeholders
        assert "{" not in result
        assert "}" not in result
    
    def test_format_prompt_downstep(self, sample_csv_content):
        """Should format prompt correctly for DOWN-STEP scenario."""
        result = format_prompt(
            test_id="r6_39",
            miner_number="39",
            step_direction="DOWN-STEP",
            power_range="3500W → 1000W",
            csv_content=sample_csv_content
        )
        
        assert "DOWN-STEP" in result
        assert "3500W → 1000W" in result
    
    def test_format_prompt_invalid_step_direction(self, sample_csv_content):
        """Should raise ValueError for invalid step_direction."""
        with pytest.raises(ValueError, match="Invalid step_direction"):
            format_prompt(
                test_id="r2_39",
                miner_number="39",
                step_direction="SIDE-STEP",  # Invalid
                power_range="1000W → 3500W",
                csv_content=sample_csv_content
            )
    
    def test_format_prompt_alternate_arrow(self, sample_csv_content):
        """Should accept ASCII arrow format for power_range."""
        result = format_prompt(
            test_id="r2_39",
            miner_number="39",
            step_direction="UP-STEP",
            power_range="1000W -> 3500W",  # ASCII arrow
            csv_content=sample_csv_content
        )
        
        assert "1000W -> 3500W" in result
    
    def test_format_prompt_warns_on_malformed_power_range(self, sample_csv_content):
        """Should warn if power_range doesn't contain arrow."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            format_prompt(
                test_id="r2_39",
                miner_number="39",
                step_direction="UP-STEP",
                power_range="1000W to 3500W",  # No arrow
                csv_content=sample_csv_content
            )
            
            assert len(w) == 1
            assert "power_range" in str(w[0].message).lower()
            assert "format" in str(w[0].message).lower()
    
    def test_format_prompt_empty_csv(self):
        """Should handle empty CSV content gracefully."""
        result = format_prompt(
            test_id="r2_39",
            miner_number="39",
            step_direction="UP-STEP",
            power_range="1000W → 3500W",
            csv_content=""
        )
        
        assert isinstance(result, str)
        # Empty CSV should still produce valid prompt structure
        assert "Test Information:" in result
    
    def test_format_prompt_preserves_csv_formatting(self):
        """Should preserve CSV formatting including newlines and commas."""
        csv_with_formatting = "col1,col2\nval1,val2\nval3,val4"
        
        result = format_prompt(
            test_id="test",
            miner_number="1",
            step_direction="UP-STEP",
            power_range="1000W → 2000W",
            csv_content=csv_with_formatting
        )
        
        assert csv_with_formatting in result
        assert "col1,col2" in result
        assert "val1,val2" in result
    
    def test_format_prompt_handles_special_characters(self):
        """Should handle special characters in input values."""
        result = format_prompt(
            test_id="r2_39_2025-08-28",
            miner_number="39",
            step_direction="UP-STEP",
            power_range="1,000W → 3,500W",  # Commas in numbers
            csv_content="data,with,commas"
        )
        
        assert "r2_39_2025-08-28" in result
        assert "1,000W → 3,500W" in result


class TestPromptQuality:
    """Test suite for prompt quality and completeness."""
    
    def test_prompt_includes_column_definitions(self):
        """Prompt should define what each CSV column means."""
        assert "miner.seconds" in ANALYSIS_PROMPT_TEMPLATE
        assert "miner.mode.power" in ANALYSIS_PROMPT_TEMPLATE
        assert "miner.summary.wattage" in ANALYSIS_PROMPT_TEMPLATE
    
    def test_prompt_explains_time_convention(self):
        """Prompt should explain the time=0 convention."""
        assert "t=0" in ANALYSIS_PROMPT_TEMPLATE or "0 =" in ANALYSIS_PROMPT_TEMPLATE
        assert "transition" in ANALYSIS_PROMPT_TEMPLATE.lower()
    
    def test_prompt_requests_narrative_output(self):
        """Prompt should request narrative/story format."""
        content_lower = ANALYSIS_PROMPT_TEMPLATE.lower()
        assert any(word in content_lower for word in ['narrative', 'story', 'describe'])
    
    def test_prompt_discourages_calculations(self):
        """Prompt should discourage raw calculations or technical jargon."""
        content_lower = ANALYSIS_PROMPT_TEMPLATE.lower()
        assert "avoid" in content_lower or "don't" in content_lower
    
    def test_prompt_focuses_on_key_aspects(self):
        """Prompt should guide LLM to focus on key power behavior aspects."""
        content_lower = ANALYSIS_PROMPT_TEMPLATE.lower()
        
        # Should mention these key aspects
        assert "stable" in content_lower or "stability" in content_lower
        assert "transition" in content_lower
        assert "respond" in content_lower or "response" in content_lower
        assert "anomal" in content_lower or "spike" in content_lower or "drop" in content_lower

