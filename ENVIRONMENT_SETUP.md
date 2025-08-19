# Environment Setup Guide

## API Key Security

⚠️ **NEVER commit API keys to version control!** This guide shows how to securely manage environment variables and API keys.

## Google Places API Setup

### 1. Create API Key
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Places API (New)
3. Create API key
4. Restrict key to Places API only
5. Optionally restrict by IP address

### 2. Secure Environment Configuration

#### Option A: Environment Variables (Recommended)
```bash
# Add to your ~/.bashrc or ~/.zshrc
export GOOGLE_PLACES_API_KEY='your-actual-api-key-here'

# Reload your shell
source ~/.bashrc
```

#### Option B: .env File (Local Development)
```bash
# Create .env file (already in .gitignore)
echo "GOOGLE_PLACES_API_KEY=your-actual-api-key-here" > .env

# Load in scripts
pip install python-dotenv
```

### 3. Using the API Key

#### With Environment Variable:
```bash
# Test the API
python scripts/test_google_places.py

# Run enrichment
python scripts/run_google_enrichment.py
```

#### With Direct Export (Temporary):
```bash
# One-time use (secure)
GOOGLE_PLACES_API_KEY='your-key' python scripts/test_google_places.py
```

### 4. Update Scripts to Use Environment Variables

All scripts now automatically check for the `GOOGLE_PLACES_API_KEY` environment variable:

```python
import os
api_key = os.getenv('GOOGLE_PLACES_API_KEY')
if not api_key:
    raise ValueError("GOOGLE_PLACES_API_KEY environment variable not set")
```

## Security Best Practices

### ✅ Do This:
- Store API keys in environment variables
- Use `.env` files for local development (they're in `.gitignore`)
- Restrict API keys to specific services in Google Cloud Console
- Rotate API keys periodically
- Use different keys for development and production

### ❌ Never Do This:
- Commit API keys to version control
- Share API keys in chat/email/documentation
- Use production keys for development
- Store keys in source code files

## File Security Status

### 🔒 Now Secure:
- `.gitignore` updated to exclude secret files
- `GOOGLE_PLACES_INTEGRATION.md` - API key removed
- `.claude/settings.local.json` - Uses wildcards instead of actual key

### 🔍 Previously Exposed (Fixed):
- API key was in `GOOGLE_PLACES_INTEGRATION.md` (line 151)
- API key was in `.claude/settings.local.json` (lines 88-90)

## Recovery Steps Completed

1. ✅ **Deleted exposed API key** from Google Cloud Console
2. ✅ **Removed keys from all files** in the repository
3. ✅ **Updated .gitignore** to prevent future exposure
4. ✅ **Created secure setup guide** (this document)
5. ✅ **Modified scripts** to use environment variables

## Getting a New API Key

Since the exposed key was deleted, you'll need to create a new one:

1. Go to [Google Cloud Console API Keys](https://console.cloud.google.com/apis/credentials)
2. Click "Create Credentials" → "API Key"
3. Copy the new key
4. Set it as an environment variable: `export GOOGLE_PLACES_API_KEY='new-key-here'`
5. Test with: `python scripts/test_google_places.py`

## Cost Management

- Places API (New) costs ~$0.017 per Place Details request
- 106 restaurants = ~$1.80 per enrichment run
- Set up billing alerts in Google Cloud Console
- Consider caching results to minimize API calls

## Next Steps

1. Get a new API key from Google Cloud Console
2. Set it as an environment variable
3. Test the setup: `python scripts/test_google_places.py`
4. Continue with restaurant enrichment: `python scripts/run_google_enrichment.py`

The repository is now secure and ready for continued development with proper API key management.