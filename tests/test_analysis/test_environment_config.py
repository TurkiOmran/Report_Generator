"""
Tests for environment configuration and API key management.

Tests cover:
- API key validation
- Environment variable loading
- Configuration error handling
- Security checks
"""

import pytest
import os
from unittest.mock import patch


class TestAPIKeyValidation:
    """Test suite for API key validation."""
    
    def test_api_key_required_for_get_analysis(self, monkeypatch):
        """Should raise ValueError if API key is missing."""
        from src.analysis.claude_client import get_analysis
        
        # Remove API key from environment
        monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
        
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY not found"):
            get_analysis("test prompt")
    
    def test_api_key_loaded_from_env(self, monkeypatch):
        """Should load API key from environment variable."""
        from src.analysis.claude_client import get_analysis
        from unittest.mock import patch, MagicMock
        
        # Set fake API key
        monkeypatch.setenv('ANTHROPIC_API_KEY', 'sk-ant-test-key-123')
        
        # Mock the anthropic client to avoid actual API call
        with patch('src.analysis.claude_client.anthropic.Anthropic') as mock_client:
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="Test analysis")]
            mock_response.usage = MagicMock(input_tokens=100, output_tokens=50)
            mock_response.model = "claude-sonnet-4"
            mock_response.stop_reason = "end_turn"
            mock_client.return_value.messages.create.return_value = mock_response
            
            result = get_analysis("test prompt")
            assert isinstance(result, dict)
            assert 'analysis' in result
    
    def test_empty_api_key_treated_as_missing(self, monkeypatch):
        """Should treat empty API key as missing."""
        from src.analysis.claude_client import get_analysis
        
        # Set empty API key
        monkeypatch.setenv('ANTHROPIC_API_KEY', '')
        
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY not found"):
            get_analysis("test prompt")
    
    def test_whitespace_api_key_treated_as_missing(self, monkeypatch):
        """Should treat whitespace-only API key as missing."""
        from src.analysis.claude_client import get_analysis
        
        # Set whitespace API key
        monkeypatch.setenv('ANTHROPIC_API_KEY', '   ')
        
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY not found"):
            get_analysis("test prompt")


class TestEnvironmentVariableLoading:
    """Test suite for environment variable loading."""
    
    def test_dotenv_loads_on_import(self):
        """dotenv.load_dotenv() should be called on module import."""
        # This test just verifies that load_dotenv is present in the module
        import src.analysis.claude_client as client_module
        import inspect
        
        # Check that load_dotenv is imported and called
        source = inspect.getsource(client_module)
        assert 'from dotenv import load_dotenv' in source
        assert 'load_dotenv()' in source
    
    def test_env_variables_precedence(self, monkeypatch, tmp_path):
        """Environment variables should take precedence over .env file."""
        # Create .env file with one key
        env_file = tmp_path / ".env"
        env_file.write_text("ANTHROPIC_API_KEY=sk-ant-from-file\n")
        
        # Set different key in environment
        monkeypatch.setenv('ANTHROPIC_API_KEY', 'sk-ant-from-env')
        monkeypatch.chdir(tmp_path)
        
        # Force reimport
        import importlib
        import src.analysis.claude_client as client_module
        importlib.reload(client_module)
        
        # Environment variable should win
        assert os.getenv('ANTHROPIC_API_KEY') == 'sk-ant-from-env'


class TestConfigurationSecurity:
    """Test suite for configuration security practices."""
    
    def test_api_key_not_logged_in_errors(self, monkeypatch, caplog):
        """Should not expose API key in error messages or logs."""
        from src.analysis.claude_client import get_analysis
        from unittest.mock import patch, MagicMock
        
        # Set API key
        monkeypatch.setenv('ANTHROPIC_API_KEY', 'sk-ant-secret-key-12345')
        
        # Mock the API to avoid actual calls
        with patch('src.analysis.claude_client.anthropic.Anthropic') as mock_client:
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="Test")]
            mock_response.usage = MagicMock(input_tokens=100, output_tokens=50)
            mock_response.model = "claude-sonnet-4"
            mock_response.stop_reason = "end_turn"
            mock_client.return_value.messages.create.return_value = mock_response
            
            try:
                get_analysis("test")
            except Exception:
                pass
        
        # Check that API key doesn't appear in logs
        log_text = caplog.text.lower()
        assert 'sk-ant-secret-key-12345' not in log_text
        assert 'secret-key' not in log_text
    
    def test_empty_key_error_message_helpful(self, monkeypatch):
        """Error message for missing key should be helpful."""
        from src.analysis.claude_client import get_analysis
        
        monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
        
        with pytest.raises(ValueError) as exc_info:
            get_analysis("test")
        
        error_msg = str(exc_info.value)
        # Should mention environment or .env file
        assert '.env' in error_msg.lower() or 'environment' in error_msg.lower()


class TestConfigurationDefaults:
    """Test suite for default configuration values."""
    
    def test_default_model_used(self, monkeypatch):
        """Should use claude-sonnet-4-20250514 as default model."""
        from src.analysis.claude_client import get_analysis
        import inspect
        
        # Check function signature defaults
        sig = inspect.signature(get_analysis)
        assert sig.parameters['model'].default == "claude-sonnet-4-20250514"
    
    def test_default_timeout_60_seconds(self, monkeypatch):
        """Should use 60 seconds as default timeout."""
        from src.analysis.claude_client import get_analysis
        import inspect
        
        # Check function signature defaults
        sig = inspect.signature(get_analysis)
        assert sig.parameters['timeout'].default == 60
    
    def test_custom_model_parameter(self, monkeypatch):
        """Should accept custom model parameter."""
        from src.analysis.claude_client import get_analysis
        from unittest.mock import patch, MagicMock
        
        monkeypatch.setenv('ANTHROPIC_API_KEY', 'sk-ant-test')
        
        # Mock the API to verify custom model parameter
        with patch('src.analysis.claude_client.anthropic.Anthropic') as mock_client:
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="Test")]
            mock_response.usage = MagicMock(input_tokens=100, output_tokens=50)
            mock_response.model = "claude-3-opus-20240229"
            mock_response.stop_reason = "end_turn"
            mock_client.return_value.messages.create.return_value = mock_response
            
            result = get_analysis("test", model="claude-3-opus-20240229")
            assert result['model'] == "claude-3-opus-20240229"
    
    def test_custom_timeout_parameter(self, monkeypatch):
        """Should accept custom timeout parameter."""
        from src.analysis.claude_client import get_analysis
        from unittest.mock import patch, MagicMock
        
        monkeypatch.setenv('ANTHROPIC_API_KEY', 'sk-ant-test')
        
        # Mock the API to verify timeout parameter is passed
        with patch('src.analysis.claude_client.anthropic.Anthropic') as mock_client:
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="Test")]
            mock_response.usage = MagicMock(input_tokens=100, output_tokens=50)
            mock_response.model = "claude-sonnet-4"
            mock_response.stop_reason = "end_turn"
            mock_client.return_value.messages.create.return_value = mock_response
            
            result = get_analysis("test", timeout=120)
            
            # Verify client was initialized with custom timeout
            mock_client.assert_called_once()
            call_kwargs = mock_client.call_args.kwargs
            assert call_kwargs['timeout'] == 120


class TestEnvExampleFile:
    """Test suite for .env.example file completeness."""
    
    def test_env_example_exists(self):
        """Should have .env.example file in project root."""
        import os
        from pathlib import Path
        
        project_root = Path(__file__).parent.parent.parent
        env_example = project_root / ".env.example"
        
        assert env_example.exists(), ".env.example file should exist in project root"
    
    def test_env_example_has_anthropic_key(self):
        """Should include ANTHROPIC_API_KEY in .env.example."""
        from pathlib import Path
        
        project_root = Path(__file__).parent.parent.parent
        env_example = project_root / ".env.example"
        
        if env_example.exists():
            content = env_example.read_text(encoding='utf-8')
            assert 'ANTHROPIC_API_KEY' in content
    
    def test_env_example_has_instructions(self):
        """Should include setup instructions in .env.example."""
        from pathlib import Path
        
        project_root = Path(__file__).parent.parent.parent
        env_example = project_root / ".env.example"
        
        if env_example.exists():
            content = env_example.read_text(encoding='utf-8')
            # Should have comments explaining how to get API key
            assert 'console.anthropic.com' in content.lower()
            assert 'api' in content.lower()
    
    def test_env_example_has_security_warnings(self):
        """Should include security warnings in .env.example."""
        from pathlib import Path
        
        project_root = Path(__file__).parent.parent.parent
        env_example = project_root / ".env.example"
        
        if env_example.exists():
            content = env_example.read_text(encoding='utf-8')
            # Should warn about security
            assert any(word in content.lower() for word in ['security', 'private', 'secret', 'never commit'])


class TestSetupDocumentation:
    """Test suite for setup documentation completeness."""
    
    def test_setup_guide_exists(self):
        """Should have SETUP.md documentation."""
        from pathlib import Path
        
        docs_dir = Path(__file__).parent.parent.parent / "docs"
        setup_doc = docs_dir / "SETUP.md"
        
        assert setup_doc.exists(), "docs/SETUP.md should exist"
    
    def test_setup_guide_explains_api_key(self):
        """Setup guide should explain how to get API key."""
        from pathlib import Path
        
        docs_dir = Path(__file__).parent.parent.parent / "docs"
        setup_doc = docs_dir / "SETUP.md"
        
        if setup_doc.exists():
            content = setup_doc.read_text(encoding='utf-8')
            assert 'api key' in content.lower()
            assert 'anthropic' in content.lower()
    
    def test_setup_guide_has_quick_start(self):
        """Setup guide should have quick start section."""
        from pathlib import Path
        
        docs_dir = Path(__file__).parent.parent.parent / "docs"
        setup_doc = docs_dir / "SETUP.md"
        
        if setup_doc.exists():
            content = setup_doc.read_text(encoding='utf-8')
            assert 'quick' in content.lower() or 'getting started' in content.lower()
    
    def test_setup_guide_explains_costs(self):
        """Setup guide should explain API costs."""
        from pathlib import Path
        
        docs_dir = Path(__file__).parent.parent.parent / "docs"
        setup_doc = docs_dir / "SETUP.md"
        
        if setup_doc.exists():
            content = setup_doc.read_text(encoding='utf-8')
            assert 'cost' in content.lower() or 'pricing' in content.lower()


class TestGitignoreConfiguration:
    """Test suite for .gitignore configuration."""
    
    def test_gitignore_excludes_env_file(self):
        """Should have .env in .gitignore."""
        from pathlib import Path
        
        project_root = Path(__file__).parent.parent.parent
        gitignore = project_root / ".gitignore"
        
        if gitignore.exists():
            content = gitignore.read_text()
            assert '.env' in content
            # Make sure .env.example is NOT excluded
            # (or if it is, it should be explicitly allowed)
    
    def test_env_file_not_in_repo(self):
        """Actual .env file should not be committed to repo."""
        from pathlib import Path
        import subprocess
        
        project_root = Path(__file__).parent.parent.parent
        
        try:
            # Check if .env is tracked by git
            result = subprocess.run(
                ['git', 'ls-files', '.env'],
                cwd=project_root,
                capture_output=True,
                text=True
            )
            
            # .env should NOT be in git ls-files output
            assert '.env' not in result.stdout, ".env file should not be tracked by git"
        except (subprocess.SubprocessError, FileNotFoundError):
            # Git not available or not a git repo, skip test
            pytest.skip("Git not available or not a git repository")

