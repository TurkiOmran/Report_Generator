# Power Profile Report Generator - Setup Guide

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment (if not already created)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

### 2. Configure API Key

```bash
# Copy the environment template
cp .env.example .env

# Edit .env and add your Anthropic API key
# Use your favorite text editor:
notepad .env  # Windows
nano .env     # macOS/Linux
```

#### Getting Your Anthropic API Key

1. Visit [Anthropic Console](https://console.anthropic.com/)
2. Sign up or log in to your account
3. Navigate to **API Keys** section
4. Click **Create Key** or copy an existing key
5. Paste it in your `.env` file:
   ```
   ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
   ```

### 3. Verify Setup

```bash
# Run a simple test to verify API connectivity
python -c "from src.analysis.claude_client import get_analysis; print('✅ Setup complete!')" 2>&1 | grep -E "(✅|ANTHROPIC_API_KEY)"
```

If you see `✅ Setup complete!`, you're ready to go!

If you see an error about `ANTHROPIC_API_KEY not found`, check your `.env` file.

---

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key for Claude | `sk-ant-api03-...` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |
| `CLAUDE_MODEL` | `claude-sonnet-4-20250514` | Claude model to use |
| `CLAUDE_TIMEOUT` | `60` | API request timeout (seconds) |
| `CLAUDE_MAX_TOKENS` | `2000` | Maximum tokens in API response |
| `ANTHROPIC_BASE_URL` | `https://api.anthropic.com` | API endpoint URL |
| `DEBUG` | `false` | Enable verbose debug logging |
| `TEST_MOCK_API` | `true` | Use mocked API calls in tests |

---

## API Cost Estimation

The LLM analysis feature uses Claude Sonnet 4 by default. Here's what to expect:

### Per Analysis Cost
- **Input**: ~14,000 tokens (one CSV file)
- **Output**: ~500 tokens (narrative analysis)
- **Cost**: ~$0.05-0.10 per analysis

### Model Pricing (as of 2025)
| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| Claude Sonnet 4 | $3.00 | $15.00 |
| Claude 3.5 Sonnet | $3.00 | $15.00 |
| Claude 3 Opus | $15.00 | $75.00 |

**Cost Control Tips:**
- Set spending limits in [Anthropic Console](https://console.anthropic.com/settings/limits)
- Monitor usage regularly
- Use Claude Sonnet instead of Opus for development
- Cache results to avoid redundant API calls

---

## Troubleshooting

### Error: "ANTHROPIC_API_KEY not found"

**Solution:** Make sure you've created a `.env` file (not `.env.example`) with your actual API key.

```bash
# Check if .env exists
ls -a | grep .env

# If only .env.example exists, copy it:
cp .env.example .env

# Then edit .env and add your API key
```

### Error: "Invalid API key"

**Solution:** Verify your API key is correct:

1. Check for typos or extra whitespace
2. Ensure key starts with `sk-ant-`
3. Verify key is active in [Anthropic Console](https://console.anthropic.com/)
4. Try generating a new key

### Error: "Request timeout"

**Solution:** Increase the timeout in your `.env` file:

```
CLAUDE_TIMEOUT=120
```

### Error: "Rate limit exceeded"

**Solution:** You've exceeded your API rate limit. Options:

1. Wait a few minutes and try again
2. Upgrade your Anthropic plan for higher limits
3. Implement request throttling in your code

---

## Security Best Practices

### ✅ DO:

- **Keep `.env` private**: Never commit it to version control
- **Use separate keys**: Different keys for dev, test, and production
- **Rotate regularly**: Change API keys periodically
- **Monitor usage**: Check [Anthropic Console](https://console.anthropic.com/) regularly
- **Set spending limits**: Configure budget alerts

### ❌ DON'T:

- **Don't commit `.env`**: It's in `.gitignore` for a reason
- **Don't share keys**: Not in screenshots, Slack, email, etc.
- **Don't hard-code**: Never put API keys directly in source code
- **Don't use prod keys for testing**: Keep environments separate

### If You Accidentally Expose Your Key:

1. **Revoke immediately** in [Anthropic Console](https://console.anthropic.com/)
2. **Generate new key**
3. **Update `.env` file**
4. **Check git history**: `git log -p | grep -i "api"`
5. **Rotate other secrets** if same credentials used elsewhere

---

## Testing Without API Key

For running tests without making actual API calls:

```bash
# Set mock mode in .env
TEST_MOCK_API=true

# Or set as environment variable
TEST_MOCK_API=true pytest

# Or run only unit tests (which use mocks by default)
pytest -m "not integration"
```

---

## Additional Resources

- [Anthropic API Documentation](https://docs.anthropic.com/)
- [Claude API Pricing](https://www.anthropic.com/pricing)
- [Anthropic Console](https://console.anthropic.com/)
- [API Rate Limits](https://docs.anthropic.com/en/api/rate-limits)

---

## Need Help?

If you encounter issues not covered here:

1. Check the [project README](../README.md)
2. Review [test examples](../tests/test_analysis/)
3. Open an issue on GitHub
4. Contact the development team

---

**Last Updated:** November 2025

