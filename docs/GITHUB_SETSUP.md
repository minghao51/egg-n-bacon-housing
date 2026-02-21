# GitHub Secrets Setup for Webapp Deployment

This document describes how to configure the required GitHub Repository Secrets for the automated webapp deployment workflow.

## Required Secrets

The deployment workflow (`.github/workflows/deploy-app.yml`) requires two API keys to generate dashboard data:

### 1. ONEMAP_EMAIL

**Purpose**: Email address for accessing Singapore's OneMap geocoding API.

**How to obtain**:
1. Use any valid email address (personal or work email)
2. No registration required - OneMap API is free and open
3. The email is used to generate an access token automatically

**Value**: Your email address (e.g., `your-email@example.com`)

### 2. GOOGLE_API_KEY

**Purpose**: API key for Google Maps Geocoding API (fallback when OneMap fails).

**How to obtain**:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to **APIs & Services** → **Credentials**
4. Click **Create Credentials** → **API Key**
5. Restrict the API key:
   - **Application restrictions**: None (or add GitHub Actions IP ranges if needed)
   - **API restrictions**: Only enable **Geocoding API**
6. Copy the API key

**Value**: Your Google Maps API key (e.g., `AIzaSy...`)

## Setup Instructions

### Step 1: Navigate to Repository Settings

1. Go to your GitHub repository
2. Click **Settings** tab
3. In the left sidebar, click **Secrets and variables** → **Actions**

### Step 2: Add ONEMAP_EMAIL Secret

1. Click **New repository secret**
2. Name: `ONEMAP_EMAIL`
3. Value: Your email address
4. Click **Add secret**

### Step 3: Add GOOGLE_API_KEY Secret

1. Click **New repository secret**
2. Name: `GOOGLE_API_KEY`
3. Value: Your Google Maps API key
4. Click **Add secret**

### Step 4: Verify Secrets

After adding both secrets, you should see:
- ✅ `ONEMAP_EMAIL`
- ✅ `GOOGLE_API_KEY`

## Troubleshooting

### Secret Not Found Error

If you see this error in the GitHub Actions workflow:
```
Error: Input required and not supplied: ONEMAP_EMAIL
```

**Solution**: Verify the secret name exactly matches (case-sensitive):
- ✅ `ONEMAP_EMAIL`
- ❌ `onemap_email`
- ❌ `ONEMAP_EMAIL_ADDRESS`

### API Key Not Working

If the data generation fails with API errors:

1. **For Google API Key**:
   - Verify the Geocoding API is enabled
   - Check if the API key has quotas/restrictions
   - Ensure billing is enabled (free tier should be sufficient)

2. **For OneMap**:
   - Verify the email address is valid
   - Check if OneMap service is available
   - Review error logs in GitHub Actions

### Testing Secrets Locally

You can test if your secrets work by setting them locally:

```bash
# Copy your .env.example to .env
cp .env.example .env

# Edit .env and add your actual values
nano .env  # or use your preferred editor

# Run the data generation script
uv run scripts/prepare_webapp_data.py
```

If this succeeds, your secrets are valid and ready for GitHub.

## Security Best Practices

1. **Never commit secrets to git** - Always use environment variables or GitHub Secrets
2. **Restrict API keys** - Only enable the specific APIs you need
3. **Monitor usage** - Check Google Cloud Console for unusual API usage
4. **Rotate keys periodically** - Update secrets if a key is compromised
5. **Use separate keys** - Don't reuse the same API key across multiple projects

## Related Documentation

- [GitHub Actions Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Google Maps Geocoding API Documentation](https://developers.google.com/maps/documentation/geocoding/overview)
- [OneMap API Documentation](https://www.onemap.gov.sg/docs/)

## Workflow Usage

Once secrets are configured, the deployment workflow will:

1. Generate dashboard data using the API keys
2. Verify all required data files are created
3. Build the Astro app with the data
4. Deploy to GitHub Pages

The workflow runs automatically on every push to the `main` branch.
