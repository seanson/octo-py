import json
import os
from pathlib import Path

import requests


class OctopusClient:
    def __init__(self, config_path: str | None = None):
        if config_path is None:
            config_path = os.path.expanduser("~/.config/octopus/cli_config.json")

        self.config = self._load_config(config_path)
        self.base_url = self.config.get("url", "").rstrip("/")
        self.api_key = self.config.get("apikey", "")

        if not self.base_url or not self.api_key:
            raise ValueError("Missing server_url or api_key in configuration")

        self.session = requests.Session()
        self.session.headers.update(
            {"X-Octopus-ApiKey": self.api_key, "Content-Type": "application/json"}
        )

    def _load_config(self, config_path: str) -> dict:
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_file) as f:
            return json.load(f)

    def _make_request(self, endpoint: str, method: str = "GET", data: dict | None = None) -> dict:
        url = f"{self.base_url}/api{endpoint}"
        if method == "GET":
            response = self.session.get(url)
        elif method == "POST":
            response = self.session.post(url, json=data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        response.raise_for_status()
        return response.json()

    def _get_all_pages(self, endpoint: str) -> list[dict]:
        all_items = []
        skip = 0
        take = 30

        while True:
            paginated_endpoint = f"{endpoint}?skip={skip}&take={take}"
            data = self._make_request(paginated_endpoint)
            items = data.get("Items", [])

            if not items:
                break

            all_items.extend(items)

            # Check if we've got all pages
            total_results = data.get("TotalResults", 0)
            if len(all_items) >= total_results:
                break

            skip += take

        return all_items

    def get_spaces(self) -> list[dict]:
        data = self._make_request("/spaces")
        return data.get("Items", [])

    def get_space_by_name(self, space_name: str) -> dict | None:
        spaces = self.get_spaces()
        for space in spaces:
            if space.get("Name", "").lower() == space_name.lower():
                return space
        return None

    def get_projects(self, space_id: str) -> list[dict]:
        return self._get_all_pages(f"/{space_id}/projects")

    def get_project_by_name(self, space_id: str, project_name: str) -> dict | None:
        projects = self.get_projects(space_id)
        # from pprint import pprint

        # pprint(projects[0])
        for project in projects:
            if project.get("Name", "").lower() == project_name.lower():
                return project
        return None

    def get_releases(self, space_id: str, project_id: str) -> list[dict]:
        data = self._make_request(f"/{space_id}/projects/{project_id}/releases")
        return data.get("Items", [])

    def get_environments(self, space_id: str) -> list[dict]:
        data = self._make_request(f"/{space_id}/environments")
        return data.get("Items", [])

    def get_latest_release_in_environment(
        self, space_id: str, project_id: str, environment_name: str = "staging"
    ) -> dict | None:
        data = self._make_request(f"/{space_id}/projects/{project_id}/releases")
        releases = data.get("Items", [])

        for release in releases:
            deployments_data = self._make_request(
                f"/{space_id}/releases/{release['Id']}/deployments"
            )
            deployments = deployments_data.get("Items", [])

            for deployment in deployments:
                env_data = self._make_request(
                    f"/{space_id}/environments/{deployment['EnvironmentId']}"
                )
                if env_data.get("Name", "").lower() == environment_name.lower():
                    return release

        return None

    def get_release_details(self, space_id: str, release_id: str) -> dict | None:
        """Get detailed information for a specific release including release notes."""
        try:
            return self._make_request(f"/{space_id}/releases/{release_id}")
        except requests.exceptions.HTTPError:
            return None

    def get_releases_between_versions(
        self, space_id: str, project_id: str, from_version: str, to_version: str
    ) -> list[dict]:
        """Get all releases between two versions (inclusive of to_version, exclusive of from_version)."""
        releases = self.get_releases(space_id, project_id)

        # Find the indices of the versions
        from_index = None
        to_index = None

        for i, release in enumerate(releases):
            if release["Version"] == from_version:
                from_index = i
            if release["Version"] == to_version:
                to_index = i

        # If we can't find the versions, return empty list
        if from_index is None or to_index is None:
            return []

        # Get releases between versions (excluding from_version, including to_version)
        # Note: releases are typically ordered newest first, so we need to handle the slice correctly
        start_idx = min(to_index, from_index)
        end_idx = max(to_index, from_index)

        if from_index > to_index:  # from_version is newer than to_version
            return []  # No releases to deploy

        return releases[start_idx : end_idx + 1]

    def get_changelog_between_versions(
        self, space_id: str, project_id: str, from_version: str, to_version: str
    ) -> str:
        """Get aggregated changelog between two versions."""
        # Get all releases for the project
        all_releases = self.get_releases(space_id, project_id)

        # Find releases between versions using semantic version comparison
        changelog_parts = []

        for release in all_releases:
            version = release["Version"]
            # Include releases that are newer than from_version and up to to_version
            if self._version_is_between(from_version, version, to_version):
                release_details = self.get_release_details(space_id, release["Id"])
                if release_details:
                    version = release_details.get("Version", "Unknown")
                    release_notes = release_details.get("ReleaseNotes") or ""
                    release_notes = release_notes.strip() if release_notes else ""

                    if release_notes:
                        changelog_parts.append(f"**{version}**\n{release_notes}")
                    else:
                        changelog_parts.append(f"**{version}**\n_No release notes available_")

        return (
            "\n\n".join(changelog_parts)
            if changelog_parts
            else "_No changelog information available_"
        )

    def _version_is_between(self, from_version: str, check_version: str, to_version: str) -> bool:
        """Simple version comparison - check if check_version is between from_version and to_version."""
        # For semantic versions like 0.0.4 and 0.0.11, we need proper comparison
        try:
            # Split versions into parts for comparison
            from_parts = [int(x) for x in from_version.split(".")]
            check_parts = [int(x) for x in check_version.split(".")]
            to_parts = [int(x) for x in to_version.split(".")]

            # Pad with zeros to make them the same length
            max_len = max(len(from_parts), len(check_parts), len(to_parts))
            from_parts += [0] * (max_len - len(from_parts))
            check_parts += [0] * (max_len - len(check_parts))
            to_parts += [0] * (max_len - len(to_parts))

            # Check if check_version > from_version and check_version <= to_version
            return from_parts < check_parts <= to_parts
        except (ValueError, AttributeError):
            # Fallback to string comparison if version parsing fails
            return from_version < check_version <= to_version

    def deploy_release(self, space_id: str, release_id: str, environment_id: str) -> dict:
        deployment_data = {"ReleaseId": release_id, "EnvironmentId": environment_id}
        return self._make_request(f"/{space_id}/deployments", method="POST", data=deployment_data)
