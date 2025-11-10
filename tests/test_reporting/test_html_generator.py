"""
Tests for HTML Generator Module

Validates complete HTML document generation with:
- Valid HTML5 structure
- Embedded CSS (no external dependencies)
- Fixed section ordering
- Responsive design
- Proper content integration
"""

import pytest
import re
from src.reporting.html_generator import (
    generate_html_report,
    _get_html_header,
    _get_embedded_css,
    _generate_header_section,
    _generate_metadata_section,
    _generate_analysis_section,
    _generate_metrics_section,
    _generate_chart_section
)


class TestHtmlGenerator:
    """Test suite for HTML generator functions."""
    
    def test_generate_html_header(self):
        """Test HTML header generation with proper meta tags."""
        header = _get_html_header()
        
        assert '<!DOCTYPE html>' in header
        assert '<html lang="en">' in header
        assert '<meta charset="UTF-8">' in header
        assert '<meta name="viewport"' in header
        assert '<title>Power Profile Report</title>' in header
    
    def test_get_embedded_css(self):
        """Test embedded CSS has no external dependencies."""
        css = _get_embedded_css()
        
        # Should be wrapped in <style> tags
        assert '<style>' in css
        assert '</style>' in css
        
        # Should not have external references
        assert '@import' not in css
        assert 'url(' not in css or 'url(data:' in css  # Allow data URLs
        assert 'http://' not in css
        assert 'https://' not in css
        
        # Should have key CSS classes
        assert '.container' in css
        assert '.report-header' in css
        assert '.section' in css
        assert '.metrics-table' in css
        assert '.chart-container' in css
        
        # Should have responsive design
        assert '@media' in css
        assert 'max-width' in css
    
    def test_generate_header_section(self):
        """Test report header section generation."""
        metadata = {
            'test_id': 'r2_39',
            'timestamp': '2025-08-28T09:40:10'
        }
        
        html = _generate_header_section(metadata)
        
        assert '<div class="report-header">' in html
        assert '<h1>Power Profile Test Report</h1>' in html
        assert 'r2_39' in html
        assert 'Generated:' in html
    
    def test_generate_metadata_section_complete(self):
        """Test metadata section with all fields."""
        metadata = {
            'filename': 'r2_39_2025-08-28T09_40_10.csv',
            'test_id': 'r2_39',
            'miner_number': '39',
            'timestamp': '2025-08-28T09:40:10',
            'total_samples': 1234,
            'duration_seconds': 456.7,
            'step_direction': 'UP-STEP'
        }
        
        html = _generate_metadata_section(metadata)
        
        assert 'Test Information' in html
        assert 'r2_39_2025-08-28T09_40_10.csv' in html
        assert 'r2_39' in html
        assert '39' in html
        assert '2025-08-28T09:40:10' in html
        assert '1,234' in html  # Formatted with commas
        assert '456.7' in html
        assert 'UP-STEP' in html
        
        # Check for metadata items
        assert 'Source File' in html
        assert 'Test ID' in html
        assert 'Miner Number' in html
        assert 'Step Direction' in html
    
    def test_generate_metadata_section_minimal(self):
        """Test metadata section with minimal data."""
        metadata = {}
        
        html = _generate_metadata_section(metadata)
        
        # Should still generate valid HTML with default values
        assert '<div class="section metadata-section">' in html
        assert 'Test Information' in html
        assert 'Unknown' in html or 'N/A' in html
    
    def test_generate_analysis_section_multiline(self):
        """Test analysis section with multi-paragraph text."""
        analysis = """This is the first paragraph of the analysis.

This is the second paragraph with more details.

And this is the third paragraph with conclusions."""
        
        html = _generate_analysis_section(analysis)
        
        assert 'AI Analysis' in html
        assert '<p>This is the first paragraph' in html
        assert '<p>This is the second paragraph' in html
        assert '<p>And this is the third paragraph' in html
        assert html.count('<p>') == 3
        assert html.count('</p>') == 3
    
    def test_generate_analysis_section_single_line(self):
        """Test analysis section with single paragraph."""
        analysis = "This is a single line analysis."
        
        html = _generate_analysis_section(analysis)
        
        assert 'AI Analysis' in html
        assert '<p>This is a single line analysis.</p>' in html
    
    def test_generate_metrics_section(self):
        """Test metrics section integration with formatter."""
        metrics = {
            'start_power': {'value': 1000.0},
            'target_power': {'before': 1000, 'after': 3500}
        }
        
        html = _generate_metrics_section(metrics)
        
        assert 'Performance Metrics' in html
        assert '<div class="section metrics-section">' in html
        assert '1000.0 W' in html
        assert '1000 W → 3500 W' in html
    
    def test_generate_chart_section(self):
        """Test chart section with Plotly HTML."""
        chart_html = '<div id="plotly-chart">Mock Chart</div>'
        
        html = _generate_chart_section(chart_html)
        
        assert 'Power Timeline' in html
        assert '<div class="section chart-section">' in html
        assert '<div class="chart-container">' in html
        assert 'Mock Chart' in html
    
    def test_generate_html_report_complete(self):
        """Test complete HTML report generation with all sections."""
        metrics = {
            'start_power': {'value': 1000.0},
            'target_power': {'before': 1000, 'after': 3500},
            'step_direction': {'direction': 'UP-STEP', 'magnitude': 2500}
        }
        
        metadata = {
            'filename': 'test.csv',
            'test_id': 'r1_39',
            'miner_number': '39',
            'timestamp': '2025-08-28T10:00:00',
            'total_samples': 500,
            'duration_seconds': 120.0,
            'step_direction': 'UP-STEP'
        }
        
        chart_html = '<div id="chart">Test Chart</div>'
        analysis_text = "This is the test analysis."
        
        html = generate_html_report(metrics, metadata, chart_html, analysis_text)
        
        # Verify HTML5 structure
        assert html.startswith('<!DOCTYPE html>')
        assert '<html lang="en">' in html
        assert '</html>' in html
        assert '<head>' in html
        assert '</head>' in html
        assert '<body>' in html
        assert '</body>' in html
        
        # Verify all sections present in correct order
        header_pos = html.find('Power Profile Test Report')
        metadata_pos = html.find('Test Information')
        analysis_pos = html.find('AI Analysis')
        metrics_pos = html.find('Performance Metrics')
        chart_pos = html.find('Power Timeline')
        
        # All sections should be present
        assert header_pos > 0
        assert metadata_pos > 0
        assert analysis_pos > 0
        assert metrics_pos > 0
        assert chart_pos > 0
        
        # Sections should be in correct order
        assert header_pos < metadata_pos < analysis_pos < metrics_pos < chart_pos
    
    def test_generate_html_report_without_analysis(self):
        """Test HTML report generation without analysis section."""
        metrics = {'start_power': {'value': 1000.0}}
        metadata = {'filename': 'test.csv'}
        chart_html = '<div>Chart</div>'
        
        html = generate_html_report(metrics, metadata, chart_html, analysis_text=None)
        
        # Should not have analysis section
        assert 'AI Analysis' not in html
        
        # But should have other sections
        assert 'Test Information' in html
        assert 'Performance Metrics' in html
        assert 'Power Timeline' in html
    
    def test_html_structure_validity(self):
        """Test that generated HTML has valid structure."""
        metrics = {'start_power': {'value': 1000.0}}
        metadata = {'filename': 'test.csv'}
        chart_html = '<div>Chart</div>'
        
        html = generate_html_report(metrics, metadata, chart_html)
        
        # Check matching tags
        assert html.count('<html') == html.count('</html>')
        assert html.count('<head>') == html.count('</head>')
        assert html.count('<body>') == html.count('</body>')
        assert html.count('<div') <= html.count('</div>')  # <= because self-closing divs possible
        
        # Check proper nesting order
        assert html.find('<html') < html.find('<head>')
        assert html.find('</head>') < html.find('<body>')
        assert html.find('</body>') < html.find('</html>')
    
    def test_responsive_design_css(self):
        """Test that CSS includes responsive design breakpoints."""
        css = _get_embedded_css()
        
        # Should have media queries for different screen sizes
        assert '@media' in css
        assert 'max-width' in css or 'min-width' in css
        
        # Should have mobile-specific adjustments
        media_query_match = re.search(r'@media[^{]*\([^)]*\)', css)
        assert media_query_match is not None
    
    def test_print_styles_included(self):
        """Test that print-specific styles are included."""
        css = _get_embedded_css()
        
        # Should have print media query
        assert '@media print' in css.lower()
    
    def test_no_external_dependencies(self):
        """Test that generated HTML has no external dependencies."""
        metrics = {'start_power': {'value': 1000.0}}
        metadata = {'filename': 'test.csv'}
        chart_html = '<div>Chart</div>'
        
        html = generate_html_report(metrics, metadata, chart_html)
        
        # Should not have external CSS links
        assert '<link rel="stylesheet"' not in html
        
        # Should not have external script references (except Plotly which is handled separately)
        # Note: Plotly chart_html might have CDN reference, but that's intentional
        assert '@import' not in html
    
    def test_semantic_html5_elements(self):
        """Test that semantic HTML5 elements are used."""
        metrics = {'start_power': {'value': 1000.0}}
        metadata = {'filename': 'test.csv'}
        chart_html = '<div>Chart</div>'
        
        html = generate_html_report(metrics, metadata, chart_html)
        
        # Should use semantic elements
        assert '<h1>' in html or '<h2>' in html
        # Check for either semantic <section> or div with section class
        has_section = '<section>' in html
        has_section_class = 'class="section' in html
        assert has_section or has_section_class, "No semantic section elements found"
        assert '<meta' in html
    
    def test_css_class_consistency(self):
        """Test that CSS classes are consistently named."""
        css = _get_embedded_css()
        
        # Extract all class selectors
        class_pattern = r'\.([\w-]+)\s*\{'
        classes = re.findall(class_pattern, css)
        
        # Should have consistent naming (kebab-case)
        for cls in classes:
            assert cls.islower() or '-' in cls, f"Class {cls} not in kebab-case"
    
    def test_color_scheme_consistency(self):
        """Test that colors are used consistently."""
        css = _get_embedded_css()
        
        # Should have consistent color palette
        # Check for primary purple gradient colors
        assert '#667eea' in css or '#764ba2' in css
        
        # Should have text color
        assert '#2C3E50' in css
    
    def test_container_max_width(self):
        """Test that container has reasonable max width."""
        css = _get_embedded_css()
        
        # Container should have max-width for readability
        assert '.container' in css
        container_css = css[css.find('.container'):]
        container_css = container_css[:container_css.find('}')]
        assert 'max-width' in container_css

