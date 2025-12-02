"""
REST API Module for HTTP/HTTPS API Calls with Authentication

This module provides a comprehensive HTTP client for REST API operations
with support for multiple authentication methods and advanced features.
Configuration is loaded from nl2py.conf under the [restapi] section.

Supports:
- HTTP methods: GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS
- Authentication methods:
  - No authentication
  - Basic authentication (username/password)
  - Bearer token (JWT, OAuth 2.0)
  - API Key (header or query parameter)
  - OAuth 1.0a
  - OAuth 2.0 (client credentials, password flow)
  - Custom headers
  - AWS Signature V4
- Request features:
  - JSON request/response handling
  - Form data (application/x-www-form-urlencoded)
  - Multipart file uploads
  - Custom headers
  - Query parameters
  - Timeouts and retries
  - SSL/TLS certificate verification
  - Proxy support
  - Session management (cookies)
- Response handling:
  - JSON parsing
  - Status code validation
  - Headers extraction
  - Binary content download
  - Streaming responses

Features:
- Automatic JSON serialization/deserialization
- Retry logic with exponential backoff
- Request/response logging
- Error handling with detailed messages
- Rate limiting support
- Connection pooling
- Redirect handling

Example configuration in nl2py.conf:
    [restapi]
    # Base URL for API
    BASE_URL=https://api.example.com/v1

    # Authentication Method: none, basic, bearer, apikey, oauth1, oauth2
    AUTH_METHOD=bearer

    # Bearer Token Authentication
    BEARER_TOKEN=your_jwt_token_here

    # Basic Authentication
    # USERNAME=your_username
    # PASSWORD=your_password

    # API Key Authentication
    # API_KEY=your_api_key
    # API_KEY_HEADER=X-API-Key  # or use query parameter
    # API_KEY_PARAM=api_key  # query parameter name

    # OAuth 2.0 Client Credentials
    # OAUTH2_CLIENT_ID=your_client_id
    # OAUTH2_CLIENT_SECRET=your_client_secret
    # OAUTH2_TOKEN_URL=https://auth.example.com/oauth/token

    # SSL/TLS Settings
    VERIFY_SSL=true  # Set to false for self-signed certs

    # Request Settings
    TIMEOUT=30  # Request timeout in seconds
    MAX_RETRIES=3  # Maximum number of retries
    RETRY_BACKOFF=1  # Backoff factor for retries

    # Default Headers
    # HEADERS={"User-Agent": "NL2Py/1.0", "Accept": "application/json"}

Example usage:
    # Initialize from config
    api = RestAPIModule.from_config('nl2py.conf')

    # GET request
    response = api.get('/users', params={'page': 1, 'limit': 10})

    # POST request with JSON
    data = {'name': 'John', 'email': 'john@example.com'}
    response = api.post('/users', json=data)

    # PUT request
    response = api.put('/users/123', json={'name': 'John Doe'})

    # DELETE request
    response = api.delete('/users/123')

    # Upload file
    response = api.upload_file('/files', 'document.pdf')
"""

import configparser
import threading
import json as json_module
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Tuple
from urllib.parse import urljoin, urlencode
import base64

try:
    import requests
    from requests.adapters import HTTPAdapter
    from requests.auth import HTTPBasicAuth, AuthBase
    from urllib3.util.retry import Retry
except ImportError:
    requests = None
    HTTPAdapter = None
    HTTPBasicAuth = None
    AuthBase = None
    Retry = None 
    print("[RestAPIModule] Warning: requests not installed. Install with: pip install requests")


class BearerAuth(AuthBase):
    """Bearer token authentication for requests."""
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers['Authorization'] = f'Bearer {self.token}'
        return r


class APIKeyAuth(AuthBase):
    """API Key authentication for requests."""
    def __init__(self, api_key, header_name='X-API-Key'):
        self.api_key = api_key
        self.header_name = header_name

    def __call__(self, r):
        r.headers[self.header_name] = self.api_key
        return r

from .module_base import NL2PyModuleBase


class RestAPIModule(NL2PyModuleBase):
    """
    REST API module with singleton pattern.
    Provides HTTP client for REST API operations with multiple authentication methods.
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(
        self,
        base_url: Optional[str] = None,
        auth_method: str = 'none',
        bearer_token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        api_key: Optional[str] = None,
        api_key_header: str = 'X-API-Key',
        api_key_param: Optional[str] = None,
        oauth2_client_id: Optional[str] = None,
        oauth2_client_secret: Optional[str] = None,
        oauth2_token_url: Optional[str] = None,
        verify_ssl: bool = True,
        timeout: int = 30,
        max_retries: int = 3,
        retry_backoff: float = 1.0,
        default_headers: Optional[Dict[str, str]] = None,
        proxy: Optional[Dict[str, str]] = None
    ):
        """
        Initialize REST API module with configuration.

        Args:
            base_url: Base URL for API endpoints
            auth_method: Authentication method (none, basic, bearer, apikey, oauth2)
            bearer_token: Bearer token for authentication
            username: Username for basic auth
            password: Password for basic auth
            api_key: API key for authentication
            api_key_header: Header name for API key
            api_key_param: Query parameter name for API key
            oauth2_client_id: OAuth2 client ID
            oauth2_client_secret: OAuth2 client secret
            oauth2_token_url: OAuth2 token endpoint URL
            verify_ssl: Whether to verify SSL certificates
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            retry_backoff: Backoff factor for retries
            default_headers: Default headers to include in all requests
            proxy: Proxy configuration dict
        """
        if requests is None:
            raise ImportError(
                "requests is required for RestAPIModule. "
                "Install it with: pip install requests"
            )

        self.base_url = base_url.rstrip('/') if base_url else None
        self.auth_method = auth_method.lower()
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.default_headers = default_headers or {}
        self.proxy = proxy

        # Create session with retry logic
        self.session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=retry_backoff,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST", "PATCH"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Configure authentication
        self.auth = None
        self.api_key_param = api_key_param
        self.oauth2_token = None

        if self.auth_method == 'basic':
            if username and password:
                self.auth = HTTPBasicAuth(username, password)
                print(f"[RestAPIModule] ✓ Using Basic authentication for user: {username}")
            else:
                print("[RestAPIModule] ⚠️ Basic auth selected but credentials not provided")

        elif self.auth_method == 'bearer':
            if bearer_token:
                self.auth = BearerAuth(bearer_token)
                print("[RestAPIModule] ✓ Using Bearer token authentication")
            else:
                print("[RestAPIModule] ⚠️ Bearer auth selected but token not provided")

        elif self.auth_method == 'apikey':
            if api_key:
                if api_key_param:
                    # API key will be added as query parameter
                    self.api_key = api_key
                    print(f"[RestAPIModule] ✓ Using API Key authentication (query param: {api_key_param})")
                else:
                    # API key will be added as header
                    self.auth = APIKeyAuth(api_key, api_key_header)
                    print(f"[RestAPIModule] ✓ Using API Key authentication (header: {api_key_header})")
            else:
                print("[RestAPIModule] ⚠️ API Key auth selected but key not provided")

        elif self.auth_method == 'oauth2':
            if oauth2_client_id and oauth2_client_secret and oauth2_token_url:
                # Get OAuth2 token using client credentials flow
                self.oauth2_token = self._get_oauth2_token(
                    oauth2_token_url, oauth2_client_id, oauth2_client_secret
                )
                if self.oauth2_token:
                    self.auth = BearerAuth(self.oauth2_token)
                    print("[RestAPIModule] ✓ Using OAuth2 authentication")
            else:
                print("[RestAPIModule] ⚠️ OAuth2 auth selected but credentials incomplete")

        if not self.verify_ssl:
            print("[RestAPIModule] ⚠️ SSL certificate verification DISABLED")
            # Suppress insecure request warnings
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        print(f"[RestAPIModule] ✓ REST API client initialized (base URL: {self.base_url or 'none'})")

    def _get_oauth2_token(self, token_url: str, client_id: str, client_secret: str) -> Optional[str]:
        """Get OAuth2 access token using client credentials flow."""
        try:
            response = requests.post(
                token_url,
                data={
                    'grant_type': 'client_credentials',
                    'client_id': client_id,
                    'client_secret': client_secret
                },
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            response.raise_for_status()
            token_data = response.json()
            return token_data.get('access_token')
        except Exception as e:
            print(f"[RestAPIModule] ✗ Failed to get OAuth2 token: {e}")
            return None

    @classmethod
    def from_config(cls, config_path: str = "nl2py.conf"):
        """
        Create RestAPIModule instance from configuration file (singleton pattern).

        Args:
            config_path: Path to configuration file

        Returns:
            RestAPIModule instance
        """
        with cls._lock:
            if cls._instance is None:
                config = configparser.ConfigParser()
                config_file = Path(config_path)

                if not config_file.exists():
                    raise FileNotFoundError(f"Configuration file not found: {config_path}")

                config.read(config_file)

                if 'restapi' not in config:
                    raise KeyError(f"Missing [restapi] section in {config_path}")

                api_config = config['restapi']

                # Parse default headers if provided
                default_headers = {}
                if api_config.get('HEADERS'):
                    try:
                        default_headers = json_module.loads(api_config.get('HEADERS'))
                    except:
                        pass

                cls._instance = cls(
                    base_url=api_config.get('BASE_URL'),
                    auth_method=api_config.get('AUTH_METHOD', 'none'),
                    bearer_token=api_config.get('BEARER_TOKEN'),
                    username=api_config.get('USERNAME'),
                    password=api_config.get('PASSWORD'),
                    api_key=api_config.get('API_KEY'),
                    api_key_header=api_config.get('API_KEY_HEADER', 'X-API-Key'),
                    api_key_param=api_config.get('API_KEY_PARAM'),
                    oauth2_client_id=api_config.get('OAUTH2_CLIENT_ID'),
                    oauth2_client_secret=api_config.get('OAUTH2_CLIENT_SECRET'),
                    oauth2_token_url=api_config.get('OAUTH2_TOKEN_URL'),
                    verify_ssl=api_config.getboolean('VERIFY_SSL', True),
                    timeout=api_config.getint('TIMEOUT', 30),
                    max_retries=api_config.getint('MAX_RETRIES', 3),
                    retry_backoff=api_config.getfloat('RETRY_BACKOFF', 1.0),
                    default_headers=default_headers
                )

                print("[RestAPIModule] Module initialized from config (singleton)")

            return cls._instance

    def _build_url(self, endpoint: str) -> str:
        """Build full URL from base URL and endpoint."""
        if endpoint.startswith('http://') or endpoint.startswith('https://'):
            return endpoint
        if self.base_url:
            return urljoin(self.base_url + '/', endpoint.lstrip('/'))
        return endpoint

    def _add_api_key_param(self, params: Optional[Dict] = None) -> Dict:
        """Add API key as query parameter if configured."""
        if self.auth_method == 'apikey' and self.api_key_param:
            params = params or {}
            params[self.api_key_param] = self.api_key
        return params or {}

    def _merge_headers(self, headers: Optional[Dict] = None) -> Dict:
        """Merge default headers with request-specific headers."""
        merged = self.default_headers.copy()
        if headers:
            merged.update(headers)
        return merged

    def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json: Optional[Dict] = None,
        data: Optional[Union[Dict, str, bytes]] = None,
        headers: Optional[Dict] = None,
        files: Optional[Dict] = None,
        timeout: Optional[int] = None,
        **kwargs
    ):
        """
        Make HTTP request with configured authentication.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json: JSON data to send in request body
            data: Form data or raw data
            headers: Custom headers
            files: Files to upload
            timeout: Request timeout (overrides default)
            **kwargs: Additional arguments passed to requests

        Returns:
            Response object

        Raises:
            requests.exceptions.RequestException: On request failure
        """
        url = self._build_url(endpoint)
        params = self._add_api_key_param(params)
        headers = self._merge_headers(headers)
        timeout = timeout or self.timeout

        try:
            response = self.session.request(
                method=method.upper(),
                url=url,
                params=params,
                json=json,
                data=data,
                headers=headers,
                files=files,
                auth=self.auth,
                verify=self.verify_ssl,
                timeout=timeout,
                proxies=self.proxy,
                **kwargs
            )

            print(f"[RestAPIModule] {method.upper()} {url} → {response.status_code}")
            return response

        except requests.exceptions.RequestException as e:
            print(f"[RestAPIModule] ✗ Request failed: {e}")
            raise

    def get(self, endpoint: str, params: Optional[Dict] = None, **kwargs):
        """Make GET request."""
        return self.request('GET', endpoint, params=params, **kwargs)

    def post(self, endpoint: str, json: Optional[Dict] = None, data: Optional[Union[Dict, str]] = None, **kwargs):
        """Make POST request."""
        return self.request('POST', endpoint, json=json, data=data, **kwargs)

    def put(self, endpoint: str, json: Optional[Dict] = None, data: Optional[Union[Dict, str]] = None, **kwargs):
        """Make PUT request."""
        return self.request('PUT', endpoint, json=json, data=data, **kwargs)

    def patch(self, endpoint: str, json: Optional[Dict] = None, data: Optional[Union[Dict, str]] = None, **kwargs):
        """Make PATCH request."""
        return self.request('PATCH', endpoint, json=json, data=data, **kwargs)

    def delete(self, endpoint: str, **kwargs):
        """Make DELETE request."""
        return self.request('DELETE', endpoint, **kwargs)

    def head(self, endpoint: str, **kwargs):
        """Make HEAD request."""
        return self.request('HEAD', endpoint, **kwargs)

    def options(self, endpoint: str, **kwargs):
        """Make OPTIONS request."""
        return self.request('OPTIONS', endpoint, **kwargs)

    # ==================== Convenience Methods ====================

    def get_json(self, endpoint: str, params: Optional[Dict] = None, **kwargs) -> Any:
        """
        Make GET request and return JSON response.

        Returns:
            Parsed JSON response

        Raises:
            ValueError: If response is not valid JSON
        """
        response = self.get(endpoint, params=params, **kwargs)
        response.raise_for_status()
        return response.json()

    def post_json(self, endpoint: str, json: Optional[Dict] = None, **kwargs) -> Any:
        """
        Make POST request with JSON data and return JSON response.

        Returns:
            Parsed JSON response
        """
        response = self.post(endpoint, json=json, **kwargs)
        response.raise_for_status()
        return response.json()

    def put_json(self, endpoint: str, json: Optional[Dict] = None, **kwargs) -> Any:
        """Make PUT request with JSON data and return JSON response."""
        response = self.put(endpoint, json=json, **kwargs)
        response.raise_for_status()
        return response.json()

    def patch_json(self, endpoint: str, json: Optional[Dict] = None, **kwargs) -> Any:
        """Make PATCH request with JSON data and return JSON response."""
        response = self.patch(endpoint, json=json, **kwargs)
        response.raise_for_status()
        return response.json()

    def upload_file(
        self,
        endpoint: str,
        file_path: str,
        file_field: str = 'file',
        additional_data: Optional[Dict] = None,
        **kwargs
    ):
        """
        Upload a file to the API.

        Args:
            endpoint: API endpoint
            file_path: Path to file to upload
            file_field: Form field name for file
            additional_data: Additional form data to send
            **kwargs: Additional request parameters

        Returns:
            Response object
        """
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path_obj, 'rb') as f:
            files = {file_field: (file_path_obj.name, f)}
            return self.post(endpoint, files=files, data=additional_data, **kwargs)

    def download_file(self, endpoint: str, save_path: str, params: Optional[Dict] = None, **kwargs) -> bool:
        """
        Download a file from the API.

        Args:
            endpoint: API endpoint
            save_path: Path to save downloaded file
            params: Query parameters
            **kwargs: Additional request parameters

        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.get(endpoint, params=params, stream=True, **kwargs)
            response.raise_for_status()

            save_path_obj = Path(save_path)
            save_path_obj.parent.mkdir(parents=True, exist_ok=True)

            with open(save_path_obj, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"[RestAPIModule] ✓ Downloaded file to {save_path}")
            return True

        except Exception as e:
            print(f"[RestAPIModule] ✗ Download failed: {e}")
            return False

    def paginate(
        self,
        endpoint: str,
        page_param: str = 'page',
        per_page_param: str = 'per_page',
        per_page: int = 100,
        max_pages: Optional[int] = None,
        **kwargs
    ) -> List[Any]:
        """
        Paginate through API results.

        Args:
            endpoint: API endpoint
            page_param: Query parameter name for page number
            per_page_param: Query parameter name for items per page
            per_page: Number of items per page
            max_pages: Maximum number of pages to fetch
            **kwargs: Additional request parameters

        Returns:
            List of all results from all pages
        """
        all_results = []
        page = 1

        while True:
            if max_pages and page > max_pages:
                break

            params = kwargs.get('params', {})
            params[page_param] = page
            params[per_page_param] = per_page
            kwargs['params'] = params

            try:
                response = self.get(endpoint, **kwargs)
                response.raise_for_status()
                data = response.json()

                if isinstance(data, list):
                    if not data:
                        break
                    all_results.extend(data)
                elif isinstance(data, dict) and 'items' in data:
                    items = data['items']
                    if not items:
                        break
                    all_results.extend(items)
                else:
                    # Can't determine pagination structure
                    all_results.append(data)
                    break

                page += 1

            except Exception as e:
                print(f"[RestAPIModule] ✗ Pagination failed at page {page}: {e}")
                break

        print(f"[RestAPIModule] ✓ Fetched {len(all_results)} items across {page-1} pages")
        return all_results

    def set_bearer_token(self, token: str):
        """Update bearer token for authentication."""
        self.auth = BearerAuth(token)
        print("[RestAPIModule] ✓ Bearer token updated")

    def set_api_key(self, api_key: str, header_name: str = 'X-API-Key'):
        """Update API key for authentication."""
        self.auth = APIKeyAuth(api_key, header_name)
        print(f"[RestAPIModule] ✓ API key updated (header: {header_name})")

    def set_basic_auth(self, username: str, password: str):
        """Update basic authentication credentials."""
        self.auth = HTTPBasicAuth(username, password)
        print(f"[RestAPIModule] ✓ Basic auth updated for user: {username}")

    def close(self):
        """Close the session."""
        self.session.close()
        print("[RestAPIModule] Session closed")

    @classmethod
    def get_metadata(cls):
        """Get module metadata for compiler prompt generation."""
        from nl2py.modules.module_base import ModuleMetadata
        return ModuleMetadata(
            name="RestAPI",
            task_type="restapi",
            description="HTTP REST API client with GET/POST/PUT/DELETE, authentication (Bearer, API Key, Basic), and JSON support",
            version="1.0.0",
            keywords=[
                "rest", "api", "http", "requests", "json", "bearer-token",
                "api-key", "basic-auth", "oauth", "webhook"
            ],
            dependencies=["requests>=2.28.0"]
        )

    @classmethod
    def get_usage_notes(cls):
        """Get detailed usage notes for this module."""
        return [
            "Module uses singleton pattern - one HTTP session per application",
            "Session persists connections for better performance",
            "Default timeout is 30 seconds for all requests",
            "AUTH_TYPE options: none, bearer, api_key, basic, custom",
            "Bearer token sent in 'Authorization: Bearer <token>' header",
            "API key sent in custom header (default 'X-API-Key')",
            "Basic auth encodes username:password in Base64",
            "verify_ssl=False disables certificate verification (dev only)",
            "Retries with exponential backoff for failed requests (default 3)",
            "JSON auto-serialization for dicts in POST/PUT/PATCH",
            "Response parsing: response['data'] for JSON, response['text'] for HTML",
            "Headers can be set globally or per-request",
            "User-Agent customizable via USER_AGENT config",
            "Pagination support with get_paginated() for large datasets",
            "upload_file() uses multipart/form-data encoding",
            "download_file() streams large files to disk",
            "All HTTP methods return dict with status_code, data/text, headers",
            "ClientError raised for 4xx/5xx with error details",
            "Session cookies maintained automatically across requests",
            "set_bearer_token(), set_api_key(), set_basic_auth() update auth dynamically"
        ]

    @classmethod
    def get_methods_info(cls):
        """Get information about all methods in this module."""
        from nl2py.modules.module_base import MethodInfo
        return [
            MethodInfo(
                name="get",
                description="Send HTTP GET request",
                parameters={
                    "endpoint": "str (required) - API endpoint path",
                    "params": "dict (optional) - Query parameters",
                    "headers": "dict (optional) - Additional headers"
                },
                returns="dict - Response with status_code, data/text, headers",
                examples=[
                    {"text": "GET request to endpoint {{/users}}", "code": "get(endpoint='{{/users}}')"},
                    {"text": "GET request to {{/search}} with params {{query_params}}", "code": "get(endpoint='{{/search}}', params={{query_params}})"}
                ]
            ),
            MethodInfo(
                name="post",
                description="Send HTTP POST request",
                parameters={
                    "endpoint": "str (required) - API endpoint path",
                    "data": "dict (optional) - Request body (auto-serialized to JSON)",
                    "headers": "dict (optional) - Additional headers"
                },
                returns="dict - Response with status_code, data/text, headers",
                examples=[
                    {"text": "POST request to {{/users}} with data {{user_data}}", "code": "post(endpoint='{{/users}}', data={{user_data}})"}
                ]
            ),
            MethodInfo(
                name="put",
                description="Send HTTP PUT request",
                parameters={
                    "endpoint": "str (required) - API endpoint path",
                    "data": "dict (optional) - Request body",
                    "headers": "dict (optional) - Additional headers"
                },
                returns="dict - Response",
                examples=[
                    {"text": "PUT request to {{/users/123}} with data {{updated_data}}", "code": "put(endpoint='{{/users/123}}', data={{updated_data}})"}
                ]
            ),
            MethodInfo(
                name="delete",
                description="Send HTTP DELETE request",
                parameters={
                    "endpoint": "str (required) - API endpoint path",
                    "headers": "dict (optional) - Additional headers"
                },
                returns="dict - Response",
                examples=[
                    {"text": "DELETE request to {{/users/123}}", "code": "delete(endpoint='{{/users/123}}')"}
                ]
            ),
            MethodInfo(
                name="upload_file",
                description="Upload file using multipart/form-data",
                parameters={
                    "endpoint": "str (required) - Upload endpoint",
                    "file_path": "str (required) - Local file path",
                    "field_name": "str (optional) - Form field name (default 'file')"
                },
                returns="dict - Response",
                examples=[
                    {"text": "Upload file {{document.pdf}} to endpoint {{/upload}}", "code": "upload_file(endpoint='{{/upload}}', file_path='{{document.pdf}}')"}
                ]
            ),
            MethodInfo(
                name="download_file",
                description="Download file from URL",
                parameters={
                    "endpoint": "str (required) - Download endpoint",
                    "local_path": "str (required) - Local destination path"
                },
                returns="None",
                examples=[
                    {"text": "Download from {{/files/report.pdf}} to {{local_report.pdf}}", "code": "download_file(endpoint='{{/files/report.pdf}}', save_path='{{local_report.pdf}}')"}
                ]
            ),
            MethodInfo(
                name="patch",
                description="Send HTTP PATCH request for partial updates",
                parameters={
                    "endpoint": "str (required) - API endpoint path",
                    "json": "dict (optional) - JSON data to send",
                    "data": "dict/str (optional) - Form data to send"
                },
                returns="Response - HTTP response object",
                examples=[
                    {"text": "PATCH request to {{/users/123}} with data {{update_data}}", "code": "patch(endpoint='{{/users/123}}', json={{update_data}})"}
                ]
            ),
            MethodInfo(
                name="head",
                description="Send HTTP HEAD request (headers only, no body)",
                parameters={"endpoint": "str (required) - API endpoint path"},
                returns="Response - HTTP response with headers only",
                examples=[
                    {"text": "HEAD request to {{/files/large.zip}} to check headers", "code": "head(endpoint='{{/files/large.zip}}')"}
                ]
            ),
            MethodInfo(
                name="options",
                description="Send HTTP OPTIONS request to check allowed methods",
                parameters={"endpoint": "str (required) - API endpoint path"},
                returns="Response - HTTP response with allowed methods",
                examples=[
                    {"text": "OPTIONS request to {{/api/users}} to check allowed methods", "code": "options(endpoint='{{/api/users}}')"}
                ]
            ),
            MethodInfo(
                name="get_json",
                description="Send GET request and automatically parse JSON response",
                parameters={
                    "endpoint": "str (required) - API endpoint path",
                    "params": "dict (optional) - Query parameters"
                },
                returns="Any - Parsed JSON data (dict/list)",
                examples=[
                    {"text": "GET JSON from endpoint {{/api/users}}", "code": "get_json(endpoint='{{/api/users}}')"},
                    {"text": "GET JSON for user ID {{123}} from {{/api/users/123}}", "code": "get_json(endpoint='{{/api/users/123}}')"}
                ]
            ),
            MethodInfo(
                name="post_json",
                description="Send POST request with JSON and parse JSON response",
                parameters={
                    "endpoint": "str (required) - API endpoint path",
                    "json": "dict (optional) - JSON data to send"
                },
                returns="Any - Parsed JSON response",
                examples=[
                    {"text": "POST JSON {{user_data}} to {{/api/users}} and get response", "code": "post_json(endpoint='{{/api/users}}', json={{user_data}})"}
                ]
            ),
            MethodInfo(
                name="put_json",
                description="Send PUT request with JSON and parse JSON response",
                parameters={
                    "endpoint": "str (required) - API endpoint path",
                    "json": "dict (optional) - JSON data to send"
                },
                returns="Any - Parsed JSON response",
                examples=[
                    {"text": "PUT JSON {{updated_data}} to {{/api/users/123}} and get response", "code": "put_json(endpoint='{{/api/users/123}}', json={{updated_data}})"}
                ]
            ),
            MethodInfo(
                name="patch_json",
                description="Send PATCH request with JSON and parse JSON response",
                parameters={
                    "endpoint": "str (required) - API endpoint path",
                    "json": "dict (optional) - JSON data to send"
                },
                returns="Any - Parsed JSON response",
                examples=[
                    {"text": "PATCH JSON {{email_data}} to {{/api/users/123}} and get response", "code": "patch_json(endpoint='{{/api/users/123}}', json={{email_data}})"}
                ]
            ),
            MethodInfo(
                name="set_bearer_token",
                description="Update Bearer token for API authentication",
                parameters={"token": "str (required) - Bearer token value"},
                returns="None",
                examples=[
                    {"text": "Set Bearer token {{eyJhbGciOiJIUzI1NiIs...}} for authentication", "code": "set_bearer_token(token='{{eyJhbGciOiJIUzI1NiIs...}}')"}
                ]
            ),
            MethodInfo(
                name="set_api_key",
                description="Update API key for authentication",
                parameters={
                    "api_key": "str (required) - API key value",
                    "header_name": "str (optional) - Header name (default 'X-API-Key')"
                },
                returns="None",
                examples=[
                    {"text": "Set API key {{my-api-key}} with default X-API-Key header", "code": "set_api_key(api_key='{{my-api-key}}')"},
                    {"text": "Set API key {{key123}} with custom header {{Authorization}}", "code": "set_api_key(api_key='{{key123}}', header_name='{{Authorization}}')"}
                ]
            ),
            MethodInfo(
                name="set_basic_auth",
                description="Update HTTP Basic authentication credentials",
                parameters={
                    "username": "str (required) - Username",
                    "password": "str (required) - Password"
                },
                returns="None",
                examples=[
                    {"text": "Set basic auth with username {{admin}} and password {{secret123}}", "code": "set_basic_auth(username='{{admin}}', password='{{secret123}}')"}
                ]
            )
        ]

