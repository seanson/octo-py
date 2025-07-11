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

    def _make_request(
        self, endpoint: str, method: str = "GET", data: dict | None = None
    ) -> dict:
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

    def deploy_release(
        self, space_id: str, release_id: str, environment_id: str
    ) -> dict:
        deployment_data = {"ReleaseId": release_id, "EnvironmentId": environment_id}
        return self._make_request(
            f"/{space_id}/deployments", method="POST", data=deployment_data
        )
