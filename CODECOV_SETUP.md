# Codecov Setup Guide

This project is now configured to use Codecov for code coverage reporting. Here's what has been set up:

## What's Been Added

1. **CI Workflow Update** (`.github/workflows/ci.yml`)

   - Added a new `coverage` job that runs tests with coverage
   - Uploads coverage reports to Codecov using the `codecov/codecov-action@v3`

2. **Codecov Configuration** (`.codecov.yml`)

   - Configured coverage thresholds (85% target)
   - Set up proper file exclusions
   - Configured status checks and notifications

3. **README Badge**

   - Added Codecov badge to the README.md file

4. **Coverage Command Update**
   - Updated `test-cov` command to generate XML output for Codecov

## Next Steps

### 1. Connect to Codecov

1. Go to [Codecov.io](https://codecov.io) and sign in with your GitHub account
2. Add your repository: `chris-haste/fastapi-logger`
3. Codecov will automatically detect the coverage reports from your CI pipeline

### 2. Get Your Codecov Token (Optional)

If you want to upload coverage reports locally or need the token for other purposes:

1. Go to your repository settings on Codecov
2. Copy the upload token (it will look like: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)

### 3. Test the Integration

1. Push your changes to trigger the CI pipeline
2. Check the "Coverage" job in your GitHub Actions
3. Verify the badge appears on your README
4. Check your Codecov dashboard for coverage reports

## Current Coverage

Your project currently has **92% code coverage**, which is excellent and well above the 85% threshold configured in Codecov.

## Badge URL

The Codecov badge URL is:

```
https://codecov.io/gh/chris-haste/fastapi-logger/branch/main/graph/badge.svg
```

## Troubleshooting

- If the badge doesn't appear, make sure the CI pipeline has run successfully
- If coverage reports aren't uploading, check that the `coverage.xml` file is being generated
- The Codecov action will fail gracefully (`fail_ci_if_error: false`) so it won't break your CI pipeline

## Configuration Details

- **Coverage Target**: 85%
- **Coverage Threshold**: 5% (allows coverage to drop by 5% before failing)
- **File Exclusions**: Examples, tests, and setup files are excluded
- **Status Checks**: Both project and patch coverage are monitored
