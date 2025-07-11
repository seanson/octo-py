# Octopus Deploy CLI

[![Tests](https://github.com/seanson/octo-py/actions/workflows/test.yml/badge.svg)](https://github.com/seanson/octo-py/actions/workflows/test.yml)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A Python command-line interface for interacting with Octopus Deploy servers. This tool provides commands for managing spaces, projects, releases, and deployments.

## Installation

### Prerequisites

- Python 3.13 or higher
- Poetry (for dependency management)

### Setup

1. Clone the repository:

```bash
git clone <repository-url>
cd octo-py
```

2. Install dependencies:

```bash
poetry install
```

3. Create configuration file:

```bash
mkdir -p ~/.config/octopus
```

Create `~/.config/octopus/cli_config.json` with your Octopus Deploy server details:

```json
{
  "url": "https://your-octopus-server.com",
  "apikey": "API-YOUR-API-KEY-HERE"
}
```

## Usage

Run the CLI using:

```bash
poetry run python src/main.py [COMMAND] [OPTIONS]
```

### Available Commands

#### `spaces`

List all spaces in your Octopus Deploy server.

```bash
poetry run python src/main.py spaces
```

**Output:**

```
Spaces-1: Default Space
Spaces-2: Development Space
```

#### `projects`

List all projects in a specific space.

```bash
poetry run python src/main.py projects <space_id>
```

**Example:**

```bash
poetry run python src/main.py projects Spaces-1
```

#### `releases`

List all releases for a specific project in a space.

```bash
poetry run python src/main.py releases <space_id> <project_id>
```

**Example:**

```bash
poetry run python src/main.py releases Spaces-1 Projects-1
```

#### `latest-release`

Get the latest release deployed to a specific environment.

```bash
poetry run python src/main.py latest-release <space_id> <project_id> [--environment <env_name>]
```

**Options:**

- `--environment`: Environment name (default: "staging")

**Example:**

```bash
poetry run python src/main.py latest-release Spaces-1 Projects-1 --environment production
```

#### `promote`

Promote the latest staging release to QA environment.

```bash
poetry run python src/main.py promote <space_name> <project_name>
```

**Example:**

```bash
poetry run python src/main.py promote "Default Space" "MyApp"
```

#### `deploy-all`

Deploy latest releases from one environment to another for all projects in a space.

```bash
poetry run python src/main.py deploy-all <source_environment> <target_environment> --space <space_name> [OPTIONS]
```

**Required Arguments:**

- `source_environment`: Source environment name (e.g., "staging", "dev")
- `target_environment`: Target environment name (e.g., "production", "qa")

**Required Options:**

- `--space`: Space name (case-insensitive)

**Optional Options:**

- `--filter`: Filter projects by name (case-insensitive substring match)
- `--exclude`: Exclude projects by name (case-insensitive substring match) - **can be used multiple times**
- `--dry-run`: Show what would be deployed without actually deploying

**Examples:**

Deploy all projects from staging to production:

```bash
poetry run python src/main.py deploy-all staging production --space "Default Space"
```

Deploy with filtering:

```bash
poetry run python src/main.py deploy-all staging production --space "Default Space" --filter "api"
```

Deploy with multiple exclusions:

```bash
poetry run python src/main.py deploy-all staging production --space "Default Space" --exclude "test" --exclude "legacy" --exclude "deprecated"
```

Dry run to see what would be deployed:

```bash
poetry run python src/main.py deploy-all staging production --space "Default Space" --dry-run
```

**Output:**
The command displays a progress bar while processing and then shows a summary table:

```
Found 5 projects in space 'Default Space'
Processing projects: 100%|████████████| 5/5 [00:30<00:00,  6.12s/project]

┌─────────────┬─────────────────┬────────────────────┬──────────────────┐
│ Project     │ Staging Version │ Production Version │ Action           │
├─────────────┼─────────────────┼────────────────────┼──────────────────┤
│ API Service │ 2.1.0           │ 2.0.0              │ Deployed         │
│ Web App     │ 1.5.2           │ 1.5.2              │ Already deployed │
│ Worker      │ 3.0.1           │ N/A                │ Deployed         │
└─────────────┴─────────────────┴────────────────────┴──────────────────┘

📊 Summary: 2 deployed, 1 already deployed, 0 skipped, 0 failed
```

### Configuration

The CLI requires a configuration file at `~/.config/octopus/cli_config.json` with the following structure:

```json
{
  "url": "https://your-octopus-server.com",
  "apikey": "API-YOUR-API-KEY-HERE"
}
```

**Configuration Details:**

- `url`: Your Octopus Deploy server URL (without trailing slash)
- `apikey`: Your Octopus Deploy API key

### Getting an API Key

1. Log in to your Octopus Deploy server
2. Go to your user profile
3. Navigate to "API Keys" tab
4. Create a new API key
5. Copy the key and add it to your configuration file

### Features

- **Case-insensitive matching**: Space names, project names, and environment names are matched case-insensitively
- **Bulk operations**: Deploy multiple projects at once with filtering and exclusion options
- **Progress tracking**: Visual progress bars for long-running operations
- **Dry run mode**: Preview deployments without actually executing them
- **Multiple exclusions**: Exclude multiple patterns by using `--exclude` multiple times
- **Detailed reporting**: Comprehensive tables and summaries of deployment results

### Error Handling

The CLI provides clear error messages for common issues:

- Missing or invalid configuration file
- Invalid API keys
- Non-existent spaces, projects, or environments
- Network connectivity issues
- Deployment failures

### Dependencies

- `requests`: HTTP client for Octopus Deploy API
- `click`: Command-line interface framework
- `tqdm`: Progress bars
- `tabulate`: Table formatting for output

### Development

To set up for development:

1. Install Poetry if you haven't already:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. Install dependencies including development dependencies:

```bash
poetry install --with dev
```

3. Run the CLI:

```bash
poetry run python src/main.py --help
```

### Testing

The project includes comprehensive pytest tests for the OctopusClient API.

#### Running Tests

The project includes a Makefile for convenient testing and development tasks.

1. Install development dependencies:

```bash
make install-dev
```

2. Run all tests:

```bash
make test
```

3. Run tests with coverage:

```bash
make test-cov
```

4. Run specific tests:

```bash
# Run a specific test class
make test-specific TEST=TestOctopusClientInitialization

# Run a specific test method
make test-specific TEST=test_init_with_valid_config
```

5. Run linting checks with ruff:

```bash
make lint
```

6. Format code with ruff:

```bash
make format
```

7. Run all checks (format, lint, test):

```bash
make check
```

8. View all available make targets:

```bash
make help
```

#### Test Structure

- `tests/test_octopus.py` - Tests for the OctopusClient API
- `tests/conftest.py` - Shared pytest fixtures

#### Test Coverage

The test suite includes:
- Configuration and initialization tests
- API request method tests (GET, POST, pagination)
- Space-related operations
- Project-related operations
- Release and deployment operations
- Error handling and edge cases

#### Running Specific Tests

Run a specific test class:

```bash
poetry run pytest tests/test_octopus.py::TestOctopusClientInitialization
```

Run a specific test:

```bash
poetry run pytest tests/test_octopus.py::TestOctopusClientInitialization::test_init_with_valid_config
```

### License

This project is licensed under the terms specified in the project configuration.
