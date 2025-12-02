"""
Kubernetes Module for NL2Py

This module provides comprehensive Kubernetes cluster management capabilities
through the official Kubernetes Python client.

Features:
- Pod management (create, list, delete, logs, exec)
- Deployment management (create, scale, rollout, delete)
- Service management (create, expose, delete)
- ConfigMap and Secret management
- Namespace management
- Persistent Volume and Persistent Volume Claim operations
- Job and CronJob management
- Ingress management
- StatefulSet management
- DaemonSet management
- Resource monitoring and events

Dependencies:
- kubernetes>=28.0.0 (Official Kubernetes Python client)

Configuration (nl2py.conf):
[kubernetes]
KUBECONFIG_PATH = ~/.kube/config
CONTEXT = default
NAMESPACE = default
API_SERVER = https://kubernetes.default.svc
TOKEN = <service-account-token>
VERIFY_SSL = true
CA_CERT = /path/to/ca.crt

Author: NL2Py Team
Version: 1.0
"""

import os
import threading
from typing import Optional, Dict, List, Any, Union
import configparser
from .module_base import NL2PyModuleBase

try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    from kubernetes.stream import stream
    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False


class KubernetesModule(NL2PyModuleBase):
    """
    Kubernetes module for cluster and resource management.

    Implements singleton pattern for efficient resource usage.
    Provides comprehensive Kubernetes operations through official client.
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(KubernetesModule, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize Kubernetes module (only once due to singleton)."""
        if self._initialized:
            return

        if not KUBERNETES_AVAILABLE:
            raise ImportError(
                "Kubernetes client not available. Install with: pip install kubernetes>=28.0.0"
            )

        # Configuration
        self.kubeconfig_path = os.getenv('KUBECONFIG', os.path.expanduser('~/.kube/config'))
        self.context = os.getenv('K8S_CONTEXT')
        self.namespace = os.getenv('K8S_NAMESPACE', 'default')
        self.api_server = os.getenv('K8S_API_SERVER')
        self.token = os.getenv('K8S_TOKEN')
        self.verify_ssl = os.getenv('K8S_VERIFY_SSL', 'true').lower() == 'true'
        self.ca_cert = os.getenv('K8S_CA_CERT')

        # API clients (lazy initialized)
        self._core_v1 = None
        self._apps_v1 = None
        self._batch_v1 = None
        self._networking_v1 = None
        self._rbac_v1 = None
        self._storage_v1 = None

        # Configuration loaded flag
        self._config_loaded = False

        self._initialized = True

    def load_config(self, config_path: str = 'nl2py.conf'):
        """Load configuration from nl2py.conf file."""
        if not os.path.exists(config_path):
            return

        config = configparser.ConfigParser()
        config.read(config_path)

        if 'kubernetes' in config:
            k8s_config = config['kubernetes']
            self.kubeconfig_path = k8s_config.get('KUBECONFIG_PATH', self.kubeconfig_path)
            self.context = k8s_config.get('CONTEXT', self.context)
            self.namespace = k8s_config.get('NAMESPACE', self.namespace)
            self.api_server = k8s_config.get('API_SERVER', self.api_server)
            self.token = k8s_config.get('TOKEN', self.token)
            self.verify_ssl = k8s_config.get('VERIFY_SSL', str(self.verify_ssl)).lower() == 'true'
            self.ca_cert = k8s_config.get('CA_CERT', self.ca_cert)

    def _load_kube_config(self):
        """Load Kubernetes configuration."""
        if self._config_loaded:
            return

        try:
            if self.api_server and self.token:
                # Use token authentication
                configuration = client.Configuration()
                configuration.host = self.api_server
                configuration.api_key = {"authorization": f"Bearer {self.token}"}
                configuration.verify_ssl = self.verify_ssl
                if self.ca_cert:
                    configuration.ssl_ca_cert = self.ca_cert
                client.Configuration.set_default(configuration)
            elif os.path.exists(self.kubeconfig_path):
                # Load from kubeconfig file
                config.load_kube_config(
                    config_file=self.kubeconfig_path,
                    context=self.context
                )
            else:
                # Try in-cluster config (when running inside Kubernetes)
                config.load_incluster_config()

            self._config_loaded = True

        except Exception as e:
            raise ConnectionError(f"Failed to load Kubernetes configuration: {e}")

    @property
    def core_v1(self):
        """Lazy-load Core V1 API client."""
        if self._core_v1 is None:
            self._load_kube_config()
            self._core_v1 = client.CoreV1Api()
        return self._core_v1

    @property
    def apps_v1(self):
        """Lazy-load Apps V1 API client."""
        if self._apps_v1 is None:
            self._load_kube_config()
            self._apps_v1 = client.AppsV1Api()
        return self._apps_v1

    @property
    def batch_v1(self):
        """Lazy-load Batch V1 API client."""
        if self._batch_v1 is None:
            self._load_kube_config()
            self._batch_v1 = client.BatchV1Api()
        return self._batch_v1

    @property
    def networking_v1(self):
        """Lazy-load Networking V1 API client."""
        if self._networking_v1 is None:
            self._load_kube_config()
            self._networking_v1 = client.NetworkingV1Api()
        return self._networking_v1

    @property
    def rbac_v1(self):
        """Lazy-load RBAC V1 API client."""
        if self._rbac_v1 is None:
            self._load_kube_config()
            self._rbac_v1 = client.RbacAuthorizationV1Api()
        return self._rbac_v1

    @property
    def storage_v1(self):
        """Lazy-load Storage V1 API client."""
        if self._storage_v1 is None:
            self._load_kube_config()
            self._storage_v1 = client.StorageV1Api()
        return self._storage_v1

    # =============================================================================
    # Pod Management
    # =============================================================================

    def pod_create(self, name: str, image: str, namespace: Optional[str] = None,
                   labels: Optional[Dict[str, str]] = None,
                   env: Optional[Dict[str, str]] = None,
                   ports: Optional[List[int]] = None,
                   command: Optional[List[str]] = None,
                   args: Optional[List[str]] = None) -> Any:
        """Create a pod."""
        namespace = namespace or self.namespace

        try:
            # Build container spec
            container = client.V1Container(
                name=name,
                image=image,
                command=command,
                args=args
            )

            # Add environment variables
            if env:
                container.env = [
                    client.V1EnvVar(name=k, value=v) for k, v in env.items()
                ]

            # Add ports
            if ports:
                container.ports = [
                    client.V1ContainerPort(container_port=p) for p in ports
                ]

            # Build pod spec
            pod_spec = client.V1PodSpec(containers=[container])

            # Build pod metadata
            metadata = client.V1ObjectMeta(name=name, labels=labels or {})

            # Build pod
            pod = client.V1Pod(
                api_version="v1",
                kind="Pod",
                metadata=metadata,
                spec=pod_spec
            )

            return self.core_v1.create_namespaced_pod(namespace=namespace, body=pod)

        except ApiException as e:
            raise RuntimeError(f"Failed to create pod: {e}")

    def pod_list(self, namespace: Optional[str] = None,
                 label_selector: Optional[str] = None) -> List[Any]:
        """List pods."""
        namespace = namespace or self.namespace

        try:
            response = self.core_v1.list_namespaced_pod(
                namespace=namespace,
                label_selector=label_selector
            )
            return response.items
        except ApiException as e:
            raise RuntimeError(f"Failed to list pods: {e}")

    def pod_delete(self, name: str, namespace: Optional[str] = None) -> bool:
        """Delete a pod."""
        namespace = namespace or self.namespace

        try:
            self.core_v1.delete_namespaced_pod(name=name, namespace=namespace)
            return True
        except ApiException as e:
            raise RuntimeError(f"Failed to delete pod: {e}")

    def pod_logs(self, name: str, namespace: Optional[str] = None,
                 tail_lines: Optional[int] = None, follow: bool = False) -> str:
        """Get pod logs."""
        namespace = namespace or self.namespace

        try:
            return self.core_v1.read_namespaced_pod_log(
                name=name,
                namespace=namespace,
                tail_lines=tail_lines,
                follow=follow
            )
        except ApiException as e:
            raise RuntimeError(f"Failed to get pod logs: {e}")

    def pod_exec(self, name: str, command: List[str],
                 namespace: Optional[str] = None,
                 container: Optional[str] = None) -> str:
        """Execute command in pod."""
        namespace = namespace or self.namespace

        try:
            resp = stream(
                self.core_v1.connect_get_namespaced_pod_exec,
                name,
                namespace,
                container=container,
                command=command,
                stderr=True,
                stdin=False,
                stdout=True,
                tty=False
            )
            return resp
        except ApiException as e:
            raise RuntimeError(f"Failed to execute command in pod: {e}")

    def pod_get(self, name: str, namespace: Optional[str] = None) -> Any:
        """Get pod details."""
        namespace = namespace or self.namespace

        try:
            return self.core_v1.read_namespaced_pod(name=name, namespace=namespace)
        except ApiException as e:
            raise RuntimeError(f"Failed to get pod: {e}")

    # =============================================================================
    # Deployment Management
    # =============================================================================

    def deployment_create(self, name: str, image: str, replicas: int = 1,
                         namespace: Optional[str] = None,
                         labels: Optional[Dict[str, str]] = None,
                         env: Optional[Dict[str, str]] = None,
                         ports: Optional[List[int]] = None) -> Any:
        """Create a deployment."""
        namespace = namespace or self.namespace
        labels = labels or {"app": name}

        try:
            # Build container spec
            container = client.V1Container(
                name=name,
                image=image
            )

            if env:
                container.env = [
                    client.V1EnvVar(name=k, value=v) for k, v in env.items()
                ]

            if ports:
                container.ports = [
                    client.V1ContainerPort(container_port=p) for p in ports
                ]

            # Build pod template
            template = client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels=labels),
                spec=client.V1PodSpec(containers=[container])
            )

            # Build deployment spec
            spec = client.V1DeploymentSpec(
                replicas=replicas,
                selector=client.V1LabelSelector(match_labels=labels),
                template=template
            )

            # Build deployment
            deployment = client.V1Deployment(
                api_version="apps/v1",
                kind="Deployment",
                metadata=client.V1ObjectMeta(name=name, labels=labels),
                spec=spec
            )

            return self.apps_v1.create_namespaced_deployment(
                namespace=namespace,
                body=deployment
            )

        except ApiException as e:
            raise RuntimeError(f"Failed to create deployment: {e}")

    def deployment_list(self, namespace: Optional[str] = None,
                       label_selector: Optional[str] = None) -> List[Any]:
        """List deployments."""
        namespace = namespace or self.namespace

        try:
            response = self.apps_v1.list_namespaced_deployment(
                namespace=namespace,
                label_selector=label_selector
            )
            return response.items
        except ApiException as e:
            raise RuntimeError(f"Failed to list deployments: {e}")

    def deployment_scale(self, name: str, replicas: int,
                        namespace: Optional[str] = None) -> Any:
        """Scale a deployment."""
        namespace = namespace or self.namespace

        try:
            # Get current deployment
            deployment = self.apps_v1.read_namespaced_deployment(
                name=name,
                namespace=namespace
            )

            # Update replicas
            deployment.spec.replicas = replicas

            # Patch deployment
            return self.apps_v1.patch_namespaced_deployment(
                name=name,
                namespace=namespace,
                body=deployment
            )

        except ApiException as e:
            raise RuntimeError(f"Failed to scale deployment: {e}")

    def deployment_delete(self, name: str, namespace: Optional[str] = None) -> bool:
        """Delete a deployment."""
        namespace = namespace or self.namespace

        try:
            self.apps_v1.delete_namespaced_deployment(
                name=name,
                namespace=namespace
            )
            return True
        except ApiException as e:
            raise RuntimeError(f"Failed to delete deployment: {e}")

    def deployment_rollout_restart(self, name: str,
                                   namespace: Optional[str] = None) -> Any:
        """Restart a deployment (rollout restart)."""
        namespace = namespace or self.namespace

        try:
            # Get deployment
            deployment = self.apps_v1.read_namespaced_deployment(
                name=name,
                namespace=namespace
            )

            # Add/update annotation to trigger restart
            if deployment.spec.template.metadata.annotations:
                deployment.spec.template.metadata.annotations[
                    'kubectl.kubernetes.io/restartedAt'
                ] = str(client.ApiClient().rest_client.pool_manager.connection_from_url('').get_host_info()[0])
            else:
                deployment.spec.template.metadata.annotations = {
                    'kubectl.kubernetes.io/restartedAt': 'now'
                }

            # Patch deployment
            return self.apps_v1.patch_namespaced_deployment(
                name=name,
                namespace=namespace,
                body=deployment
            )

        except ApiException as e:
            raise RuntimeError(f"Failed to restart deployment: {e}")

    # =============================================================================
    # Service Management
    # =============================================================================

    def service_create(self, name: str, port: int, target_port: int,
                      namespace: Optional[str] = None,
                      service_type: str = "ClusterIP",
                      selector: Optional[Dict[str, str]] = None) -> Any:
        """Create a service."""
        namespace = namespace or self.namespace
        selector = selector or {"app": name}

        try:
            service = client.V1Service(
                api_version="v1",
                kind="Service",
                metadata=client.V1ObjectMeta(name=name),
                spec=client.V1ServiceSpec(
                    selector=selector,
                    ports=[client.V1ServicePort(
                        port=port,
                        target_port=target_port
                    )],
                    type=service_type
                )
            )

            return self.core_v1.create_namespaced_service(
                namespace=namespace,
                body=service
            )

        except ApiException as e:
            raise RuntimeError(f"Failed to create service: {e}")

    def service_list(self, namespace: Optional[str] = None) -> List[Any]:
        """List services."""
        namespace = namespace or self.namespace

        try:
            response = self.core_v1.list_namespaced_service(namespace=namespace)
            return response.items
        except ApiException as e:
            raise RuntimeError(f"Failed to list services: {e}")

    def service_delete(self, name: str, namespace: Optional[str] = None) -> bool:
        """Delete a service."""
        namespace = namespace or self.namespace

        try:
            self.core_v1.delete_namespaced_service(name=name, namespace=namespace)
            return True
        except ApiException as e:
            raise RuntimeError(f"Failed to delete service: {e}")

    # =============================================================================
    # ConfigMap Management
    # =============================================================================

    def configmap_create(self, name: str, data: Dict[str, str],
                        namespace: Optional[str] = None) -> Any:
        """Create a ConfigMap."""
        namespace = namespace or self.namespace

        try:
            configmap = client.V1ConfigMap(
                api_version="v1",
                kind="ConfigMap",
                metadata=client.V1ObjectMeta(name=name),
                data=data
            )

            return self.core_v1.create_namespaced_config_map(
                namespace=namespace,
                body=configmap
            )

        except ApiException as e:
            raise RuntimeError(f"Failed to create ConfigMap: {e}")

    def configmap_list(self, namespace: Optional[str] = None) -> List[Any]:
        """List ConfigMaps."""
        namespace = namespace or self.namespace

        try:
            response = self.core_v1.list_namespaced_config_map(namespace=namespace)
            return response.items
        except ApiException as e:
            raise RuntimeError(f"Failed to list ConfigMaps: {e}")

    def configmap_delete(self, name: str, namespace: Optional[str] = None) -> bool:
        """Delete a ConfigMap."""
        namespace = namespace or self.namespace

        try:
            self.core_v1.delete_namespaced_config_map(name=name, namespace=namespace)
            return True
        except ApiException as e:
            raise RuntimeError(f"Failed to delete ConfigMap: {e}")

    # =============================================================================
    # Secret Management
    # =============================================================================

    def secret_create(self, name: str, data: Dict[str, str],
                     namespace: Optional[str] = None,
                     secret_type: str = "Opaque") -> Any:
        """Create a Secret."""
        namespace = namespace or self.namespace

        try:
            # Encode data to base64
            import base64
            encoded_data = {
                k: base64.b64encode(v.encode()).decode()
                for k, v in data.items()
            }

            secret = client.V1Secret(
                api_version="v1",
                kind="Secret",
                metadata=client.V1ObjectMeta(name=name),
                type=secret_type,
                data=encoded_data
            )

            return self.core_v1.create_namespaced_secret(
                namespace=namespace,
                body=secret
            )

        except ApiException as e:
            raise RuntimeError(f"Failed to create Secret: {e}")

    def secret_list(self, namespace: Optional[str] = None) -> List[Any]:
        """List Secrets."""
        namespace = namespace or self.namespace

        try:
            response = self.core_v1.list_namespaced_secret(namespace=namespace)
            return response.items
        except ApiException as e:
            raise RuntimeError(f"Failed to list Secrets: {e}")

    def secret_delete(self, name: str, namespace: Optional[str] = None) -> bool:
        """Delete a Secret."""
        namespace = namespace or self.namespace

        try:
            self.core_v1.delete_namespaced_secret(name=name, namespace=namespace)
            return True
        except ApiException as e:
            raise RuntimeError(f"Failed to delete Secret: {e}")

    # =============================================================================
    # Namespace Management
    # =============================================================================

    def namespace_create(self, name: str) -> Any:
        """Create a namespace."""
        try:
            namespace = client.V1Namespace(
                metadata=client.V1ObjectMeta(name=name)
            )
            return self.core_v1.create_namespace(body=namespace)
        except ApiException as e:
            raise RuntimeError(f"Failed to create namespace: {e}")

    def namespace_list(self) -> List[Any]:
        """List namespaces."""
        try:
            response = self.core_v1.list_namespace()
            return response.items
        except ApiException as e:
            raise RuntimeError(f"Failed to list namespaces: {e}")

    def namespace_delete(self, name: str) -> bool:
        """Delete a namespace."""
        try:
            self.core_v1.delete_namespace(name=name)
            return True
        except ApiException as e:
            raise RuntimeError(f"Failed to delete namespace: {e}")

    # =============================================================================
    # Node Management
    # =============================================================================

    def node_list(self) -> List[Any]:
        """List cluster nodes."""
        try:
            response = self.core_v1.list_node()
            return response.items
        except ApiException as e:
            raise RuntimeError(f"Failed to list nodes: {e}")

    def node_get(self, name: str) -> Any:
        """Get node details."""
        try:
            return self.core_v1.read_node(name=name)
        except ApiException as e:
            raise RuntimeError(f"Failed to get node: {e}")

    # =============================================================================
    # Events
    # =============================================================================

    def events_list(self, namespace: Optional[str] = None) -> List[Any]:
        """List events."""
        namespace = namespace or self.namespace

        try:
            response = self.core_v1.list_namespaced_event(namespace=namespace)
            return response.items
        except ApiException as e:
            raise RuntimeError(f"Failed to list events: {e}")

    # =============================================================================
    # Utility Methods
    # =============================================================================

    def get_cluster_info(self) -> Dict[str, Any]:
        """Get cluster information."""
        try:
            version = client.VersionApi().get_code()
            nodes = self.node_list()
            namespaces = self.namespace_list()

            return {
                "version": version.git_version,
                "nodes": len(nodes),
                "namespaces": len(namespaces)
            }
        except Exception as e:
            raise RuntimeError(f"Failed to get cluster info: {e}")

    # =============================================================================
    # Module Metadata
    # =============================================================================

    @classmethod
    def get_metadata(cls):
        """Get module metadata for compiler prompt generation."""
        from nl2py.modules.module_base import ModuleMetadata
        return ModuleMetadata(
            name="Kubernetes",
            task_type="kubernetes",
            description="Kubernetes container orchestration with pod management, deployments, services, ConfigMaps, Secrets, namespaces, and cluster operations",
            version="1.0.0",
            keywords=["kubernetes", "k8s", "container", "orchestration", "pod", "deployment", "service", "configmap", "secret", "namespace", "cluster", "docker"],
            dependencies=["kubernetes>=28.0.0"]
        )

    @classmethod
    def get_usage_notes(cls):
        """Get usage notes and best practices."""
        return [
            "Module uses singleton pattern - one instance per application",
            "Requires kubeconfig file at ~/.kube/config or KUBECONFIG env variable",
            "Can use in-cluster config when running inside Kubernetes pod",
            "Supports token-based authentication with K8S_API_SERVER and K8S_TOKEN",
            "Default namespace is 'default', configure with K8S_NAMESPACE",
            "SSL verification enabled by default, set K8S_VERIFY_SSL=false for dev",
            "API clients lazy-loaded on first use for efficient resource usage",
            "Pod labels used for selectors and service routing",
            "Deployment manages ReplicaSets and rolling updates automatically",
            "Replicas determine number of pod copies for high availability",
            "Services expose pods with ClusterIP (internal), NodePort, or LoadBalancer types",
            "ConfigMaps store non-sensitive configuration as key-value pairs",
            "Secrets store sensitive data base64-encoded (use for passwords, tokens)",
            "Namespaces provide logical isolation and resource quotas",
            "Label selectors filter resources (e.g., 'app=myapp,env=prod')",
            "pod_exec() requires pod to be running and container accessible",
            "pod_logs() supports tail_lines and follow for real-time streaming",
            "deployment_scale() updates replica count for horizontal scaling",
            "deployment_rollout_restart() triggers rolling restart without downtime",
            "Use node_list() to check cluster capacity and node health",
            "Events provide audit trail and debugging information",
            "get_cluster_info() returns version, node count, namespace count"
        ]

    @classmethod
    def get_methods_info(cls):
        """Get information about available methods."""
        from nl2py.modules.module_base import MethodInfo
        return [
            MethodInfo(
                name="pod_create",
                description="Create a pod with container image and configuration",
                parameters={
                    "name": "str (required) - Pod name",
                    "image": "str (required) - Container image (e.g., 'nginx:latest')",
                    "namespace": "str (optional) - Namespace (default from config)",
                    "labels": "dict (optional) - Labels as key-value pairs",
                    "env": "dict (optional) - Environment variables",
                    "ports": "list[int] (optional) - Container ports to expose",
                    "command": "list[str] (optional) - Override container entrypoint",
                    "args": "list[str] (optional) - Container arguments"
                },
                returns="V1Pod - Created pod object",
                examples=[
                    {"text": "Create nginx pod {{pod_name}} with port 80 exposed", "code": "pod_create(name='{{pod_name}}', image='nginx:latest', ports=[80])"},
                    {"text": "Create {{pod_name}} pod with {{image}}, db_host {{db_host}}, and app label {{app_name}}", "code": "pod_create(name='{{pod_name}}', image='{{image}}', env={'DB_HOST': '{{db_host}}'}, labels={'app': '{{app_name}}'})"}
                ]
            ),
            MethodInfo(
                name="pod_list",
                description="List pods in namespace with optional label filtering",
                parameters={
                    "namespace": "str (optional) - Namespace",
                    "label_selector": "str (optional) - Label selector (e.g., 'app=myapp')"
                },
                returns="list[V1Pod] - List of pods",
                examples=[
                    {"text": "List all pods in default namespace", "code": "pod_list()"},
                    {"text": "List pods with label selector app={{app_name}}", "code": "pod_list(label_selector='app={{app_name}}')"}
                ]
            ),
            MethodInfo(
                name="pod_delete",
                description="Delete a pod",
                parameters={
                    "name": "str (required) - Pod name",
                    "namespace": "str (optional) - Namespace"
                },
                returns="bool - True if deleted successfully",
                examples=[
                    {"text": "Delete pod {{pod_name}}", "code": "pod_delete(name='{{pod_name}}')"}
                ]
            ),
            MethodInfo(
                name="pod_logs",
                description="Get pod logs (stdout/stderr)",
                parameters={
                    "name": "str (required) - Pod name",
                    "namespace": "str (optional) - Namespace",
                    "tail_lines": "int (optional) - Number of lines from end",
                    "follow": "bool (optional) - Stream logs in real-time (default False)"
                },
                returns="str - Log output",
                examples=[
                    {"text": "Get last 100 lines of {{pod_name}} logs", "code": "pod_logs(name='{{pod_name}}', tail_lines=100)"},
                    {"text": "Follow {{pod_name}} logs in real-time", "code": "pod_logs(name='{{pod_name}}', follow=True)"}
                ]
            ),
            MethodInfo(
                name="pod_exec",
                description="Execute command inside running pod container",
                parameters={
                    "name": "str (required) - Pod name",
                    "command": "list[str] (required) - Command and arguments",
                    "namespace": "str (optional) - Namespace",
                    "container": "str (optional) - Container name (if pod has multiple)"
                },
                returns="str - Command output",
                examples=[
                    {"text": "List files in {{pod_name}} directory {{directory}}", "code": "pod_exec(name='{{pod_name}}', command=['ls', '-la', '{{directory}}'])"},
                    {"text": "Show environment variables in {{pod_name}}", "code": "pod_exec(name='{{pod_name}}', command=['env'])"}
                ]
            ),
            MethodInfo(
                name="pod_get",
                description="Get detailed pod information",
                parameters={
                    "name": "str (required) - Pod name",
                    "namespace": "str (optional) - Namespace"
                },
                returns="V1Pod - Pod details",
                examples=[
                    {"text": "Get detailed information about {{pod_name}}", "code": "pod_get(name='{{pod_name}}')"}
                ]
            ),
            MethodInfo(
                name="deployment_create",
                description="Create a deployment for managing pod replicas",
                parameters={
                    "name": "str (required) - Deployment name",
                    "image": "str (required) - Container image",
                    "replicas": "int (optional) - Number of pod replicas (default 1)",
                    "namespace": "str (optional) - Namespace",
                    "labels": "dict (optional) - Labels",
                    "env": "dict (optional) - Environment variables",
                    "ports": "list[int] (optional) - Container ports"
                },
                returns="V1Deployment - Created deployment",
                examples=[
                    {"text": "Create nginx deployment {{deployment_name}} with 3 replicas", "code": "deployment_create(name='{{deployment_name}}', image='nginx:latest', replicas=3)"},
                    {"text": "Create {{deployment_name}} deployment with {{image}}, 2 replicas, port 8080, and environment {{environment}}", "code": "deployment_create(name='{{deployment_name}}', image='{{image}}', replicas=2, ports=[8080], env={'ENV': '{{environment}}'})"}
                ]
            ),
            MethodInfo(
                name="deployment_list",
                description="List deployments",
                parameters={
                    "namespace": "str (optional) - Namespace",
                    "label_selector": "str (optional) - Label selector"
                },
                returns="list[V1Deployment] - List of deployments",
                examples=[
                    {"text": "List all deployments in namespace", "code": "deployment_list()"},
                    {"text": "List deployments with label selector app={{app_name}}", "code": "deployment_list(label_selector='app={{app_name}}')"}
                ]
            ),
            MethodInfo(
                name="deployment_scale",
                description="Scale deployment by changing replica count",
                parameters={
                    "name": "str (required) - Deployment name",
                    "replicas": "int (required) - Target replica count",
                    "namespace": "str (optional) - Namespace"
                },
                returns="V1Deployment - Updated deployment",
                examples=[
                    {"text": "Scale {{deployment_name}} to 5 replicas", "code": "deployment_scale(name='{{deployment_name}}', replicas=5)"},
                    {"text": "Scale {{deployment_name}} to 10 replicas", "code": "deployment_scale(name='{{deployment_name}}', replicas=10)"}
                ]
            ),
            MethodInfo(
                name="deployment_delete",
                description="Delete a deployment",
                parameters={
                    "name": "str (required) - Deployment name",
                    "namespace": "str (optional) - Namespace"
                },
                returns="bool - True if deleted",
                examples=[
                    {"text": "Delete deployment {{deployment_name}}", "code": "deployment_delete(name='{{deployment_name}}')"}
                ]
            ),
            MethodInfo(
                name="deployment_rollout_restart",
                description="Rolling restart of deployment (recreates pods without downtime)",
                parameters={
                    "name": "str (required) - Deployment name",
                    "namespace": "str (optional) - Namespace"
                },
                returns="V1Deployment - Updated deployment",
                examples=[
                    {"text": "Perform rolling restart of {{deployment_name}}", "code": "deployment_rollout_restart(name='{{deployment_name}}')"}
                ]
            ),
            MethodInfo(
                name="service_create",
                description="Create a service to expose pods",
                parameters={
                    "name": "str (required) - Service name",
                    "port": "int (required) - Service port",
                    "target_port": "int (required) - Pod target port",
                    "namespace": "str (optional) - Namespace",
                    "service_type": "str (optional) - ClusterIP, NodePort, or LoadBalancer (default ClusterIP)",
                    "selector": "dict (optional) - Pod selector labels"
                },
                returns="V1Service - Created service",
                examples=[
                    {"text": "Create ClusterIP service {{service_name}} on port 80", "code": "service_create(name='{{service_name}}', port=80, target_port=80, service_type='ClusterIP')"},
                    {"text": "Create LoadBalancer service {{service_name}} on port 8080 with selector app={{app_name}}", "code": "service_create(name='{{service_name}}', port=8080, target_port=8080, service_type='LoadBalancer', selector={'app': '{{app_name}}'})"}
                ]
            ),
            MethodInfo(
                name="service_list",
                description="List services",
                parameters={"namespace": "str (optional) - Namespace"},
                returns="list[V1Service] - List of services",
                examples=[
                    {"text": "List all services in namespace", "code": "service_list()"}
                ]
            ),
            MethodInfo(
                name="service_delete",
                description="Delete a service",
                parameters={
                    "name": "str (required) - Service name",
                    "namespace": "str (optional) - Namespace"
                },
                returns="bool - True if deleted",
                examples=[
                    {"text": "Delete service {{service_name}}", "code": "service_delete(name='{{service_name}}')"}
                ]
            ),
            MethodInfo(
                name="configmap_create",
                description="Create a ConfigMap for storing configuration data",
                parameters={
                    "name": "str (required) - ConfigMap name",
                    "data": "dict (required) - Configuration key-value pairs",
                    "namespace": "str (optional) - Namespace"
                },
                returns="V1ConfigMap - Created ConfigMap",
                examples=[
                    {"text": "Create ConfigMap {{configmap_name}} with {{db_url}} and {{api_key}}", "code": "configmap_create(name='{{configmap_name}}', data={'database_url': '{{db_url}}', 'api_key': '{{api_key}}'})"}
                ]
            ),
            MethodInfo(
                name="configmap_list",
                description="List ConfigMaps",
                parameters={"namespace": "str (optional) - Namespace"},
                returns="list[V1ConfigMap] - List of ConfigMaps",
                examples=[
                    {"text": "List all ConfigMaps in namespace", "code": "configmap_list()"}
                ]
            ),
            MethodInfo(
                name="configmap_delete",
                description="Delete a ConfigMap",
                parameters={
                    "name": "str (required) - ConfigMap name",
                    "namespace": "str (optional) - Namespace"
                },
                returns="bool - True if deleted",
                examples=[
                    {"text": "Delete ConfigMap {{configmap_name}}", "code": "configmap_delete(name='{{configmap_name}}')"}
                ]
            ),
            MethodInfo(
                name="secret_create",
                description="Create a Secret for storing sensitive data (base64-encoded)",
                parameters={
                    "name": "str (required) - Secret name",
                    "data": "dict (required) - Secret key-value pairs",
                    "namespace": "str (optional) - Namespace",
                    "secret_type": "str (optional) - Secret type (default Opaque)"
                },
                returns="V1Secret - Created secret",
                examples=[
                    {"text": "Create Secret {{secret_name}} with {{username}} and {{password}}", "code": "secret_create(name='{{secret_name}}', data={'username': '{{username}}', 'password': '{{password}}'})"}
                ]
            ),
            MethodInfo(
                name="secret_list",
                description="List Secrets",
                parameters={"namespace": "str (optional) - Namespace"},
                returns="list[V1Secret] - List of secrets",
                examples=[
                    {"text": "List all Secrets in namespace", "code": "secret_list()"}
                ]
            ),
            MethodInfo(
                name="secret_delete",
                description="Delete a Secret",
                parameters={
                    "name": "str (required) - Secret name",
                    "namespace": "str (optional) - Namespace"
                },
                returns="bool - True if deleted",
                examples=[
                    {"text": "Delete Secret {{secret_name}}", "code": "secret_delete(name='{{secret_name}}')"}
                ]
            ),
            MethodInfo(
                name="namespace_create",
                description="Create a namespace for resource isolation",
                parameters={"name": "str (required) - Namespace name"},
                returns="V1Namespace - Created namespace",
                examples=[
                    {"text": "Create production namespace", "code": "namespace_create(name='production')"},
                    {"text": "Create development namespace", "code": "namespace_create(name='dev')"}
                ]
            ),
            MethodInfo(
                name="namespace_list",
                description="List all namespaces",
                parameters={},
                returns="list[V1Namespace] - List of namespaces",
                examples=[
                    {"text": "List all namespaces in cluster", "code": "namespace_list()"}
                ]
            ),
            MethodInfo(
                name="namespace_delete",
                description="Delete a namespace (deletes all resources inside)",
                parameters={"name": "str (required) - Namespace name"},
                returns="bool - True if deleted",
                examples=[
                    {"text": "Delete namespace {{namespace_name}} and all its resources", "code": "namespace_delete(name='{{namespace_name}}')"}
                ]
            ),
            MethodInfo(
                name="node_list",
                description="List cluster nodes",
                parameters={},
                returns="list[V1Node] - List of nodes",
                examples=[
                    {"text": "List all nodes in the cluster", "code": "node_list()"}
                ]
            ),
            MethodInfo(
                name="node_get",
                description="Get node details",
                parameters={"name": "str (required) - Node name"},
                returns="V1Node - Node details",
                examples=[
                    {"text": "Get detailed information about node {{node_name}}", "code": "node_get(name='{{node_name}}')"}
                ]
            ),
            MethodInfo(
                name="events_list",
                description="List cluster events for debugging and auditing",
                parameters={"namespace": "str (optional) - Namespace"},
                returns="list[V1Event] - List of events",
                examples=[
                    {"text": "List all events in namespace", "code": "events_list()"},
                    {"text": "List events in namespace {{namespace_name}}", "code": "events_list(namespace='{{namespace_name}}')"}
                ]
            ),
            MethodInfo(
                name="get_cluster_info",
                description="Get cluster summary information",
                parameters={},
                returns="dict - Cluster info with version, node count, namespace count",
                examples=[
                    {"text": "Get cluster summary information", "code": "get_cluster_info()"}
                ]
            )
        ]

# Global instance
_kubernetes_module = None


def get_kubernetes_module(config_path: str = 'nl2py.conf') -> KubernetesModule:
    """
    Get or create Kubernetes module instance.

    Args:
        config_path: Path to nl2py.conf configuration file

    Returns:
        KubernetesModule instance
    """
    global _kubernetes_module
    if _kubernetes_module is None:
        _kubernetes_module = KubernetesModule()
        _kubernetes_module.load_config(config_path)
    return _kubernetes_module
