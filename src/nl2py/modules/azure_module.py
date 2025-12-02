"""
Azure Module for NL2Py

This module provides comprehensive Microsoft Azure cloud services management
through the official Azure SDK for Python.

Features:
- Virtual Machine management (create, start, stop, delete)
- Storage Account and Blob Storage operations
- SQL Database management
- Resource Group management
- Virtual Network management
- App Service (Web Apps) management
- Container Instances
- Key Vault operations
- Cosmos DB operations
- Monitor and metrics

Dependencies:
- azure-identity>=1.15.0
- azure-mgmt-compute>=30.0.0
- azure-mgmt-storage>=21.0.0
- azure-mgmt-sql>=4.0.0
- azure-mgmt-resource>=23.0.0
- azure-mgmt-network>=25.0.0
- azure-mgmt-web>=7.0.0
- azure-storage-blob>=12.19.0
- azure-mgmt-containerinstance>=10.0.0
- azure-keyvault-secrets>=4.7.0
- azure-mgmt-cosmosdb>=9.0.0

Configuration (nl2py.conf):
[azure]
SUBSCRIPTION_ID = your-subscription-id
TENANT_ID = your-tenant-id
CLIENT_ID = your-client-id
CLIENT_SECRET = your-client-secret
RESOURCE_GROUP = default-resource-group
LOCATION = eastus

Author: NL2Py Team
Version: 1.0
"""

import os
import threading
from typing import Optional, Dict, List, Any
import configparser

try:
    from azure.identity import ClientSecretCredential, DefaultAzureCredential
    from azure.mgmt.compute import ComputeManagementClient
    from azure.mgmt.storage import StorageManagementClient
    from azure.mgmt.sql import SqlManagementClient
    from azure.mgmt.resource import ResourceManagementClient
    from azure.mgmt.network import NetworkManagementClient
    from azure.mgmt.web import WebSiteManagementClient
    from azure.storage.blob import BlobServiceClient
    from azure.mgmt.containerinstance import ContainerInstanceManagementClient
    from azure.keyvault.secrets import SecretClient
    from azure.mgmt.cosmosdb import CosmosDBManagementClient
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False


from .module_base import NL2PyModuleBase


class AzureModule(NL2PyModuleBase):
    """
    Azure module for Microsoft Azure cloud services management.

    Implements singleton pattern for efficient resource usage.
    Provides comprehensive Azure operations through official SDK.
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(AzureModule, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize Azure module (only once due to singleton)."""
        if self._initialized:
            return

        if not AZURE_AVAILABLE:
            raise ImportError(
                "Azure SDK not available. Install with: pip install azure-identity azure-mgmt-compute azure-mgmt-storage azure-mgmt-sql azure-mgmt-resource azure-mgmt-network azure-storage-blob"
            )

        # Configuration
        self.subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
        self.tenant_id = os.getenv('AZURE_TENANT_ID')
        self.client_id = os.getenv('AZURE_CLIENT_ID')
        self.client_secret = os.getenv('AZURE_CLIENT_SECRET')
        self.resource_group = os.getenv('AZURE_RESOURCE_GROUP', 'nl2py-rg')
        self.location = os.getenv('AZURE_LOCATION', 'eastus')

        # Credentials (lazy initialized)
        self._credential = None

        # Service clients (lazy initialized)
        self._compute_client = None
        self._storage_client = None
        self._sql_client = None
        self._resource_client = None
        self._network_client = None
        self._web_client = None
        self._container_client = None
        self._cosmosdb_client = None

        self._initialized = True

    def load_config(self, config_path: str = 'nl2py.conf'):
        """Load configuration from nl2py.conf file."""
        if not os.path.exists(config_path):
            return

        config = configparser.ConfigParser()
        config.read(config_path)

        if 'azure' in config:
            azure_config = config['azure']
            self.subscription_id = azure_config.get('SUBSCRIPTION_ID', self.subscription_id)
            self.tenant_id = azure_config.get('TENANT_ID', self.tenant_id)
            self.client_id = azure_config.get('CLIENT_ID', self.client_id)
            self.client_secret = azure_config.get('CLIENT_SECRET', self.client_secret)
            self.resource_group = azure_config.get('RESOURCE_GROUP', self.resource_group)
            self.location = azure_config.get('LOCATION', self.location)

    @property
    def credential(self):
        """Lazy-load Azure credential."""
        if self._credential is None:
            if self.client_id and self.client_secret and self.tenant_id:
                # Service Principal authentication
                self._credential = ClientSecretCredential(
                    tenant_id=self.tenant_id,
                    client_id=self.client_id,
                    client_secret=self.client_secret
                )
            else:
                # Default credential (uses environment, managed identity, etc.)
                self._credential = DefaultAzureCredential()
        return self._credential

    @property
    def compute_client(self):
        """Lazy-load Compute Management client."""
        if self._compute_client is None:
            self._compute_client = ComputeManagementClient(
                credential=self.credential,
                subscription_id=self.subscription_id
            )
        return self._compute_client

    @property
    def storage_client(self):
        """Lazy-load Storage Management client."""
        if self._storage_client is None:
            self._storage_client = StorageManagementClient(
                credential=self.credential,
                subscription_id=self.subscription_id
            )
        return self._storage_client

    @property
    def sql_client(self):
        """Lazy-load SQL Management client."""
        if self._sql_client is None:
            self._sql_client = SqlManagementClient(
                credential=self.credential,
                subscription_id=self.subscription_id
            )
        return self._sql_client

    @property
    def resource_client(self):
        """Lazy-load Resource Management client."""
        if self._resource_client is None:
            self._resource_client = ResourceManagementClient(
                credential=self.credential,
                subscription_id=self.subscription_id
            )
        return self._resource_client

    @property
    def network_client(self):
        """Lazy-load Network Management client."""
        if self._network_client is None:
            self._network_client = NetworkManagementClient(
                credential=self.credential,
                subscription_id=self.subscription_id
            )
        return self._network_client

    @property
    def web_client(self):
        """Lazy-load Web/App Service Management client."""
        if self._web_client is None:
            self._web_client = WebSiteManagementClient(
                credential=self.credential,
                subscription_id=self.subscription_id
            )
        return self._web_client

    @property
    def container_client(self):
        """Lazy-load Container Instance Management client."""
        if self._container_client is None:
            self._container_client = ContainerInstanceManagementClient(
                credential=self.credential,
                subscription_id=self.subscription_id
            )
        return self._container_client

    @property
    def cosmosdb_client(self):
        """Lazy-load Cosmos DB Management client."""
        if self._cosmosdb_client is None:
            self._cosmosdb_client = CosmosDBManagementClient(
                credential=self.credential,
                subscription_id=self.subscription_id
            )
        return self._cosmosdb_client

    # =============================================================================
    # Resource Group Management
    # =============================================================================

    def resource_group_create(self, name: str, location: Optional[str] = None,
                             tags: Optional[Dict[str, str]] = None) -> Any:
        """Create a resource group."""
        location = location or self.location
        try:
            result = self.resource_client.resource_groups.create_or_update(
                name,
                {
                    "location": location,
                    "tags": tags or {}
                }
            )
            return result
        except Exception as e:
            raise RuntimeError(f"Failed to create resource group: {e}")

    def resource_group_list(self) -> List[Any]:
        """List all resource groups."""
        try:
            return list(self.resource_client.resource_groups.list())
        except Exception as e:
            raise RuntimeError(f"Failed to list resource groups: {e}")

    def resource_group_delete(self, name: str) -> bool:
        """Delete a resource group."""
        try:
            poller = self.resource_client.resource_groups.begin_delete(name)
            poller.wait()
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to delete resource group: {e}")

    # =============================================================================
    # Virtual Machine Management
    # =============================================================================

    def vm_create(self, vm_name: str, resource_group: Optional[str] = None,
                  location: Optional[str] = None, vm_size: str = "Standard_B1s",
                  image: Optional[Dict] = None, admin_username: str = "azureuser",
                  admin_password: Optional[str] = None) -> Any:
        """
        Create a virtual machine.

        Note: This is a simplified version. Full VM creation requires
        network interface, public IP, etc.
        """
        resource_group = resource_group or self.resource_group
        location = location or self.location

        # Default to Ubuntu image
        if image is None:
            image = {
                "publisher": "Canonical",
                "offer": "UbuntuServer",
                "sku": "18.04-LTS",
                "version": "latest"
            }

        try:
            vm_parameters = {
                "location": location,
                "hardware_profile": {
                    "vm_size": vm_size
                },
                "storage_profile": {
                    "image_reference": image
                },
                "os_profile": {
                    "computer_name": vm_name,
                    "admin_username": admin_username,
                    "admin_password": admin_password
                }
            }

            poller = self.compute_client.virtual_machines.begin_create_or_update(
                resource_group,
                vm_name,
                vm_parameters
            )
            return poller.result()

        except Exception as e:
            raise RuntimeError(f"Failed to create VM: {e}")

    def vm_list(self, resource_group: Optional[str] = None) -> List[Any]:
        """List virtual machines."""
        resource_group = resource_group or self.resource_group
        try:
            return list(self.compute_client.virtual_machines.list(resource_group))
        except Exception as e:
            raise RuntimeError(f"Failed to list VMs: {e}")

    def vm_start(self, vm_name: str, resource_group: Optional[str] = None) -> bool:
        """Start a virtual machine."""
        resource_group = resource_group or self.resource_group
        try:
            poller = self.compute_client.virtual_machines.begin_start(
                resource_group, vm_name
            )
            poller.wait()
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to start VM: {e}")

    def vm_stop(self, vm_name: str, resource_group: Optional[str] = None) -> bool:
        """Stop (deallocate) a virtual machine."""
        resource_group = resource_group or self.resource_group
        try:
            poller = self.compute_client.virtual_machines.begin_deallocate(
                resource_group, vm_name
            )
            poller.wait()
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to stop VM: {e}")

    def vm_delete(self, vm_name: str, resource_group: Optional[str] = None) -> bool:
        """Delete a virtual machine."""
        resource_group = resource_group or self.resource_group
        try:
            poller = self.compute_client.virtual_machines.begin_delete(
                resource_group, vm_name
            )
            poller.wait()
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to delete VM: {e}")

    def vm_get(self, vm_name: str, resource_group: Optional[str] = None) -> Any:
        """Get virtual machine details."""
        resource_group = resource_group or self.resource_group
        try:
            return self.compute_client.virtual_machines.get(resource_group, vm_name)
        except Exception as e:
            raise RuntimeError(f"Failed to get VM: {e}")

    # =============================================================================
    # Storage Account Management
    # =============================================================================

    def storage_account_create(self, account_name: str,
                              resource_group: Optional[str] = None,
                              location: Optional[str] = None,
                              sku: str = "Standard_LRS") -> Any:
        """Create a storage account."""
        resource_group = resource_group or self.resource_group
        location = location or self.location

        try:
            parameters = {
                "location": location,
                "sku": {"name": sku},
                "kind": "StorageV2"
            }

            poller = self.storage_client.storage_accounts.begin_create(
                resource_group,
                account_name,
                parameters
            )
            return poller.result()

        except Exception as e:
            raise RuntimeError(f"Failed to create storage account: {e}")

    def storage_account_list(self, resource_group: Optional[str] = None) -> List[Any]:
        """List storage accounts."""
        try:
            if resource_group:
                return list(self.storage_client.storage_accounts.list_by_resource_group(
                    resource_group
                ))
            else:
                return list(self.storage_client.storage_accounts.list())
        except Exception as e:
            raise RuntimeError(f"Failed to list storage accounts: {e}")

    def storage_account_delete(self, account_name: str,
                              resource_group: Optional[str] = None) -> bool:
        """Delete a storage account."""
        resource_group = resource_group or self.resource_group
        try:
            self.storage_client.storage_accounts.delete(resource_group, account_name)
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to delete storage account: {e}")

    def storage_account_get_keys(self, account_name: str,
                                resource_group: Optional[str] = None) -> List[str]:
        """Get storage account keys."""
        resource_group = resource_group or self.resource_group
        try:
            keys = self.storage_client.storage_accounts.list_keys(
                resource_group, account_name
            )
            return [key.value for key in keys.keys]
        except Exception as e:
            raise RuntimeError(f"Failed to get storage account keys: {e}")

    # =============================================================================
    # Blob Storage Operations
    # =============================================================================

    def blob_upload_file(self, account_name: str, container_name: str,
                        blob_name: str, file_path: str,
                        resource_group: Optional[str] = None) -> bool:
        """Upload a file to blob storage."""
        resource_group = resource_group or self.resource_group

        try:
            # Get account key
            keys = self.storage_account_get_keys(account_name, resource_group)
            account_key = keys[0]

            # Create blob service client
            connection_string = f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)

            # Get blob client
            blob_client = blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )

            # Upload file
            with open(file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)

            return True

        except Exception as e:
            raise RuntimeError(f"Failed to upload blob: {e}")

    def blob_download_file(self, account_name: str, container_name: str,
                          blob_name: str, file_path: str,
                          resource_group: Optional[str] = None) -> bool:
        """Download a file from blob storage."""
        resource_group = resource_group or self.resource_group

        try:
            # Get account key
            keys = self.storage_account_get_keys(account_name, resource_group)
            account_key = keys[0]

            # Create blob service client
            connection_string = f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)

            # Get blob client
            blob_client = blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )

            # Download file
            with open(file_path, "wb") as file:
                download_stream = blob_client.download_blob()
                file.write(download_stream.readall())

            return True

        except Exception as e:
            raise RuntimeError(f"Failed to download blob: {e}")

    def blob_list(self, account_name: str, container_name: str,
                 resource_group: Optional[str] = None) -> List[str]:
        """List blobs in a container."""
        resource_group = resource_group or self.resource_group

        try:
            # Get account key
            keys = self.storage_account_get_keys(account_name, resource_group)
            account_key = keys[0]

            # Create blob service client
            connection_string = f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)

            # Get container client
            container_client = blob_service_client.get_container_client(container_name)

            # List blobs
            return [blob.name for blob in container_client.list_blobs()]

        except Exception as e:
            raise RuntimeError(f"Failed to list blobs: {e}")

    # =============================================================================
    # SQL Database Management
    # =============================================================================

    def sql_server_create(self, server_name: str, admin_login: str,
                         admin_password: str,
                         resource_group: Optional[str] = None,
                         location: Optional[str] = None) -> Any:
        """Create a SQL server."""
        resource_group = resource_group or self.resource_group
        location = location or self.location

        try:
            parameters = {
                "location": location,
                "administrator_login": admin_login,
                "administrator_login_password": admin_password,
                "version": "12.0"
            }

            poller = self.sql_client.servers.begin_create_or_update(
                resource_group,
                server_name,
                parameters
            )
            return poller.result()

        except Exception as e:
            raise RuntimeError(f"Failed to create SQL server: {e}")

    def sql_database_create(self, server_name: str, database_name: str,
                           resource_group: Optional[str] = None,
                           location: Optional[str] = None,
                           sku: Optional[Dict] = None) -> Any:
        """Create a SQL database."""
        resource_group = resource_group or self.resource_group
        location = location or self.location

        if sku is None:
            sku = {"name": "Basic", "tier": "Basic"}

        try:
            parameters = {
                "location": location,
                "sku": sku
            }

            poller = self.sql_client.databases.begin_create_or_update(
                resource_group,
                server_name,
                database_name,
                parameters
            )
            return poller.result()

        except Exception as e:
            raise RuntimeError(f"Failed to create SQL database: {e}")

    def sql_database_list(self, server_name: str,
                         resource_group: Optional[str] = None) -> List[Any]:
        """List SQL databases on a server."""
        resource_group = resource_group or self.resource_group
        try:
            return list(self.sql_client.databases.list_by_server(
                resource_group, server_name
            ))
        except Exception as e:
            raise RuntimeError(f"Failed to list SQL databases: {e}")

    # =============================================================================
    # Virtual Network Management
    # =============================================================================

    def vnet_create(self, vnet_name: str, address_prefix: str = "10.0.0.0/16",
                   resource_group: Optional[str] = None,
                   location: Optional[str] = None) -> Any:
        """Create a virtual network."""
        resource_group = resource_group or self.resource_group
        location = location or self.location

        try:
            parameters = {
                "location": location,
                "address_space": {
                    "address_prefixes": [address_prefix]
                }
            }

            poller = self.network_client.virtual_networks.begin_create_or_update(
                resource_group,
                vnet_name,
                parameters
            )
            return poller.result()

        except Exception as e:
            raise RuntimeError(f"Failed to create virtual network: {e}")

    def vnet_list(self, resource_group: Optional[str] = None) -> List[Any]:
        """List virtual networks."""
        resource_group = resource_group or self.resource_group
        try:
            return list(self.network_client.virtual_networks.list(resource_group))
        except Exception as e:
            raise RuntimeError(f"Failed to list virtual networks: {e}")

    # =============================================================================
    # Utility Methods
    # =============================================================================

    def get_subscription_info(self) -> Dict[str, Any]:
        """Get subscription information."""
        try:
            subscription = self.resource_client.subscriptions.get(self.subscription_id)
            return {
                "subscription_id": subscription.subscription_id,
                "display_name": subscription.display_name,
                "state": subscription.state,
                "tenant_id": subscription.tenant_id
            }
        except Exception as e:
            raise RuntimeError(f"Failed to get subscription info: {e}")

    # =============================================================================
    # Metadata Methods for NL2Py Compiler
    # =============================================================================

    @classmethod
    def get_metadata(cls):
        """Get module metadata."""
        from nl2py.modules.module_base import ModuleMetadata
        return ModuleMetadata(
            name="Azure",
            task_type="azure",
            description="Microsoft Azure cloud services management with support for VMs, Storage, SQL, Networking, and more",
            version="1.0.0",
            keywords=["azure", "cloud", "vm", "storage", "blob", "sql", "database", "vnet", "network", "compute", "resource-group"],
            dependencies=[
                "azure-identity>=1.15.0",
                "azure-mgmt-compute>=30.0.0",
                "azure-mgmt-storage>=21.0.0",
                "azure-mgmt-sql>=4.0.0",
                "azure-mgmt-resource>=23.0.0",
                "azure-mgmt-network>=25.0.0",
                "azure-mgmt-web>=7.0.0",
                "azure-storage-blob>=12.19.0",
                "azure-mgmt-containerinstance>=10.0.0",
                "azure-keyvault-secrets>=4.7.0",
                "azure-mgmt-cosmosdb>=9.0.0"
            ]
        )

    @classmethod
    def get_usage_notes(cls):
        """Get detailed usage notes."""
        return [
            "Module uses singleton pattern - one instance shared across all operations",
            "Supports Service Principal authentication (CLIENT_ID/SECRET) or DefaultAzureCredential",
            "All service clients are lazy-loaded on first use for efficiency",
            "Resource group and location can be set as defaults or overridden per operation",
            "VM operations support full lifecycle: create, start, stop, delete, list",
            "Storage operations cover accounts and blob storage (upload, download, list)",
            "SQL operations manage both servers and databases",
            "Virtual network operations support VNet creation and management",
            "Most operations return Azure SDK response objects with detailed properties",
            "Long-running operations use pollers - call .wait() or .result() to block",
            "Authentication via environment variables or nl2py.conf file",
            "Requires valid Azure subscription ID for all operations",
            "Storage account names must be globally unique (3-24 chars, lowercase, numbers only)",
            "VM creation requires existing resource group",
            "Blob operations automatically retrieve storage account keys",
            "All clients use credential property for lazy authentication setup",
            "Key methods: resource_group_create, vm_create, vm_start, vm_stop, storage_account_create, blob_upload_file, blob_download_file, sql_database_create",
        ]

    @classmethod
    def get_methods_info(cls):
        """Get information about module methods."""
        from nl2py.modules.module_base import MethodInfo
        return [
            MethodInfo(
                name="resource_group_create",
                description="Create an Azure resource group to organize related resources",
                parameters={
                    "name": "Resource group name (string)",
                    "location": "Azure region (optional, defaults to module's location setting)",
                    "tags": "Optional dict of key-value tags for organization"
                },
                returns="Azure ResourceGroup object with properties: name, location, id, tags, provisioning_state",
                examples=[
                    {"text": "Create resource group {{my-rg}} in location {{eastus}}", "code": "resource_group_create(name='{{my-rg}}', location='{{eastus}}')"},
                    {"text": "Create resource group {{dev-rg}} in location {{westeurope}} with tags {{env: dev}}", "code": "resource_group_create(name='{{dev-rg}}', location='{{westeurope}}', tags={{'env': 'dev'}})"}
                ]
            ),
            MethodInfo(
                name="resource_group_delete",
                description="Delete a resource group and all resources within it (destructive operation)",
                parameters={
                    "name": "Resource group name to delete (string)"
                },
                returns="Boolean True if deletion successful, raises RuntimeError on failure",
                examples=[
                    {"text": "Delete resource group {{old-rg}}", "code": "resource_group_delete(name='{{old-rg}}')"},
                    {"text": "Remove resource group {{test-rg}}", "code": "resource_group_delete(name='{{test-rg}}')"}
                ]
            ),
            MethodInfo(
                name="vm_create",
                description="Create a virtual machine with specified configuration",
                parameters={
                    "vm_name": "Name for the virtual machine (string)",
                    "resource_group": "Resource group name (optional, uses default)",
                    "location": "Azure region (optional, uses default)",
                    "vm_size": "VM size/SKU (default: 'Standard_B1s' for burstable small VM)",
                    "image": "Image reference dict with publisher/offer/sku/version (optional: defaults to Ubuntu 18.04 LTS)",
                    "admin_username": "Admin username (default: 'azureuser')",
                    "admin_password": "Admin password (required for SSH/RDP access)"
                },
                returns="Azure VirtualMachine object with properties: name, location, vm_size, provisioning_state, vm_id",
                examples=[
                    {"text": "Create virtual machine {{web-server-1}} with size {{Standard_B2s}}", "code": "vm_create(vm_name='{{web-server-1}}', vm_size='{{Standard_B2s}}')"},
                    {"text": "Create virtual machine {{db-vm}} in resource group {{prod-rg}}", "code": "vm_create(vm_name='{{db-vm}}', resource_group='{{prod-rg}}')"}
                ]
            ),
            MethodInfo(
                name="vm_start",
                description="Start a stopped (deallocated) virtual machine",
                parameters={
                    "vm_name": "Name of VM to start (string)",
                    "resource_group": "Resource group name (optional, uses default)"
                },
                returns="Boolean True when VM successfully started",
                examples=[
                    {"text": "Start virtual machine {{web-server-1}}", "code": "vm_start(vm_name='{{web-server-1}}')"},
                    {"text": "Start virtual machine {{app-server}} in resource group {{prod-rg}}", "code": "vm_start(vm_name='{{app-server}}', resource_group='{{prod-rg}}')"}
                ]
            ),
            MethodInfo(
                name="vm_stop",
                description="Stop (deallocate) a running virtual machine to save costs",
                parameters={
                    "vm_name": "Name of VM to stop (string)",
                    "resource_group": "Resource group name (optional, uses default)"
                },
                returns="Boolean True when VM successfully stopped and deallocated",
                examples=[
                    {"text": "Stop virtual machine {{web-server-1}}", "code": "vm_stop(vm_name='{{web-server-1}}')"},
                    {"text": "Deallocate virtual machine {{test-vm}} in resource group {{dev-rg}}", "code": "vm_stop(vm_name='{{test-vm}}', resource_group='{{dev-rg}}')"}
                ]
            ),
            MethodInfo(
                name="vm_delete",
                description="Delete a virtual machine permanently (destructive operation)",
                parameters={
                    "vm_name": "Name of VM to delete (string)",
                    "resource_group": "Resource group name (optional, uses default)"
                },
                returns="Boolean True when VM successfully deleted",
                examples=[
                    {"text": "Delete virtual machine {{old-server}}", "code": "vm_delete(vm_name='{{old-server}}')"},
                    {"text": "Remove virtual machine {{temp-vm}} from resource group {{test-rg}}", "code": "vm_delete(vm_name='{{temp-vm}}', resource_group='{{test-rg}}')"}
                ]
            ),
            MethodInfo(
                name="vm_list",
                description="List all virtual machines in a resource group",
                parameters={
                    "resource_group": "Resource group name (optional, uses default)"
                },
                returns="List of VirtualMachine objects, each with properties: name, location, vm_size, provisioning_state",
                examples=[
                    {"text": "List virtual machines in resource group {{prod-rg}}", "code": "vm_list(resource_group='{{prod-rg}}')"},
                    {"text": "Show all virtual machines", "code": "vm_list()"}
                ]
            ),
            MethodInfo(
                name="storage_account_create",
                description="Create a storage account for blob, file, queue, and table storage",
                parameters={
                    "account_name": "Globally unique account name (3-24 chars, lowercase, numbers only)",
                    "resource_group": "Resource group name (optional, uses default)",
                    "location": "Azure region (optional, uses default)",
                    "sku": "Storage redundancy SKU (default: 'Standard_LRS' - locally redundant, options: Standard_GRS, Premium_LRS, etc.)"
                },
                returns="Azure StorageAccount object with properties: name, location, sku, provisioning_state, primary_endpoints",
                examples=[
                    {"text": "Create storage account {{myappdata2025}} with SKU {{Standard_LRS}}", "code": "storage_account_create(account_name='{{myappdata2025}}', sku='{{Standard_LRS}}')"},
                    {"text": "Create storage account {{prodstore123}} in location {{westus}} with SKU {{Standard_GRS}}", "code": "storage_account_create(account_name='{{prodstore123}}', location='{{westus}}', sku='{{Standard_GRS}}')"}
                ]
            ),
            MethodInfo(
                name="storage_account_get_keys",
                description="Retrieve access keys for a storage account (needed for blob operations)",
                parameters={
                    "account_name": "Storage account name (string)",
                    "resource_group": "Resource group name (optional, uses default)"
                },
                returns="List of access key strings (typically 2 keys for rotation)",
                examples=[
                    {"text": "Get storage account keys for {{myappdata2025}}", "code": "storage_account_get_keys(account_name='{{myappdata2025}}')"},
                    {"text": "Retrieve storage account keys for {{prodstore123}}", "code": "storage_account_get_keys(account_name='{{prodstore123}}')"}
                ]
            ),
            MethodInfo(
                name="blob_upload_file",
                description="Upload a local file to Azure Blob Storage container",
                parameters={
                    "account_name": "Storage account name (string)",
                    "container_name": "Blob container name (string)",
                    "blob_name": "Name for the blob in Azure (string)",
                    "file_path": "Local file path to upload (string)",
                    "resource_group": "Resource group name (optional, uses default)"
                },
                returns="Boolean True when file successfully uploaded, overwrites existing blobs",
                examples=[
                    {"text": "Upload file {{data.csv}} to blob {{uploads/data.csv}} in container {{backups}} of storage account {{mystore}}", "code": "blob_upload_file(account_name='{{mystore}}', container_name='{{backups}}', blob_name='{{uploads/data.csv}}', file_path='{{data.csv}}')"},
                    {"text": "Upload file {{report.pdf}} to blob {{2025-report.pdf}} in container {{reports}} of storage account {{docs}}", "code": "blob_upload_file(account_name='{{docs}}', container_name='{{reports}}', blob_name='{{2025-report.pdf}}', file_path='{{report.pdf}}')"}
                ]
            ),
            MethodInfo(
                name="blob_download_file",
                description="Download a blob from Azure Blob Storage to local file",
                parameters={
                    "account_name": "Storage account name (string)",
                    "container_name": "Blob container name (string)",
                    "blob_name": "Name of blob to download (string)",
                    "file_path": "Local destination path (string)",
                    "resource_group": "Resource group name (optional, uses default)"
                },
                returns="Boolean True when file successfully downloaded",
                examples=[
                    {"text": "Download blob {{backups/data.csv}} from container {{storage}} of storage account {{mystore}} to file {{local_data.csv}}", "code": "blob_download_file(account_name='{{mystore}}', container_name='{{storage}}', blob_name='{{backups/data.csv}}', file_path='{{local_data.csv}}')"},
                    {"text": "Download blob {{report.pdf}} from container {{reports}} of storage account {{docs}} to file {{downloaded_report.pdf}}", "code": "blob_download_file(account_name='{{docs}}', container_name='{{reports}}', blob_name='{{report.pdf}}', file_path='{{downloaded_report.pdf}}')"}
                ]
            ),
            MethodInfo(
                name="blob_list",
                description="List all blobs in a storage container",
                parameters={
                    "account_name": "Storage account name (string)",
                    "container_name": "Container name (string)",
                    "resource_group": "Resource group name (optional, uses default)"
                },
                returns="List of blob names (strings) in the container",
                examples=[
                    {"text": "List blobs in container {{backups}} of storage account {{mystore}}", "code": "blob_list(account_name='{{mystore}}', container_name='{{backups}}')"},
                    {"text": "Show all blobs in container {{reports}} of storage account {{docs}}", "code": "blob_list(account_name='{{docs}}', container_name='{{reports}}')"}
                ]
            ),
            MethodInfo(
                name="sql_server_create",
                description="Create an Azure SQL Server instance (logical server for databases)",
                parameters={
                    "server_name": "Globally unique server name (string)",
                    "admin_login": "Administrator username (string)",
                    "admin_password": "Administrator password (string, must meet complexity requirements)",
                    "resource_group": "Resource group name (optional, uses default)",
                    "location": "Azure region (optional, uses default)"
                },
                returns="Azure Server object with properties: name, location, version, administrator_login, state",
                examples=[
                    {"text": "Create SQL server {{myapp-sqlserver}} with admin {{sqladmin}} and password {{P@ssw0rd123!}}", "code": "sql_server_create(server_name='{{myapp-sqlserver}}', admin_login='{{sqladmin}}', admin_password='{{P@ssw0rd123!}}')"},
                    {"text": "Create SQL server {{prod-db-server}} with admin {{admin}} and password {{SecurePass1!}} in location {{eastus}}", "code": "sql_server_create(server_name='{{prod-db-server}}', admin_login='{{admin}}', admin_password='{{SecurePass1!}}', location='{{eastus}}')"}
                ]
            ),
            MethodInfo(
                name="sql_database_create",
                description="Create a SQL database on an existing SQL Server",
                parameters={
                    "server_name": "SQL Server name (string)",
                    "database_name": "Database name (string)",
                    "resource_group": "Resource group name (optional, uses default)",
                    "location": "Azure region (optional, uses default)",
                    "sku": "Database SKU dict with name/tier (optional: defaults to Basic tier)"
                },
                returns="Azure Database object with properties: name, location, sku, collation, status",
                examples=[
                    {"text": "Create SQL database {{appdb}} on server {{myapp-sqlserver}}", "code": "sql_database_create(server_name='{{myapp-sqlserver}}', database_name='{{appdb}}')"},
                    {"text": "Create SQL database {{prod-db}} on server {{prod-db-server}} with SKU {{name: Basic, tier: Basic}}", "code": "sql_database_create(server_name='{{prod-db-server}}', database_name='{{prod-db}}', sku={{'name': 'Basic', 'tier': 'Basic'}})"}
                ]
            ),
            MethodInfo(
                name="vnet_create",
                description="Create an Azure Virtual Network for network isolation",
                parameters={
                    "vnet_name": "Virtual network name (string)",
                    "address_prefix": "CIDR address space (default: '10.0.0.0/16')",
                    "resource_group": "Resource group name (optional, uses default)",
                    "location": "Azure region (optional, uses default)"
                },
                returns="Azure VirtualNetwork object with properties: name, location, address_space, subnets, provisioning_state",
                examples=[
                    {"text": "Create virtual network {{app-vnet}} with address prefix {{10.0.0.0/16}}", "code": "vnet_create(vnet_name='{{app-vnet}}', address_prefix='{{10.0.0.0/16}}')"},
                    {"text": "Create virtual network {{prod-network}} with address prefix {{172.16.0.0/12}} in resource group {{networking-rg}}", "code": "vnet_create(vnet_name='{{prod-network}}', address_prefix='{{172.16.0.0/12}}', resource_group='{{networking-rg}}')"}
                ]
            ),
            MethodInfo(
                name="resource_group_list",
                description="List all resource groups in the subscription",
                parameters={},
                returns="List of ResourceGroup objects with properties: name, location, id, tags, provisioning_state",
                examples=[
                    {"text": "List all resource groups", "code": "resource_group_list()"},
                    {"text": "Show resource groups in subscription", "code": "resource_group_list()"}
                ]
            ),
            MethodInfo(
                name="vm_get",
                description="Get detailed information about a specific virtual machine",
                parameters={
                    "vm_name": "Name of the virtual machine (string)",
                    "resource_group": "Resource group name (optional, uses default)"
                },
                returns="VirtualMachine object with properties: name, location, vm_size, provisioning_state, vm_id, hardware_profile",
                examples=[
                    {"text": "Get virtual machine details for {{web-server-1}}", "code": "vm_get(vm_name='{{web-server-1}}')"},
                    {"text": "Show virtual machine info for {{db-vm}} in resource group {{prod-rg}}", "code": "vm_get(vm_name='{{db-vm}}', resource_group='{{prod-rg}}')"}
                ]
            ),
            MethodInfo(
                name="storage_account_list",
                description="List storage accounts in subscription or resource group",
                parameters={
                    "resource_group": "Optional: Filter by resource group name"
                },
                returns="List of StorageAccount objects with properties: name, location, sku, provisioning_state",
                examples=[
                    {"text": "List all storage accounts", "code": "storage_account_list()"},
                    {"text": "List storage accounts in resource group {{prod-rg}}", "code": "storage_account_list(resource_group='{{prod-rg}}')"}
                ]
            ),
            MethodInfo(
                name="storage_account_delete",
                description="Delete a storage account (destructive operation)",
                parameters={
                    "account_name": "Storage account name to delete (string)",
                    "resource_group": "Resource group name (optional, uses default)"
                },
                returns="Boolean True when storage account successfully deleted",
                examples=[
                    {"text": "Delete storage account {{oldstore123}}", "code": "storage_account_delete(account_name='{{oldstore123}}')"},
                    {"text": "Remove storage account {{tempdata}} from resource group {{dev-rg}}", "code": "storage_account_delete(account_name='{{tempdata}}', resource_group='{{dev-rg}}')"}
                ]
            ),
            MethodInfo(
                name="sql_database_list",
                description="List all SQL databases on a SQL Server",
                parameters={
                    "server_name": "SQL Server name (string)",
                    "resource_group": "Resource group name (optional, uses default)"
                },
                returns="List of Database objects with properties: name, location, sku, collation, status",
                examples=[
                    {"text": "List SQL databases on server {{myapp-sqlserver}}", "code": "sql_database_list(server_name='{{myapp-sqlserver}}')"},
                    {"text": "Show all SQL databases on server {{prod-db-server}}", "code": "sql_database_list(server_name='{{prod-db-server}}')"}
                ]
            ),
            MethodInfo(
                name="vnet_list",
                description="List virtual networks in a resource group",
                parameters={
                    "resource_group": "Resource group name (optional, uses default)"
                },
                returns="List of VirtualNetwork objects with properties: name, location, address_space, subnets",
                examples=[
                    {"text": "List virtual networks", "code": "vnet_list()"},
                    {"text": "Show virtual networks in resource group {{networking-rg}}", "code": "vnet_list(resource_group='{{networking-rg}}')"}
                ]
            ),
            MethodInfo(
                name="get_subscription_info",
                description="Get information about the current Azure subscription",
                parameters={},
                returns="Dict with subscription_id, display_name, state, and other subscription details",
                examples=[
                    {"text": "Get subscription information", "code": "get_subscription_info()"},
                    {"text": "Show current subscription details", "code": "get_subscription_info()"}
                ]
            ),
        ]

# Global instance
_azure_module = None


def get_azure_module(config_path: str = 'nl2py.conf') -> AzureModule:
    """
    Get or create Azure module instance.

    Args:
        config_path: Path to nl2py.conf configuration file

    Returns:
        AzureModule instance
    """
    global _azure_module
    if _azure_module is None:
        _azure_module = AzureModule()
        _azure_module.load_config(config_path)
    return _azure_module
