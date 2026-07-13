"""Tests for the Click CLI defined in main.py."""

from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from src.main import cli


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_client(mocker):
    """Patch OctopusClient so the cli group injects a mock client into the context."""
    client = MagicMock()
    mocker.patch("src.main.OctopusClient", return_value=client)
    return client


class TestCliGroup:
    """The top-level group builds the Octopus client."""

    def test_client_init_failure_exits_1(self, runner, mocker):
        mocker.patch("src.main.OctopusClient", side_effect=RuntimeError("bad config"))
        result = runner.invoke(cli, ["spaces"])
        assert result.exit_code == 1
        assert "Error initializing Octopus client: bad config" in result.stderr


class TestSpacesCommand:
    def test_lists_spaces(self, runner, mock_client):
        mock_client.get_spaces.return_value = [
            {"Id": "Spaces-1", "Name": "Default"},
            {"Id": "Spaces-2", "Name": "Dev"},
        ]
        result = runner.invoke(cli, ["spaces"])
        assert result.exit_code == 0
        assert "Spaces-1: Default" in result.output
        assert "Spaces-2: Dev" in result.output

    def test_error_exits_1(self, runner, mock_client):
        mock_client.get_spaces.side_effect = RuntimeError("boom")
        result = runner.invoke(cli, ["spaces"])
        assert result.exit_code == 1
        assert "Error fetching spaces: boom" in result.stderr


class TestProjectsCommand:
    def test_lists_projects(self, runner, mock_client):
        mock_client.get_projects.return_value = [{"Id": "Projects-1", "Name": "API"}]
        result = runner.invoke(cli, ["projects", "Spaces-1"])
        assert result.exit_code == 0
        assert "Projects-1: API" in result.output
        mock_client.get_projects.assert_called_once_with("Spaces-1")

    def test_error_exits_1(self, runner, mock_client):
        mock_client.get_projects.side_effect = RuntimeError("nope")
        result = runner.invoke(cli, ["projects", "Spaces-1"])
        assert result.exit_code == 1
        assert "Error fetching projects: nope" in result.stderr


class TestReleasesCommand:
    def test_lists_releases(self, runner, mock_client):
        mock_client.get_releases.return_value = [{"Id": "Releases-1", "Version": "2.1.0"}]
        result = runner.invoke(cli, ["releases", "Spaces-1", "Projects-1"])
        assert result.exit_code == 0
        assert "Releases-1: 2.1.0" in result.output
        mock_client.get_releases.assert_called_once_with("Spaces-1", "Projects-1")

    def test_error_exits_1(self, runner, mock_client):
        mock_client.get_releases.side_effect = RuntimeError("fail")
        result = runner.invoke(cli, ["releases", "Spaces-1", "Projects-1"])
        assert result.exit_code == 1
        assert "Error fetching releases: fail" in result.stderr


class TestLatestReleaseCommand:
    def test_found_default_env(self, runner, mock_client):
        mock_client.get_latest_release_in_environment.return_value = {
            "Id": "Releases-1",
            "Version": "2.1.0",
        }
        result = runner.invoke(cli, ["latest-release", "Spaces-1", "Projects-1"])
        assert result.exit_code == 0
        assert "Releases-1: 2.1.0" in result.output
        mock_client.get_latest_release_in_environment.assert_called_once_with(
            "Spaces-1", "Projects-1", "staging"
        )

    def test_found_custom_env(self, runner, mock_client):
        mock_client.get_latest_release_in_environment.return_value = {
            "Id": "Releases-2",
            "Version": "3.0.0",
        }
        result = runner.invoke(
            cli,
            ["latest-release", "Spaces-1", "Projects-1", "--environment", "production"],
        )
        assert result.exit_code == 0
        mock_client.get_latest_release_in_environment.assert_called_once_with(
            "Spaces-1", "Projects-1", "production"
        )

    def test_none_found(self, runner, mock_client):
        mock_client.get_latest_release_in_environment.return_value = None
        result = runner.invoke(
            cli, ["latest-release", "Spaces-1", "Projects-1", "--environment", "qa"]
        )
        assert result.exit_code == 0
        assert "No releases found in qa environment" in result.output

    def test_error_exits_1(self, runner, mock_client):
        mock_client.get_latest_release_in_environment.side_effect = RuntimeError("x")
        result = runner.invoke(cli, ["latest-release", "Spaces-1", "Projects-1"])
        assert result.exit_code == 1
        assert "Error fetching latest release: x" in result.stderr


class TestPromoteCommand:
    @staticmethod
    def _happy_path(mock_client):
        mock_client.get_space_by_name.return_value = {"Id": "Spaces-1", "Name": "Default"}
        mock_client.get_project_by_name.return_value = {"Id": "Projects-1", "Name": "API"}
        mock_client.get_latest_release_in_environment.return_value = {
            "Id": "Releases-1",
            "Version": "2.1.0",
        }
        mock_client.get_environments.return_value = [{"Id": "Environments-3", "Name": "QA"}]
        mock_client.deploy_release.return_value = {"Id": "Deployments-1"}

    def test_success(self, runner, mock_client):
        self._happy_path(mock_client)
        result = runner.invoke(cli, ["promote", "Default", "API"])
        assert result.exit_code == 0
        assert "Promoting release 2.1.0 from staging to QA" in result.output
        assert "Deployment created: Deployments-1" in result.output
        mock_client.deploy_release.assert_called_once_with(
            "Spaces-1", "Releases-1", "Environments-3"
        )

    def test_space_not_found(self, runner, mock_client):
        mock_client.get_space_by_name.return_value = None
        result = runner.invoke(cli, ["promote", "Nope", "API"])
        assert result.exit_code == 1
        assert "Space 'Nope' not found" in result.output

    def test_project_not_found(self, runner, mock_client):
        mock_client.get_space_by_name.return_value = {"Id": "Spaces-1"}
        mock_client.get_project_by_name.return_value = None
        result = runner.invoke(cli, ["promote", "Default", "Ghost"])
        assert result.exit_code == 1
        assert "Project 'Ghost' not found in space 'Default'" in result.output

    def test_no_staging_release(self, runner, mock_client):
        mock_client.get_space_by_name.return_value = {"Id": "Spaces-1"}
        mock_client.get_project_by_name.return_value = {"Id": "Projects-1"}
        mock_client.get_latest_release_in_environment.return_value = None
        result = runner.invoke(cli, ["promote", "Default", "API"])
        assert result.exit_code == 1
        assert "No releases found in staging environment" in result.output

    def test_qa_environment_not_found(self, runner, mock_client):
        mock_client.get_space_by_name.return_value = {"Id": "Spaces-1"}
        mock_client.get_project_by_name.return_value = {"Id": "Projects-1"}
        mock_client.get_latest_release_in_environment.return_value = {
            "Id": "Releases-1",
            "Version": "2.1.0",
        }
        mock_client.get_environments.return_value = [{"Id": "Environments-2", "Name": "Staging"}]
        result = runner.invoke(cli, ["promote", "Default", "API"])
        assert result.exit_code == 1
        assert "QA environment not found" in result.output

    def test_error_exits_1(self, runner, mock_client):
        mock_client.get_space_by_name.side_effect = RuntimeError("api down")
        result = runner.invoke(cli, ["promote", "Default", "API"])
        assert result.exit_code == 1
        assert "Error promoting release: api down" in result.stderr


class TestDeployAllCommand:
    """The bulk deploy command and its filtering / dry-run / output branches."""

    @staticmethod
    def _release_by_env(mapping):
        """Build a get_latest_release_in_environment side effect keyed by environment."""

        def _side_effect(_space_id, _project_id, environment):
            return mapping.get(environment)

        return _side_effect

    def test_space_not_found(self, runner, mock_client):
        mock_client.get_space_by_name.return_value = None
        result = runner.invoke(cli, ["deploy-all", "staging", "production", "--space", "Nope"])
        assert result.exit_code == 1
        assert "Space 'Nope' not found" in result.output

    def test_target_environment_not_found(self, runner, mock_client):
        mock_client.get_space_by_name.return_value = {"Id": "Spaces-1"}
        mock_client.get_projects.return_value = [{"Id": "P1", "Name": "API"}]
        mock_client.get_environments.return_value = [{"Id": "E2", "Name": "Staging"}]
        result = runner.invoke(cli, ["deploy-all", "staging", "production", "--space", "Default"])
        assert result.exit_code == 1
        assert "Target environment 'production' not found" in result.output

    def test_no_projects_to_process(self, runner, mock_client):
        mock_client.get_space_by_name.return_value = {"Id": "Spaces-1"}
        mock_client.get_projects.return_value = []
        mock_client.get_environments.return_value = [{"Id": "E4", "Name": "Production"}]
        result = runner.invoke(cli, ["deploy-all", "staging", "production", "--space", "Default"])
        assert result.exit_code == 0
        assert "Found 0 projects in space 'Default'" in result.output
        assert "No projects to process" in result.output

    def test_deploys_release(self, runner, mock_client):
        mock_client.get_space_by_name.return_value = {"Id": "Spaces-1"}
        mock_client.get_projects.return_value = [{"Id": "P1", "Name": "API"}]
        mock_client.get_environments.return_value = [{"Id": "E4", "Name": "Production"}]
        mock_client.get_latest_release_in_environment.side_effect = self._release_by_env(
            {"staging": {"Id": "R1", "Version": "2.1.0"}, "production": None}
        )
        result = runner.invoke(cli, ["deploy-all", "staging", "production", "--space", "Default"])
        assert result.exit_code == 0
        assert "1 deployed" in result.output
        mock_client.deploy_release.assert_called_once_with("Spaces-1", "R1", "E4")

    def test_already_deployed(self, runner, mock_client):
        mock_client.get_space_by_name.return_value = {"Id": "Spaces-1"}
        mock_client.get_projects.return_value = [{"Id": "P1", "Name": "API"}]
        mock_client.get_environments.return_value = [{"Id": "E4", "Name": "Production"}]
        mock_client.get_latest_release_in_environment.side_effect = self._release_by_env(
            {
                "staging": {"Id": "R1", "Version": "2.1.0"},
                "production": {"Id": "R2", "Version": "2.1.0"},
            }
        )
        result = runner.invoke(cli, ["deploy-all", "staging", "production", "--space", "Default"])
        assert result.exit_code == 0
        assert "1 already deployed" in result.output
        mock_client.deploy_release.assert_not_called()

    def test_skips_when_no_source_release(self, runner, mock_client):
        mock_client.get_space_by_name.return_value = {"Id": "Spaces-1"}
        mock_client.get_projects.return_value = [{"Id": "P1", "Name": "API"}]
        mock_client.get_environments.return_value = [{"Id": "E4", "Name": "Production"}]
        mock_client.get_latest_release_in_environment.return_value = None
        result = runner.invoke(cli, ["deploy-all", "staging", "production", "--space", "Default"])
        assert result.exit_code == 0
        assert "1 skipped" in result.output
        mock_client.deploy_release.assert_not_called()

    def test_deploy_failure_recorded(self, runner, mock_client):
        mock_client.get_space_by_name.return_value = {"Id": "Spaces-1"}
        mock_client.get_projects.return_value = [{"Id": "P1", "Name": "API"}]
        mock_client.get_environments.return_value = [{"Id": "E4", "Name": "Production"}]
        mock_client.get_latest_release_in_environment.side_effect = self._release_by_env(
            {"staging": {"Id": "R1", "Version": "2.1.0"}, "production": None}
        )
        mock_client.deploy_release.side_effect = RuntimeError("permission denied")
        result = runner.invoke(cli, ["deploy-all", "staging", "production", "--space", "Default"])
        assert result.exit_code == 0
        assert "1 failed" in result.output

    def test_dry_run_with_changelog(self, runner, mock_client):
        mock_client.get_space_by_name.return_value = {"Id": "Spaces-1"}
        mock_client.get_projects.return_value = [{"Id": "P1", "Name": "API"}]
        mock_client.get_environments.return_value = [{"Id": "E4", "Name": "Production"}]
        mock_client.get_latest_release_in_environment.side_effect = self._release_by_env(
            {
                "staging": {"Id": "R1", "Version": "2.1.0"},
                "production": {"Id": "R2", "Version": "2.0.0"},
            }
        )
        mock_client.get_changelog_between_versions.return_value = "Fixed a bug"
        result = runner.invoke(
            cli, ["deploy-all", "staging", "production", "--space", "Default", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "1 would be deployed" in result.output
        assert "Fixed a bug" in result.output
        mock_client.deploy_release.assert_not_called()
        mock_client.get_changelog_between_versions.assert_called_once_with(
            "Spaces-1", "P1", "2.0.0", "2.1.0"
        )

    def test_dry_run_no_target_uses_release_notes(self, runner, mock_client):
        mock_client.get_space_by_name.return_value = {"Id": "Spaces-1"}
        mock_client.get_projects.return_value = [{"Id": "P1", "Name": "API"}]
        mock_client.get_environments.return_value = [{"Id": "E4", "Name": "Production"}]
        mock_client.get_latest_release_in_environment.side_effect = self._release_by_env(
            {"staging": {"Id": "R1", "Version": "2.1.0"}, "production": None}
        )
        mock_client.get_release_details.return_value = {"ReleaseNotes": "First release"}
        result = runner.invoke(
            cli, ["deploy-all", "staging", "production", "--space", "Default", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "First release" in result.output
        mock_client.get_release_details.assert_called_once_with("Spaces-1", "R1")

    def test_dry_run_no_target_no_release_notes(self, runner, mock_client):
        mock_client.get_space_by_name.return_value = {"Id": "Spaces-1"}
        mock_client.get_projects.return_value = [{"Id": "P1", "Name": "API"}]
        mock_client.get_environments.return_value = [{"Id": "E4", "Name": "Production"}]
        mock_client.get_latest_release_in_environment.side_effect = self._release_by_env(
            {"staging": {"Id": "R1", "Version": "2.1.0"}, "production": None}
        )
        mock_client.get_release_details.return_value = {}
        result = runner.invoke(
            cli, ["deploy-all", "staging", "production", "--space", "Default", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "No release notes available" in result.output

    def test_dry_run_empty_changelog(self, runner, mock_client):
        mock_client.get_space_by_name.return_value = {"Id": "Spaces-1"}
        mock_client.get_projects.return_value = [{"Id": "P1", "Name": "API"}]
        mock_client.get_environments.return_value = [{"Id": "E4", "Name": "Production"}]
        mock_client.get_latest_release_in_environment.side_effect = self._release_by_env(
            {
                "staging": {"Id": "R1", "Version": "2.1.0"},
                "production": {"Id": "R2", "Version": "2.0.0"},
            }
        )
        mock_client.get_changelog_between_versions.return_value = ""
        result = runner.invoke(
            cli, ["deploy-all", "staging", "production", "--space", "Default", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "No changelog available" in result.output

    def test_filter_reporting(self, runner, mock_client):
        mock_client.get_space_by_name.return_value = {"Id": "Spaces-1"}
        mock_client.get_projects.return_value = [
            {"Id": "P1", "Name": "API Service"},
            {"Id": "P2", "Name": "Web App"},
        ]
        mock_client.get_environments.return_value = [{"Id": "E4", "Name": "Production"}]
        mock_client.get_latest_release_in_environment.return_value = None
        result = runner.invoke(
            cli,
            ["deploy-all", "staging", "production", "--space", "Default", "--filter", "api"],
        )
        assert result.exit_code == 0
        assert "Found 1 projects matching filter 'api'" in result.output

    def test_exclude_reporting(self, runner, mock_client):
        mock_client.get_space_by_name.return_value = {"Id": "Spaces-1"}
        mock_client.get_projects.return_value = [
            {"Id": "P1", "Name": "API Service"},
            {"Id": "P2", "Name": "Web App"},
        ]
        mock_client.get_environments.return_value = [{"Id": "E4", "Name": "Production"}]
        mock_client.get_latest_release_in_environment.return_value = None
        result = runner.invoke(
            cli,
            ["deploy-all", "staging", "production", "--space", "Default", "--exclude", "web"],
        )
        assert result.exit_code == 0
        assert "Found 1 projects excluding 'web'" in result.output

    def test_filter_and_exclude_reporting(self, runner, mock_client):
        mock_client.get_space_by_name.return_value = {"Id": "Spaces-1"}
        mock_client.get_projects.return_value = [
            {"Id": "P1", "Name": "API Service"},
            {"Id": "P2", "Name": "API Legacy"},
        ]
        mock_client.get_environments.return_value = [{"Id": "E4", "Name": "Production"}]
        mock_client.get_latest_release_in_environment.return_value = None
        result = runner.invoke(
            cli,
            [
                "deploy-all",
                "staging",
                "production",
                "--space",
                "Default",
                "--filter",
                "api",
                "--exclude",
                "legacy",
            ],
        )
        assert result.exit_code == 0
        assert "matching filter 'api' and excluding 'legacy'" in result.output

    def test_tabulate_output_written_to_file(self, runner, mock_client):
        mock_client.get_space_by_name.return_value = {"Id": "Spaces-1"}
        mock_client.get_projects.return_value = [{"Id": "P1", "Name": "API"}]
        mock_client.get_environments.return_value = [{"Id": "E4", "Name": "Production"}]
        mock_client.get_latest_release_in_environment.side_effect = self._release_by_env(
            {"staging": {"Id": "R1", "Version": "2.1.0"}, "production": None}
        )
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                [
                    "deploy-all",
                    "staging",
                    "production",
                    "--space",
                    "Default",
                    "--tabulate-output",
                    "out.txt",
                ],
            )
            assert result.exit_code == 0
            assert "Table output written to: out.txt" in result.output
            with open("out.txt") as f:
                contents = f.read()
        assert "API" in contents

    def test_unexpected_error_reports_and_raises(self, runner, mock_client):
        mock_client.get_space_by_name.side_effect = RuntimeError("kaboom")
        result = runner.invoke(cli, ["deploy-all", "staging", "production", "--space", "Default"])
        assert result.exit_code == 1
        assert "Error in bulk promotion: kaboom" in result.stderr
        assert isinstance(result.exception, RuntimeError)
