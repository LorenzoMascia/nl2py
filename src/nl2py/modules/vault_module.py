"""
HashiCorp Vault Module for Secrets Management

This module provides secure secrets management through HashiCorp Vault.
Configuration is loaded from nl2py.conf under the [vault] section.

Supports:
- Multiple authentication methods: Token, AppRole, Kubernetes, AWS IAM, LDAP, GitHub, TLS Certificate
- KV Secrets Engine v1 and v2
- Dynamic secrets (databases, AWS, etc.)
- Transit encryption engine (encryption as a service)
- Secret leasing and renewal
- SSL/TLS with optional certificate verification
- Multiple namespaces (Vault Enterprise)
- Batch operations for performance

Features:
- Read/write secrets securely
- Secret versioning (KV v2)
- Dynamic credentials generation
- Encryption/decryption operations
- Secret metadata management
- Automatic token renewal
- Lease management
- Secret rotation

Example configuration in nl2py.conf:
    [vault]
    URL=https://vault.example.com:8200
    VERIFY_SSL=true

    # Token Authentication (simplest)
    AUTH_METHOD=token
    TOKEN=s.xxxxxxxxxxxxxxxxxxxxxxxx

    # AppRole Authentication (recommended for apps)
    # AUTH_METHOD=approle
    # ROLE_ID=xxxxx-xxxx-xxxx-xxxx-xxxxx
    # SECRET_ID=xxxxx-xxxx-xxxx-xxxx-xxxxx

    # Kubernetes Authentication
    # AUTH_METHOD=kubernetes
    # K8S_ROLE=my-role
    # K8S_JWT_PATH=/var/run/secrets/kubernetes.io/serviceaccount/token

    # AWS IAM Authentication
    # AUTH_METHOD=aws
    # AWS_ROLE=my-role

    # Settings
    NAMESPACE=admin  # For Vault Enterprise
    MOUNT_POINT=secret  # KV mount point
    KV_VERSION=2  # KV engine version (1 or 2)

Usage in generated code:
    from nl2py.modules import VaultModule

    # Initialize module
    vault = VaultModule.from_config('nl2py.conf')

    # Read/Write secrets
    vault.write_secret('myapp/database', {'username': 'admin', 'password': 'secret'})
    secret = vault.read_secret('myapp/database')

    # List secrets
    secrets = vault.list_secrets('myapp/')

    # Delete secrets
    vault.delete_secret('myapp/old-creds')

    # Encryption (Transit engine)
    ciphertext = vault.encrypt('my-key', 'sensitive data')
    plaintext = vault.decrypt('my-key', ciphertext)
"""

import configparser
import json
import os
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

try:
    import hvac
    from hvac.exceptions import InvalidPath, Forbidden, VaultError
except ImportError:
    hvac = None
    InvalidPath = Exception
    Forbidden = Exception
    VaultError = Exception

from .module_base import NL2PyModuleBase


class VaultModule(NL2PyModuleBase):
    """
    HashiCorp Vault secrets management module.

    Supports multiple authentication methods and secret engines.
    """

    _instance = None
    _lock = threading.Lock()

    # Supported authentication methods
    AUTH_METHODS = [
        'token', 'approle', 'kubernetes', 'aws', 'ldap',
        'github', 'userpass', 'cert'
    ]

    def __init__(
        self,
        url: str,
        auth_method: str = 'token',
        token: Optional[str] = None,
        role_id: Optional[str] = None,
        secret_id: Optional[str] = None,
        k8s_role: Optional[str] = None,
        k8s_jwt_path: Optional[str] = None,
        aws_role: Optional[str] = None,
        verify_ssl: bool = True,
        ca_cert: Optional[str] = None,
        client_cert: Optional[str] = None,
        client_key: Optional[str] = None,
        namespace: Optional[str] = None,
        mount_point: str = 'secret',
        kv_version: int = 2
    ):
        """
        Initialize the VaultModule.

        Args:
            url: Vault server URL (e.g., https://vault.example.com:8200)
            auth_method: Authentication method (token, approle, kubernetes, aws, etc.)
            token: Vault token (for token auth)
            role_id: AppRole role ID
            secret_id: AppRole secret ID
            k8s_role: Kubernetes role name
            k8s_jwt_path: Path to Kubernetes JWT token
            aws_role: AWS IAM role name
            verify_ssl: Verify SSL certificates
            ca_cert: Path to CA certificate
            client_cert: Path to client certificate (for cert auth)
            client_key: Path to client key (for cert auth)
            namespace: Vault namespace (Enterprise feature)
            mount_point: KV secrets engine mount point
            kv_version: KV engine version (1 or 2)
        """
        if hvac is None:
            raise ImportError(
                "hvac (HashiCorp Vault client) is required. Install with: pip install hvac"
            )

        self.url = url
        self.auth_method = auth_method
        self.mount_point = mount_point
        self.kv_version = kv_version
        self.namespace = namespace

        # SSL/TLS configuration
        if not verify_ssl:
            print("[VaultModule] ⚠️  SSL certificate verification DISABLED")
            verify = False
        elif ca_cert:
            verify = ca_cert
        else:
            verify = True

        # Client certificate for TLS auth
        cert = None
        if client_cert and client_key:
            cert = (client_cert, client_key)

        # Initialize hvac client
        self.client = hvac.Client(
            url=url,
            verify=verify,
            cert=cert,
            namespace=namespace
        )

        # Authenticate based on method
        self._authenticate(
            auth_method=auth_method,
            token=token,
            role_id=role_id,
            secret_id=secret_id,
            k8s_role=k8s_role,
            k8s_jwt_path=k8s_jwt_path,
            aws_role=aws_role
        )

        # Verify authentication
        if not self.client.is_authenticated():
            raise RuntimeError("Failed to authenticate with Vault")

        print(f"[VaultModule] Connected to Vault at {url} using {auth_method} auth")
        print(f"[VaultModule] Using KV v{kv_version} engine at mount point '{mount_point}'")

    def _authenticate(
        self,
        auth_method: str,
        token: Optional[str] = None,
        role_id: Optional[str] = None,
        secret_id: Optional[str] = None,
        k8s_role: Optional[str] = None,
        k8s_jwt_path: Optional[str] = None,
        aws_role: Optional[str] = None
    ):
        """Authenticate with Vault using specified method."""

        if auth_method == 'token':
            if not token:
                raise ValueError("Token is required for token authentication")
            self.client.token = token

        elif auth_method == 'approle':
            if not role_id or not secret_id:
                raise ValueError("role_id and secret_id are required for AppRole auth")
            response = self.client.auth.approle.login(
                role_id=role_id,
                secret_id=secret_id
            )
            self.client.token = response['auth']['client_token']

        elif auth_method == 'kubernetes':
            if not k8s_role:
                raise ValueError("k8s_role is required for Kubernetes auth")

            # Read JWT token
            jwt_path = k8s_jwt_path or '/var/run/secrets/kubernetes.io/serviceaccount/token'
            with open(jwt_path, 'r') as f:
                jwt = f.read().strip()

            response = self.client.auth.kubernetes.login(
                role=k8s_role,
                jwt=jwt
            )
            self.client.token = response['auth']['client_token']

        elif auth_method == 'aws':
            if not aws_role:
                raise ValueError("aws_role is required for AWS auth")

            response = self.client.auth.aws.iam_login(
                role=aws_role
            )
            self.client.token = response['auth']['client_token']

        elif auth_method == 'ldap':
            # LDAP auth requires username/password at runtime
            print("[VaultModule] LDAP auth requires username/password - use login_ldap() method")

        elif auth_method == 'github':
            # GitHub auth requires token at runtime
            print("[VaultModule] GitHub auth requires token - use login_github() method")

        elif auth_method == 'userpass':
            # UserPass auth requires username/password at runtime
            print("[VaultModule] UserPass auth requires username/password - use login_userpass() method")

        elif auth_method == 'cert':
            # Certificate auth uses client certificate provided in __init__
            response = self.client.auth.cert.login()
            self.client.token = response['auth']['client_token']

        else:
            raise ValueError(f"Unsupported auth method: {auth_method}")

    @classmethod
    def from_config(cls, config_path: str = "nl2py.conf") -> 'VaultModule':
        """
        Create a VaultModule from configuration file.
        Uses singleton pattern to ensure only one instance exists.

        Args:
            config_path: Path to nl2py.conf file

        Returns:
            VaultModule instance
        """
        with cls._lock:
            if cls._instance is None:
                config = configparser.ConfigParser()
                path = Path(config_path)

                if not path.exists():
                    raise FileNotFoundError(f"Configuration file not found: {config_path}")

                config.read(path)

                if 'vault' not in config:
                    raise KeyError("Missing [vault] section in nl2py.conf")

                vault_config = config['vault']

                # Required
                url = vault_config.get('URL')
                if not url:
                    raise ValueError("URL is required in [vault] section")

                # Authentication
                auth_method = vault_config.get('AUTH_METHOD', 'token').lower()
                token = vault_config.get('TOKEN', None)
                role_id = vault_config.get('ROLE_ID', None)
                secret_id = vault_config.get('SECRET_ID', None)
                k8s_role = vault_config.get('K8S_ROLE', None)
                k8s_jwt_path = vault_config.get('K8S_JWT_PATH', None)
                aws_role = vault_config.get('AWS_ROLE', None)

                # SSL/TLS
                verify_ssl = vault_config.getboolean('VERIFY_SSL', True)
                ca_cert = vault_config.get('CA_CERT', None)
                client_cert = vault_config.get('CLIENT_CERT', None)
                client_key = vault_config.get('CLIENT_KEY', None)

                # Settings
                namespace = vault_config.get('NAMESPACE', None)
                mount_point = vault_config.get('MOUNT_POINT', 'secret')
                kv_version = vault_config.getint('KV_VERSION', 2)

                cls._instance = cls(
                    url=url,
                    auth_method=auth_method,
                    token=token,
                    role_id=role_id,
                    secret_id=secret_id,
                    k8s_role=k8s_role,
                    k8s_jwt_path=k8s_jwt_path,
                    aws_role=aws_role,
                    verify_ssl=verify_ssl,
                    ca_cert=ca_cert,
                    client_cert=client_cert,
                    client_key=client_key,
                    namespace=namespace,
                    mount_point=mount_point,
                    kv_version=kv_version
                )

            return cls._instance

    # ==================== KV Secrets Operations ====================

    def read_secret(self, path: str, version: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Read a secret from Vault.

        Args:
            path: Secret path (e.g., 'myapp/database')
            version: Secret version (KV v2 only, None = latest)

        Returns:
            Secret data dict or None if not found
        """
        try:
            if self.kv_version == 2:
                response = self.client.secrets.kv.v2.read_secret_version(
                    path=path,
                    mount_point=self.mount_point,
                    version=version
                )
                return response['data']['data']
            else:
                response = self.client.secrets.kv.v1.read_secret(
                    path=path,
                    mount_point=self.mount_point
                )
                return response['data']
        except InvalidPath:
            return None

    def write_secret(self, path: str, secret: Dict[str, Any], cas: Optional[int] = None) -> Dict[str, Any]:
        """
        Write a secret to Vault.

        Args:
            path: Secret path
            secret: Secret data (key-value pairs)
            cas: Check-and-Set version (KV v2 only, for optimistic locking)

        Returns:
            Response metadata
        """
        if self.kv_version == 2:
            response = self.client.secrets.kv.v2.create_or_update_secret(
                path=path,
                secret=secret,
                mount_point=self.mount_point,
                cas=cas
            )
        else:
            response = self.client.secrets.kv.v1.create_or_update_secret(
                path=path,
                secret=secret,
                mount_point=self.mount_point
            )

        print(f"[VaultModule] Secret written to {path}")
        return response

    def delete_secret(self, path: str, versions: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Delete a secret (or specific versions).

        Args:
            path: Secret path
            versions: Version numbers to delete (KV v2 only, None = delete latest)

        Returns:
            Response dict
        """
        if self.kv_version == 2:
            if versions:
                response = self.client.secrets.kv.v2.delete_secret_versions(
                    path=path,
                    versions=versions,
                    mount_point=self.mount_point
                )
            else:
                response = self.client.secrets.kv.v2.delete_latest_version_of_secret(
                    path=path,
                    mount_point=self.mount_point
                )
        else:
            response = self.client.secrets.kv.v1.delete_secret(
                path=path,
                mount_point=self.mount_point
            )

        print(f"[VaultModule] Secret deleted at {path}")
        return response

    def list_secrets(self, path: str = '') -> List[str]:
        """
        List secrets at a path.

        Args:
            path: Directory path (e.g., 'myapp/')

        Returns:
            List of secret names/subdirectories
        """
        try:
            if self.kv_version == 2:
                response = self.client.secrets.kv.v2.list_secrets(
                    path=path,
                    mount_point=self.mount_point
                )
            else:
                response = self.client.secrets.kv.v1.list_secrets(
                    path=path,
                    mount_point=self.mount_point
                )
            return response['data']['keys']
        except InvalidPath:
            return []

    def get_secret_metadata(self, path: str) -> Optional[Dict[str, Any]]:
        """Get secret metadata (KV v2 only)."""
        if self.kv_version != 2:
            raise NotImplementedError("Metadata is only available in KV v2")

        try:
            response = self.client.secrets.kv.v2.read_secret_metadata(
                path=path,
                mount_point=self.mount_point
            )
            return response['data']
        except InvalidPath:
            return None

    def undelete_secret(self, path: str, versions: List[int]) -> Dict[str, Any]:
        """Undelete secret versions (KV v2 only)."""
        if self.kv_version != 2:
            raise NotImplementedError("Undelete is only available in KV v2")

        response = self.client.secrets.kv.v2.undelete_secret_versions(
            path=path,
            versions=versions,
            mount_point=self.mount_point
        )
        print(f"[VaultModule] Secret undeleted at {path}")
        return response

    def destroy_secret(self, path: str, versions: List[int]) -> Dict[str, Any]:
        """Permanently destroy secret versions (KV v2 only)."""
        if self.kv_version != 2:
            raise NotImplementedError("Destroy is only available in KV v2")

        response = self.client.secrets.kv.v2.destroy_secret_versions(
            path=path,
            versions=versions,
            mount_point=self.mount_point
        )
        print(f"[VaultModule] Secret permanently destroyed at {path}")
        return response

    # ==================== Transit Encryption ====================

    def encrypt(
        self,
        key_name: str,
        plaintext: Union[str, bytes],
        context: Optional[str] = None,
        mount_point: str = 'transit'
    ) -> str:
        """
        Encrypt data using Transit engine.

        Args:
            key_name: Encryption key name
            plaintext: Data to encrypt
            context: Base64-encoded context (for key derivation)
            mount_point: Transit engine mount point

        Returns:
            Ciphertext (vault:v1:...)
        """
        import base64

        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')

        plaintext_b64 = base64.b64encode(plaintext).decode('utf-8')

        response = self.client.secrets.transit.encrypt_data(
            name=key_name,
            plaintext=plaintext_b64,
            context=context,
            mount_point=mount_point
        )

        return response['data']['ciphertext']

    def decrypt(
        self,
        key_name: str,
        ciphertext: str,
        context: Optional[str] = None,
        mount_point: str = 'transit'
    ) -> str:
        """
        Decrypt data using Transit engine.

        Args:
            key_name: Encryption key name
            ciphertext: Encrypted data (vault:v1:...)
            context: Base64-encoded context (must match encryption)
            mount_point: Transit engine mount point

        Returns:
            Decrypted plaintext
        """
        import base64

        response = self.client.secrets.transit.decrypt_data(
            name=key_name,
            ciphertext=ciphertext,
            context=context,
            mount_point=mount_point
        )

        plaintext_b64 = response['data']['plaintext']
        plaintext = base64.b64decode(plaintext_b64).decode('utf-8')

        return plaintext

    def create_transit_key(
        self,
        key_name: str,
        key_type: str = 'aes256-gcm96',
        mount_point: str = 'transit'
    ) -> Dict[str, Any]:
        """Create a new encryption key in Transit engine."""
        response = self.client.secrets.transit.create_key(
            name=key_name,
            key_type=key_type,
            mount_point=mount_point
        )
        print(f"[VaultModule] Transit key created: {key_name}")
        return response

    def rotate_transit_key(self, key_name: str, mount_point: str = 'transit') -> Dict[str, Any]:
        """Rotate a Transit encryption key."""
        response = self.client.secrets.transit.rotate_key(
            name=key_name,
            mount_point=mount_point
        )
        print(f"[VaultModule] Transit key rotated: {key_name}")
        return response

    # ==================== Dynamic Secrets ====================

    def read_database_creds(
        self,
        role_name: str,
        mount_point: str = 'database'
    ) -> Dict[str, Any]:
        """
        Generate dynamic database credentials.

        Args:
            role_name: Database role name
            mount_point: Database secrets engine mount point

        Returns:
            Dict with username, password, and lease info
        """
        response = self.client.secrets.database.generate_credentials(
            name=role_name,
            mount_point=mount_point
        )

        creds = {
            'username': response['data']['username'],
            'password': response['data']['password'],
            'lease_id': response['lease_id'],
            'lease_duration': response['lease_duration']
        }

        print(f"[VaultModule] Generated database credentials for role {role_name}")
        return creds

    def read_aws_creds(
        self,
        role_name: str,
        mount_point: str = 'aws'
    ) -> Dict[str, Any]:
        """Generate dynamic AWS credentials."""
        response = self.client.secrets.aws.generate_credentials(
            name=role_name,
            mount_point=mount_point
        )

        creds = {
            'access_key': response['data']['access_key'],
            'secret_key': response['data']['secret_key'],
            'security_token': response['data'].get('security_token'),
            'lease_id': response['lease_id'],
            'lease_duration': response['lease_duration']
        }

        print(f"[VaultModule] Generated AWS credentials for role {role_name}")
        return creds

    # ==================== Lease Management ====================

    def renew_lease(self, lease_id: str, increment: Optional[int] = None) -> Dict[str, Any]:
        """Renew a lease."""
        response = self.client.sys.renew_lease(
            lease_id=lease_id,
            increment=increment
        )
        print(f"[VaultModule] Lease renewed: {lease_id}")
        return response

    def revoke_lease(self, lease_id: str) -> Dict[str, Any]:
        """Revoke a lease."""
        response = self.client.sys.revoke_lease(lease_id=lease_id)
        print(f"[VaultModule] Lease revoked: {lease_id}")
        return response

    # ==================== Authentication Helpers ====================

    def login_userpass(self, username: str, password: str) -> str:
        """Login using username/password authentication."""
        response = self.client.auth.userpass.login(
            username=username,
            password=password
        )
        self.client.token = response['auth']['client_token']
        print(f"[VaultModule] Logged in as {username}")
        return self.client.token

    def login_ldap(self, username: str, password: str) -> str:
        """Login using LDAP authentication."""
        response = self.client.auth.ldap.login(
            username=username,
            password=password
        )
        self.client.token = response['auth']['client_token']
        print(f"[VaultModule] Logged in via LDAP as {username}")
        return self.client.token

    def login_github(self, token: str) -> str:
        """Login using GitHub authentication."""
        response = self.client.auth.github.login(token=token)
        self.client.token = response['auth']['client_token']
        print("[VaultModule] Logged in via GitHub")
        return self.client.token

    # ==================== Token Management ====================

    def renew_token(self, increment: Optional[int] = None) -> Dict[str, Any]:
        """Renew the current token."""
        response = self.client.auth.token.renew_self(increment=increment)
        print("[VaultModule] Token renewed")
        return response

    def lookup_token(self) -> Dict[str, Any]:
        """Get information about the current token."""
        return self.client.auth.token.lookup_self()

    # ==================== Health & Status ====================

    def is_authenticated(self) -> bool:
        """Check if client is authenticated."""
        return self.client.is_authenticated()

    def is_sealed(self) -> bool:
        """Check if Vault is sealed."""
        return self.client.sys.is_sealed()

    def get_health(self) -> Dict[str, Any]:
        """Get Vault health status."""
        return self.client.sys.read_health_status()

    def close(self):
        """Close connection."""
        if self.client:
            self.client = None
            print("[VaultModule] Connection closed")

    def __del__(self):
        """Destructor to ensure connection is closed."""
        try:
            self.close()
        except:
            pass

    @classmethod
    def get_metadata(cls):
        """Get module metadata for compiler prompt generation."""
        from nl2py.modules.module_base import ModuleMetadata
        return ModuleMetadata(
            name="Vault",
            task_type="vault",
            description="HashiCorp Vault secrets management with KV storage, dynamic credentials, encryption, and multiple auth methods",
            version="1.0.0",
            keywords=[
                "vault", "hashicorp", "secrets", "security", "encryption",
                "kv", "dynamic-credentials", "transit", "approle", "kubernetes"
            ],
            dependencies=["hvac>=1.0.0"]
        )

    @classmethod
    def get_usage_notes(cls):
        """Get detailed usage notes for this module."""
        return [
            "Module uses singleton pattern - one Vault client per application",
            "Supports multiple auth methods: token, approle, kubernetes, aws, ldap, github, userpass, cert",
            "KV v2 supports versioning, metadata, and soft delete (default)",
            "KV v1 simpler but no versioning or metadata",
            "Default mount point is 'secret' for KV engine",
            "Transit engine provides encryption-as-a-service",
            "Dynamic secrets auto-generate time-limited credentials",
            "Leases have TTL and can be renewed or revoked",
            "AppRole recommended for app authentication (role_id + secret_id)",
            "Token auth simplest but less secure for production",
            "Kubernetes auth for pods (requires service account JWT)",
            "AWS auth for EC2/Lambda (uses IAM credentials)",
            "verify_ssl=False only for development with self-signed certs",
            "Namespace support for Vault Enterprise (multi-tenancy)",
            "cas (check-and-set) prevents concurrent write conflicts (KV v2)",
            "Soft deleted secrets can be undeleted (KV v2)",
            "Destroy permanently removes secret versions (KV v2)",
            "Transit encryption returns 'vault:v1:...' ciphertext format",
            "Key rotation supported for Transit keys without re-encryption",
            "Always check is_authenticated() after initialization"
        ]

    @classmethod
    def get_methods_info(cls):
        """Get information about all methods in this module."""
        from nl2py.modules.module_base import MethodInfo
        return [
            MethodInfo(
                name="read_secret",
                description="Read a secret from KV engine",
                parameters={
                    "path": "str (required) - Secret path (e.g., 'myapp/database')",
                    "version": "int (optional) - Version number (KV v2 only, None = latest)"
                },
                returns="dict/None - Secret data or None if not found",
                examples=[
                    {"text": "Read latest version of secret at path {{myapp/database}}", "code": "read_secret(path='{{myapp/database}}')"},
                    {"text": "Read version {{3}} of secret at path {{app/creds}}", "code": "read_secret(path='{{app/creds}}', version={{3}})"}
                ]
            ),
            MethodInfo(
                name="write_secret",
                description="Write a secret to KV engine",
                parameters={
                    "path": "str (required) - Secret path",
                    "secret": "dict (required) - Key-value pairs to store",
                    "cas": "int (optional) - Check-and-set version (KV v2 only)"
                },
                returns="dict - Response metadata",
                examples=[
                    {"text": "Write secret at path {{myapp/database}} with username {{admin}} and password {{secret123}}", "code": "write_secret(path='{{myapp/database}}', secret={{'username': '{{admin}}', 'password': '{{secret123}}'}})"}
                ]
            ),
            MethodInfo(
                name="delete_secret",
                description="Delete a secret or specific versions",
                parameters={
                    "path": "str (required) - Secret path",
                    "versions": "list (optional) - Version numbers to delete (KV v2 only)"
                },
                returns="dict - Response",
                examples=[
                    {"text": "Delete latest version of secret at path {{myapp/old-creds}}", "code": "delete_secret(path='{{myapp/old-creds}}')"},
                    {"text": "Delete versions {{1}}, {{2}}, {{3}} of secret at path {{app/data}}", "code": "delete_secret(path='{{app/data}}', versions=[{{1}}, {{2}}, {{3}}])"}
                ]
            ),
            MethodInfo(
                name="list_secrets",
                description="List secrets at a path",
                parameters={"path": "str (optional) - Directory path (e.g., 'myapp/')"},
                returns="list - Secret names and subdirectories",
                examples=[
                    {"text": "List secrets at path {{myapp/}}", "code": "list_secrets(path='{{myapp/}}')"},
                    {"text": "List all secrets at root", "code": "list_secrets()"}
                ]
            ),
            MethodInfo(
                name="encrypt",
                description="Encrypt data using Transit engine",
                parameters={
                    "key_name": "str (required) - Encryption key name",
                    "plaintext": "str/bytes (required) - Data to encrypt",
                    "context": "str (optional) - Base64 context for key derivation",
                    "mount_point": "str (optional) - Transit mount point (default 'transit')"
                },
                returns="str - Ciphertext (vault:v1:...)",
                examples=[
                    {"text": "Encrypt plaintext {{sensitive data}} with key {{my-key}}", "code": "encrypt(key_name='{{my-key}}', plaintext='{{sensitive data}}')"}
                ]
            ),
            MethodInfo(
                name="decrypt",
                description="Decrypt data using Transit engine",
                parameters={
                    "key_name": "str (required) - Encryption key name",
                    "ciphertext": "str (required) - Encrypted data",
                    "context": "str (optional) - Base64 context (must match encryption)",
                    "mount_point": "str (optional) - Transit mount point (default 'transit')"
                },
                returns="str - Decrypted plaintext",
                examples=[
                    {"text": "Decrypt ciphertext {{vault:v1:...}} with key {{my-key}}", "code": "decrypt(key_name='{{my-key}}', ciphertext='{{vault:v1:...}}')"}
                ]
            ),
            MethodInfo(
                name="read_database_creds",
                description="Generate dynamic database credentials",
                parameters={
                    "role_name": "str (required) - Database role name",
                    "mount_point": "str (optional) - Database engine mount (default 'database')"
                },
                returns="dict - username, password, lease_id, lease_duration",
                examples=[
                    {"text": "Generate database credentials for role {{readonly}}", "code": "read_database_creds(role_name='{{readonly}}')"}
                ]
            ),
            MethodInfo(
                name="read_aws_creds",
                description="Generate dynamic AWS credentials",
                parameters={
                    "role_name": "str (required) - AWS role name",
                    "mount_point": "str (optional) - AWS engine mount (default 'aws')"
                },
                returns="dict - access_key, secret_key, security_token, lease info",
                examples=[
                    {"text": "Generate AWS credentials for role {{s3-access}}", "code": "read_aws_creds(role_name='{{s3-access}}')"}
                ]
            ),
            MethodInfo(
                name="renew_lease",
                description="Renew a secret lease",
                parameters={
                    "lease_id": "str (required) - Lease ID to renew",
                    "increment": "int (optional) - Renewal increment in seconds"
                },
                returns="dict - Response with new lease info",
                examples=[
                    {"text": "Renew lease {{database/creds/readonly/abc123}}", "code": "renew_lease(lease_id='{{database/creds/readonly/abc123}}')"}
                ]
            ),
            MethodInfo(
                name="revoke_lease",
                description="Revoke a secret lease",
                parameters={"lease_id": "str (required) - Lease ID to revoke"},
                returns="dict - Response",
                examples=[
                    {"text": "Revoke lease {{database/creds/readonly/abc123}}", "code": "revoke_lease(lease_id='{{database/creds/readonly/abc123}}')"}
                ]
            ),
            MethodInfo(
                name="is_authenticated",
                description="Check if client is authenticated with Vault",
                parameters={},
                returns="bool - True if authenticated",
                examples=[
                    {"text": "Check authentication status", "code": "is_authenticated()"}
                ]
            ),
            MethodInfo(
                name="is_sealed",
                description="Check if Vault is sealed",
                parameters={},
                returns="bool - True if sealed",
                examples=[
                    {"text": "Check if Vault is sealed", "code": "is_sealed()"}
                ]
            ),
            MethodInfo(
                name="get_secret_metadata",
                description="Get secret metadata including versions (KV v2 only)",
                parameters={"path": "str (required) - Secret path"},
                returns="dict/None - Metadata with versions, created/updated times",
                examples=[
                    {"text": "Get metadata for secret at path {{myapp/database}}", "code": "get_secret_metadata(path='{{myapp/database}}')"}
                ]
            ),
            MethodInfo(
                name="destroy_secret",
                description="Permanently destroy secret versions (unrecoverable, KV v2 only)",
                parameters={
                    "path": "str (required) - Secret path",
                    "versions": "list (required) - Version numbers to destroy"
                },
                returns="dict - Response",
                examples=[
                    {"text": "Permanently destroy versions {{1}}, {{2}} of secret at path {{myapp/old-data}}", "code": "destroy_secret(path='{{myapp/old-data}}', versions=[{{1}}, {{2}}])"}
                ]
            ),
            MethodInfo(
                name="login_userpass",
                description="Authenticate using username/password method",
                parameters={
                    "username": "str (required) - Username",
                    "password": "str (required) - Password"
                },
                returns="str - Authentication token",
                examples=[
                    {"text": "Login with username {{admin}} and password {{password123}}", "code": "login_userpass(username='{{admin}}', password='{{password123}}')"}
                ]
            ),
            MethodInfo(
                name="login_ldap",
                description="Authenticate using LDAP credentials",
                parameters={
                    "username": "str (required) - LDAP username",
                    "password": "str (required) - LDAP password"
                },
                returns="str - Authentication token",
                examples=[
                    {"text": "Login with LDAP username {{john.doe}} and password {{password}}", "code": "login_ldap(username='{{john.doe}}', password='{{password}}')"}
                ]
            ),
            MethodInfo(
                name="login_github",
                description="Authenticate using GitHub personal access token",
                parameters={"token": "str (required) - GitHub personal access token"},
                returns="str - Authentication token",
                examples=[
                    {"text": "Login with GitHub token {{ghp_xxxxxxxxxxxx}}", "code": "login_github(token='{{ghp_xxxxxxxxxxxx}}')"}
                ]
            ),
            MethodInfo(
                name="renew_token",
                description="Renew the current authentication token",
                parameters={"increment": "int (optional) - Renewal increment in seconds"},
                returns="dict - Response with new token TTL",
                examples=[
                    {"text": "Renew authentication token", "code": "renew_token()"},
                    {"text": "Renew token with increment {{3600}}", "code": "renew_token(increment={{3600}})"}
                ]
            ),
            MethodInfo(
                name="get_health",
                description="Get Vault server health status",
                parameters={},
                returns="dict - Health info including sealed status, version, cluster info",
                examples=[
                    {"text": "Get Vault health status", "code": "get_health()"}
                ]
            ),
            MethodInfo(
                name="lookup_token",
                description="Get information about the current token",
                parameters={},
                returns="dict - Token info including policies, TTL, accessor",
                examples=[
                    {"text": "Get current token information", "code": "lookup_token()"}
                ]
            ),
            MethodInfo(
                name="undelete_secret",
                description="Restore soft-deleted secret versions (KV v2 only)",
                parameters={
                    "path": "str (required) - Secret path",
                    "versions": "list[int] (required) - Version numbers to restore"
                },
                returns="dict - Response",
                examples=[
                    {"text": "Restore versions {{1}}, {{2}} of secret at path {{myapp/config}}", "code": "undelete_secret(path='{{myapp/config}}', versions=[{{1}}, {{2}}])"}
                ]
            ),
            MethodInfo(
                name="rotate_transit_key",
                description="Rotate a Transit encryption key (creates new version)",
                parameters={
                    "key_name": "str (required) - Transit key name",
                    "mount_point": "str (optional) - Transit mount point (default 'transit')"
                },
                returns="dict - Response with new key version",
                examples=[
                    {"text": "Rotate Transit encryption key {{my-encryption-key}}", "code": "rotate_transit_key(key_name='{{my-encryption-key}}')"}
                ]
            )
        ]

