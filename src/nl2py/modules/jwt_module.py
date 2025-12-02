"""
JWT (JSON Web Token) Module for NL2Py

This module provides comprehensive JWT token management including:
- Token Creation: Generate JWT tokens with custom claims
- Token Verification: Validate and verify JWT signatures
- Token Decoding: Decode token payloads without verification
- Algorithm Support: HS256, HS384, HS512, RS256, RS384, RS512, ES256, ES384, ES512
- Claims Validation: Expiration, not-before, audience, issuer checks
- Refresh Tokens: Generate and manage refresh tokens
- Public/Private Key Support: RSA and ECDSA key pairs

Configuration in nl2py.conf:
    [jwt]
    SECRET_KEY = your-secret-key-here
    ALGORITHM = HS256
    ISSUER = your-app-name
    AUDIENCE = your-audience
    ACCESS_TOKEN_EXPIRE_MINUTES = 15
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    PRIVATE_KEY_PATH = /path/to/private.pem
    PUBLIC_KEY_PATH = /path/to/public.pem
"""

import os
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
import json
from .module_base import NL2PyModuleBase

try:
    import jwt
    from jwt import PyJWT
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
except ImportError:
    raise ImportError(
        "JWT module requires PyJWT and cryptography. "
        "Install with: pip install PyJWT[crypto] cryptography"
    )


class JWTModule(NL2PyModuleBase):
    """
    JWT module for token management and authentication.

    Implements singleton pattern for efficient resource usage.
    Provides comprehensive JWT operations through PyJWT library.
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls, config: Optional[Dict[str, Any]] = None):
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize JWT module with configuration.

        Args:
            config: Configuration dictionary from nl2py.conf
        """
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            self.config = config or {}

            # Secret key for symmetric algorithms (HS256, HS384, HS512)
            self.secret_key = self.config.get('SECRET_KEY') or os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')

            # Algorithm (HS256, HS384, HS512, RS256, RS384, RS512, ES256, ES384, ES512)
            self.algorithm = self.config.get('ALGORITHM') or os.getenv('JWT_ALGORITHM', 'HS256')

            # Token settings
            self.issuer = self.config.get('ISSUER') or os.getenv('JWT_ISSUER', 'aibasic')
            self.audience = self.config.get('AUDIENCE') or os.getenv('JWT_AUDIENCE')

            # Expiration settings
            self.access_token_expire_minutes = int(
                self.config.get('ACCESS_TOKEN_EXPIRE_MINUTES') or
                os.getenv('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', '15')
            )
            self.refresh_token_expire_days = int(
                self.config.get('REFRESH_TOKEN_EXPIRE_DAYS') or
                os.getenv('JWT_REFRESH_TOKEN_EXPIRE_DAYS', '7')
            )

            # RSA/ECDSA key paths for asymmetric algorithms
            self.private_key_path = self.config.get('PRIVATE_KEY_PATH') or os.getenv('JWT_PRIVATE_KEY_PATH')
            self.public_key_path = self.config.get('PUBLIC_KEY_PATH') or os.getenv('JWT_PUBLIC_KEY_PATH')

            # Lazy-loaded keys
            self._private_key = None
            self._public_key = None

            self._initialized = True

    @property
    def private_key(self):
        """Get private key for asymmetric algorithms (lazy-loaded)."""
        if self._private_key is None and self.private_key_path:
            if os.path.exists(self.private_key_path):
                with open(self.private_key_path, 'rb') as key_file:
                    self._private_key = serialization.load_pem_private_key(
                        key_file.read(),
                        password=None,
                        backend=default_backend()
                    )
            else:
                raise FileNotFoundError(f"Private key not found: {self.private_key_path}")
        return self._private_key

    @property
    def public_key(self):
        """Get public key for asymmetric algorithms (lazy-loaded)."""
        if self._public_key is None and self.public_key_path:
            if os.path.exists(self.public_key_path):
                with open(self.public_key_path, 'rb') as key_file:
                    self._public_key = serialization.load_pem_public_key(
                        key_file.read(),
                        backend=default_backend()
                    )
            else:
                raise FileNotFoundError(f"Public key not found: {self.public_key_path}")
        return self._public_key

    def _get_signing_key(self):
        """Get the appropriate signing key based on algorithm."""
        if self.algorithm.startswith('HS'):
            # Symmetric algorithm - use secret key
            return self.secret_key
        elif self.algorithm.startswith(('RS', 'ES', 'PS')):
            # Asymmetric algorithm - use private key
            return self.private_key
        else:
            raise ValueError(f"Unsupported algorithm: {self.algorithm}")

    def _get_verification_key(self):
        """Get the appropriate verification key based on algorithm."""
        if self.algorithm.startswith('HS'):
            # Symmetric algorithm - use secret key
            return self.secret_key
        elif self.algorithm.startswith(('RS', 'ES', 'PS')):
            # Asymmetric algorithm - use public key
            return self.public_key
        else:
            raise ValueError(f"Unsupported algorithm: {self.algorithm}")

    def create_token(self, payload: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT token with the given payload.

        Args:
            payload: Dictionary of claims to include in the token
            expires_delta: Optional custom expiration time

        Returns:
            Encoded JWT token string
        """
        try:
            to_encode = payload.copy()

            # Add expiration time
            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)

            to_encode.update({
                'exp': expire,
                'iat': datetime.utcnow(),
                'iss': self.issuer,
            })

            # Add audience if configured
            if self.audience:
                to_encode['aud'] = self.audience

            # Encode token
            signing_key = self._get_signing_key()
            encoded_jwt = jwt.encode(to_encode, signing_key, algorithm=self.algorithm)

            return encoded_jwt

        except Exception as e:
            raise RuntimeError(f"Failed to create JWT token: {e}")

    def create_access_token(self, subject: str, additional_claims: Optional[Dict[str, Any]] = None) -> str:
        """
        Create an access token with standard claims.

        Args:
            subject: Subject (user ID, username, etc.)
            additional_claims: Optional additional claims to include

        Returns:
            Encoded access token
        """
        payload = {'sub': subject, 'type': 'access'}

        if additional_claims:
            payload.update(additional_claims)

        expires_delta = timedelta(minutes=self.access_token_expire_minutes)
        return self.create_token(payload, expires_delta)

    def create_refresh_token(self, subject: str, additional_claims: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a refresh token with extended expiration.

        Args:
            subject: Subject (user ID, username, etc.)
            additional_claims: Optional additional claims to include

        Returns:
            Encoded refresh token
        """
        payload = {'sub': subject, 'type': 'refresh'}

        if additional_claims:
            payload.update(additional_claims)

        expires_delta = timedelta(days=self.refresh_token_expire_days)
        return self.create_token(payload, expires_delta)

    def verify_token(self, token: str, verify_exp: bool = True, audience: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string
            verify_exp: Whether to verify expiration
            audience: Optional audience to verify

        Returns:
            Decoded token payload

        Raises:
            jwt.ExpiredSignatureError: If token is expired
            jwt.InvalidTokenError: If token is invalid
        """
        try:
            verification_key = self._get_verification_key()

            # Build verification options
            options = {
                'verify_signature': True,
                'verify_exp': verify_exp,
                'verify_nbf': True,
                'verify_iat': True,
                'verify_aud': bool(audience or self.audience),
                'require_exp': True,
                'require_iat': True,
            }

            # Decode and verify token
            decoded = jwt.decode(
                token,
                verification_key,
                algorithms=[self.algorithm],
                audience=audience or self.audience,
                issuer=self.issuer,
                options=options
            )

            return decoded

        except jwt.ExpiredSignatureError:
            raise RuntimeError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise RuntimeError(f"Invalid token: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to verify token: {e}")

    def decode_token(self, token: str, verify: bool = False) -> Dict[str, Any]:
        """
        Decode a JWT token without verification (unsafe for production).

        Args:
            token: JWT token string
            verify: Whether to verify signature (default: False)

        Returns:
            Decoded token payload
        """
        try:
            options = {
                'verify_signature': verify,
                'verify_exp': False,
                'verify_nbf': False,
                'verify_iat': False,
                'verify_aud': False,
            }

            if verify:
                verification_key = self._get_verification_key()
                decoded = jwt.decode(token, verification_key, algorithms=[self.algorithm], options=options)
            else:
                decoded = jwt.decode(token, options={'verify_signature': False}, algorithms=[self.algorithm])

            return decoded

        except Exception as e:
            raise RuntimeError(f"Failed to decode token: {e}")

    def refresh_access_token(self, refresh_token: str) -> str:
        """
        Create a new access token from a valid refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New access token
        """
        try:
            # Verify refresh token
            payload = self.verify_token(refresh_token)

            # Validate token type
            if payload.get('type') != 'refresh':
                raise RuntimeError("Invalid token type: expected refresh token")

            # Get subject
            subject = payload.get('sub')
            if not subject:
                raise RuntimeError("Refresh token missing subject claim")

            # Extract additional claims (excluding standard JWT claims)
            additional_claims = {
                k: v for k, v in payload.items()
                if k not in ['sub', 'type', 'exp', 'iat', 'nbf', 'iss', 'aud', 'jti']
            }

            # Create new access token
            return self.create_access_token(subject, additional_claims)

        except Exception as e:
            raise RuntimeError(f"Failed to refresh access token: {e}")

    def get_token_claims(self, token: str) -> Dict[str, Any]:
        """
        Get all claims from a token without verification.

        Args:
            token: JWT token string

        Returns:
            Dictionary of all claims
        """
        return self.decode_token(token, verify=False)

    def get_token_header(self, token: str) -> Dict[str, Any]:
        """
        Get the header from a JWT token.

        Args:
            token: JWT token string

        Returns:
            Dictionary of header claims (alg, typ, kid, etc.)
        """
        try:
            header = jwt.get_unverified_header(token)
            return header
        except Exception as e:
            raise RuntimeError(f"Failed to get token header: {e}")

    def is_token_expired(self, token: str) -> bool:
        """
        Check if a token is expired without full verification.

        Args:
            token: JWT token string

        Returns:
            True if expired, False otherwise
        """
        try:
            payload = self.decode_token(token, verify=False)
            exp = payload.get('exp')

            if exp is None:
                return False

            return datetime.fromtimestamp(exp) < datetime.utcnow()

        except Exception:
            return True

    def get_token_expiration(self, token: str) -> Optional[datetime]:
        """
        Get the expiration time of a token.

        Args:
            token: JWT token string

        Returns:
            Expiration datetime or None if no expiration
        """
        try:
            payload = self.decode_token(token, verify=False)
            exp = payload.get('exp')

            if exp:
                return datetime.fromtimestamp(exp)

            return None

        except Exception as e:
            raise RuntimeError(f"Failed to get token expiration: {e}")

    def validate_token_structure(self, token: str) -> bool:
        """
        Validate that a token has the correct JWT structure.

        Args:
            token: JWT token string

        Returns:
            True if valid structure, False otherwise
        """
        try:
            parts = token.split('.')
            return len(parts) == 3
        except Exception:
            return False

    def create_token_pair(self, subject: str, additional_claims: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        Create both access and refresh tokens.

        Args:
            subject: Subject (user ID, username, etc.)
            additional_claims: Optional additional claims to include

        Returns:
            Dictionary with 'access_token' and 'refresh_token'
        """
        return {
            'access_token': self.create_access_token(subject, additional_claims),
            'refresh_token': self.create_refresh_token(subject, additional_claims)
        }

    def blacklist_check(self, token: str, blacklist: set) -> bool:
        """
        Check if a token's JTI (JWT ID) is in a blacklist.

        Args:
            token: JWT token string
            blacklist: Set of blacklisted JTI values

        Returns:
            True if blacklisted, False otherwise
        """
        try:
            payload = self.decode_token(token, verify=False)
            jti = payload.get('jti')

            if jti:
                return jti in blacklist

            return False

        except Exception:
            return True  # Consider invalid tokens as blacklisted

    def close(self):
        """Close JWT module and cleanup resources."""
        self._private_key = None
        self._public_key = None

    @classmethod
    def get_metadata(cls):
        """Get module metadata."""
        from nl2py.modules.module_base import ModuleMetadata
        return ModuleMetadata(
            name="JWT",
            task_type="jwt",
            description="JSON Web Token creation, verification, and management with support for symmetric and asymmetric algorithms",
            version="1.0.0",
            keywords=["jwt", "token", "authentication", "authorization", "security", "oauth", "access-token", "refresh-token", "claims"],
            dependencies=[
                "PyJWT[crypto]>=2.8.0",
                "cryptography>=41.0.0"
            ]
        )

    @classmethod
    def get_usage_notes(cls):
        """Get detailed usage notes."""
        return [
            "Module uses singleton pattern - one instance shared across operations",
            "Supports symmetric algorithms (HS256, HS384, HS512) with secret key",
            "Supports asymmetric algorithms (RS256, RS384, RS512, ES256, ES384, ES512) with RSA/ECDSA keys",
            "Default algorithm is HS256 - change in config for production use",
            "Secret key should be strong and kept secure - use environment variables in production",
            "Access tokens typically expire in 15 minutes (configurable)",
            "Refresh tokens typically expire in 7 days (configurable)",
            "Tokens include standard claims: iss (issuer), aud (audience), exp (expiration), iat (issued at), sub (subject)",
            "Asymmetric algorithms require private key for signing, public key for verification",
            "Private/public keys loaded lazily from PEM files specified in config",
            "Token verification checks signature, expiration, issuer, and audience by default",
            "decode_token() can read payload without verification (useful for debugging, unsafe for auth)",
            "Refresh tokens should be stored securely and used only to obtain new access tokens",
            "Token blacklisting requires external storage (Redis, database) to track revoked JTI values",
            "is_token_expired() checks expiration without full verification",
            "create_token_pair() generates both access and refresh tokens in one call",
            "Key methods: create_access_token, create_refresh_token, verify_token, refresh_access_token, decode_token"
        ]

    @classmethod
    def get_methods_info(cls):
        """Get information about module methods."""
        from nl2py.modules.module_base import MethodInfo
        return [
            MethodInfo(
                name="create_token",
                description="Create a JWT token with custom payload and expiration",
                parameters={
                    "payload": "Dictionary of claims to include in token",
                    "expires_delta": "Optional timedelta for custom expiration (overrides default)"
                },
                returns="Encoded JWT token string",
                examples=[
                    {"text": "Create token with payload user_id {{123}} and role {{admin}}", "code": "create_token(payload={{'user_id': {{123}}, 'role': '{{admin}}'}})"},
                    {"text": "Create token with subject {{user@example.com}} expires in {{30}} minutes", "code": "create_token(payload={{'sub': '{{user@example.com}}'}}, expires_delta=timedelta(minutes={{30}}))"},
                ]
            ),
            MethodInfo(
                name="create_access_token",
                description="Create a short-lived access token for API authentication",
                parameters={
                    "subject": "Subject identifier (user ID, username, email, etc.)",
                    "additional_claims": "Optional dict of extra claims to include (e.g., roles, permissions)"
                },
                returns="Encoded access token string with 'access' type and default expiration",
                examples=[
                    {"text": "Create access token for subject {{user123}}", "code": "create_access_token(subject='{{user123}}')"},
                    {"text": "Create access token for {{user@example.com}} with role {{admin}} and permissions {{read}}, {{write}}", "code": "create_access_token(subject='{{user@example.com}}', additional_claims={{'role': '{{admin}}', 'permissions': ['{{read}}', '{{write}}']}})"},
                ]
            ),
            MethodInfo(
                name="create_refresh_token",
                description="Create a long-lived refresh token for obtaining new access tokens",
                parameters={
                    "subject": "Subject identifier (user ID, username, email, etc.)",
                    "additional_claims": "Optional dict of extra claims to include"
                },
                returns="Encoded refresh token string with 'refresh' type and extended expiration",
                examples=[
                    {"text": "Create refresh token for subject {{user123}}", "code": "create_refresh_token(subject='{{user123}}')"},
                    {"text": "Create refresh token for {{user@example.com}} with device {{mobile}}", "code": "create_refresh_token(subject='{{user@example.com}}', additional_claims={{'device': '{{mobile}}'}})"},
                ]
            ),
            MethodInfo(
                name="verify_token",
                description="Verify JWT signature and validate all claims including expiration",
                parameters={
                    "token": "JWT token string to verify",
                    "verify_exp": "Whether to check expiration (default: True)",
                    "audience": "Expected audience value to verify (optional, uses config default)"
                },
                returns="Decoded payload dictionary if valid",
                examples=[
                    {"text": "Verify JWT token {{eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...}}", "code": "verify_token(token='{{eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...}}')"},
                    {"text": "Verify token {{eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...}} with audience {{api.example.com}}", "code": "verify_token(token='{{eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...}}', audience='{{api.example.com}}')"},
                    {"text": "Verify token {{eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...}} without expiration check", "code": "verify_token(token='{{eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...}}', verify_exp=False)"},
                ]
            ),
            MethodInfo(
                name="decode_token",
                description="Decode token payload without verification (unsafe for authentication)",
                parameters={
                    "token": "JWT token string to decode",
                    "verify": "Whether to verify signature (default: False)"
                },
                returns="Decoded payload dictionary",
                examples=[
                    {"text": "Decode JWT token {{eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...}}", "code": "decode_token(token='{{eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...}}')"},
                    {"text": "Decode token {{eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...}} without verification", "code": "decode_token(token='{{eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...}}', verify=False)"},
                ]
            ),
            MethodInfo(
                name="refresh_access_token",
                description="Generate new access token from valid refresh token",
                parameters={
                    "refresh_token": "Valid refresh token string"
                },
                returns="New access token with same subject and additional claims",
                examples=[
                    {"text": "Refresh access token using refresh token {{eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...}}", "code": "refresh_access_token(refresh_token='{{eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...}}')"},
                ]
            ),
            MethodInfo(
                name="create_token_pair",
                description="Create both access and refresh tokens simultaneously",
                parameters={
                    "subject": "Subject identifier (user ID, username, email, etc.)",
                    "additional_claims": "Optional dict of extra claims for both tokens"
                },
                returns="Dictionary with 'access_token' and 'refresh_token' keys",
                examples=[
                    {"text": "Create access and refresh token pair for subject {{user123}}", "code": "create_token_pair(subject='{{user123}}')"},
                    {"text": "Create token pair for {{user@example.com}} with role {{admin}}", "code": "create_token_pair(subject='{{user@example.com}}', additional_claims={{'role': '{{admin}}'}})"},
                ]
            ),
            MethodInfo(
                name="get_token_claims",
                description="Extract all claims from token without verification",
                parameters={
                    "token": "JWT token string"
                },
                returns="Dictionary of all claims (sub, exp, iat, iss, aud, custom claims)",
                examples=[
                    {"text": "Get all claims from token {{eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...}}", "code": "get_token_claims(token='{{eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...}}')"},
                ]
            ),
            MethodInfo(
                name="get_token_header",
                description="Extract header information from token (algorithm, type, key ID)",
                parameters={
                    "token": "JWT token string"
                },
                returns="Dictionary with header fields (alg, typ, kid if present)",
                examples=[
                    {"text": "Get header (algorithm, type) from token {{eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...}}", "code": "get_token_header(token='{{eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...}}')"},
                ]
            ),
            MethodInfo(
                name="is_token_expired",
                description="Check if token is expired without full verification",
                parameters={
                    "token": "JWT token string"
                },
                returns="Boolean: True if expired, False if still valid",
                examples=[
                    {"text": "Check if token {{eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...}} is expired", "code": "is_token_expired(token='{{eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...}}')"},
                ]
            ),
            MethodInfo(
                name="get_token_expiration",
                description="Get expiration datetime of a token",
                parameters={
                    "token": "JWT token string"
                },
                returns="Datetime object representing expiration time, or None if no expiration",
                examples=[
                    {"text": "Get expiration datetime of token {{eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...}}", "code": "get_token_expiration(token='{{eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...}}')"},
                ]
            ),
            MethodInfo(
                name="validate_token_structure",
                description="Validate JWT structure (three base64 parts separated by dots)",
                parameters={
                    "token": "Token string to validate"
                },
                returns="Boolean: True if valid JWT structure, False otherwise",
                examples=[
                    {"text": "Validate structure of token {{eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...}}", "code": "validate_token_structure(token='{{eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...}}')"},
                ]
            ),
            MethodInfo(
                name="blacklist_check",
                description="Check if token's JTI (JWT ID) is in a blacklist set",
                parameters={
                    "token": "JWT token string",
                    "blacklist": "Set of blacklisted JTI values"
                },
                returns="Boolean: True if blacklisted, False otherwise",
                examples=[
                    {"text": "Check if token {{eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...}} is in blacklist {{jti_blacklist_set}}", "code": "blacklist_check(token='{{eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...}}', blacklist={{jti_blacklist_set}})"},
                    {"text": "Check if token {{eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...}} is blacklisted in {{revoked_tokens}}", "code": "blacklist_check(token='{{eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...}}', blacklist={{revoked_tokens}})"},
                ]
            ),
        ]

# Module metadata
__all__ = ['JWTModule']
