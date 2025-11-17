# GitHub Actions CI/CD Workflows

This directory contains the CI/CD workflows for the NBA Game Recommender project.

## Workflows

### 1. CI - Run Tests (`ci.yml`)

**Triggers:**
- Pull requests to `main` or `master` branches
- Direct pushes to `main` or `master` branches

**What it does:**
- Sets up Python 3.11
- Installs dependencies using `uv`
- Runs the complete test suite with coverage
- Uploads coverage reports to Codecov (optional)

**No setup required** - this workflow works out of the box.

### 2. CD - Deploy to Render (`cd.yml`)

**Triggers:**
- Pushes to `main` or `master` branches (typically after PR merge)

**What it does:**
- Triggers an automatic deployment to Render
- Verifies the deployment was triggered successfully

**Setup Required:**

1. **Get your Render Deploy Hook URL:**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Select your service (`nba-game-recommender`)
   - Navigate to **Settings** → **Deploy Hook**
   - Copy the Deploy Hook URL

2. **Add the URL as a GitHub Secret:**
   - Go to your GitHub repository
   - Navigate to **Settings** → **Secrets and variables** → **Actions**
   - Click **New repository secret**
   - Name: `RENDER_DEPLOY_HOOK_URL`
   - Value: Paste the Deploy Hook URL from Render
   - Click **Add secret**

3. **That's it!** The CD workflow will now automatically deploy to Render whenever changes are merged to the main branch.

## Optional: Codecov Integration

To enable code coverage reporting:

1. Sign up at [codecov.io](https://codecov.io/)
2. Add your repository
3. Get your Codecov token
4. Add it as a GitHub secret named `CODECOV_TOKEN`

This is optional - the CI workflow will continue to work without it.

## Workflow Behavior

- **On Pull Request:** Only CI runs (tests)
- **On PR Merge to Main:** Both CI runs and CD triggers deployment
- **On Direct Push to Main:** Both CI runs and CD triggers deployment

## Testing Locally

Before pushing, you can run tests locally:

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src --cov-report=term-missing
```
