"""
Keycloak Module for NL2Py

This module provides comprehensive integration with Keycloak Identity and Access Management,
enabling natural language management of users, roles, groups, clients, and realms.

Features:
- Realm Management: Create, configure, delete realms
- User Management: Create, modify, delete users, manage credentials
- Role Management: Create roles, assign to users and groups
- Group Management: Create groups, manage hierarchies and memberships
- Client Management: Register and configure OAuth2/OIDC clients
- Authentication: User authentication and token management
- Federation: Configure identity providers and user federation

Architecture:
- Singleton pattern with thread-safe initialization
- Admin REST API client using python-keycloak
- Configuration from nl2py.conf with environment variable fallbacks
- Token-based authentication with automatic refresh

Usage:
    10 (keycloak) connect to server "http://localhost:8080"
    20 (keycloak) create user "john.doe" with email "john@example.com"
    30 (keycloak) create role "admin"
    40 (keycloak) assign role "admin" to user "john.doe"
"""

import threading
import os
from typing import Optional, Dict, Any, List
from .module_base import NL2PyModuleBase

# Keycloak Client Library
try:
    from keycloak import KeycloakAdmin, KeycloakOpenID
    from keycloak.exceptions import KeycloakError, KeycloakAuthenticationError
    KEYCLOAK_AVAILABLE = True
except ImportError:
    KEYCLOAK_AVAILABLE = False


class KeycloakModule(NL2PyModuleBase):
    """
    Keycloak module for Identity and Access Management.

    Implements singleton pattern for efficient resource usage.
    Provides comprehensive Keycloak operations through python-keycloak library.
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the Keycloak module with configuration from nl2py.conf."""
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            if not KEYCLOAK_AVAILABLE:
                raise RuntimeError(
                    "Keycloak library not installed. "
                    "Install with: pip install python-keycloak"
                )

            # Read configuration
            self.server_url = os.getenv('KEYCLOAK_SERVER_URL', 'http://localhost:8080')
            self.admin_username = os.getenv('KEYCLOAK_ADMIN_USERNAME', 'admin')
            self.admin_password = os.getenv('KEYCLOAK_ADMIN_PASSWORD', 'admin')
            self.realm_name = os.getenv('KEYCLOAK_REALM', 'master')
            self.client_id = os.getenv('KEYCLOAK_CLIENT_ID', 'admin-cli')
            self.client_secret = os.getenv('KEYCLOAK_CLIENT_SECRET', '')

            # Connection settings
            self.verify_ssl = os.getenv('KEYCLOAK_VERIFY_SSL', 'true').lower() == 'true'
            self.timeout = int(os.getenv('KEYCLOAK_TIMEOUT', '10'))

            # Lazy-loaded clients
            self._admin_client = None
            self._openid_client = None

            self._initialized = True

    @property
    def admin(self):
        """Get Keycloak Admin client (lazy-loaded)."""
        if self._admin_client is None:
            try:
                self._admin_client = KeycloakAdmin(
                    server_url=self.server_url,
                    username=self.admin_username,
                    password=self.admin_password,
                    realm_name=self.realm_name,
                    client_id=self.client_id,
                    client_secret_key=self.client_secret if self.client_secret else None,
                    verify=self.verify_ssl,
                    timeout=self.timeout
                )
            except Exception as e:
                raise RuntimeError(f"Failed to connect to Keycloak: {e}")
        return self._admin_client

    @property
    def openid(self):
        """Get Keycloak OpenID client (lazy-loaded)."""
        if self._openid_client is None:
            self._openid_client = KeycloakOpenID(
                server_url=self.server_url,
                realm_name=self.realm_name,
                client_id=self.client_id,
                client_secret_key=self.client_secret if self.client_secret else None,
                verify=self.verify_ssl
            )
        return self._openid_client

    def set_realm(self, realm_name: str):
        """Switch to a different realm."""
        self.realm_name = realm_name
        self._admin_client = None  # Reset to reload with new realm
        self._openid_client = None

    # =========================================================================
    # Realm Management
    # =========================================================================

    def realm_create(self, realm_name: str, enabled: bool = True, **kwargs) -> Dict[str, Any]:
        """Create a new realm."""
        payload = {
            "realm": realm_name,
            "enabled": enabled
        }

        # Add optional parameters
        if 'displayName' in kwargs:
            payload['displayName'] = kwargs['displayName']
        if 'displayNameHtml' in kwargs:
            payload['displayNameHtml'] = kwargs['displayNameHtml']

        try:
            self.admin.create_realm(payload=payload, skip_exists=False)
            return {
                "realm": realm_name,
                "enabled": enabled,
                "created": True
            }
        except Exception as e:
            raise RuntimeError(f"Failed to create realm: {e}")

    def realm_get(self, realm_name: Optional[str] = None) -> Dict[str, Any]:
        """Get realm details."""
        realm_name = realm_name or self.realm_name
        try:
            # Temporarily switch realm to get details
            original_realm = self.realm_name
            self.set_realm(realm_name)
            realm = self.admin.get_realm(realm_name)
            self.set_realm(original_realm)
            return realm
        except Exception as e:
            raise RuntimeError(f"Failed to get realm: {e}")

    def realm_delete(self, realm_name: str) -> Dict[str, Any]:
        """Delete a realm."""
        try:
            self.admin.delete_realm(realm_name=realm_name)
            return {
                "realm": realm_name,
                "deleted": True
            }
        except Exception as e:
            raise RuntimeError(f"Failed to delete realm: {e}")

    # =========================================================================
    # User Management
    # =========================================================================

    def user_create(self, username: str, **kwargs) -> Dict[str, Any]:
        """Create a new user."""
        payload = {
            "username": username,
            "enabled": kwargs.get('enabled', True),
            "emailVerified": kwargs.get('emailVerified', False)
        }

        # Add optional fields
        if 'email' in kwargs:
            payload['email'] = kwargs['email']
        if 'firstName' in kwargs:
            payload['firstName'] = kwargs['firstName']
        if 'lastName' in kwargs:
            payload['lastName'] = kwargs['lastName']
        if 'attributes' in kwargs:
            payload['attributes'] = kwargs['attributes']

        try:
            user_id = self.admin.create_user(payload=payload)

            # Set password if provided
            if 'password' in kwargs:
                self.admin.set_user_password(
                    user_id=user_id,
                    password=kwargs['password'],
                    temporary=kwargs.get('temporary', False)
                )

            return {
                "user_id": user_id,
                "username": username,
                "created": True
            }
        except Exception as e:
            raise RuntimeError(f"Failed to create user: {e}")

    def user_get(self, username: str) -> Dict[str, Any]:
        """Get user details by username."""
        try:
            users = self.admin.get_users({"username": username})
            if not users:
                raise RuntimeError(f"User not found: {username}")
            return users[0]
        except Exception as e:
            raise RuntimeError(f"Failed to get user: {e}")

    def user_get_by_id(self, user_id: str) -> Dict[str, Any]:
        """Get user details by ID."""
        try:
            return self.admin.get_user(user_id=user_id)
        except Exception as e:
            raise RuntimeError(f"Failed to get user: {e}")

    def user_update(self, username: str, **kwargs) -> Dict[str, Any]:
        """Update user attributes."""
        try:
            user = self.user_get(username)
            user_id = user['id']

            payload = {}
            if 'email' in kwargs:
                payload['email'] = kwargs['email']
            if 'firstName' in kwargs:
                payload['firstName'] = kwargs['firstName']
            if 'lastName' in kwargs:
                payload['lastName'] = kwargs['lastName']
            if 'enabled' in kwargs:
                payload['enabled'] = kwargs['enabled']
            if 'attributes' in kwargs:
                payload['attributes'] = kwargs['attributes']

            self.admin.update_user(user_id=user_id, payload=payload)

            return {
                "user_id": user_id,
                "username": username,
                "updated": True
            }
        except Exception as e:
            raise RuntimeError(f"Failed to update user: {e}")

    def user_delete(self, username: str) -> Dict[str, Any]:
        """Delete a user."""
        try:
            user = self.user_get(username)
            user_id = user['id']
            self.admin.delete_user(user_id=user_id)

            return {
                "user_id": user_id,
                "username": username,
                "deleted": True
            }
        except Exception as e:
            raise RuntimeError(f"Failed to delete user: {e}")

    def user_set_password(self, username: str, password: str, temporary: bool = False) -> Dict[str, Any]:
        """Set user password."""
        try:
            user = self.user_get(username)
            user_id = user['id']

            self.admin.set_user_password(
                user_id=user_id,
                password=password,
                temporary=temporary
            )

            return {
                "user_id": user_id,
                "username": username,
                "password_set": True,
                "temporary": temporary
            }
        except Exception as e:
            raise RuntimeError(f"Failed to set password: {e}")

    def user_list(self, **query) -> List[Dict[str, Any]]:
        """List users with optional filters."""
        try:
            return self.admin.get_users(query=query)
        except Exception as e:
            raise RuntimeError(f"Failed to list users: {e}")

    # =========================================================================
    # Role Management
    # =========================================================================

    def role_create(self, role_name: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Create a realm role."""
        payload = {"name": role_name}
        if description:
            payload["description"] = description

        try:
            self.admin.create_realm_role(payload=payload, skip_exists=False)
            return {
                "role_name": role_name,
                "created": True
            }
        except Exception as e:
            raise RuntimeError(f"Failed to create role: {e}")

    def role_get(self, role_name: str) -> Dict[str, Any]:
        """Get role details."""
        try:
            return self.admin.get_realm_role(role_name=role_name)
        except Exception as e:
            raise RuntimeError(f"Failed to get role: {e}")

    def role_delete(self, role_name: str) -> Dict[str, Any]:
        """Delete a realm role."""
        try:
            self.admin.delete_realm_role(role_name=role_name)
            return {
                "role_name": role_name,
                "deleted": True
            }
        except Exception as e:
            raise RuntimeError(f"Failed to delete role: {e}")

    def role_list(self) -> List[Dict[str, Any]]:
        """List all realm roles."""
        try:
            return self.admin.get_realm_roles()
        except Exception as e:
            raise RuntimeError(f"Failed to list roles: {e}")

    def user_assign_role(self, username: str, role_name: str) -> Dict[str, Any]:
        """Assign a realm role to a user."""
        try:
            user = self.user_get(username)
            user_id = user['id']
            role = self.role_get(role_name)

            self.admin.assign_realm_roles(user_id=user_id, roles=[role])

            return {
                "user_id": user_id,
                "username": username,
                "role_name": role_name,
                "assigned": True
            }
        except Exception as e:
            raise RuntimeError(f"Failed to assign role: {e}")

    def user_remove_role(self, username: str, role_name: str) -> Dict[str, Any]:
        """Remove a realm role from a user."""
        try:
            user = self.user_get(username)
            user_id = user['id']
            role = self.role_get(role_name)

            self.admin.delete_realm_roles_of_user(user_id=user_id, roles=[role])

            return {
                "user_id": user_id,
                "username": username,
                "role_name": role_name,
                "removed": True
            }
        except Exception as e:
            raise RuntimeError(f"Failed to remove role: {e}")

    def user_get_roles(self, username: str) -> List[Dict[str, Any]]:
        """Get all roles assigned to a user."""
        try:
            user = self.user_get(username)
            user_id = user['id']
            return self.admin.get_realm_roles_of_user(user_id=user_id)
        except Exception as e:
            raise RuntimeError(f"Failed to get user roles: {e}")

    # =========================================================================
    # Group Management
    # =========================================================================

    def group_create(self, group_name: str, **kwargs) -> Dict[str, Any]:
        """Create a group."""
        payload = {"name": group_name}

        if 'attributes' in kwargs:
            payload['attributes'] = kwargs['attributes']

        try:
            group_id = self.admin.create_group(payload=payload, skip_exists=False)
            return {
                "group_id": group_id,
                "group_name": group_name,
                "created": True
            }
        except Exception as e:
            raise RuntimeError(f"Failed to create group: {e}")

    def group_get(self, group_name: str) -> Dict[str, Any]:
        """Get group by name."""
        try:
            groups = self.admin.get_groups({"search": group_name})
            for group in groups:
                if group['name'] == group_name:
                    return group
            raise RuntimeError(f"Group not found: {group_name}")
        except Exception as e:
            raise RuntimeError(f"Failed to get group: {e}")

    def group_delete(self, group_name: str) -> Dict[str, Any]:
        """Delete a group."""
        try:
            group = self.group_get(group_name)
            group_id = group['id']
            self.admin.delete_group(group_id=group_id)

            return {
                "group_id": group_id,
                "group_name": group_name,
                "deleted": True
            }
        except Exception as e:
            raise RuntimeError(f"Failed to delete group: {e}")

    def group_add_user(self, group_name: str, username: str) -> Dict[str, Any]:
        """Add user to group."""
        try:
            group = self.group_get(group_name)
            user = self.user_get(username)

            self.admin.group_user_add(user_id=user['id'], group_id=group['id'])

            return {
                "group_name": group_name,
                "username": username,
                "added": True
            }
        except Exception as e:
            raise RuntimeError(f"Failed to add user to group: {e}")

    def group_remove_user(self, group_name: str, username: str) -> Dict[str, Any]:
        """Remove user from group."""
        try:
            group = self.group_get(group_name)
            user = self.user_get(username)

            self.admin.group_user_remove(user_id=user['id'], group_id=group['id'])

            return {
                "group_name": group_name,
                "username": username,
                "removed": True
            }
        except Exception as e:
            raise RuntimeError(f"Failed to remove user from group: {e}")

    # =========================================================================
    # Client Management
    # =========================================================================

    def client_create(self, client_id: str, **kwargs) -> Dict[str, Any]:
        """Create an OAuth2/OIDC client."""
        payload = {
            "clientId": client_id,
            "enabled": kwargs.get('enabled', True),
            "protocol": kwargs.get('protocol', 'openid-connect'),
            "publicClient": kwargs.get('publicClient', False),
            "directAccessGrantsEnabled": kwargs.get('directAccessGrantsEnabled', True),
        }

        if 'redirectUris' in kwargs:
            payload['redirectUris'] = kwargs['redirectUris']
        if 'webOrigins' in kwargs:
            payload['webOrigins'] = kwargs['webOrigins']
        if 'secret' in kwargs:
            payload['secret'] = kwargs['secret']

        try:
            client_uuid = self.admin.create_client(payload=payload, skip_exists=False)
            return {
                "client_uuid": client_uuid,
                "client_id": client_id,
                "created": True
            }
        except Exception as e:
            raise RuntimeError(f"Failed to create client: {e}")

    def client_get(self, client_id: str) -> Dict[str, Any]:
        """Get client by client ID."""
        try:
            client_uuid = self.admin.get_client_id(client_id=client_id)
            return self.admin.get_client(client_id=client_uuid)
        except Exception as e:
            raise RuntimeError(f"Failed to get client: {e}")

    def client_delete(self, client_id: str) -> Dict[str, Any]:
        """Delete a client."""
        try:
            client_uuid = self.admin.get_client_id(client_id=client_id)
            self.admin.delete_client(client_id=client_uuid)

            return {
                "client_id": client_id,
                "deleted": True
            }
        except Exception as e:
            raise RuntimeError(f"Failed to delete client: {e}")

    # =========================================================================
    # Authentication
    # =========================================================================

    def authenticate(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate user and get tokens."""
        try:
            token = self.openid.token(username=username, password=password)
            return {
                "access_token": token['access_token'],
                "refresh_token": token['refresh_token'],
                "expires_in": token['expires_in'],
                "token_type": token['token_type']
            }
        except Exception as e:
            raise RuntimeError(f"Authentication failed: {e}")

    def token_refresh(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token."""
        try:
            token = self.openid.refresh_token(refresh_token=refresh_token)
            return {
                "access_token": token['access_token'],
                "refresh_token": token['refresh_token'],
                "expires_in": token['expires_in']
            }
        except Exception as e:
            raise RuntimeError(f"Token refresh failed: {e}")

    def logout(self, refresh_token: str) -> Dict[str, Any]:
        """Logout user (invalidate token)."""
        try:
            self.openid.logout(refresh_token=refresh_token)
            return {"logged_out": True}
        except Exception as e:
            raise RuntimeError(f"Logout failed: {e}")

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_server_info(self) -> Dict[str, Any]:
        """Get Keycloak server information."""
        try:
            return {
                "server_url": self.server_url,
                "realm": self.realm_name,
                "client_id": self.client_id,
                "connected": self._admin_client is not None
            }
        except Exception as e:
            raise RuntimeError(f"Failed to get server info: {e}")

    # =========================================================================
    # Module Metadata
    # =========================================================================

    @classmethod
    def get_metadata(cls):
        """Get module metadata for compiler prompt generation."""
        from nl2py.modules.module_base import ModuleMetadata
        return ModuleMetadata(
            name="Keycloak",
            task_type="keycloak",
            description="Keycloak Identity and Access Management (IAM) with user management, roles, groups, OAuth2/OIDC clients, realm management, and authentication",
            version="1.0.0",
            keywords=["keycloak", "iam", "identity", "access-management", "authentication", "authorization", "oauth2", "oidc", "sso", "users", "roles", "groups", "realms"],
            dependencies=["python-keycloak>=2.0.0"]
        )

    @classmethod
    def get_usage_notes(cls):
        """Get usage notes and best practices."""
        return [
            "Module uses singleton pattern - one instance per application",
            "Requires Keycloak server running (default: http://localhost:8080)",
            "Admin credentials required for management operations (KEYCLOAK_ADMIN_USERNAME, KEYCLOAK_ADMIN_PASSWORD)",
            "Default realm is 'master', configure with KEYCLOAK_REALM",
            "Default client is 'admin-cli' for admin operations",
            "SSL/TLS verification enabled by default, set KEYCLOAK_VERIFY_SSL=false for dev",
            "set_realm() switches to different realm for multi-realm operations",
            "User passwords can be temporary (must change on first login) or permanent",
            "Realm roles are global within realm, client roles are client-specific",
            "Groups support hierarchical structure and role inheritance",
            "OAuth2/OIDC clients support public (browser apps) and confidential (server apps) types",
            "directAccessGrantsEnabled=true allows username/password authentication (Resource Owner Password Credentials flow)",
            "redirectUris must be configured for Authorization Code flow",
            "webOrigins controls CORS for browser-based apps",
            "authenticate() returns JWT access_token and refresh_token",
            "Access tokens expire (default 5 minutes), use refresh_token to get new ones",
            "Always call logout() to invalidate refresh tokens when done",
            "User attributes stored as dict, useful for custom profile fields",
            "Email verification controlled by emailVerified flag",
            "Federation allows integration with LDAP, Active Directory, external IDPs"
        ]

    @classmethod
    def get_methods_info(cls):
        """Get information about available methods."""
        from nl2py.modules.module_base import MethodInfo
        return [
            MethodInfo(
                name="set_realm",
                description="Switch to a different realm for subsequent operations",
                parameters={"realm_name": "str (required) - Realm name to switch to"},
                returns="None",
                examples=[
                    {"text": "Switch to realm {{myapp}}", "code": "set_realm(realm_name='{{myapp}}')"},
                    {"text": "Switch to realm {{production}}", "code": "set_realm(realm_name='{{production}}')"}
                ]
            ),
            MethodInfo(
                name="realm_create",
                description="Create a new realm",
                parameters={
                    "realm_name": "str (required) - Realm name",
                    "enabled": "bool (optional) - Enable realm (default True)",
                    "displayName": "str (optional) - Display name",
                    "displayNameHtml": "str (optional) - HTML display name"
                },
                returns="dict - Result with realm name and created status",
                examples=[
                    {"text": "Create realm {{myapp}} with display name {{My Application}}", "code": "realm_create(realm_name='{{myapp}}', enabled={{True}}, displayName='{{My Application}}')"}
                ]
            ),
            MethodInfo(
                name="realm_get",
                description="Get realm details",
                parameters={"realm_name": "str (optional) - Realm name (default current realm)"},
                returns="dict - Realm configuration",
                examples=[
                    {"text": "Get details of realm {{myapp}}", "code": "realm_get(realm_name='{{myapp}}')"},
                    {"text": "Get details of current realm", "code": "realm_get()"}
                ]
            ),
            MethodInfo(
                name="realm_delete",
                description="Delete a realm (caution: deletes all users, roles, clients)",
                parameters={"realm_name": "str (required) - Realm name to delete"},
                returns="dict - Result with deleted status",
                examples=[
                    {"text": "Delete realm {{test-realm}}", "code": "realm_delete(realm_name='{{test-realm}}')"}
                ]
            ),
            MethodInfo(
                name="user_create",
                description="Create a new user",
                parameters={
                    "username": "str (required) - Username",
                    "email": "str (optional) - Email address",
                    "firstName": "str (optional) - First name",
                    "lastName": "str (optional) - Last name",
                    "password": "str (optional) - Password",
                    "temporary": "bool (optional) - Temporary password (default False)",
                    "enabled": "bool (optional) - Enable user (default True)",
                    "emailVerified": "bool (optional) - Email verified (default False)",
                    "attributes": "dict (optional) - Custom attributes"
                },
                returns="dict - Result with user_id and created status",
                examples=[
                    {"text": "Create user {{john.doe}} with email {{john@example.com}} and password {{secret123}}", "code": "user_create(username='{{john.doe}}', email='{{john@example.com}}', password='{{secret123}}')"},
                    {"text": "Create user {{alice}} with first name {{Alice}} and last name {{Smith}}", "code": "user_create(username='{{alice}}', firstName='{{Alice}}', lastName='{{Smith}}', enabled={{True}})"}
                ]
            ),
            MethodInfo(
                name="user_get",
                description="Get user details by username",
                parameters={"username": "str (required) - Username"},
                returns="dict - User details",
                examples=[
                    {"text": "Get user details for {{john.doe}}", "code": "user_get(username='{{john.doe}}')"}
                ]
            ),
            MethodInfo(
                name="user_update",
                description="Update user attributes",
                parameters={
                    "username": "str (required) - Username",
                    "email": "str (optional) - New email",
                    "firstName": "str (optional) - New first name",
                    "lastName": "str (optional) - New last name",
                    "enabled": "bool (optional) - Enable/disable user",
                    "attributes": "dict (optional) - Custom attributes"
                },
                returns="dict - Result with updated status",
                examples=[
                    {"text": "Update user {{john.doe}} email to {{newemail@example.com}} and disable account", "code": "user_update(username='{{john.doe}}', email='{{newemail@example.com}}', enabled={{False}})"}
                ]
            ),
            MethodInfo(
                name="user_delete",
                description="Delete a user",
                parameters={"username": "str (required) - Username"},
                returns="dict - Result with deleted status",
                examples=[
                    {"text": "Delete user {{old.user}}", "code": "user_delete(username='{{old.user}}')"}
                ]
            ),
            MethodInfo(
                name="user_set_password",
                description="Set or reset user password",
                parameters={
                    "username": "str (required) - Username",
                    "password": "str (required) - New password",
                    "temporary": "bool (optional) - Temporary password requiring change on first login (default False)"
                },
                returns="dict - Result with password_set status",
                examples=[
                    {"text": "Set temporary password {{newpassword123}} for user {{john.doe}}", "code": "user_set_password(username='{{john.doe}}', password='{{newpassword123}}', temporary={{True}})"}
                ]
            ),
            MethodInfo(
                name="user_list",
                description="List users with optional filters",
                parameters={"query": "dict (optional) - Filter parameters (username, email, firstName, lastName, etc.)"},
                returns="list[dict] - List of users",
                examples=[
                    {"text": "List all users", "code": "user_list()"},
                    {"text": "List users filtered by email domain {{example.com}}", "code": "user_list(query={{'email': '{{example.com}}'}})" }
                ]
            ),
            MethodInfo(
                name="role_create",
                description="Create a realm role",
                parameters={
                    "role_name": "str (required) - Role name",
                    "description": "str (optional) - Role description"
                },
                returns="dict - Result with created status",
                examples=[
                    {"text": "Create role {{admin}} with description {{Administrator role}}", "code": "role_create(role_name='{{admin}}', description='{{Administrator role}}')"},
                    {"text": "Create role {{user}}", "code": "role_create(role_name='{{user}}')"}
                ]
            ),
            MethodInfo(
                name="role_get",
                description="Get role details",
                parameters={"role_name": "str (required) - Role name"},
                returns="dict - Role details",
                examples=[
                    {"text": "Get details of role {{admin}}", "code": "role_get(role_name='{{admin}}')"}
                ]
            ),
            MethodInfo(
                name="role_delete",
                description="Delete a realm role",
                parameters={"role_name": "str (required) - Role name"},
                returns="dict - Result with deleted status",
                examples=[
                    {"text": "Delete role {{old-role}}", "code": "role_delete(role_name='{{old-role}}')"}
                ]
            ),
            MethodInfo(
                name="role_list",
                description="List all realm roles",
                parameters={},
                returns="list[dict] - List of roles",
                examples=[
                    {"text": "List all realm roles", "code": "role_list()"}
                ]
            ),
            MethodInfo(
                name="user_assign_role",
                description="Assign a realm role to a user",
                parameters={
                    "username": "str (required) - Username",
                    "role_name": "str (required) - Role name to assign"
                },
                returns="dict - Result with assigned status",
                examples=[
                    {"text": "Assign role {{admin}} to user {{john.doe}}", "code": "user_assign_role(username='{{john.doe}}', role_name='{{admin}}')"}
                ]
            ),
            MethodInfo(
                name="user_remove_role",
                description="Remove a realm role from a user",
                parameters={
                    "username": "str (required) - Username",
                    "role_name": "str (required) - Role name to remove"
                },
                returns="dict - Result with removed status",
                examples=[
                    {"text": "Remove role {{admin}} from user {{john.doe}}", "code": "user_remove_role(username='{{john.doe}}', role_name='{{admin}}')"}
                ]
            ),
            MethodInfo(
                name="user_get_roles",
                description="Get all roles assigned to a user",
                parameters={"username": "str (required) - Username"},
                returns="list[dict] - List of assigned roles",
                examples=[
                    {"text": "Get all roles for user {{john.doe}}", "code": "user_get_roles(username='{{john.doe}}')"}
                ]
            ),
            MethodInfo(
                name="group_create",
                description="Create a group",
                parameters={
                    "group_name": "str (required) - Group name",
                    "attributes": "dict (optional) - Custom attributes"
                },
                returns="dict - Result with group_id and created status",
                examples=[
                    {"text": "Create group {{developers}}", "code": "group_create(group_name='{{developers}}')"},
                    {"text": "Create group {{admins}} with department {{IT}}", "code": "group_create(group_name='{{admins}}', attributes={{'department': '{{IT}}'}})" }
                ]
            ),
            MethodInfo(
                name="group_get",
                description="Get group by name",
                parameters={"group_name": "str (required) - Group name"},
                returns="dict - Group details",
                examples=[
                    {"text": "Get details of group {{developers}}", "code": "group_get(group_name='{{developers}}')"}
                ]
            ),
            MethodInfo(
                name="group_delete",
                description="Delete a group",
                parameters={"group_name": "str (required) - Group name"},
                returns="dict - Result with deleted status",
                examples=[
                    {"text": "Delete group {{old-group}}", "code": "group_delete(group_name='{{old-group}}')"}
                ]
            ),
            MethodInfo(
                name="group_add_user",
                description="Add user to a group",
                parameters={
                    "group_name": "str (required) - Group name",
                    "username": "str (required) - Username"
                },
                returns="dict - Result with added status",
                examples=[
                    {"text": "Add user {{john.doe}} to group {{developers}}", "code": "group_add_user(group_name='{{developers}}', username='{{john.doe}}')"}
                ]
            ),
            MethodInfo(
                name="group_remove_user",
                description="Remove user from a group",
                parameters={
                    "group_name": "str (required) - Group name",
                    "username": "str (required) - Username"
                },
                returns="dict - Result with removed status",
                examples=[
                    {"text": "Remove user {{john.doe}} from group {{developers}}", "code": "group_remove_user(group_name='{{developers}}', username='{{john.doe}}')"}
                ]
            ),
            MethodInfo(
                name="client_create",
                description="Create an OAuth2/OIDC client application",
                parameters={
                    "client_id": "str (required) - Client ID",
                    "enabled": "bool (optional) - Enable client (default True)",
                    "protocol": "str (optional) - Protocol: openid-connect or saml (default openid-connect)",
                    "publicClient": "bool (optional) - Public client (no secret) for browser apps (default False)",
                    "directAccessGrantsEnabled": "bool (optional) - Enable password flow (default True)",
                    "redirectUris": "list[str] (optional) - Redirect URIs for authorization code flow",
                    "webOrigins": "list[str] (optional) - Web origins for CORS",
                    "secret": "str (optional) - Client secret for confidential clients"
                },
                returns="dict - Result with client_uuid and created status",
                examples=[
                    {"text": "Create client {{myapp}} with redirect URI {{http://localhost:3000/callback}}", "code": "client_create(client_id='{{myapp}}', redirectUris=['{{http://localhost:3000/callback}}'])"},
                    {"text": "Create public client {{spa}} with redirect URI {{http://localhost:8080/*}}", "code": "client_create(client_id='{{spa}}', publicClient={{True}}, redirectUris=['{{http://localhost:8080/*}}'])"}
                ]
            ),
            MethodInfo(
                name="client_get",
                description="Get client by client ID",
                parameters={"client_id": "str (required) - Client ID"},
                returns="dict - Client configuration",
                examples=[
                    {"text": "Get client {{myapp}} configuration", "code": "client_get(client_id='{{myapp}}')"}
                ]
            ),
            MethodInfo(
                name="client_delete",
                description="Delete a client",
                parameters={"client_id": "str (required) - Client ID"},
                returns="dict - Result with deleted status",
                examples=[
                    {"text": "Delete client {{old-app}}", "code": "client_delete(client_id='{{old-app}}')"}
                ]
            ),
            MethodInfo(
                name="authenticate",
                description="Authenticate user and get access/refresh tokens",
                parameters={
                    "username": "str (required) - Username",
                    "password": "str (required) - Password"
                },
                returns="dict - Tokens with access_token, refresh_token, expires_in, token_type",
                examples=[
                    {"text": "Authenticate user {{john.doe}} with password {{password123}}", "code": "authenticate(username='{{john.doe}}', password='{{password123}}')"}
                ]
            ),
            MethodInfo(
                name="token_refresh",
                description="Refresh access token using refresh token",
                parameters={"refresh_token": "str (required) - Refresh token"},
                returns="dict - New tokens with access_token, refresh_token, expires_in",
                examples=[
                    {"text": "Refresh access token using {{refresh_token}}", "code": "token_refresh(refresh_token='{{refresh_token}}')"}
                ]
            ),
            MethodInfo(
                name="logout",
                description="Logout user and invalidate refresh token",
                parameters={"refresh_token": "str (required) - Refresh token to invalidate"},
                returns="dict - Result with logged_out status",
                examples=[
                    {"text": "Logout and invalidate {{refresh_token}}", "code": "logout(refresh_token='{{refresh_token}}')"}
                ]
            ),
            MethodInfo(
                name="get_server_info",
                description="Get Keycloak server connection information",
                parameters={},
                returns="dict - Server info with server_url, realm, client_id, connected",
                examples=[
                    {"text": "Get Keycloak server connection information", "code": "get_server_info()"}
                ]
            ),
            MethodInfo(
                name="user_get_by_id",
                description="Get user details by internal user ID",
                parameters={"user_id": "str (required) - Keycloak internal user ID (UUID)"},
                returns="dict - User details with attributes, credentials, groups, roles",
                examples=[
                    {"text": "Get user by UUID {{a1b2c3d4-e5f6-7890-abcd-ef1234567890}}", "code": "user_get_by_id(user_id='{{a1b2c3d4-e5f6-7890-abcd-ef1234567890}}')"}
                ]
            )
        ]

# Singleton instance
_keycloak_module = None

def get_keycloak_module() -> KeycloakModule:
    """Get the singleton Keycloak module instance."""
    global _keycloak_module
    if _keycloak_module is None:
        _keycloak_module = KeycloakModule()
    return _keycloak_module
