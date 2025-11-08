"""Verification test to ensure project structure is working"""
import sys
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def test_module_imports():
    """Test that all project modules can be imported"""
    # Data processing modules
    from data_processing import ingestion, validation
    
    # Metrics modules
    from metrics import basic_metrics, time_metrics, anomaly_metrics
    
    # Other modules
    import analysis
    import visualization
    import reporting
    
    assert ingestion is not None
    assert validation is not None
    assert basic_metrics is not None
    assert time_metrics is not None
    assert anomaly_metrics is not None
    assert analysis is not None
    assert visualization is not None
    assert reporting is not None


def test_dependencies_available():
    """Test that all required dependencies are installed"""
    import pandas as pd
    import numpy as np
    import plotly
    import anthropic
    import pydantic
    import dotenv
    import pytest
    
    # Test basic functionality
    df = pd.DataFrame({'a': [1, 2, 3]})
    arr = np.array([1, 2, 3])
    
    assert len(df) == 3
    assert len(arr) == 3


if __name__ == "__main__":
    test_module_imports()
    test_dependencies_available()
    print("✅ All verification tests passed!")

