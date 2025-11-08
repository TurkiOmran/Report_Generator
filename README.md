# Power Profile Report Generator

A Python tool for analyzing miner power profile test data and generating comprehensive reports with AI-powered insights.

## Features

- **Data Ingestion & Validation**: Robust CSV parsing with Pydantic schema validation
- **Deterministic Metrics**: Calculate 10+ power profile metrics including start power, band entry, stable plateau, and anomaly detection
- **AI Analysis**: LLM-powered insights using Claude (Anthropic API)
- **Interactive Visualizations**: Plotly charts with zoom, pan, and hover details
- **Comprehensive Reports**: Automated report generation with metrics, charts, and analysis

## Project Structure

```
project-root/
├── src/
│   ├── data_processing/     # CSV ingestion and validation
│   ├── metrics/             # Metric calculation modules
│   ├── analysis/            # LLM-powered analysis
│   ├── visualization/       # Plotly chart generation
│   └── reporting/           # Report generation
├── tests/                   # Test suite with real CSV data
└── requirements.txt         # Python dependencies
```

## Setup

### Prerequisites

- Python 3.13+
- pip

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd Report_Genrator
```

2. Create and activate virtual environment:
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your Anthropic API key
```

## Usage

```python
# Coming soon - example usage will be added as modules are implemented
```

## Development

### Running Tests

```bash
pytest
```

### Test Coverage

```bash
pytest --cov=src --cov-report=html
```

## Reference

This project implements metrics based on the pseudocode specification in `R_Test_Metrics_Complete_Pseudocode_v3.md`.

## License

[Add license information]

