"""
Terraform Module for Infrastructure as Code (IaC)

This module provides comprehensive integration with HashiCorp Terraform,
enabling infrastructure provisioning, management, and automation through
Python. It supports all major cloud providers (AWS, Azure, GCP, etc.) and
on-premises infrastructure.

Configuration is loaded from nl2py.conf under the [terraform] section.

Features:
- Initialize Terraform working directory
- Plan infrastructure changes (dry-run)
- Apply infrastructure changes
- Destroy infrastructure
- Import existing resources
- Workspace management (dev, staging, prod)
- State management and locking
- Variable management
- Output retrieval
- Module usage
- Provider configuration

Supports:
- AWS, Azure, GCP, DigitalOcean, and 2000+ providers
- Terraform Cloud and Terraform Enterprise
- Local and remote state backends (S3, Azure Storage, GCS, etc.)
- Multiple workspaces for environment isolation
- Complex infrastructure dependencies
- Terraform modules (reusable components)

Example configuration in nl2py.conf:
    [terraform]
    # Working Directory
    WORKING_DIR = /path/to/terraform/project

    # Terraform Binary Path (optional, uses PATH if not specified)
    # TERRAFORM_BIN = /usr/local/bin/terraform

    # Backend Configuration (optional)
    # BACKEND_TYPE = s3
    # BACKEND_CONFIG = {"bucket": "my-tf-state", "key": "terraform.tfstate", "region": "us-east-1"}

    # Default Workspace
    # DEFAULT_WORKSPACE = default

    # Variables (optional)
    # VARIABLES = {"environment": "dev", "instance_type": "t2.micro"}

    # Auto Approve (use with caution!)
    # AUTO_APPROVE = false

    # Parallelism (number of concurrent operations)
    # PARALLELISM = 10

Example usage:
    from nl2py.modules import TerraformModule

    # Initialize from config
    tf = TerraformModule.from_config('nl2py.conf')

    # Initialize Terraform
    tf.init()

    # Plan changes
    plan_result = tf.plan(variables={'environment': 'production'})

    # Apply changes
    apply_result = tf.apply(variables={'environment': 'production'})

    # Get outputs
    outputs = tf.output()
    print(f"Server IP: {outputs['server_ip']}")

    # Destroy infrastructure
    tf.destroy(auto_approve=True)
"""

import configparser
import threading
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
import subprocess
import shutil
from .module_base import NL2PyModuleBase

try:
    from python_terraform import Terraform, IsFlagged, IsNotFlagged
except ImportError:
    Terraform = None
    IsFlagged = None
    IsNotFlagged = None


class TerraformModule(NL2PyModuleBase):
    """
    Terraform Module for Infrastructure as Code management.

    Provides Python interface to Terraform CLI for provisioning and managing
    cloud and on-premises infrastructure across multiple providers.
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure only one Terraform instance per working directory."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        working_dir: str = '.',
        terraform_bin: Optional[str] = None,
        backend_type: Optional[str] = None,
        backend_config: Optional[Dict[str, Any]] = None,
        default_workspace: str = 'default',
        variables: Optional[Dict[str, Any]] = None,
        auto_approve: bool = False,
        parallelism: int = 10,
        **kwargs
    ):
        """
        Initialize Terraform Module.

        Args:
            working_dir: Terraform working directory (contains .tf files)
            terraform_bin: Path to terraform binary (optional, uses PATH)
            backend_type: Backend type (s3, azurerm, gcs, local, etc.)
            backend_config: Backend configuration dict
            default_workspace: Default workspace name
            variables: Default variables dict
            auto_approve: Auto-approve applies/destroys (use with caution!)
            parallelism: Number of concurrent operations (default: 10)
        """
        if self._initialized:
            return

        if Terraform is None:
            raise ImportError(
                "python-terraform library is required for Terraform module. "
                "Install it with: pip install python-terraform"
            )

        with self._lock:
            if self._initialized:
                return

            self.working_dir = os.path.abspath(working_dir)
            self.terraform_bin = terraform_bin
            self.backend_type = backend_type
            self.backend_config = backend_config or {}
            self.default_workspace = default_workspace
            self.default_variables = variables or {}
            self.auto_approve = auto_approve
            self.parallelism = parallelism

            # Verify Terraform is installed
            if not self._verify_terraform_installed():
                raise RuntimeError(
                    "Terraform is not installed or not in PATH. "
                    "Download from: https://www.terraform.io/downloads"
                )

            # Initialize Terraform object
            if terraform_bin:
                self.tf = Terraform(working_dir=self.working_dir, terraform_bin_path=terraform_bin)
            else:
                self.tf = Terraform(working_dir=self.working_dir)

            # Track initialization state
            self._is_initialized = False
            self._current_workspace = None

            self._initialized = True

    def _verify_terraform_installed(self) -> bool:
        """Verify Terraform is installed."""
        try:
            if self.terraform_bin:
                result = subprocess.run(
                    [self.terraform_bin, 'version'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            else:
                result = subprocess.run(
                    ['terraform', 'version'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def get_version(self) -> str:
        """Get Terraform version."""
        try:
            if self.terraform_bin:
                result = subprocess.run(
                    [self.terraform_bin, 'version'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            else:
                result = subprocess.run(
                    ['terraform', 'version'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

            if result.returncode == 0:
                # Extract version from output
                version_line = result.stdout.split('\n')[0]
                return version_line.replace('Terraform v', '')
            return 'unknown'
        except Exception:
            return 'unknown'

    @classmethod
    def from_config(cls, config_path: str, section: str = 'terraform') -> 'TerraformModule':
        """
        Create TerraformModule instance from configuration file.

        Args:
            config_path: Path to configuration file
            section: Configuration section name (default: 'terraform')

        Returns:
            TerraformModule instance
        """
        config = configparser.ConfigParser()
        config.read(config_path)

        if section not in config:
            raise ValueError(f"Section [{section}] not found in {config_path}")

        cfg = config[section]

        # Parse backend config JSON if provided
        backend_config = None
        if 'BACKEND_CONFIG' in cfg:
            try:
                backend_config = json.loads(cfg['BACKEND_CONFIG'])
            except json.JSONDecodeError:
                backend_config = None

        # Parse variables JSON if provided
        variables = None
        if 'VARIABLES' in cfg:
            try:
                variables = json.loads(cfg['VARIABLES'])
            except json.JSONDecodeError:
                variables = None

        # Build initialization parameters
        init_params = {
            'working_dir': cfg.get('WORKING_DIR', '.'),
            'terraform_bin': cfg.get('TERRAFORM_BIN', None),
            'backend_type': cfg.get('BACKEND_TYPE', None),
            'backend_config': backend_config,
            'default_workspace': cfg.get('DEFAULT_WORKSPACE', 'default'),
            'variables': variables,
            'auto_approve': cfg.getboolean('AUTO_APPROVE', False),
            'parallelism': cfg.getint('PARALLELISM', 10)
        }

        # Remove None values
        init_params = {k: v for k, v in init_params.items() if v is not None}

        return cls(**init_params)

    def init(
        self,
        backend: bool = True,
        reconfigure: bool = False,
        upgrade: bool = False,
        plugin_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Initialize Terraform working directory.

        Args:
            backend: Configure backend (default: True)
            reconfigure: Reconfigure backend (ignore saved config)
            upgrade: Upgrade modules and plugins
            plugin_dir: Directory containing plugin binaries

        Returns:
            Dict with return_code, stdout, stderr
        """
        init_kwargs = {}

        if not backend:
            init_kwargs['backend'] = False

        if reconfigure:
            init_kwargs['reconfigure'] = IsFlagged

        if upgrade:
            init_kwargs['upgrade'] = IsFlagged

        if plugin_dir:
            init_kwargs['plugin_dir'] = plugin_dir

        # Add backend config if provided
        if self.backend_config:
            init_kwargs['backend_config'] = self.backend_config

        return_code, stdout, stderr = self.tf.init(**init_kwargs)

        if return_code == 0:
            self._is_initialized = True

        return {
            'return_code': return_code,
            'stdout': stdout,
            'stderr': stderr,
            'success': return_code == 0
        }

    def plan(
        self,
        variables: Optional[Dict[str, Any]] = None,
        out: Optional[str] = None,
        destroy: bool = False,
        detailed_exitcode: bool = False
    ) -> Dict[str, Any]:
        """
        Create Terraform execution plan.

        Args:
            variables: Variables dict (merged with default_variables)
            out: Save plan to file
            destroy: Create destroy plan
            detailed_exitcode: Return detailed exit code (0=no changes, 1=error, 2=changes)

        Returns:
            Dict with return_code, stdout, stderr, has_changes
        """
        # Merge variables
        plan_vars = {**self.default_variables, **(variables or {})}

        plan_kwargs = {
            'var': plan_vars,
            'parallelism': self.parallelism
        }

        if out:
            plan_kwargs['out'] = out

        if destroy:
            plan_kwargs['destroy'] = IsFlagged

        if detailed_exitcode:
            plan_kwargs['detailed_exitcode'] = IsFlagged

        return_code, stdout, stderr = self.tf.plan(**plan_kwargs)

        # With detailed_exitcode: 0=no changes, 1=error, 2=has changes
        has_changes = return_code == 2 if detailed_exitcode else None

        return {
            'return_code': return_code,
            'stdout': stdout,
            'stderr': stderr,
            'success': return_code in [0, 2] if detailed_exitcode else return_code == 0,
            'has_changes': has_changes
        }

    def apply(
        self,
        variables: Optional[Dict[str, Any]] = None,
        plan_file: Optional[str] = None,
        auto_approve: Optional[bool] = None,
        target: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Apply Terraform changes.

        Args:
            variables: Variables dict (merged with default_variables)
            plan_file: Apply specific plan file
            auto_approve: Auto-approve (overrides default)
            target: Apply only to specific resources

        Returns:
            Dict with return_code, stdout, stderr
        """
        # Merge variables
        apply_vars = {**self.default_variables, **(variables or {})}

        apply_kwargs = {
            'var': apply_vars,
            'parallelism': self.parallelism
        }

        # Auto-approve
        if auto_approve is None:
            auto_approve = self.auto_approve

        if auto_approve:
            apply_kwargs['auto_approve'] = IsFlagged

        # Plan file
        if plan_file:
            apply_kwargs['dir_or_plan'] = plan_file

        # Targets
        if target:
            apply_kwargs['target'] = target

        return_code, stdout, stderr = self.tf.apply(**apply_kwargs)

        return {
            'return_code': return_code,
            'stdout': stdout,
            'stderr': stderr,
            'success': return_code == 0
        }

    def destroy(
        self,
        variables: Optional[Dict[str, Any]] = None,
        auto_approve: Optional[bool] = None,
        target: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Destroy Terraform-managed infrastructure.

        Args:
            variables: Variables dict (merged with default_variables)
            auto_approve: Auto-approve (overrides default)
            target: Destroy only specific resources

        Returns:
            Dict with return_code, stdout, stderr
        """
        # Merge variables
        destroy_vars = {**self.default_variables, **(variables or {})}

        destroy_kwargs = {
            'var': destroy_vars,
            'parallelism': self.parallelism
        }

        # Auto-approve
        if auto_approve is None:
            auto_approve = self.auto_approve

        if auto_approve:
            destroy_kwargs['auto_approve'] = IsFlagged

        # Targets
        if target:
            destroy_kwargs['target'] = target

        return_code, stdout, stderr = self.tf.destroy(**destroy_kwargs)

        return {
            'return_code': return_code,
            'stdout': stdout,
            'stderr': stderr,
            'success': return_code == 0
        }

    def output(
        self,
        name: Optional[str] = None,
        json_format: bool = True
    ) -> Union[Dict[str, Any], Any]:
        """
        Read Terraform outputs.

        Args:
            name: Specific output name (returns all if None)
            json_format: Parse as JSON (default: True)

        Returns:
            Output value(s)
        """
        output_kwargs = {}

        if name:
            output_kwargs['name'] = name

        if json_format:
            output_kwargs['json'] = IsFlagged

        return_code, stdout, stderr = self.tf.output(**output_kwargs)

        if return_code != 0:
            return None

        if json_format:
            try:
                result = json.loads(stdout)
                if name:
                    # Single output
                    return result.get('value')
                else:
                    # All outputs - extract values
                    return {k: v.get('value') for k, v in result.items()}
            except json.JSONDecodeError:
                return stdout

        return stdout

    def workspace_list(self) -> List[str]:
        """List all workspaces."""
        return_code, stdout, stderr = self.tf.workspace('list')

        if return_code != 0:
            return []

        # Parse workspace list
        workspaces = []
        for line in stdout.split('\n'):
            line = line.strip()
            if line:
                # Remove * prefix from current workspace
                workspace = line.lstrip('* ').strip()
                if workspace:
                    workspaces.append(workspace)

        return workspaces

    def workspace_select(self, name: str) -> Dict[str, Any]:
        """Select workspace."""
        return_code, stdout, stderr = self.tf.workspace('select', name)

        if return_code == 0:
            self._current_workspace = name

        return {
            'return_code': return_code,
            'stdout': stdout,
            'stderr': stderr,
            'success': return_code == 0
        }

    def workspace_new(self, name: str) -> Dict[str, Any]:
        """Create new workspace."""
        return_code, stdout, stderr = self.tf.workspace('new', name)

        if return_code == 0:
            self._current_workspace = name

        return {
            'return_code': return_code,
            'stdout': stdout,
            'stderr': stderr,
            'success': return_code == 0
        }

    def workspace_delete(self, name: str) -> Dict[str, Any]:
        """Delete workspace."""
        return_code, stdout, stderr = self.tf.workspace('delete', name)

        return {
            'return_code': return_code,
            'stdout': stdout,
            'stderr': stderr,
            'success': return_code == 0
        }

    def import_resource(
        self,
        address: str,
        id: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Import existing resource into Terraform state.

        Args:
            address: Resource address (e.g., 'aws_instance.example')
            id: Resource ID in provider
            variables: Variables dict

        Returns:
            Dict with return_code, stdout, stderr
        """
        # Merge variables
        import_vars = {**self.default_variables, **(variables or {})}

        import_kwargs = {
            'var': import_vars
        }

        return_code, stdout, stderr = self.tf.import_cmd(address, id, **import_kwargs)

        return {
            'return_code': return_code,
            'stdout': stdout,
            'stderr': stderr,
            'success': return_code == 0
        }

    def validate(self) -> Dict[str, Any]:
        """
        Validate Terraform configuration.

        Returns:
            Dict with return_code, stdout, stderr, valid
        """
        return_code, stdout, stderr = self.tf.validate(json=IsFlagged)

        valid = False
        if return_code == 0:
            try:
                result = json.loads(stdout)
                valid = result.get('valid', False)
            except json.JSONDecodeError:
                valid = False

        return {
            'return_code': return_code,
            'stdout': stdout,
            'stderr': stderr,
            'valid': valid,
            'success': return_code == 0
        }

    def fmt(
        self,
        check: bool = False,
        recursive: bool = True,
        diff: bool = False
    ) -> Dict[str, Any]:
        """
        Format Terraform configuration files.

        Args:
            check: Check if files are formatted (don't modify)
            recursive: Process subdirectories
            diff: Show formatting differences

        Returns:
            Dict with return_code, stdout, stderr
        """
        fmt_kwargs = {}

        if check:
            fmt_kwargs['check'] = IsFlagged

        if recursive:
            fmt_kwargs['recursive'] = IsFlagged

        if diff:
            fmt_kwargs['diff'] = IsFlagged

        return_code, stdout, stderr = self.tf.fmt(**fmt_kwargs)

        return {
            'return_code': return_code,
            'stdout': stdout,
            'stderr': stderr,
            'success': return_code == 0,
            'formatted_files': stdout.strip().split('\n') if stdout.strip() else []
        }

    def state_list(self) -> List[str]:
        """List resources in Terraform state."""
        return_code, stdout, stderr = self.tf.state('list')

        if return_code != 0:
            return []

        # Parse resource list
        resources = []
        for line in stdout.split('\n'):
            line = line.strip()
            if line:
                resources.append(line)

        return resources

    def state_show(self, address: str) -> Dict[str, Any]:
        """Show resource in state."""
        return_code, stdout, stderr = self.tf.state('show', address)

        return {
            'return_code': return_code,
            'stdout': stdout,
            'stderr': stderr,
            'success': return_code == 0
        }

    def state_rm(self, address: str) -> Dict[str, Any]:
        """Remove resource from state."""
        return_code, stdout, stderr = self.tf.state('rm', address)

        return {
            'return_code': return_code,
            'stdout': stdout,
            'stderr': stderr,
            'success': return_code == 0
        }

    def refresh(
        self,
        variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Refresh Terraform state.

        Args:
            variables: Variables dict

        Returns:
            Dict with return_code, stdout, stderr
        """
        # Merge variables
        refresh_vars = {**self.default_variables, **(variables or {})}

        refresh_kwargs = {
            'var': refresh_vars
        }

        return_code, stdout, stderr = self.tf.refresh(**refresh_kwargs)

        return {
            'return_code': return_code,
            'stdout': stdout,
            'stderr': stderr,
            'success': return_code == 0
        }

    def show(
        self,
        plan_file: Optional[str] = None,
        json_format: bool = True
    ) -> Union[Dict[str, Any], str]:
        """
        Show Terraform state or plan.

        Args:
            plan_file: Show specific plan file
            json_format: Output as JSON

        Returns:
            State/plan data
        """
        show_kwargs = {}

        if plan_file:
            show_kwargs['file_path'] = plan_file

        if json_format:
            show_kwargs['json'] = IsFlagged

        return_code, stdout, stderr = self.tf.show(**show_kwargs)

        if return_code != 0:
            return None

        if json_format:
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                return stdout

        return stdout

    # ============================================================================
    # Metadata Methods (for NL2Py compiler prompt generation)
    # ============================================================================

    @classmethod
    def get_metadata(cls):
        """Get module metadata for compiler prompt generation."""
        from nl2py.modules.module_base import ModuleMetadata
        return ModuleMetadata(
            name="Terraform",
            task_type="terraform",
            description="HashiCorp Terraform Infrastructure as Code (IaC) for provisioning and managing cloud resources with init, plan, apply, destroy, and workspace management",
            version="1.0.0",
            keywords=[
                "terraform", "iac", "infrastructure", "cloud", "provisioning",
                "aws", "azure", "gcp", "devops", "automation", "state", "workspace"
            ],
            dependencies=["python-terraform>=0.10.0"]
        )

    @classmethod
    def get_usage_notes(cls):
        """Get detailed usage notes for this module."""
        return [
            "Module uses singleton pattern - one instance per working directory",
            "Requires Terraform CLI installed and in PATH or specified via terraform_bin",
            "Working directory must contain .tf configuration files",
            "Always run init() before other operations to initialize Terraform",
            "Supports 2000+ cloud providers: AWS, Azure, GCP, DigitalOcean, etc.",
            "State files track infrastructure resources (local or remote backend)",
            "Remote backends (S3, Azure Storage, GCS) enable team collaboration",
            "Workspaces provide environment isolation (dev, staging, production)",
            "Variables can be set via default_variables or per-operation",
            "plan() creates execution plan without making changes (dry-run)",
            "apply() provisions/modifies infrastructure resources",
            "destroy() tears down all managed infrastructure (use with caution!)",
            "auto_approve=True skips confirmation prompts (use carefully!)",
            "Parallelism controls concurrent resource operations (default 10)",
            "Detailed exit codes: 0=no changes, 1=error, 2=has changes",
            "Outputs retrieve values like IP addresses, URLs after apply",
            "State operations (list, show, rm) manage resource state",
            "import_resource() brings existing resources under Terraform management",
            "validate() checks configuration syntax without accessing providers",
            "fmt() formats .tf files to canonical style",
            "Target specific resources with target parameter for selective operations",
            "Always backup state files before manual state operations",
            "Use version constraints in .tf files for provider compatibility",
            "Sensitive outputs marked with 'sensitive=true' hidden by default"
        ]

    @classmethod
    def get_methods_info(cls):
        """Get information about all methods in this module."""
        from nl2py.modules.module_base import MethodInfo
        return [
            MethodInfo(
                name="init",
                description="Initialize Terraform working directory, download providers and modules",
                parameters={
                    "backend": "bool (optional) - Configure backend (default True)",
                    "reconfigure": "bool (optional) - Reconfigure backend ignoring saved config (default False)",
                    "upgrade": "bool (optional) - Upgrade modules and plugins (default False)",
                    "plugin_dir": "str (optional) - Custom plugin directory path"
                },
                returns="dict - Result with return_code, stdout, stderr, success",
                examples=[
                    {"text": "Initialize Terraform working directory", "code": "terraform.init()"},
                    {"text": "Initialize Terraform with reconfigure={{True}} and upgrade={{True}}", "code": "terraform.init(reconfigure={{True}}, upgrade={{True}})"}
                ]
            ),
            MethodInfo(
                name="plan",
                description="Create execution plan showing what changes Terraform will make",
                parameters={
                    "variables": "dict (optional) - Variables to pass (merged with defaults)",
                    "out": "str (optional) - Save plan to file path",
                    "destroy": "bool (optional) - Create destroy plan (default False)",
                    "detailed_exitcode": "bool (optional) - Return detailed exit code (default False)"
                },
                returns="dict - Result with return_code, stdout, stderr, success, has_changes",
                examples=[
                    {"text": "Create Terraform execution plan", "code": "terraform.plan()"},
                    {"text": "Plan with variables environment={{production}} and instance_count={{3}}", "code": "terraform.plan(variables={{'environment': '{{production}}', 'instance_count': {{3}}}})"},
                    {"text": "Save plan to file {{prod.tfplan}} with detailed_exitcode={{True}}", "code": "terraform.plan(out='{{prod.tfplan}}', detailed_exitcode={{True}})"}
                ]
            ),
            MethodInfo(
                name="apply",
                description="Apply Terraform changes to provision/modify infrastructure",
                parameters={
                    "variables": "dict (optional) - Variables to pass",
                    "plan_file": "str (optional) - Apply specific saved plan file",
                    "auto_approve": "bool (optional) - Skip confirmation prompt (default from config)",
                    "target": "list[str] (optional) - Apply only to specific resources"
                },
                returns="dict - Result with return_code, stdout, stderr, success",
                examples=[
                    {"text": "Apply Terraform changes with auto_approve={{True}}", "code": "terraform.apply(auto_approve={{True}})"},
                    {"text": "Apply with variable env={{prod}} and auto_approve={{True}}", "code": "terraform.apply(variables={{'env': '{{prod}}'}}, auto_approve={{True}})"},
                    {"text": "Apply saved plan file {{prod.tfplan}}", "code": "terraform.apply(plan_file='{{prod.tfplan}}')"},
                    {"text": "Apply to specific targets {{aws_instance.web}} and {{aws_security_group.web}}", "code": "terraform.apply(target={{'aws_instance.web', 'aws_security_group.web'}})"}
                ]
            ),
            MethodInfo(
                name="destroy",
                description="Destroy all Terraform-managed infrastructure resources",
                parameters={
                    "variables": "dict (optional) - Variables to pass",
                    "auto_approve": "bool (optional) - Skip confirmation prompt",
                    "target": "list[str] (optional) - Destroy only specific resources"
                },
                returns="dict - Result with return_code, stdout, stderr, success",
                examples=[
                    {"text": "Destroy all Terraform infrastructure with auto_approve={{True}}", "code": "terraform.destroy(auto_approve={{True}})"},
                    {"text": "Destroy infrastructure with variable environment={{dev}}", "code": "terraform.destroy(variables={{'environment': '{{dev}}'}})"},
                    {"text": "Destroy specific target {{aws_instance.test}}", "code": "terraform.destroy(target={{'aws_instance.test'}})"}
                ]
            ),
            MethodInfo(
                name="output",
                description="Read Terraform output values (e.g., IP addresses, URLs)",
                parameters={
                    "name": "str (optional) - Specific output name (returns all if None)",
                    "json_format": "bool (optional) - Parse as JSON (default True)"
                },
                returns="dict or any - Output value(s)",
                examples=[
                    {"text": "Get all Terraform outputs", "code": "terraform.output()"},
                    {"text": "Get specific output {{server_public_ip}}", "code": "terraform.output(name='{{server_public_ip}}')"}
                ]
            ),
            MethodInfo(
                name="workspace_list",
                description="List all available Terraform workspaces",
                parameters={},
                returns="list[str] - List of workspace names",
                examples=[
                    {"text": "List all available workspaces", "code": "terraform.workspace_list()"}
                ]
            ),
            MethodInfo(
                name="workspace_select",
                description="Switch to a different Terraform workspace",
                parameters={"name": "str (required) - Workspace name to switch to"},
                returns="dict - Result with success status",
                examples=[
                    {"text": "Switch to workspace {{production}}", "code": "terraform.workspace_select(name='{{production}}')"},
                    {"text": "Switch to workspace {{dev}}", "code": "terraform.workspace_select(name='{{dev}}')"}
                ]
            ),
            MethodInfo(
                name="workspace_new",
                description="Create and switch to new Terraform workspace",
                parameters={"name": "str (required) - New workspace name"},
                returns="dict - Result with success status",
                examples=[
                    {"text": "Create new workspace {{staging}}", "code": "terraform.workspace_new(name='{{staging}}')"},
                    {"text": "Create new workspace {{feature-test}}", "code": "terraform.workspace_new(name='{{feature-test}}')"}
                ]
            ),
            MethodInfo(
                name="workspace_delete",
                description="Delete a Terraform workspace (cannot delete current workspace)",
                parameters={"name": "str (required) - Workspace name to delete"},
                returns="dict - Result with success status",
                examples=[
                    {"text": "Delete workspace {{old-test}}", "code": "terraform.workspace_delete(name='{{old-test}}')"}
                ]
            ),
            MethodInfo(
                name="import_resource",
                description="Import existing infrastructure resource into Terraform state",
                parameters={
                    "address": "str (required) - Terraform resource address (e.g., 'aws_instance.web')",
                    "id": "str (required) - Provider-specific resource ID",
                    "variables": "dict (optional) - Variables to pass"
                },
                returns="dict - Result with success status",
                examples=[
                    {"text": "Import AWS EC2 instance {{aws_instance.web}} with id {{i-0123456789abcdef}}", "code": "terraform.import_resource(address='{{aws_instance.web}}', id='{{i-0123456789abcdef}}')"},
                    {"text": "Import Azure VM {{azurerm_virtual_machine.vm}} with id {{/subscriptions/.../vm-name}}", "code": "terraform.import_resource(address='{{azurerm_virtual_machine.vm}}', id='{{/subscriptions/.../vm-name}}')"}
                ]
            ),
            MethodInfo(
                name="validate",
                description="Validate Terraform configuration syntax without accessing providers",
                parameters={},
                returns="dict - Result with return_code, stdout, stderr, valid, success",
                examples=[
                    {"text": "Validate Terraform configuration", "code": "terraform.validate()"}
                ]
            ),
            MethodInfo(
                name="fmt",
                description="Format Terraform configuration files to canonical style",
                parameters={
                    "check": "bool (optional) - Check if files are formatted without modifying (default False)",
                    "recursive": "bool (optional) - Process subdirectories (default True)",
                    "diff": "bool (optional) - Show formatting differences (default False)"
                },
                returns="dict - Result with formatted_files list",
                examples=[
                    {"text": "Format all Terraform configuration files", "code": "terraform.fmt()"},
                    {"text": "Check formatting with check={{True}} without modifying", "code": "terraform.fmt(check={{True}})"},
                    {"text": "Show formatting differences with diff={{True}}", "code": "terraform.fmt(diff={{True}})"}
                ]
            ),
            MethodInfo(
                name="state_list",
                description="List all resources in Terraform state",
                parameters={},
                returns="list[str] - List of resource addresses",
                examples=[
                    {"text": "List all resources in state", "code": "terraform.state_list()"}
                ]
            ),
            MethodInfo(
                name="state_show",
                description="Show detailed information about a resource in state",
                parameters={"address": "str (required) - Resource address"},
                returns="dict - Result with resource details",
                examples=[
                    {"text": "Show details of resource {{aws_instance.web}} in state", "code": "terraform.state_show(address='{{aws_instance.web}}')"}
                ]
            ),
            MethodInfo(
                name="state_rm",
                description="Remove resource from Terraform state (does not destroy resource)",
                parameters={"address": "str (required) - Resource address to remove"},
                returns="dict - Result with success status",
                examples=[
                    {"text": "Remove resource {{aws_instance.old}} from state without destroying", "code": "terraform.state_rm(address='{{aws_instance.old}}')"}
                ]
            ),
            MethodInfo(
                name="refresh",
                description="Refresh Terraform state to match real infrastructure",
                parameters={"variables": "dict (optional) - Variables to pass"},
                returns="dict - Result with success status",
                examples=[
                    {"text": "Refresh Terraform state", "code": "terraform.refresh()"},
                    {"text": "Refresh state with variable region={{us-east-1}}", "code": "terraform.refresh(variables={{'region': '{{us-east-1}}'}})"}
                ]
            ),
            MethodInfo(
                name="show",
                description="Show Terraform state or plan in human-readable format",
                parameters={
                    "plan_file": "str (optional) - Show specific plan file",
                    "json_format": "bool (optional) - Output as JSON (default True)"
                },
                returns="dict or str - State/plan data",
                examples=[
                    {"text": "Show current Terraform state", "code": "terraform.show()"},
                    {"text": "Show details of plan file {{prod.tfplan}}", "code": "terraform.show(plan_file='{{prod.tfplan}}')"}
                ]
            ),
            MethodInfo(
                name="get_version",
                description="Get installed Terraform CLI version",
                parameters={},
                returns="str - Version string",
                examples=[
                    {"text": "Get Terraform CLI version", "code": "terraform.get_version()"}
                ]
            )
        ]

# Convenience function for quick access
def get_terraform_module(config_path: str = 'nl2py.conf') -> TerraformModule:
    """Get or create Terraform module instance from config."""
    return TerraformModule.from_config(config_path)
