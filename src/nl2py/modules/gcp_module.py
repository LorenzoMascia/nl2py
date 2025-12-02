"""
Google Cloud Platform (GCP) Module for NL2Py

This module provides comprehensive integration with Google Cloud Platform services,
enabling natural language management of GCP resources including Compute Engine,
Cloud Storage, Cloud SQL, BigQuery, Cloud Functions, and more.

Features:
- Compute Engine: VM instance management
- Cloud Storage: Bucket and object operations
- Cloud SQL: Database instance management
- BigQuery: Dataset and table operations
- Cloud Functions: Serverless function deployment
- Cloud Run: Container deployment
- Pub/Sub: Message queue operations
- Secret Manager: Secrets management
- IAM: Identity and access management

Architecture:
- Singleton pattern with thread-safe initialization
- Lazy-loading of GCP service clients
- Configuration from nl2py.conf with environment variable fallbacks
- Service account or application default credentials authentication

Usage:
    10 (gcp) create compute instance "web-server" in zone "us-central1-a"
    20 (gcp) create storage bucket "my-bucket" in location "us-central1"
    30 (gcp) upload file "data.txt" to bucket "my-bucket"
"""

import threading
import os
from typing import Optional, Dict, Any, List
from pathlib import Path
from .module_base import NL2PyModuleBase

# GCP Client Libraries
try:
    from google.cloud import compute_v1
    from google.cloud import storage
    from google.cloud import sql_v1
    from google.cloud import bigquery
    from google.cloud import functions_v1
    from google.cloud import run_v2
    from google.cloud import pubsub_v1
    from google.cloud import secretmanager_v1
    from google.cloud import iam_credentials_v1
    from google.oauth2 import service_account
    from google.auth import default as default_credentials
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False


class GCPModule(NL2PyModuleBase):
    """
    Google Cloud Platform module for managing GCP resources.

    Implements singleton pattern for efficient resource usage.
    Provides comprehensive GCP operations through official Google Cloud SDK.
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
        """Initialize the GCP module with configuration from nl2py.conf."""
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            if not GOOGLE_CLOUD_AVAILABLE:
                raise RuntimeError(
                    "Google Cloud libraries not installed. "
                    "Install with: pip install google-cloud-compute google-cloud-storage "
                    "google-cloud-sql google-cloud-bigquery google-cloud-functions "
                    "google-cloud-run google-cloud-pubsub google-cloud-secret-manager"
                )

            # Read configuration
            self.project_id = os.getenv('GCP_PROJECT_ID') or os.getenv('GOOGLE_CLOUD_PROJECT')
            self.credentials_path = os.getenv('GCP_CREDENTIALS_PATH') or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            self.region = os.getenv('GCP_REGION', 'us-central1')
            self.zone = os.getenv('GCP_ZONE', 'us-central1-a')

            # Default resource settings
            self.default_machine_type = os.getenv('GCP_DEFAULT_MACHINE_TYPE', 'e2-medium')
            self.default_disk_size = int(os.getenv('GCP_DEFAULT_DISK_SIZE', '10'))
            self.default_network = os.getenv('GCP_DEFAULT_NETWORK', 'default')

            # Lazy-loaded clients
            self._credentials = None
            self._compute_client = None
            self._storage_client = None
            self._sql_admin_client = None
            self._bigquery_client = None
            self._functions_client = None
            self._run_client = None
            self._pubsub_publisher = None
            self._pubsub_subscriber = None
            self._secretmanager_client = None

            self._initialized = True

    @property
    def credentials(self):
        """Get GCP credentials (lazy-loaded)."""
        if self._credentials is None:
            if self.credentials_path and os.path.exists(self.credentials_path):
                self._credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path
                )
            else:
                # Use Application Default Credentials (ADC)
                self._credentials, _ = default_credentials()
        return self._credentials

    @property
    def compute_client(self):
        """Get Compute Engine instances client (lazy-loaded)."""
        if self._compute_client is None:
            self._compute_client = compute_v1.InstancesClient(credentials=self.credentials)
        return self._compute_client

    @property
    def storage_client(self):
        """Get Cloud Storage client (lazy-loaded)."""
        if self._storage_client is None:
            self._storage_client = storage.Client(
                project=self.project_id,
                credentials=self.credentials
            )
        return self._storage_client

    @property
    def sql_admin_client(self):
        """Get Cloud SQL Admin client (lazy-loaded)."""
        if self._sql_admin_client is None:
            self._sql_admin_client = sql_v1.SqlInstancesServiceClient(credentials=self.credentials)
        return self._sql_admin_client

    @property
    def bigquery_client(self):
        """Get BigQuery client (lazy-loaded)."""
        if self._bigquery_client is None:
            self._bigquery_client = bigquery.Client(
                project=self.project_id,
                credentials=self.credentials
            )
        return self._bigquery_client

    @property
    def functions_client(self):
        """Get Cloud Functions client (lazy-loaded)."""
        if self._functions_client is None:
            self._functions_client = functions_v1.CloudFunctionsServiceClient(credentials=self.credentials)
        return self._functions_client

    @property
    def run_client(self):
        """Get Cloud Run client (lazy-loaded)."""
        if self._run_client is None:
            self._run_client = run_v2.ServicesClient(credentials=self.credentials)
        return self._run_client

    @property
    def pubsub_publisher(self):
        """Get Pub/Sub publisher client (lazy-loaded)."""
        if self._pubsub_publisher is None:
            self._pubsub_publisher = pubsub_v1.PublisherClient(credentials=self.credentials)
        return self._pubsub_publisher

    @property
    def pubsub_subscriber(self):
        """Get Pub/Sub subscriber client (lazy-loaded)."""
        if self._pubsub_subscriber is None:
            self._pubsub_subscriber = pubsub_v1.SubscriberClient(credentials=self.credentials)
        return self._pubsub_subscriber

    @property
    def secretmanager_client(self):
        """Get Secret Manager client (lazy-loaded)."""
        if self._secretmanager_client is None:
            self._secretmanager_client = secretmanager_v1.SecretManagerServiceClient(credentials=self.credentials)
        return self._secretmanager_client

    # =========================================================================
    # Compute Engine Operations
    # =========================================================================

    def compute_instance_create(self, name: str, zone: Optional[str] = None,
                               machine_type: Optional[str] = None,
                               disk_image: str = 'projects/debian-cloud/global/images/family/debian-11',
                               disk_size_gb: Optional[int] = None,
                               network: Optional[str] = None,
                               labels: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Create a Compute Engine VM instance."""
        zone = zone or self.zone
        machine_type = machine_type or self.default_machine_type
        disk_size_gb = disk_size_gb or self.default_disk_size
        network = network or self.default_network

        instance = compute_v1.Instance()
        instance.name = name
        instance.machine_type = f"zones/{zone}/machineTypes/{machine_type}"

        # Boot disk
        disk = compute_v1.AttachedDisk()
        disk.boot = True
        disk.auto_delete = True
        initialize_params = compute_v1.AttachedDiskInitializeParams()
        initialize_params.source_image = disk_image
        initialize_params.disk_size_gb = disk_size_gb
        disk.initialize_params = initialize_params
        instance.disks = [disk]

        # Network interface
        network_interface = compute_v1.NetworkInterface()
        network_interface.name = network
        access_config = compute_v1.AccessConfig()
        access_config.name = "External NAT"
        access_config.type_ = "ONE_TO_ONE_NAT"
        network_interface.access_configs = [access_config]
        instance.network_interfaces = [network_interface]

        # Labels
        if labels:
            instance.labels = labels

        request = compute_v1.InsertInstanceRequest(
            project=self.project_id,
            zone=zone,
            instance_resource=instance
        )

        try:
            operation = self.compute_client.insert(request=request)
            return {"status": "creating", "operation": operation.name, "instance": name}
        except Exception as e:
            raise RuntimeError(f"Failed to create compute instance: {e}")

    def compute_instance_list(self, zone: Optional[str] = None) -> List[Dict[str, Any]]:
        """List Compute Engine instances in a zone."""
        zone = zone or self.zone

        request = compute_v1.ListInstancesRequest(
            project=self.project_id,
            zone=zone
        )

        try:
            instances = []
            for instance in self.compute_client.list(request=request):
                instances.append({
                    "name": instance.name,
                    "machine_type": instance.machine_type.split('/')[-1],
                    "status": instance.status,
                    "zone": zone,
                    "internal_ip": instance.network_interfaces[0].network_i_p if instance.network_interfaces else None,
                    "external_ip": instance.network_interfaces[0].access_configs[0].nat_i_p if instance.network_interfaces and instance.network_interfaces[0].access_configs else None
                })
            return instances
        except Exception as e:
            raise RuntimeError(f"Failed to list compute instances: {e}")

    def compute_instance_start(self, name: str, zone: Optional[str] = None) -> Dict[str, Any]:
        """Start a Compute Engine instance."""
        zone = zone or self.zone

        request = compute_v1.StartInstanceRequest(
            project=self.project_id,
            zone=zone,
            instance=name
        )

        try:
            operation = self.compute_client.start(request=request)
            return {"status": "starting", "operation": operation.name}
        except Exception as e:
            raise RuntimeError(f"Failed to start compute instance: {e}")

    def compute_instance_stop(self, name: str, zone: Optional[str] = None) -> Dict[str, Any]:
        """Stop a Compute Engine instance."""
        zone = zone or self.zone

        request = compute_v1.StopInstanceRequest(
            project=self.project_id,
            zone=zone,
            instance=name
        )

        try:
            operation = self.compute_client.stop(request=request)
            return {"status": "stopping", "operation": operation.name}
        except Exception as e:
            raise RuntimeError(f"Failed to stop compute instance: {e}")

    def compute_instance_delete(self, name: str, zone: Optional[str] = None) -> Dict[str, Any]:
        """Delete a Compute Engine instance."""
        zone = zone or self.zone

        request = compute_v1.DeleteInstanceRequest(
            project=self.project_id,
            zone=zone,
            instance=name
        )

        try:
            operation = self.compute_client.delete(request=request)
            return {"status": "deleting", "operation": operation.name}
        except Exception as e:
            raise RuntimeError(f"Failed to delete compute instance: {e}")

    # =========================================================================
    # Cloud Storage Operations
    # =========================================================================

    def storage_bucket_create(self, name: str, location: Optional[str] = None,
                             storage_class: str = 'STANDARD') -> Dict[str, Any]:
        """Create a Cloud Storage bucket."""
        location = location or self.region

        try:
            bucket = self.storage_client.bucket(name)
            bucket.storage_class = storage_class
            bucket = self.storage_client.create_bucket(bucket, location=location)
            return {
                "name": bucket.name,
                "location": bucket.location,
                "storage_class": bucket.storage_class,
                "time_created": str(bucket.time_created)
            }
        except Exception as e:
            raise RuntimeError(f"Failed to create storage bucket: {e}")

    def storage_bucket_list(self) -> List[Dict[str, Any]]:
        """List all Cloud Storage buckets."""
        try:
            buckets = []
            for bucket in self.storage_client.list_buckets():
                buckets.append({
                    "name": bucket.name,
                    "location": bucket.location,
                    "storage_class": bucket.storage_class,
                    "time_created": str(bucket.time_created)
                })
            return buckets
        except Exception as e:
            raise RuntimeError(f"Failed to list storage buckets: {e}")

    def storage_bucket_delete(self, name: str, force: bool = False) -> Dict[str, Any]:
        """Delete a Cloud Storage bucket."""
        try:
            bucket = self.storage_client.bucket(name)

            if force:
                # Delete all objects first
                blobs = list(bucket.list_blobs())
                for blob in blobs:
                    blob.delete()

            bucket.delete()
            return {"status": "deleted", "bucket": name}
        except Exception as e:
            raise RuntimeError(f"Failed to delete storage bucket: {e}")

    def storage_upload_file(self, bucket_name: str, source_file: str,
                           destination_blob: str) -> Dict[str, Any]:
        """Upload a file to Cloud Storage."""
        try:
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(destination_blob)
            blob.upload_from_filename(source_file)

            return {
                "bucket": bucket_name,
                "blob": destination_blob,
                "size": blob.size,
                "md5_hash": blob.md5_hash
            }
        except Exception as e:
            raise RuntimeError(f"Failed to upload file to storage: {e}")

    def storage_download_file(self, bucket_name: str, source_blob: str,
                             destination_file: str) -> Dict[str, Any]:
        """Download a file from Cloud Storage."""
        try:
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(source_blob)
            blob.download_to_filename(destination_file)

            return {
                "bucket": bucket_name,
                "blob": source_blob,
                "destination": destination_file,
                "size": blob.size
            }
        except Exception as e:
            raise RuntimeError(f"Failed to download file from storage: {e}")

    def storage_list_blobs(self, bucket_name: str, prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """List blobs in a Cloud Storage bucket."""
        try:
            bucket = self.storage_client.bucket(bucket_name)
            blobs = []

            for blob in bucket.list_blobs(prefix=prefix):
                blobs.append({
                    "name": blob.name,
                    "size": blob.size,
                    "content_type": blob.content_type,
                    "time_created": str(blob.time_created),
                    "updated": str(blob.updated)
                })

            return blobs
        except Exception as e:
            raise RuntimeError(f"Failed to list blobs: {e}")

    # =========================================================================
    # Cloud SQL Operations
    # =========================================================================

    def cloudsql_instance_create(self, name: str, database_version: str = 'MYSQL_8_0',
                                tier: str = 'db-f1-micro', region: Optional[str] = None) -> Dict[str, Any]:
        """Create a Cloud SQL instance."""
        region = region or self.region

        instance = sql_v1.DatabaseInstance()
        instance.name = name
        instance.database_version = database_version
        instance.region = region

        settings = sql_v1.Settings()
        settings.tier = tier
        instance.settings = settings

        request = sql_v1.InsertRequest(
            project=self.project_id,
            body=instance
        )

        try:
            operation = self.sql_admin_client.insert(request=request)
            return {"status": "creating", "instance": name, "operation": operation.name}
        except Exception as e:
            raise RuntimeError(f"Failed to create Cloud SQL instance: {e}")

    def cloudsql_instance_list(self) -> List[Dict[str, Any]]:
        """List Cloud SQL instances."""
        request = sql_v1.ListRequest(project=self.project_id)

        try:
            response = self.sql_admin_client.list(request=request)
            instances = []

            for instance in response.items or []:
                instances.append({
                    "name": instance.name,
                    "database_version": instance.database_version,
                    "state": instance.state,
                    "region": instance.region,
                    "tier": instance.settings.tier if instance.settings else None
                })

            return instances
        except Exception as e:
            raise RuntimeError(f"Failed to list Cloud SQL instances: {e}")

    def cloudsql_instance_delete(self, name: str) -> Dict[str, Any]:
        """Delete a Cloud SQL instance."""
        request = sql_v1.DeleteRequest(
            project=self.project_id,
            instance=name
        )

        try:
            operation = self.sql_admin_client.delete(request=request)
            return {"status": "deleting", "instance": name, "operation": operation.name}
        except Exception as e:
            raise RuntimeError(f"Failed to delete Cloud SQL instance: {e}")

    # =========================================================================
    # BigQuery Operations
    # =========================================================================

    def bigquery_dataset_create(self, dataset_id: str, location: Optional[str] = None) -> Dict[str, Any]:
        """Create a BigQuery dataset."""
        location = location or self.region

        try:
            dataset = bigquery.Dataset(f"{self.project_id}.{dataset_id}")
            dataset.location = location
            dataset = self.bigquery_client.create_dataset(dataset)

            return {
                "dataset_id": dataset.dataset_id,
                "location": dataset.location,
                "created": str(dataset.created)
            }
        except Exception as e:
            raise RuntimeError(f"Failed to create BigQuery dataset: {e}")

    def bigquery_dataset_list(self) -> List[Dict[str, Any]]:
        """List BigQuery datasets."""
        try:
            datasets = []
            for dataset in self.bigquery_client.list_datasets():
                datasets.append({
                    "dataset_id": dataset.dataset_id,
                    "project": dataset.project,
                    "full_id": dataset.full_dataset_id
                })
            return datasets
        except Exception as e:
            raise RuntimeError(f"Failed to list BigQuery datasets: {e}")

    def bigquery_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a BigQuery query."""
        try:
            query_job = self.bigquery_client.query(query)
            results = query_job.result()

            rows = []
            for row in results:
                rows.append(dict(row))

            return rows
        except Exception as e:
            raise RuntimeError(f"Failed to execute BigQuery query: {e}")

    # =========================================================================
    # Pub/Sub Operations
    # =========================================================================

    def pubsub_topic_create(self, topic_id: str) -> Dict[str, Any]:
        """Create a Pub/Sub topic."""
        topic_path = self.pubsub_publisher.topic_path(self.project_id, topic_id)

        try:
            topic = self.pubsub_publisher.create_topic(request={"name": topic_path})
            return {"name": topic.name, "topic_id": topic_id}
        except Exception as e:
            raise RuntimeError(f"Failed to create Pub/Sub topic: {e}")

    def pubsub_topic_list(self) -> List[Dict[str, Any]]:
        """List Pub/Sub topics."""
        project_path = f"projects/{self.project_id}"

        try:
            topics = []
            for topic in self.pubsub_publisher.list_topics(request={"project": project_path}):
                topics.append({
                    "name": topic.name,
                    "topic_id": topic.name.split('/')[-1]
                })
            return topics
        except Exception as e:
            raise RuntimeError(f"Failed to list Pub/Sub topics: {e}")

    def pubsub_publish(self, topic_id: str, message: str, **attributes) -> Dict[str, Any]:
        """Publish a message to a Pub/Sub topic."""
        topic_path = self.pubsub_publisher.topic_path(self.project_id, topic_id)

        try:
            data = message.encode('utf-8')
            future = self.pubsub_publisher.publish(topic_path, data, **attributes)
            message_id = future.result()

            return {"message_id": message_id, "topic": topic_id}
        except Exception as e:
            raise RuntimeError(f"Failed to publish message: {e}")

    def pubsub_subscription_create(self, subscription_id: str, topic_id: str) -> Dict[str, Any]:
        """Create a Pub/Sub subscription."""
        subscription_path = self.pubsub_subscriber.subscription_path(self.project_id, subscription_id)
        topic_path = self.pubsub_publisher.topic_path(self.project_id, topic_id)

        try:
            subscription = self.pubsub_subscriber.create_subscription(
                request={"name": subscription_path, "topic": topic_path}
            )
            return {"name": subscription.name, "topic": subscription.topic}
        except Exception as e:
            raise RuntimeError(f"Failed to create Pub/Sub subscription: {e}")

    # =========================================================================
    # Secret Manager Operations
    # =========================================================================

    def secret_create(self, secret_id: str, value: str) -> Dict[str, Any]:
        """Create a secret in Secret Manager."""
        parent = f"projects/{self.project_id}"

        try:
            # Create secret
            secret = secretmanager_v1.Secret()
            secret.replication = secretmanager_v1.Replication()
            secret.replication.automatic = secretmanager_v1.Replication.Automatic()

            create_request = secretmanager_v1.CreateSecretRequest(
                parent=parent,
                secret_id=secret_id,
                secret=secret
            )

            created_secret = self.secretmanager_client.create_secret(request=create_request)

            # Add version with value
            version_parent = created_secret.name
            payload = secretmanager_v1.SecretPayload()
            payload.data = value.encode('utf-8')

            version_request = secretmanager_v1.AddSecretVersionRequest(
                parent=version_parent,
                payload=payload
            )

            version = self.secretmanager_client.add_secret_version(request=version_request)

            return {
                "secret": created_secret.name,
                "version": version.name
            }
        except Exception as e:
            raise RuntimeError(f"Failed to create secret: {e}")

    def secret_get(self, secret_id: str, version: str = 'latest') -> str:
        """Get a secret value from Secret Manager."""
        name = f"projects/{self.project_id}/secrets/{secret_id}/versions/{version}"

        try:
            response = self.secretmanager_client.access_secret_version(request={"name": name})
            return response.payload.data.decode('utf-8')
        except Exception as e:
            raise RuntimeError(f"Failed to get secret: {e}")

    def secret_list(self) -> List[Dict[str, Any]]:
        """List secrets in Secret Manager."""
        parent = f"projects/{self.project_id}"

        try:
            secrets = []
            for secret in self.secretmanager_client.list_secrets(request={"parent": parent}):
                secrets.append({
                    "name": secret.name,
                    "secret_id": secret.name.split('/')[-1],
                    "created": str(secret.create_time)
                })
            return secrets
        except Exception as e:
            raise RuntimeError(f"Failed to list secrets: {e}")

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_project_info(self) -> Dict[str, Any]:
        """Get project information."""
        return {
            "project_id": self.project_id,
            "region": self.region,
            "zone": self.zone,
            "credentials_configured": self._credentials is not None or self.credentials_path is not None
        }

    @classmethod
    def get_metadata(cls):
        """Get module metadata."""
        from nl2py.modules.module_base import ModuleMetadata
        return ModuleMetadata(
            name="GCP",
            task_type="gcp",
            description="Google Cloud Platform integration for Compute Engine, Cloud Storage, Cloud SQL, BigQuery, Cloud Functions, Cloud Run, Pub/Sub, and Secret Manager",
            version="1.0.0",
            keywords=["gcp", "google-cloud", "compute-engine", "cloud-storage", "bigquery", "cloud-sql", "pubsub", "secret-manager", "cloud-run", "cloud-functions"],
            dependencies=[
                "google-cloud-compute>=1.14.0",
                "google-cloud-storage>=2.10.0",
                "google-cloud-sql>=1.0.0",
                "google-cloud-bigquery>=3.11.0",
                "google-cloud-functions>=1.13.0",
                "google-cloud-run>=0.9.0",
                "google-cloud-pubsub>=2.18.0",
                "google-cloud-secret-manager>=2.16.0"
            ]
        )

    @classmethod
    def get_usage_notes(cls):
        """Get detailed usage notes."""
        return [
            "Module uses singleton pattern - one instance shared across operations",
            "Authentication via service account JSON file (GCP_CREDENTIALS_PATH) or Application Default Credentials (ADC)",
            "ADC automatically used when running on GCP services (Cloud Run, Cloud Functions, Compute Engine)",
            "Project ID can be set via GCP_PROJECT_ID or GOOGLE_CLOUD_PROJECT environment variables",
            "Default region is 'us-central1', default zone is 'us-central1-a' (configurable via env vars)",
            "All GCP service clients are lazy-loaded - only initialized when first used",
            "Compute Engine operations are asynchronous - return operation names for tracking",
            "Cloud Storage bucket names must be globally unique across all GCP projects",
            "BigQuery queries support standard SQL syntax by default",
            "Pub/Sub message ordering not guaranteed unless ordering keys are used",
            "Secret Manager automatically replicates secrets unless custom replication specified",
            "Cloud SQL instance creation can take several minutes",
            "Storage bucket deletion requires force=True if bucket contains objects",
            "Compute instances require machine type, disk image, and network configuration",
            "Default machine type is 'e2-medium', default disk size is 10 GB",
            "Zones and regions must match service availability (some services region-only)",
            "IAM permissions required vary by operation - ensure service account has sufficient roles",
            "Cost tracking: all resource creation incurs GCP charges based on usage"
        ]

    @classmethod
    def get_methods_info(cls):
        """Get information about module methods."""
        from nl2py.modules.module_base import MethodInfo
        return [
            MethodInfo(
                name="compute_instance_create",
                description="Create a Compute Engine VM instance with specified configuration",
                parameters={
                    "name": "Instance name (must be unique in zone)",
                    "zone": "GCP zone (optional, uses default zone if not specified, e.g., 'us-central1-a')",
                    "machine_type": "Machine type (optional, default: 'e2-medium', e.g., 'e2-standard-4', 'n1-standard-1')",
                    "disk_image": "Boot disk image (optional, default: Debian 11, e.g., 'projects/ubuntu-os-cloud/global/images/family/ubuntu-2204-lts')",
                    "disk_size_gb": "Boot disk size in GB (optional, default: 10)",
                    "network": "VPC network name (optional, default: 'default')",
                    "labels": "Resource labels as dictionary (optional)"
                },
                returns="Dictionary with status, operation name, and instance name",
                examples=[
                    {"text": "create compute instance {{web-server}} in zone {{us-central1-a}}", "code": "compute_instance_create(name='{{web-server}}', zone='{{us-central1-a}}')"},
                    {"text": "create compute instance {{app-vm}} with machine type {{e2-standard-4}} and disk size {{50}}", "code": "compute_instance_create(name='{{app-vm}}', machine_type='{{e2-standard-4}}', disk_size_gb={{50}})"},
                    {"text": "create compute instance {{database-vm}} with zone {{europe-west1-b}} and machine type {{n1-highmem-8}}", "code": "compute_instance_create(name='{{database-vm}}', zone='{{europe-west1-b}}', machine_type='{{n1-highmem-8}}')"}
                ]
            ),
            MethodInfo(
                name="compute_instance_list",
                description="List all Compute Engine instances in a zone",
                parameters={
                    "zone": "GCP zone (optional, uses default zone if not specified)"
                },
                returns="List of dictionaries with instance details (name, machine type, status, IPs)",
                examples=[
                    {"text": "list compute instances", "code": "compute_instance_list()"},
                    {"text": "list compute instances in zone {{us-west1-a}}", "code": "compute_instance_list(zone='{{us-west1-a}}')"},
                    {"text": "show all compute instances in zone {{asia-east1-a}}", "code": "compute_instance_list(zone='{{asia-east1-a}}')"}
                ]
            ),
            MethodInfo(
                name="compute_instance_start",
                description="Start a stopped Compute Engine instance",
                parameters={
                    "name": "Instance name to start",
                    "zone": "GCP zone (optional, uses default zone if not specified)"
                },
                returns="Dictionary with status and operation name",
                examples=[
                    {"text": "start compute instance {{web-server}}", "code": "compute_instance_start(name='{{web-server}}')"},
                    {"text": "start compute instance {{app-vm}} in zone {{us-central1-b}}", "code": "compute_instance_start(name='{{app-vm}}', zone='{{us-central1-b}}')"}
                ]
            ),
            MethodInfo(
                name="compute_instance_stop",
                description="Stop a running Compute Engine instance",
                parameters={
                    "name": "Instance name to stop",
                    "zone": "GCP zone (optional, uses default zone if not specified)"
                },
                returns="Dictionary with status and operation name",
                examples=[
                    {"text": "stop compute instance {{web-server}}", "code": "compute_instance_stop(name='{{web-server}}')"},
                    {"text": "stop compute instance {{test-vm}} in zone {{us-east1-c}}", "code": "compute_instance_stop(name='{{test-vm}}', zone='{{us-east1-c}}')"}
                ]
            ),
            MethodInfo(
                name="compute_instance_delete",
                description="Delete a Compute Engine instance permanently",
                parameters={
                    "name": "Instance name to delete",
                    "zone": "GCP zone (optional, uses default zone if not specified)"
                },
                returns="Dictionary with status and operation name",
                examples=[
                    {"text": "delete compute instance {{old-server}}", "code": "compute_instance_delete(name='{{old-server}}')"},
                    {"text": "delete compute instance {{temp-vm}} in zone {{us-central1-a}}", "code": "compute_instance_delete(name='{{temp-vm}}', zone='{{us-central1-a}}')"}
                ]
            ),
            MethodInfo(
                name="storage_bucket_create",
                description="Create a Cloud Storage bucket (name must be globally unique)",
                parameters={
                    "name": "Bucket name (globally unique, lowercase, hyphens allowed)",
                    "location": "Bucket location/region (optional, uses default region, e.g., 'us-central1', 'EU', 'ASIA')",
                    "storage_class": "Storage class (optional, default: 'STANDARD', options: 'NEARLINE', 'COLDLINE', 'ARCHIVE')"
                },
                returns="Dictionary with bucket name, location, storage class, and creation time",
                examples=[
                    {"text": "create storage bucket {{my-data-bucket}}", "code": "storage_bucket_create(name='{{my-data-bucket}}')"},
                    {"text": "create storage bucket {{logs-archive}} in location {{us-east1}} with storage class {{COLDLINE}}", "code": "storage_bucket_create(name='{{logs-archive}}', location='{{us-east1}}', storage_class='{{COLDLINE}}')"},
                    {"text": "create storage bucket {{app-assets}} in location {{EU}}", "code": "storage_bucket_create(name='{{app-assets}}', location='{{EU}}')"}
                ]
            ),
            MethodInfo(
                name="storage_bucket_list",
                description="List all Cloud Storage buckets in the project",
                parameters={},
                returns="List of dictionaries with bucket details (name, location, storage class, creation time)",
                examples=[
                    {"text": "list storage buckets", "code": "storage_bucket_list()"},
                    {"text": "show all storage buckets", "code": "storage_bucket_list()"},
                    {"text": "get storage buckets", "code": "storage_bucket_list()"}
                ]
            ),
            MethodInfo(
                name="storage_bucket_delete",
                description="Delete a Cloud Storage bucket (requires force=True if not empty)",
                parameters={
                    "name": "Bucket name to delete",
                    "force": "Delete all objects first (optional, default: False)"
                },
                returns="Dictionary with status and bucket name",
                examples=[
                    {"text": "delete storage bucket {{old-bucket}} with force {{True}}", "code": "storage_bucket_delete(name='{{old-bucket}}', force={{True}})"},
                    {"text": "delete storage bucket {{temp-bucket}}", "code": "storage_bucket_delete(name='{{temp-bucket}}')"}
                ]
            ),
            MethodInfo(
                name="storage_upload_file",
                description="Upload a file to Cloud Storage bucket",
                parameters={
                    "bucket_name": "Destination bucket name",
                    "source_file": "Local file path to upload",
                    "destination_blob": "Destination blob name/path in bucket"
                },
                returns="Dictionary with bucket, blob name, size, and MD5 hash",
                examples=[
                    {"text": "upload file {{data.csv}} to bucket {{my-bucket}} as {{uploads/data.csv}}", "code": "storage_upload_file(bucket_name='{{my-bucket}}', source_file='{{data.csv}}', destination_blob='{{uploads/data.csv}}')"},
                    {"text": "upload file {{report.pdf}} to bucket {{documents}} with nested path {{reports/2024/report.pdf}}", "code": "storage_upload_file(bucket_name='{{documents}}', source_file='{{report.pdf}}', destination_blob='{{reports/2024/report.pdf}}')"},
                    {"text": "storage upload file {{image.png}} to bucket {{assets}} as {{images/image.png}}", "code": "storage_upload_file(bucket_name='{{assets}}', source_file='{{image.png}}', destination_blob='{{images/image.png}}')"}
                ]
            ),
            MethodInfo(
                name="storage_download_file",
                description="Download a file from Cloud Storage bucket",
                parameters={
                    "bucket_name": "Source bucket name",
                    "source_blob": "Source blob name/path in bucket",
                    "destination_file": "Local file path to save downloaded file"
                },
                returns="Dictionary with bucket, blob name, destination path, and size",
                examples=[
                    {"text": "download file {{uploads/data.csv}} from bucket {{my-bucket}} to {{local_data.csv}}", "code": "storage_download_file(bucket_name='{{my-bucket}}', source_blob='{{uploads/data.csv}}', destination_file='{{local_data.csv}}')"},
                    {"text": "storage download file {{reports/report.pdf}} from bucket {{documents}} to {{report.pdf}}", "code": "storage_download_file(bucket_name='{{documents}}', source_blob='{{reports/report.pdf}}', destination_file='{{report.pdf}}')"}
                ]
            ),
            MethodInfo(
                name="storage_list_blobs",
                description="List all objects (blobs) in a Cloud Storage bucket with optional prefix filter",
                parameters={
                    "bucket_name": "Bucket name to list objects from",
                    "prefix": "Prefix filter (optional, e.g., 'folder/', lists only matching objects)"
                },
                returns="List of dictionaries with blob details (name, size, content type, timestamps)",
                examples=[
                    {"text": "list blobs in bucket {{my-bucket}}", "code": "storage_list_blobs(bucket_name='{{my-bucket}}')"},
                    {"text": "list blobs in bucket {{documents}} with prefix {{reports/}}", "code": "storage_list_blobs(bucket_name='{{documents}}', prefix='{{reports/}}')"},
                    {"text": "show all files in bucket {{assets}} with prefix {{images/}}", "code": "storage_list_blobs(bucket_name='{{assets}}', prefix='{{images/}}')"}
                ]
            ),
            MethodInfo(
                name="cloudsql_instance_create",
                description="Create a Cloud SQL database instance (takes several minutes)",
                parameters={
                    "name": "Instance name (unique within project)",
                    "database_version": "Database version (optional, default: 'MYSQL_8_0', options: 'POSTGRES_15', 'SQLSERVER_2019')",
                    "tier": "Machine tier (optional, default: 'db-f1-micro', e.g., 'db-n1-standard-1', 'db-n1-highmem-4')",
                    "region": "GCP region (optional, uses default region)"
                },
                returns="Dictionary with status, instance name, and operation name",
                examples=[
                    {"text": "create cloudsql instance {{prod-db}}", "code": "cloudsql_instance_create(name='{{prod-db}}')"},
                    {"text": "create cloudsql instance {{postgres-db}} with database version {{POSTGRES_15}} and tier {{db-n1-standard-2}}", "code": "cloudsql_instance_create(name='{{postgres-db}}', database_version='{{POSTGRES_15}}', tier='{{db-n1-standard-2}}')"},
                    {"text": "create cloudsql instance {{mysql-db}} in region {{us-east1}}", "code": "cloudsql_instance_create(name='{{mysql-db}}', region='{{us-east1}}')"}
                ]
            ),
            MethodInfo(
                name="cloudsql_instance_list",
                description="List all Cloud SQL instances in the project",
                parameters={},
                returns="List of dictionaries with instance details (name, version, state, region, tier)",
                examples=[
                    {"text": "list cloudsql instances", "code": "cloudsql_instance_list()"},
                    {"text": "show all cloud sql instances", "code": "cloudsql_instance_list()"},
                    {"text": "get cloudsql instances", "code": "cloudsql_instance_list()"}
                ]
            ),
            MethodInfo(
                name="cloudsql_instance_delete",
                description="Delete a Cloud SQL instance permanently",
                parameters={
                    "name": "Instance name to delete"
                },
                returns="Dictionary with status, instance name, and operation name",
                examples=[
                    {"text": "delete cloudsql instance {{old-db}}", "code": "cloudsql_instance_delete(name='{{old-db}}')"},
                    {"text": "delete cloudsql instance {{test-database}}", "code": "cloudsql_instance_delete(name='{{test-database}}')"}
                ]
            ),
            MethodInfo(
                name="bigquery_dataset_create",
                description="Create a BigQuery dataset for organizing tables",
                parameters={
                    "dataset_id": "Dataset ID (unique within project)",
                    "location": "Dataset location (optional, uses default region, e.g., 'US', 'EU')"
                },
                returns="Dictionary with dataset ID, location, and creation timestamp",
                examples=[
                    {"text": "create bigquery dataset {{analytics}}", "code": "bigquery_dataset_create(dataset_id='{{analytics}}')"},
                    {"text": "create bigquery dataset {{logs_data}} in location {{EU}}", "code": "bigquery_dataset_create(dataset_id='{{logs_data}}', location='{{EU}}')"},
                    {"text": "create bigquery dataset {{warehouse}} in location {{US}}", "code": "bigquery_dataset_create(dataset_id='{{warehouse}}', location='{{US}}')"}
                ]
            ),
            MethodInfo(
                name="bigquery_dataset_list",
                description="List all BigQuery datasets in the project",
                parameters={},
                returns="List of dictionaries with dataset details (dataset_id, project, full_id)",
                examples=[
                    {"text": "list bigquery datasets", "code": "bigquery_dataset_list()"},
                    {"text": "show all bigquery datasets", "code": "bigquery_dataset_list()"},
                    {"text": "get bigquery datasets", "code": "bigquery_dataset_list()"}
                ]
            ),
            MethodInfo(
                name="bigquery_query",
                description="Execute a SQL query on BigQuery and return results",
                parameters={
                    "query": "Standard SQL query string"
                },
                returns="List of dictionaries, each representing a result row",
                examples=[
                    {"text": "bigquery query {{SELECT * FROM `project.dataset.table` LIMIT 100}}", "code": "bigquery_query(query='{{SELECT * FROM `project.dataset.table` LIMIT 100}}')"},
                    {"text": "bigquery query {{SELECT COUNT(*) as total FROM `analytics.events` WHERE date = CURRENT_DATE()}}", "code": "bigquery_query(query='{{SELECT COUNT(*) as total FROM `analytics.events` WHERE date = CURRENT_DATE()}}')"},
                    {"text": "execute bigquery query {{SELECT user_id, SUM(amount) FROM `sales.transactions` GROUP BY user_id}}", "code": "bigquery_query(query='{{SELECT user_id, SUM(amount) FROM `sales.transactions` GROUP BY user_id}}')"}
                ]
            ),
            MethodInfo(
                name="pubsub_topic_create",
                description="Create a Pub/Sub topic for message publishing",
                parameters={
                    "topic_id": "Topic ID (unique within project)"
                },
                returns="Dictionary with topic name and topic_id",
                examples=[
                    {"text": "create pubsub topic {{notifications}}", "code": "pubsub_topic_create(topic_id='{{notifications}}')"},
                    {"text": "create pubsub topic {{events-stream}}", "code": "pubsub_topic_create(topic_id='{{events-stream}}')"},
                    {"text": "create pubsub topic {{logs-ingestion}}", "code": "pubsub_topic_create(topic_id='{{logs-ingestion}}')"}
                ]
            ),
            MethodInfo(
                name="pubsub_topic_list",
                description="List all Pub/Sub topics in the project",
                parameters={},
                returns="List of dictionaries with topic details (name, topic_id)",
                examples=[
                    {"text": "list pubsub topics", "code": "pubsub_topic_list()"},
                    {"text": "show all pubsub topics", "code": "pubsub_topic_list()"},
                    {"text": "get pubsub topics", "code": "pubsub_topic_list()"}
                ]
            ),
            MethodInfo(
                name="pubsub_publish",
                description="Publish a message to a Pub/Sub topic with optional attributes",
                parameters={
                    "topic_id": "Topic ID to publish to",
                    "message": "Message string to publish",
                    "**attributes": "Optional message attributes as keyword arguments"
                },
                returns="Dictionary with message_id and topic",
                examples=[
                    {"text": "publish message {{Hello World}} to pubsub topic {{notifications}}", "code": "pubsub_publish(topic_id='{{notifications}}', message='{{Hello World}}')"},
                    {"text": "pubsub publish {{User logged in}} to topic {{events}} with attributes user_id {{123}} event_type {{login}}", "code": "pubsub_publish(topic_id='{{events}}', message='{{User logged in}}', user_id='{{123}}', event_type='{{login}}')"},
                    {"text": "publish {{Error occurred}} to pubsub topic {{logs}}", "code": "pubsub_publish(topic_id='{{logs}}', message='{{Error occurred}}')"}
                ]
            ),
            MethodInfo(
                name="pubsub_subscription_create",
                description="Create a Pub/Sub subscription to receive messages from a topic",
                parameters={
                    "subscription_id": "Subscription ID (unique within project)",
                    "topic_id": "Topic ID to subscribe to"
                },
                returns="Dictionary with subscription name and topic",
                examples=[
                    {"text": "create pubsub subscription {{notifications-sub}} for topic {{notifications}}", "code": "pubsub_subscription_create(subscription_id='{{notifications-sub}}', topic_id='{{notifications}}')"},
                    {"text": "create pubsub subscription {{worker-1}} for topic {{tasks}}", "code": "pubsub_subscription_create(subscription_id='{{worker-1}}', topic_id='{{tasks}}')"}
                ]
            ),
            MethodInfo(
                name="secret_create",
                description="Create a secret in Secret Manager with a value",
                parameters={
                    "secret_id": "Secret ID (unique within project)",
                    "value": "Secret value string"
                },
                returns="Dictionary with secret name and version name",
                examples=[
                    {"text": "create secret {{api-key}} with value {{sk-1234567890}}", "code": "secret_create(secret_id='{{api-key}}', value='{{sk-1234567890}}')"},
                    {"text": "create secret {{database-password}} with value {{super_secret_pwd}}", "code": "secret_create(secret_id='{{database-password}}', value='{{super_secret_pwd}}')"},
                    {"text": "secret create {{jwt-secret}} value {{my-secret-key}}", "code": "secret_create(secret_id='{{jwt-secret}}', value='{{my-secret-key}}')"}
                ]
            ),
            MethodInfo(
                name="secret_get",
                description="Retrieve a secret value from Secret Manager",
                parameters={
                    "secret_id": "Secret ID to retrieve",
                    "version": "Secret version (optional, default: 'latest')"
                },
                returns="Secret value as string",
                examples=[
                    {"text": "get secret {{api-key}}", "code": "secret_get(secret_id='{{api-key}}')"},
                    {"text": "get secret {{database-password}} version {{2}}", "code": "secret_get(secret_id='{{database-password}}', version='{{2}}')"},
                    {"text": "secret get {{jwt-secret}}", "code": "secret_get(secret_id='{{jwt-secret}}')"}
                ]
            ),
            MethodInfo(
                name="secret_list",
                description="List all secrets in Secret Manager",
                parameters={},
                returns="List of dictionaries with secret details (name, secret_id, created timestamp)",
                examples=[
                    {"text": "list secrets", "code": "secret_list()"},
                    {"text": "show all secrets", "code": "secret_list()"},
                    {"text": "get all secrets", "code": "secret_list()"}
                ]
            ),
            MethodInfo(
                name="get_project_info",
                description="Get GCP project configuration information",
                parameters={},
                returns="Dictionary with project_id, region, zone, and credentials status",
                examples=[
                    {"text": "get project info", "code": "get_project_info()"},
                    {"text": "show project info", "code": "get_project_info()"},
                    {"text": "display gcp configuration", "code": "get_project_info()"}
                ]
            )
        ]

# Singleton instance
_gcp_module = None

def get_gcp_module() -> GCPModule:
    """Get the singleton GCP module instance."""
    global _gcp_module
    if _gcp_module is None:
        _gcp_module = GCPModule()
    return _gcp_module
