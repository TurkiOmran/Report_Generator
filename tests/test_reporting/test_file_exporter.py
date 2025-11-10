"""
Tests for File Exporter Module

Validates file export functionality with:
- Directory creation
- Filename generation
- UTF-8 encoding
- Error handling (permissions, disk space)
- Single-file portability validation
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from src.reporting.file_exporter import (
    save_report,
    generate_filename,
    validate_single_file_portability,
    cleanup_old_reports,
    get_report_list
)


class TestFileExporter:
    """Test suite for file exporter functions."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        # Cleanup after test
        shutil.rmtree(temp_path, ignore_errors=True)
    
    @pytest.fixture
    def sample_html(self):
        """Sample HTML content for testing."""
        return """<!DOCTYPE html>
<html>
<head>
    <title>Test Report</title>
    <style>body { margin: 0; }</style>
</head>
<body>
    <h1>Test Report</h1>
    <p>This is a test report.</p>
</body>
</html>"""
    
    @pytest.fixture
    def sample_metadata(self):
        """Sample metadata for testing."""
        return {
            'test_id': 'r2_39',
            'timestamp': '2025-08-28T09:40:10',
            'filename': 'r2_39_2025-08-28T09_40_10.csv'
        }
    
    def test_save_report_creates_directory(self, temp_dir, sample_html):
        """Test that save_report creates output directory if it doesn't exist."""
        output_dir = os.path.join(temp_dir, 'new_reports')
        
        # Directory shouldn't exist yet
        assert not os.path.exists(output_dir)
        
        # Save report
        file_path = save_report(sample_html, output_dir=output_dir, filename='test_report')
        
        # Directory should now exist
        assert os.path.exists(output_dir)
        assert os.path.isdir(output_dir)
        assert os.path.exists(file_path)
    
    def test_save_report_with_custom_filename(self, temp_dir, sample_html):
        """Test save_report with custom filename."""
        file_path = save_report(sample_html, output_dir=temp_dir, filename='custom_report')
        
        assert os.path.exists(file_path)
        assert 'custom_report.html' in file_path
    
    def test_save_report_with_metadata(self, temp_dir, sample_html, sample_metadata):
        """Test save_report generates filename from metadata."""
        file_path = save_report(sample_html, output_dir=temp_dir, metadata=sample_metadata)
        
        assert os.path.exists(file_path)
        assert 'report_r2_39_2025-08-28T09_40_10.html' in file_path
    
    def test_save_report_utf8_encoding(self, temp_dir, sample_metadata):
        """Test that save_report preserves UTF-8 encoding."""
        # HTML with UTF-8 characters
        html_with_unicode = """<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
    <p>Unicode: °C → ± ✓ ✗</p>
    <p>Chinese: 中文</p>
    <p>Emoji: 🔥 ⚡</p>
</body>
</html>"""
        
        file_path = save_report(html_with_unicode, output_dir=temp_dir, metadata=sample_metadata)
        
        # Read file and verify UTF-8 characters preserved
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert '°C' in content
        assert '→' in content
        assert '±' in content
        assert '✓' in content
        assert '✗' in content
        assert '中文' in content
        assert '🔥' in content
        assert '⚡' in content
    
    def test_save_report_empty_content_raises_error(self, temp_dir):
        """Test that save_report raises error for empty content."""
        with pytest.raises(ValueError, match="html_content cannot be empty"):
            save_report("", output_dir=temp_dir)
        
        with pytest.raises(ValueError, match="html_content cannot be empty"):
            save_report("   ", output_dir=temp_dir)
    
    def test_save_report_adds_html_extension(self, temp_dir, sample_html):
        """Test that .html extension is added if not present."""
        file_path = save_report(sample_html, output_dir=temp_dir, filename='report_no_ext')
        
        assert file_path.endswith('.html')
        assert os.path.exists(file_path)
    
    def test_save_report_preserves_html_extension(self, temp_dir, sample_html):
        """Test that existing .html extension is preserved."""
        file_path = save_report(sample_html, output_dir=temp_dir, filename='report.html')
        
        # Should not have double extension
        assert file_path.endswith('.html')
        assert not file_path.endswith('.html.html')
    
    def test_generate_filename_with_metadata(self, sample_metadata):
        """Test filename generation with complete metadata."""
        filename = generate_filename(sample_metadata)
        
        assert filename == 'report_r2_39_2025-08-28T09_40_10'
        assert '.html' not in filename  # Extension added by save_report
    
    def test_generate_filename_without_metadata(self):
        """Test filename generation falls back to current timestamp."""
        filename = generate_filename(None)
        
        assert filename.startswith('report_')
        assert 'T' in filename  # ISO format timestamp
        # Should contain current year
        assert str(datetime.now().year) in filename
    
    def test_generate_filename_with_partial_metadata(self):
        """Test filename generation with incomplete metadata."""
        partial_metadata = {'test_id': 'r2_39'}  # Missing timestamp
        
        filename = generate_filename(partial_metadata)
        
        # Should fall back to current timestamp
        assert filename.startswith('report_')
        assert str(datetime.now().year) in filename
    
    def test_generate_filename_timestamp_formatting(self):
        """Test that colons in timestamp are replaced for filename safety."""
        metadata = {
            'test_id': 'r1_39',
            'timestamp': '2025-08-28T09:40:10'
        }
        
        filename = generate_filename(metadata)
        
        # Colons should be replaced with underscores
        assert ':' not in filename
        assert '09_40_10' in filename
    
    def test_validate_single_file_portability_valid(self, temp_dir, sample_html):
        """Test validation of portable HTML file."""
        file_path = save_report(sample_html, output_dir=temp_dir, filename='portable_report')
        
        is_portable = validate_single_file_portability(file_path)
        
        assert is_portable is True
    
    def test_validate_single_file_portability_external_css(self, temp_dir):
        """Test validation fails for HTML with external CSS."""
        html_with_external_css = """<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="external.css">
</head>
<body>Test</body>
</html>"""
        
        file_path = save_report(html_with_external_css, output_dir=temp_dir, filename='external_css')
        
        is_portable = validate_single_file_portability(file_path)
        
        assert is_portable is False
    
    def test_validate_single_file_portability_allows_plotly_cdn(self, temp_dir):
        """Test validation allows Plotly CDN reference."""
        html_with_plotly = """<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
</head>
<body>
    <div id="plotly-chart"></div>
</body>
</html>"""
        
        file_path = save_report(html_with_plotly, output_dir=temp_dir, filename='plotly_report')
        
        # Should still be considered portable (Plotly CDN is allowed)
        is_portable = validate_single_file_portability(file_path)
        
        # This should be True since we allow Plotly CDN
        assert is_portable is True
    
    def test_validate_single_file_portability_file_not_found(self):
        """Test validation raises error for non-existent file."""
        with pytest.raises(FileNotFoundError):
            validate_single_file_portability('/nonexistent/file.html')
    
    def test_cleanup_old_reports_dry_run(self, temp_dir, sample_html):
        """Test cleanup in dry run mode doesn't delete files."""
        # Create some old reports (must start with 'report_' to match cleanup pattern)
        old_file = save_report(sample_html, output_dir=temp_dir, filename='report_old_1')
        new_file = save_report(sample_html, output_dir=temp_dir, filename='report_new_1')
        
        # Make one file appear old by modifying its timestamp
        old_time = datetime.now() - timedelta(days=35)
        os.utime(old_file, (old_time.timestamp(), old_time.timestamp()))
        
        # Run cleanup in dry run mode
        count = cleanup_old_reports(output_dir=temp_dir, max_age_days=30, dry_run=True)
        
        # File should still exist
        assert os.path.exists(old_file)
        assert count == 1  # Would delete 1 file
    
    def test_cleanup_old_reports_deletes_old_files(self, temp_dir, sample_html):
        """Test cleanup actually deletes old files."""
        # Create some reports (must start with 'report_' to match cleanup pattern)
        old_file = save_report(sample_html, output_dir=temp_dir, filename='report_old_2')
        new_file = save_report(sample_html, output_dir=temp_dir, filename='report_new_2')
        
        # Make one file appear old
        old_time = datetime.now() - timedelta(days=35)
        os.utime(old_file, (old_time.timestamp(), old_time.timestamp()))
        
        # Run cleanup
        count = cleanup_old_reports(output_dir=temp_dir, max_age_days=30, dry_run=False)
        
        # Old file should be deleted
        assert not os.path.exists(old_file)
        # New file should still exist
        assert os.path.exists(new_file)
        assert count == 1
    
    def test_cleanup_old_reports_preserves_recent_files(self, temp_dir, sample_html):
        """Test cleanup doesn't delete recent files."""
        # Create recent reports
        file1 = save_report(sample_html, output_dir=temp_dir, filename='recent_1')
        file2 = save_report(sample_html, output_dir=temp_dir, filename='recent_2')
        
        # Run cleanup
        count = cleanup_old_reports(output_dir=temp_dir, max_age_days=30)
        
        # Both files should still exist
        assert os.path.exists(file1)
        assert os.path.exists(file2)
        assert count == 0
    
    def test_cleanup_old_reports_nonexistent_directory(self):
        """Test cleanup handles non-existent directory gracefully."""
        count = cleanup_old_reports(output_dir='/nonexistent/dir', max_age_days=30)
        
        assert count == 0
    
    def test_get_report_list_empty_directory(self, temp_dir):
        """Test get_report_list with empty directory."""
        reports = get_report_list(output_dir=temp_dir)
        
        assert reports == []
    
    def test_get_report_list_with_reports(self, temp_dir, sample_html):
        """Test get_report_list returns all reports with metadata."""
        # Create some reports
        file1 = save_report(sample_html, output_dir=temp_dir, filename='report_1')
        file2 = save_report(sample_html, output_dir=temp_dir, filename='report_2')
        
        reports = get_report_list(output_dir=temp_dir)
        
        assert len(reports) == 2
        
        # Check structure
        for report in reports:
            assert 'filename' in report
            assert 'path' in report
            assert 'size' in report
            assert 'modified_time' in report
            assert report['filename'].endswith('.html')
            assert report['size'] > 0
    
    def test_get_report_list_sorted_by_modified_time(self, temp_dir, sample_html):
        """Test get_report_list returns reports sorted by modification time."""
        # Create reports with different timestamps
        old_file = save_report(sample_html, output_dir=temp_dir, filename='report_old')
        
        # Make it older
        old_time = datetime.now() - timedelta(days=5)
        os.utime(old_file, (old_time.timestamp(), old_time.timestamp()))
        
        # Create newer report
        new_file = save_report(sample_html, output_dir=temp_dir, filename='report_new')
        
        reports = get_report_list(output_dir=temp_dir)
        
        # Newest should be first
        assert 'report_new' in reports[0]['filename']
        assert 'report_old' in reports[1]['filename']
    
    def test_get_report_list_nonexistent_directory(self):
        """Test get_report_list handles non-existent directory gracefully."""
        reports = get_report_list(output_dir='/nonexistent/dir')
        
        assert reports == []
    
    def test_save_report_returns_absolute_path(self, temp_dir, sample_html):
        """Test that save_report returns absolute path."""
        file_path = save_report(sample_html, output_dir=temp_dir, filename='test')
        
        assert os.path.isabs(file_path)
        assert os.path.exists(file_path)
    
    def test_save_report_nested_directory_creation(self, temp_dir, sample_html):
        """Test save_report creates nested directories."""
        nested_dir = os.path.join(temp_dir, 'level1', 'level2', 'level3')
        
        file_path = save_report(sample_html, output_dir=nested_dir, filename='nested_report')
        
        assert os.path.exists(nested_dir)
        assert os.path.exists(file_path)
    
    def test_multiple_reports_same_directory(self, temp_dir, sample_html):
        """Test saving multiple reports to same directory."""
        file1 = save_report(sample_html, output_dir=temp_dir, filename='report_a')
        file2 = save_report(sample_html, output_dir=temp_dir, filename='report_b')
        file3 = save_report(sample_html, output_dir=temp_dir, filename='report_c')
        
        assert os.path.exists(file1)
        assert os.path.exists(file2)
        assert os.path.exists(file3)
        
        reports = get_report_list(output_dir=temp_dir)
        assert len(reports) == 3

