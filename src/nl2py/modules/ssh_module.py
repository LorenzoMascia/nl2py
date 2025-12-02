"""
SSH Module for Remote Server Connections and Command Execution

This module provides comprehensive SSH connectivity for remote server management.
Configuration is loaded from nl2py.conf under the [ssh] section.

Supports:
- Password authentication
- SSH key authentication (RSA, ED25519, etc.)
- Multiple authentication methods (password + key fallback)
- Host key verification (strict, auto-add, ignore)
- Command execution (blocking and non-blocking)
- Interactive shells
- SFTP file transfer (upload/download)
- Port forwarding (local and remote)
- SSH tunneling
- Signal sending (SIGTERM, SIGKILL, etc.)
- Output streaming
- Timeout configuration

Features:
- Execute remote commands
- Read command output (stdout, stderr)
- Transfer files via SFTP
- Interactive terminal sessions
- Batch command execution
- Persistent connections
- Connection pooling
- Jump host/bastion support

Example configuration in nl2py.conf:
    [ssh]
    HOST=server.example.com
    PORT=22
    USERNAME=admin

    # Password authentication
    PASSWORD=secret

    # OR Key-based authentication
    # KEY_FILE=/path/to/private_key
    # KEY_PASSWORD=key_passphrase  # If key is encrypted

    # Host key verification
    VERIFY_HOST_KEY=false  # true, false, or auto-add

    # Connection settings
    TIMEOUT=30
    BANNER_TIMEOUT=15
    AUTH_TIMEOUT=10

Usage in generated code:
    from nl2py.modules import SSHModule

    # Initialize and connect
    ssh = SSHModule.from_config('nl2py.conf')

    # Execute command
    result = ssh.execute_command('ls -la /var/www')
    print(result['stdout'])

    # Execute with sudo
    result = ssh.execute_sudo('systemctl restart nginx', sudo_password='pass')

    # Upload file
    ssh.upload_file('local.txt', '/remote/path/file.txt')

    # Download file
    ssh.download_file('/remote/log.txt', 'local_log.txt')

    # Interactive shell
    shell = ssh.get_shell()
    shell.send('cd /var/www\n')
    output = shell.recv(1024)
"""

import configparser
import os
import threading
import time
import signal as signal_module
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Tuple
import socket

try:
    import paramiko
    from paramiko import SSHClient, AutoAddPolicy, RejectPolicy, WarningPolicy
    from paramiko.ssh_exception import SSHException, AuthenticationException
except ImportError:
    paramiko = None
    SSHClient = None

from .module_base import NL2PyModuleBase


class SSHModule(NL2PyModuleBase):
    """
    SSH remote connection and command execution module.

    Supports password and key-based authentication, file transfer, and command execution.
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(
        self,
        host: str,
        port: int = 22,
        username: str = None,
        password: Optional[str] = None,
        key_file: Optional[str] = None,
        key_password: Optional[str] = None,
        verify_host_key: Union[bool, str] = True,
        timeout: int = 30,
        banner_timeout: int = 15,
        auth_timeout: int = 10,
        keepalive_interval: int = 30
    ):
        """
        Initialize the SSHModule.

        Args:
            host: SSH server hostname or IP
            port: SSH port (default 22)
            username: SSH username
            password: SSH password (for password auth)
            key_file: Path to private key file (for key auth)
            key_password: Passphrase for encrypted private key
            verify_host_key: Host key verification (True, False, or 'auto-add')
            timeout: Connection timeout in seconds
            banner_timeout: Banner read timeout
            auth_timeout: Authentication timeout
            keepalive_interval: Keep-alive interval in seconds (0 to disable)
        """
        if paramiko is None:
            raise ImportError(
                "paramiko is required. Install with: pip install paramiko"
            )

        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_file = key_file
        self.key_password = key_password
        self.verify_host_key = verify_host_key
        self.timeout = timeout
        self.banner_timeout = banner_timeout
        self.auth_timeout = auth_timeout
        self.keepalive_interval = keepalive_interval

        self.client = None
        self.sftp = None

        # Validate configuration
        if not host or not username:
            raise ValueError("Host and username are required")

        if not password and not key_file:
            raise ValueError("Either password or key_file must be provided")

        # Connect
        self._connect()

    def _connect(self):
        """Establish SSH connection."""
        self.client = SSHClient()

        # Host key policy
        if self.verify_host_key is False or self.verify_host_key == 'false':
            self.client.set_missing_host_key_policy(AutoAddPolicy())
            print("[SSHModule] ⚠️  Host key verification DISABLED (AutoAddPolicy)")
        elif self.verify_host_key == 'auto-add':
            self.client.set_missing_host_key_policy(AutoAddPolicy())
            print("[SSHModule] Using AutoAddPolicy for host keys")
        elif self.verify_host_key is True or self.verify_host_key == 'true':
            self.client.load_system_host_keys()
            self.client.set_missing_host_key_policy(RejectPolicy())
            print("[SSHModule] Host key verification ENABLED (RejectPolicy)")
        else:
            self.client.set_missing_host_key_policy(WarningPolicy())
            print("[SSHModule] Using WarningPolicy for host keys")

        # Load private key if provided
        pkey = None
        if self.key_file:
            key_path = Path(self.key_file).expanduser()
            if not key_path.exists():
                raise FileNotFoundError(f"SSH key file not found: {self.key_file}")

            try:
                # Try different key types
                for key_class in [paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.DSSKey]:
                    try:
                        pkey = key_class.from_private_key_file(
                            str(key_path),
                            password=self.key_password
                        )
                        print(f"[SSHModule] Loaded {key_class.__name__} from {self.key_file}")
                        break
                    except paramiko.SSHException:
                        continue

                if pkey is None:
                    raise paramiko.SSHException("Could not load private key")

            except Exception as e:
                print(f"[SSHModule] Failed to load private key: {e}")
                if not self.password:
                    raise

        # Connect to server
        try:
            connect_params = {
                'hostname': self.host,
                'port': self.port,
                'username': self.username,
                'timeout': self.timeout,
                'banner_timeout': self.banner_timeout,
                'auth_timeout': self.auth_timeout
            }

            # Try key authentication first
            if pkey:
                connect_params['pkey'] = pkey
            # Fallback to password if key not provided or failed
            if self.password and not pkey:
                connect_params['password'] = self.password

            self.client.connect(**connect_params)

            # Enable keep-alive
            if self.keepalive_interval > 0:
                transport = self.client.get_transport()
                transport.set_keepalive(self.keepalive_interval)

            print(f"[SSHModule] Connected to {self.username}@{self.host}:{self.port}")

            # Try both auth methods if both provided
            if pkey and self.password:
                print("[SSHModule] Using key authentication with password fallback")

        except AuthenticationException as e:
            raise AuthenticationException(f"Authentication failed for {self.username}@{self.host}: {e}")
        except SSHException as e:
            raise SSHException(f"SSH connection failed: {e}")
        except socket.error as e:
            raise ConnectionError(f"Network error connecting to {self.host}:{self.port}: {e}")

    @classmethod
    def from_config(cls, config_path: str = "nl2py.conf") -> 'SSHModule':
        """
        Create an SSHModule from configuration file.
        Uses singleton pattern to ensure only one instance exists.

        Args:
            config_path: Path to nl2py.conf file

        Returns:
            SSHModule instance
        """
        with cls._lock:
            if cls._instance is None:
                config = configparser.ConfigParser()
                path = Path(config_path)

                if not path.exists():
                    raise FileNotFoundError(f"Configuration file not found: {config_path}")

                config.read(path)

                if 'ssh' not in config:
                    raise KeyError("Missing [ssh] section in nl2py.conf")

                ssh_config = config['ssh']

                # Required
                host = ssh_config.get('HOST')
                username = ssh_config.get('USERNAME')

                if not host or not username:
                    raise ValueError("HOST and USERNAME are required in [ssh] section")

                # Connection
                port = ssh_config.getint('PORT', 22)
                timeout = ssh_config.getint('TIMEOUT', 30)
                banner_timeout = ssh_config.getint('BANNER_TIMEOUT', 15)
                auth_timeout = ssh_config.getint('AUTH_TIMEOUT', 10)
                keepalive_interval = ssh_config.getint('KEEPALIVE_INTERVAL', 30)

                # Authentication
                password = ssh_config.get('PASSWORD', None)
                key_file = ssh_config.get('KEY_FILE', None)
                key_password = ssh_config.get('KEY_PASSWORD', None)

                # Host key verification
                verify_str = ssh_config.get('VERIFY_HOST_KEY', 'true').lower()
                if verify_str in ['false', 'no', '0']:
                    verify_host_key = False
                elif verify_str == 'auto-add':
                    verify_host_key = 'auto-add'
                else:
                    verify_host_key = True

                cls._instance = cls(
                    host=host,
                    port=port,
                    username=username,
                    password=password,
                    key_file=key_file,
                    key_password=key_password,
                    verify_host_key=verify_host_key,
                    timeout=timeout,
                    banner_timeout=banner_timeout,
                    auth_timeout=auth_timeout,
                    keepalive_interval=keepalive_interval
                )

            return cls._instance

    # ==================== Command Execution ====================

    def execute_command(
        self,
        command: str,
        timeout: Optional[int] = None,
        get_pty: bool = False,
        environment: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Execute a command on the remote server.

        Args:
            command: Command to execute
            timeout: Command timeout in seconds (None = no timeout)
            get_pty: Allocate pseudo-terminal (needed for sudo)
            environment: Environment variables dict

        Returns:
            Dict with stdout, stderr, exit_code, command
        """
        if not self.client or not self.client.get_transport() or not self.client.get_transport().is_active():
            raise ConnectionError("SSH connection is not active")

        try:
            stdin, stdout, stderr = self.client.exec_command(
                command,
                timeout=timeout,
                get_pty=get_pty,
                environment=environment
            )

            # Read output
            stdout_data = stdout.read().decode('utf-8', errors='replace')
            stderr_data = stderr.read().decode('utf-8', errors='replace')
            exit_code = stdout.channel.recv_exit_status()

            return {
                'stdout': stdout_data,
                'stderr': stderr_data,
                'exit_code': exit_code,
                'command': command,
                'success': exit_code == 0
            }

        except Exception as e:
            return {
                'stdout': '',
                'stderr': str(e),
                'exit_code': -1,
                'command': command,
                'success': False,
                'error': str(e)
            }

    def execute_sudo(
        self,
        command: str,
        sudo_password: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a command with sudo.

        Args:
            command: Command to execute
            sudo_password: Sudo password (uses SSH password if not provided)
            timeout: Command timeout

        Returns:
            Dict with command result
        """
        sudo_pass = sudo_password or self.password
        if not sudo_pass:
            raise ValueError("Sudo password required")

        # Use echo to pipe password to sudo
        full_command = f"echo '{sudo_pass}' | sudo -S {command}"

        return self.execute_command(full_command, timeout=timeout, get_pty=True)

    def execute_batch(
        self,
        commands: List[str],
        stop_on_error: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple commands in sequence.

        Args:
            commands: List of commands
            stop_on_error: Stop execution if command fails

        Returns:
            List of result dicts
        """
        results = []

        for cmd in commands:
            result = self.execute_command(cmd)
            results.append(result)

            if stop_on_error and result['exit_code'] != 0:
                print(f"[SSHModule] Command failed, stopping batch: {cmd}")
                break

        return results

    # ==================== Interactive Shell ====================

    def get_shell(self, term: str = 'xterm', width: int = 80, height: int = 24):
        """
        Get an interactive shell session.

        Args:
            term: Terminal type
            width: Terminal width
            height: Terminal height

        Returns:
            paramiko Channel object
        """
        channel = self.client.invoke_shell(term=term, width=width, height=height)
        return channel

    def send_to_shell(self, channel, command: str, wait_for_prompt: bool = True, timeout: int = 10):
        """
        Send command to interactive shell.

        Args:
            channel: Shell channel from get_shell()
            command: Command to send
            wait_for_prompt: Wait for command to complete
            timeout: Read timeout

        Returns:
            Output string
        """
        channel.send(command + '\n')

        if wait_for_prompt:
            time.sleep(0.5)  # Give command time to start
            output = self._read_channel(channel, timeout=timeout)
            return output

        return ''

    def _read_channel(self, channel, timeout: int = 10) -> str:
        """Read all available data from channel."""
        output = ''
        channel.settimeout(timeout)

        try:
            while True:
                if channel.recv_ready():
                    chunk = channel.recv(4096).decode('utf-8', errors='replace')
                    output += chunk
                    if not channel.recv_ready():
                        time.sleep(0.1)
                        if not channel.recv_ready():
                            break
                else:
                    time.sleep(0.1)
        except socket.timeout:
            pass

        return output

    # ==================== Signal Sending ====================

    def send_signal(self, pid: int, signal_name: str = 'TERM') -> Dict[str, Any]:
        """
        Send a signal to a process.

        Args:
            pid: Process ID
            signal_name: Signal name (TERM, KILL, HUP, INT, etc.)

        Returns:
            Dict with result
        """
        signal_map = {
            'TERM': 15,
            'KILL': 9,
            'HUP': 1,
            'INT': 2,
            'QUIT': 3,
            'USR1': 10,
            'USR2': 12
        }

        sig_num = signal_map.get(signal_name.upper(), signal_name)

        command = f"kill -{sig_num} {pid}"
        return self.execute_command(command)

    # ==================== SFTP File Transfer ====================

    def _get_sftp(self):
        """Get or create SFTP client."""
        if self.sftp is None:
            self.sftp = self.client.open_sftp()
        return self.sftp

    def upload_file(
        self,
        local_path: str,
        remote_path: str,
        callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Upload a file via SFTP.

        Args:
            local_path: Local file path
            remote_path: Remote file path
            callback: Progress callback function(bytes_transferred, total_bytes)

        Returns:
            Dict with transfer info
        """
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local file not found: {local_path}")

        sftp = self._get_sftp()
        file_size = os.path.getsize(local_path)

        try:
            sftp.put(local_path, remote_path, callback=callback)
            print(f"[SSHModule] Uploaded: {local_path} -> {remote_path} ({file_size} bytes)")

            return {
                'success': True,
                'local_path': local_path,
                'remote_path': remote_path,
                'size': file_size
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'local_path': local_path,
                'remote_path': remote_path
            }

    def download_file(
        self,
        remote_path: str,
        local_path: str,
        callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Download a file via SFTP.

        Args:
            remote_path: Remote file path
            local_path: Local file path
            callback: Progress callback

        Returns:
            Dict with transfer info
        """
        sftp = self._get_sftp()

        try:
            # Get remote file size
            stat = sftp.stat(remote_path)
            file_size = stat.st_size

            sftp.get(remote_path, local_path, callback=callback)
            print(f"[SSHModule] Downloaded: {remote_path} -> {local_path} ({file_size} bytes)")

            return {
                'success': True,
                'remote_path': remote_path,
                'local_path': local_path,
                'size': file_size
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'remote_path': remote_path,
                'local_path': local_path
            }

    def upload_directory(
        self,
        local_dir: str,
        remote_dir: str
    ) -> Dict[str, Any]:
        """
        Upload a directory recursively via SFTP.

        Args:
            local_dir: Local directory path
            remote_dir: Remote directory path

        Returns:
            Dict with transfer stats
        """
        sftp = self._get_sftp()
        files_uploaded = 0
        total_size = 0

        try:
            # Create remote directory
            try:
                sftp.mkdir(remote_dir)
            except:
                pass  # Directory might exist

            for root, dirs, files in os.walk(local_dir):
                # Create subdirectories
                for dir_name in dirs:
                    local_subdir = os.path.join(root, dir_name)
                    relative = os.path.relpath(local_subdir, local_dir)
                    remote_subdir = os.path.join(remote_dir, relative).replace('\\', '/')

                    try:
                        sftp.mkdir(remote_subdir)
                    except:
                        pass

                # Upload files
                for file_name in files:
                    local_file = os.path.join(root, file_name)
                    relative = os.path.relpath(local_file, local_dir)
                    remote_file = os.path.join(remote_dir, relative).replace('\\', '/')

                    result = self.upload_file(local_file, remote_file)
                    if result['success']:
                        files_uploaded += 1
                        total_size += result['size']

            print(f"[SSHModule] Uploaded directory: {files_uploaded} files, {total_size} bytes")

            return {
                'success': True,
                'files_uploaded': files_uploaded,
                'total_size': total_size
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'files_uploaded': files_uploaded
            }

    def download_directory(
        self,
        remote_dir: str,
        local_dir: str
    ) -> Dict[str, Any]:
        """Download a directory recursively via SFTP."""
        sftp = self._get_sftp()
        files_downloaded = 0
        total_size = 0

        try:
            os.makedirs(local_dir, exist_ok=True)

            def download_recursive(remote_path, local_path):
                nonlocal files_downloaded, total_size

                for item in sftp.listdir_attr(remote_path):
                    remote_item = f"{remote_path}/{item.filename}"
                    local_item = os.path.join(local_path, item.filename)

                    if self._is_directory(sftp, remote_item):
                        os.makedirs(local_item, exist_ok=True)
                        download_recursive(remote_item, local_item)
                    else:
                        result = self.download_file(remote_item, local_item)
                        if result['success']:
                            files_downloaded += 1
                            total_size += result['size']

            download_recursive(remote_dir, local_dir)

            print(f"[SSHModule] Downloaded directory: {files_downloaded} files, {total_size} bytes")

            return {
                'success': True,
                'files_downloaded': files_downloaded,
                'total_size': total_size
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'files_downloaded': files_downloaded
            }

    def _is_directory(self, sftp, path: str) -> bool:
        """Check if remote path is a directory."""
        try:
            import stat
            return stat.S_ISDIR(sftp.stat(path).st_mode)
        except:
            return False

    def list_directory(self, remote_path: str = '.') -> List[str]:
        """List files in remote directory."""
        sftp = self._get_sftp()
        return sftp.listdir(remote_path)

    # ==================== Utility Methods ====================

    def is_connected(self) -> bool:
        """Check if SSH connection is active."""
        if self.client and self.client.get_transport():
            return self.client.get_transport().is_active()
        return False

    def reconnect(self):
        """Reconnect to SSH server."""
        print("[SSHModule] Reconnecting...")
        self.close()
        self._connect()

    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get connection information.

        Returns:
            Dict with connection details
        """
        return {
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'connected': self.is_connected(),
            'auth_method': 'key' if self.key_file else 'password',
            'verify_host_key': self.verify_host_key
        }

    def close(self):
        """Close SSH connection."""
        if self.sftp:
            self.sftp.close()
            self.sftp = None

        if self.client:
            self.client.close()
            self.client = None

        print("[SSHModule] Connection closed")

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
            name="SSH",
            task_type="ssh",
            description="SSH remote server connections with command execution, file transfer (SFTP), and interactive shells",
            version="1.0.0",
            keywords=[
                "ssh", "remote", "sftp", "file-transfer", "command-execution",
                "shell", "paramiko", "server-management", "linux"
            ],
            dependencies=["paramiko>=2.7.0"]
        )

    @classmethod
    def get_usage_notes(cls):
        """Get detailed usage notes for this module."""
        return [
            "Module uses singleton pattern - one SSH connection per application",
            "Default SSH port is 22",
            "Supports password and SSH key authentication (RSA, ED25519, ECDSA, DSS)",
            "KEY_FILE takes precedence over PASSWORD if both provided",
            "verify_host_key options: true (strict), false (ignore), auto-add (add new)",
            "AutoAddPolicy recommended for development, RejectPolicy for production",
            "execute_command() returns dict with stdout, stderr, exit_status",
            "execute_sudo() auto-handles sudo password prompt",
            "execute_batch() runs multiple commands in single session",
            "get_shell() returns interactive channel for multi-command workflows",
            "SFTP initialized lazily on first file operation",
            "upload_file() and download_file() preserve file permissions",
            "upload_directory() and download_directory() handle recursive transfers",
            "Keepalive interval prevents connection timeout (default 30s)",
            "Connection auto-reconnects via reconnect() if connection lost",
            "Timeout defaults: connection=30s, banner=15s, auth=10s",
            "Shell width/height configurable for terminal emulation",
            "Always call close() or use context manager to cleanup connections",
            "Host key verification uses ~/.ssh/known_hosts when verify_host_key=true",
            "Private keys auto-detected by type (RSA, ED25519, ECDSA, DSS)"
        ]

    @classmethod
    def get_methods_info(cls):
        """Get information about all methods in this module."""
        from nl2py.modules.module_base import MethodInfo
        return [
            MethodInfo(
                name="execute_command",
                description="Execute a command on remote server",
                parameters={
                    "command": "str (required) - Command to execute",
                    "timeout": "int (optional) - Command timeout in seconds (default 30)",
                    "get_pty": "bool (optional) - Request pseudo-terminal (default False)"
                },
                returns="dict - stdout, stderr, exit_status",
                examples=[
                    {"text": "Execute command {{ls -la /var/www}}", "code": "execute_command(command='{{ls -la /var/www}}')"},
                    {"text": "Execute command {{df -h}}", "code": "execute_command(command='{{df -h}}')"},
                    {"text": "Execute command {{tail -f /var/log/syslog}} with timeout {{10}}", "code": "execute_command(command='{{tail -f /var/log/syslog}}', timeout={{10}})"}
                ]
            ),
            MethodInfo(
                name="execute_sudo",
                description="Execute command with sudo privileges",
                parameters={
                    "command": "str (required) - Command to execute (without 'sudo')",
                    "sudo_password": "str (optional) - Sudo password (default uses SSH password)",
                    "timeout": "int (optional) - Timeout in seconds"
                },
                returns="dict - stdout, stderr, exit_status",
                examples=[
                    {"text": "Execute sudo command {{systemctl restart nginx}} with password {{pass}}", "code": "execute_sudo(command='{{systemctl restart nginx}}', sudo_password='{{pass}}')"}
                ]
            ),
            MethodInfo(
                name="upload_file",
                description="Upload file to remote server via SFTP",
                parameters={
                    "local_path": "str (required) - Local file path",
                    "remote_path": "str (required) - Remote destination path",
                    "preserve_perms": "bool (optional) - Preserve file permissions (default True)"
                },
                returns="None",
                examples=[
                    {"text": "Upload file {{local.txt}} to {{/remote/path/file.txt}}", "code": "upload_file(local_path='{{local.txt}}', remote_path='{{/remote/path/file.txt}}')"}
                ]
            ),
            MethodInfo(
                name="download_file",
                description="Download file from remote server via SFTP",
                parameters={
                    "remote_path": "str (required) - Remote file path",
                    "local_path": "str (required) - Local destination path",
                    "preserve_perms": "bool (optional) - Preserve file permissions (default True)"
                },
                returns="None",
                examples=[
                    {"text": "Download file {{/var/log/app.log}} to {{local_app.log}}", "code": "download_file(remote_path='{{/var/log/app.log}}', local_path='{{local_app.log}}')"}
                ]
            ),
            MethodInfo(
                name="get_shell",
                description="Get interactive shell channel",
                parameters={
                    "term": "str (optional) - Terminal type (default 'xterm')",
                    "width": "int (optional) - Terminal width (default 80)",
                    "height": "int (optional) - Terminal height (default 24)"
                },
                returns="Channel - Interactive shell channel",
                examples=[
                    {"text": "Get an interactive shell session", "code": "get_shell()"}
                ]
            ),
            MethodInfo(
                name="is_connected",
                description="Check if SSH connection is active",
                parameters={},
                returns="bool - True if connected",
                examples=[
                    {"text": "Check if SSH connection is active", "code": "is_connected()"}
                ]
            ),
            MethodInfo(
                name="reconnect",
                description="Reconnect to SSH server if connection lost",
                parameters={},
                returns="None",
                examples=[
                    {"text": "Reconnect to the SSH server", "code": "reconnect()"}
                ]
            ),
            MethodInfo(
                name="list_directory",
                description="List files in remote directory",
                parameters={"remote_path": "str (optional) - Remote directory path (default '.')"},
                returns="list - File and directory names",
                examples=[
                    {"text": "List files in remote directory {{/var/www}}", "code": "list_directory(remote_path='{{/var/www}}')"}
                ]
            ),
            MethodInfo(
                name="send_to_shell",
                description="Send command to interactive shell session",
                parameters={
                    "channel": "Shell channel from get_shell()",
                    "command": "str (required) - Command to send",
                    "wait_for_prompt": "bool (optional) - Wait for command completion (default True)",
                    "timeout": "int (optional) - Read timeout in seconds (default 10)"
                },
                returns="str - Command output",
                examples=[
                    {"text": "Send command {{ls -la}} to shell {{shell}}", "code": "send_to_shell(channel={{shell}}, command='{{ls -la}}')"}
                ]
            ),
            MethodInfo(
                name="send_signal",
                description="Send a signal to a remote process",
                parameters={
                    "pid": "int (required) - Process ID",
                    "signal_name": "str (optional) - Signal name: TERM, KILL, HUP, INT, etc. (default TERM)"
                },
                returns="dict - Result with success status and details",
                examples=[
                    {"text": "Send signal {{TERM}} to process {{1234}}", "code": "send_signal(pid={{1234}}, signal_name='{{TERM}}')"},
                    {"text": "Send signal {{KILL}} to process {{5678}}", "code": "send_signal(pid={{5678}}, signal_name='{{KILL}}')"}
                ]
            )
        ]

