"""Shared pytest fixtures and configuration."""

import os
import sys

import pytest

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture
def sample_spaces():
    """Sample space data for testing."""
    return [
        {"Id": "Spaces-1", "Name": "Default", "Description": "Default space"},
        {"Id": "Spaces-2", "Name": "Development", "Description": "Dev space"},
        {"Id": "Spaces-3", "Name": "Production", "Description": "Prod space"},
    ]


@pytest.fixture
def sample_projects():
    """Sample project data for testing."""
    return [
        {
            "Id": "Projects-1",
            "Name": "API Service",
            "Description": "Main API service",
            "SpaceId": "Spaces-1",
        },
        {
            "Id": "Projects-2",
            "Name": "Web Application",
            "Description": "Frontend web app",
            "SpaceId": "Spaces-1",
        },
        {
            "Id": "Projects-3",
            "Name": "Background Worker",
            "Description": "Background job processor",
            "SpaceId": "Spaces-1",
        },
    ]


@pytest.fixture
def sample_releases():
    """Sample release data for testing."""
    return [
        {
            "Id": "Releases-1",
            "Version": "2.1.0",
            "ProjectId": "Projects-1",
            "Created": "2024-01-15T10:00:00Z",
        },
        {
            "Id": "Releases-2",
            "Version": "2.0.0",
            "ProjectId": "Projects-1",
            "Created": "2024-01-10T10:00:00Z",
        },
        {
            "Id": "Releases-3",
            "Version": "1.9.0",
            "ProjectId": "Projects-1",
            "Created": "2024-01-05T10:00:00Z",
        },
    ]


@pytest.fixture
def sample_environments():
    """Sample environment data for testing."""
    return [
        {"Id": "Environments-1", "Name": "Development", "SortOrder": 1},
        {"Id": "Environments-2", "Name": "Staging", "SortOrder": 2},
        {"Id": "Environments-3", "Name": "QA", "SortOrder": 3},
        {"Id": "Environments-4", "Name": "Production", "SortOrder": 4},
    ]


@pytest.fixture
def sample_deployments():
    """Sample deployment data for testing."""
    return [
        {
            "Id": "Deployments-1",
            "ReleaseId": "Releases-1",
            "EnvironmentId": "Environments-2",
            "State": "Success",
            "Created": "2024-01-16T10:00:00Z",
        },
        {
            "Id": "Deployments-2",
            "ReleaseId": "Releases-2",
            "EnvironmentId": "Environments-4",
            "State": "Success",
            "Created": "2024-01-11T10:00:00Z",
        },
    ]
