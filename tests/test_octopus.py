"""Tests for the OctopusClient API."""
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import requests
from src.octopus import OctopusClient


@pytest.fixture
def mock_config():
    """Mock configuration data."""
    return {
        "url": "https://octopus.example.com",
        "apikey": "API-TESTKEY123"
    }


@pytest.fixture
def mock_config_file(tmp_path, mock_config):
    """Create a temporary config file."""
    config_file = tmp_path / "cli_config.json"
    config_file.write_text(json.dumps(mock_config))
    return str(config_file)


@pytest.fixture
def mock_session():
    """Mock requests session."""
    session = Mock(spec=requests.Session)
    session.headers = Mock()
    session.headers.update = Mock()
    return session


@pytest.fixture
def client(mock_config_file, mock_session):
    """Create OctopusClient instance with mocked session."""
    with patch('requests.Session', return_value=mock_session):
        return OctopusClient(config_path=mock_config_file)


class TestOctopusClientInitialization:
    """Test OctopusClient initialization and configuration."""
    
    def test_init_with_valid_config(self, mock_config_file, mock_session):
        """Test successful initialization with valid config."""
        with patch('requests.Session', return_value=mock_session):
            client = OctopusClient(config_path=mock_config_file)
            
        assert client.base_url == "https://octopus.example.com"
        assert client.api_key == "API-TESTKEY123"
        mock_session.headers.update.assert_called_once_with({
            "X-Octopus-ApiKey": "API-TESTKEY123",
            "Content-Type": "application/json"
        })
    
    def test_init_with_default_config_path(self, mock_session):
        """Test initialization with default config path."""
        mock_config_data = {"url": "https://test.com", "apikey": "test-key"}
        
        with patch('os.path.expanduser', return_value="/home/user/.config/octopus/cli_config.json"):
            with patch('builtins.open', mock_open(read_data=json.dumps(mock_config_data))):
                with patch('pathlib.Path.exists', return_value=True):
                    with patch('requests.Session', return_value=mock_session):
                        client = OctopusClient()
        
        assert client.base_url == "https://test.com"
        assert client.api_key == "test-key"
    
    def test_init_removes_trailing_slash_from_url(self, tmp_path, mock_session):
        """Test that trailing slash is removed from URL."""
        config = {"url": "https://octopus.example.com/", "apikey": "API-KEY"}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))
        
        with patch('requests.Session', return_value=mock_session):
            client = OctopusClient(config_path=str(config_file))
        
        assert client.base_url == "https://octopus.example.com"
    
    def test_init_with_missing_config_file(self):
        """Test initialization fails with missing config file."""
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            OctopusClient(config_path="/nonexistent/config.json")
    
    def test_init_with_missing_url(self, tmp_path):
        """Test initialization fails with missing URL in config."""
        config = {"apikey": "API-KEY"}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))
        
        with pytest.raises(ValueError, match="Missing server_url or api_key"):
            OctopusClient(config_path=str(config_file))
    
    def test_init_with_missing_api_key(self, tmp_path):
        """Test initialization fails with missing API key in config."""
        config = {"url": "https://octopus.example.com"}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))
        
        with pytest.raises(ValueError, match="Missing server_url or api_key"):
            OctopusClient(config_path=str(config_file))
    
    def test_init_with_empty_url(self, tmp_path):
        """Test initialization fails with empty URL."""
        config = {"url": "", "apikey": "API-KEY"}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))
        
        with pytest.raises(ValueError, match="Missing server_url or api_key"):
            OctopusClient(config_path=str(config_file))


class TestApiRequestMethods:
    """Test API request methods."""
    
    def test_make_request_get(self, client):
        """Test GET request."""
        mock_response = Mock()
        mock_response.json.return_value = {"result": "success"}
        client.session.get.return_value = mock_response
        
        result = client._make_request("/test-endpoint")
        
        client.session.get.assert_called_once_with(
            "https://octopus.example.com/api/test-endpoint"
        )
        mock_response.raise_for_status.assert_called_once()
        assert result == {"result": "success"}
    
    def test_make_request_post(self, client):
        """Test POST request."""
        mock_response = Mock()
        mock_response.json.return_value = {"created": True}
        client.session.post.return_value = mock_response
        
        data = {"name": "Test Project"}
        result = client._make_request("/projects", method="POST", data=data)
        
        client.session.post.assert_called_once_with(
            "https://octopus.example.com/api/projects",
            json=data
        )
        mock_response.raise_for_status.assert_called_once()
        assert result == {"created": True}
    
    def test_make_request_unsupported_method(self, client):
        """Test unsupported HTTP method raises error."""
        with pytest.raises(ValueError, match="Unsupported HTTP method: PUT"):
            client._make_request("/test", method="PUT")
    
    def test_make_request_http_error(self, client):
        """Test HTTP error handling."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        client.session.get.return_value = mock_response
        
        with pytest.raises(requests.HTTPError):
            client._make_request("/nonexistent")
    
    def test_get_all_pages_single_page(self, client):
        """Test pagination with single page."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "Items": [{"Id": "1"}, {"Id": "2"}],
            "TotalResults": 2
        }
        client.session.get.return_value = mock_response
        
        result = client._get_all_pages("/projects")
        
        assert result == [{"Id": "1"}, {"Id": "2"}]
        client.session.get.assert_called_once_with(
            "https://octopus.example.com/api/projects?skip=0&take=30"
        )
    
    def test_get_all_pages_multiple_pages(self, client):
        """Test pagination with multiple pages."""
        # Mock responses for 3 pages
        responses = [
            {"Items": [{"Id": str(i)} for i in range(1, 31)], "TotalResults": 75},
            {"Items": [{"Id": str(i)} for i in range(31, 61)], "TotalResults": 75},
            {"Items": [{"Id": str(i)} for i in range(61, 76)], "TotalResults": 75},
        ]
        
        mock_response = Mock()
        mock_response.json.side_effect = responses
        client.session.get.return_value = mock_response
        
        result = client._get_all_pages("/projects")
        
        assert len(result) == 75
        assert result[0]["Id"] == "1"
        assert result[74]["Id"] == "75"
        assert client.session.get.call_count == 3
    
    def test_get_all_pages_empty_result(self, client):
        """Test pagination with no results."""
        mock_response = Mock()
        mock_response.json.return_value = {"Items": [], "TotalResults": 0}
        client.session.get.return_value = mock_response
        
        result = client._get_all_pages("/projects")
        
        assert result == []


class TestSpaceRelatedMethods:
    """Test space-related API methods."""
    
    def test_get_spaces(self, client):
        """Test getting all spaces."""
        mock_spaces = [
            {"Id": "Spaces-1", "Name": "Default"},
            {"Id": "Spaces-2", "Name": "Development"}
        ]
        mock_response = Mock()
        mock_response.json.return_value = {"Items": mock_spaces}
        client.session.get.return_value = mock_response
        
        result = client.get_spaces()
        
        assert result == mock_spaces
        client.session.get.assert_called_once_with(
            "https://octopus.example.com/api/spaces"
        )
    
    def test_get_space_by_name_found(self, client):
        """Test finding space by name (case-insensitive)."""
        mock_spaces = [
            {"Id": "Spaces-1", "Name": "Default"},
            {"Id": "Spaces-2", "Name": "Development"}
        ]
        
        with patch.object(client, 'get_spaces', return_value=mock_spaces):
            # Test exact match
            result = client.get_space_by_name("Default")
            assert result == {"Id": "Spaces-1", "Name": "Default"}
            
            # Test case-insensitive match
            result = client.get_space_by_name("DEVELOPMENT")
            assert result == {"Id": "Spaces-2", "Name": "Development"}
    
    def test_get_space_by_name_not_found(self, client):
        """Test space not found by name."""
        mock_spaces = [{"Id": "Spaces-1", "Name": "Default"}]
        
        with patch.object(client, 'get_spaces', return_value=mock_spaces):
            result = client.get_space_by_name("NonExistent")
            assert result is None


class TestProjectRelatedMethods:
    """Test project-related API methods."""
    
    def test_get_projects(self, client):
        """Test getting all projects in a space."""
        mock_projects = [
            {"Id": "Projects-1", "Name": "API"},
            {"Id": "Projects-2", "Name": "Web"}
        ]
        
        with patch.object(client, '_get_all_pages', return_value=mock_projects) as mock_get_all:
            result = client.get_projects("Spaces-1")
            
        assert result == mock_projects
        mock_get_all.assert_called_once_with("/Spaces-1/projects")
    
    def test_get_project_by_name_found(self, client):
        """Test finding project by name (case-insensitive)."""
        mock_projects = [
            {"Id": "Projects-1", "Name": "API Service"},
            {"Id": "Projects-2", "Name": "Web App"}
        ]
        
        with patch.object(client, 'get_projects', return_value=mock_projects):
            # Test exact match
            result = client.get_project_by_name("Spaces-1", "API Service")
            assert result == {"Id": "Projects-1", "Name": "API Service"}
            
            # Test case-insensitive match
            result = client.get_project_by_name("Spaces-1", "web app")
            assert result == {"Id": "Projects-2", "Name": "Web App"}
    
    def test_get_project_by_name_not_found(self, client):
        """Test project not found by name."""
        mock_projects = [{"Id": "Projects-1", "Name": "API"}]
        
        with patch.object(client, 'get_projects', return_value=mock_projects):
            result = client.get_project_by_name("Spaces-1", "NonExistent")
            assert result is None


class TestReleaseAndDeploymentMethods:
    """Test release and deployment related methods."""
    
    def test_get_releases(self, client):
        """Test getting releases for a project."""
        mock_releases = [
            {"Id": "Releases-1", "Version": "1.0.0"},
            {"Id": "Releases-2", "Version": "1.0.1"}
        ]
        mock_response = Mock()
        mock_response.json.return_value = {"Items": mock_releases}
        client.session.get.return_value = mock_response
        
        result = client.get_releases("Spaces-1", "Projects-1")
        
        assert result == mock_releases
        client.session.get.assert_called_once_with(
            "https://octopus.example.com/api/Spaces-1/projects/Projects-1/releases"
        )
    
    def test_get_environments(self, client):
        """Test getting environments for a space."""
        mock_environments = [
            {"Id": "Environments-1", "Name": "Development"},
            {"Id": "Environments-2", "Name": "Staging"}
        ]
        mock_response = Mock()
        mock_response.json.return_value = {"Items": mock_environments}
        client.session.get.return_value = mock_response
        
        result = client.get_environments("Spaces-1")
        
        assert result == mock_environments
        client.session.get.assert_called_once_with(
            "https://octopus.example.com/api/Spaces-1/environments"
        )
    
    def test_get_latest_release_in_environment_found(self, client):
        """Test getting latest release deployed to an environment."""
        mock_releases = [
            {"Id": "Releases-1", "Version": "1.0.1"},
            {"Id": "Releases-2", "Version": "1.0.0"}
        ]
        mock_deployments = [
            {"Id": "Deployments-1", "EnvironmentId": "Environments-1"}
        ]
        mock_environment = {"Id": "Environments-1", "Name": "Staging"}
        
        # Mock the API calls
        mock_responses = [
            # First call: get releases
            {"Items": mock_releases},
            # Second call: get deployments for first release
            {"Items": mock_deployments},
            # Third call: get environment details
            mock_environment
        ]
        
        mock_response = Mock()
        mock_response.json.side_effect = mock_responses
        client.session.get.return_value = mock_response
        
        result = client.get_latest_release_in_environment("Spaces-1", "Projects-1", "staging")
        
        assert result == {"Id": "Releases-1", "Version": "1.0.1"}
        assert client.session.get.call_count == 3
    
    def test_get_latest_release_in_environment_not_found(self, client):
        """Test when no release is deployed to the environment."""
        mock_releases = [{"Id": "Releases-1", "Version": "1.0.0"}]
        mock_deployments = [{"Id": "Deployments-1", "EnvironmentId": "Environments-2"}]
        mock_environment = {"Id": "Environments-2", "Name": "Production"}
        
        mock_responses = [
            {"Items": mock_releases},
            {"Items": mock_deployments},
            mock_environment
        ]
        
        mock_response = Mock()
        mock_response.json.side_effect = mock_responses
        client.session.get.return_value = mock_response
        
        result = client.get_latest_release_in_environment("Spaces-1", "Projects-1", "staging")
        
        assert result is None
    
    def test_deploy_release(self, client):
        """Test deploying a release."""
        mock_deployment = {"Id": "Deployments-123", "State": "Queued"}
        mock_response = Mock()
        mock_response.json.return_value = mock_deployment
        client.session.post.return_value = mock_response
        
        result = client.deploy_release("Spaces-1", "Releases-1", "Environments-1")
        
        assert result == mock_deployment
        client.session.post.assert_called_once_with(
            "https://octopus.example.com/api/Spaces-1/deployments",
            json={
                "ReleaseId": "Releases-1",
                "EnvironmentId": "Environments-1"
            }
        )


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling."""
    
    def test_get_space_by_name_with_empty_name(self, client):
        """Test handling empty space name."""
        mock_spaces = [{"Id": "Spaces-1", "Name": "Default"}]
        
        with patch.object(client, 'get_spaces', return_value=mock_spaces):
            result = client.get_space_by_name("")
            assert result is None
    
    def test_get_project_by_name_with_missing_name_field(self, client):
        """Test handling project without Name field."""
        mock_projects = [
            {"Id": "Projects-1"},  # Missing Name field
            {"Id": "Projects-2", "Name": "Web App"}
        ]
        
        with patch.object(client, 'get_projects', return_value=mock_projects):
            result = client.get_project_by_name("Spaces-1", "Web App")
            assert result == {"Id": "Projects-2", "Name": "Web App"}
    
    def test_pagination_with_no_total_results(self, client):
        """Test pagination when TotalResults is missing."""
        # When TotalResults is missing (defaults to 0), pagination stops after first page
        mock_response = Mock()
        mock_response.json.return_value = {"Items": [{"Id": "1"}, {"Id": "2"}]}
        client.session.get.return_value = mock_response
        
        result = client._get_all_pages("/projects")
        
        assert len(result) == 2
        assert result == [{"Id": "1"}, {"Id": "2"}]
        # Should only make one request when TotalResults is missing/0
        assert client.session.get.call_count == 1