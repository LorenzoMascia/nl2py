"""
Prometheus Module for NL2Py

This module provides comprehensive Prometheus monitoring and observability capabilities.
It enables metric collection, exposition, and querying from Prometheus servers.

Features:
- Metric Types: Counter, Gauge, Histogram, Summary
- Metric Collection: Increment, set, observe, time operations
- Metric Exposition: HTTP endpoint for Prometheus scraping
- PromQL Queries: Query Prometheus server with PromQL
- Labels: Multi-dimensional metrics with labels
- Pushgateway: Push metrics to Prometheus Pushgateway
- Custom Collectors: Register custom metric collectors
- Metric Registry: Manage multiple metric registries

Author: NL2Py Team
License: MIT
"""

import threading
import time
import os
from typing import Optional, Dict, List, Any, Union
from prometheus_client import (
    Counter, Gauge, Histogram, Summary,
    CollectorRegistry, push_to_gateway, delete_from_gateway,
    start_http_server, generate_latest, REGISTRY
)
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily
from prometheus_api_client import PrometheusConnect
import requests
from .module_base import NL2PyModuleBase


class PrometheusModule(NL2PyModuleBase):
    """
    Prometheus module for monitoring and observability.

    Provides comprehensive Prometheus integration including:
    - Creating and managing metrics (Counter, Gauge, Histogram, Summary)
    - Exposing metrics via HTTP endpoint
    - Querying Prometheus server with PromQL
    - Pushing metrics to Pushgateway
    - Multi-dimensional labels
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        """Singleton pattern - only one instance allowed."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize Prometheus module with configuration."""
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            # Load configuration
            self._load_config()

            # Metric storage
            self._metrics = {}
            self._registry = CollectorRegistry() if self.use_custom_registry else REGISTRY

            # Prometheus client for queries
            self._prometheus_client = None

            # HTTP server for metric exposition
            self._http_server_started = False

            self._initialized = True

    def _load_config(self):
        """Load configuration from environment or config file."""
        # Prometheus server settings (for queries)
        self.prometheus_url = os.getenv('PROMETHEUS_URL', 'http://localhost:9090')
        self.prometheus_headers = {}

        # Metric exposition settings
        self.exposition_port = int(os.getenv('PROMETHEUS_EXPOSITION_PORT', '8000'))
        self.exposition_addr = os.getenv('PROMETHEUS_EXPOSITION_ADDR', '0.0.0.0')

        # Pushgateway settings
        self.pushgateway_url = os.getenv('PROMETHEUS_PUSHGATEWAY_URL', 'localhost:9091')
        self.pushgateway_job = os.getenv('PROMETHEUS_PUSHGATEWAY_JOB', 'aibasic')

        # Default metric settings
        self.default_namespace = os.getenv('PROMETHEUS_NAMESPACE', 'aibasic')
        self.default_subsystem = os.getenv('PROMETHEUS_SUBSYSTEM', '')

        # Registry settings
        self.use_custom_registry = os.getenv('PROMETHEUS_CUSTOM_REGISTRY', 'false').lower() == 'true'

        # Auto-start HTTP server
        self.auto_start_http = os.getenv('PROMETHEUS_AUTO_START_HTTP', 'false').lower() == 'true'

    @property
    def prometheus_client(self):
        """Get Prometheus API client (lazy-loaded)."""
        if self._prometheus_client is None:
            try:
                self._prometheus_client = PrometheusConnect(
                    url=self.prometheus_url,
                    headers=self.prometheus_headers,
                    disable_ssl=False
                )
            except Exception as e:
                raise RuntimeError(f"Failed to connect to Prometheus: {e}")
        return self._prometheus_client

    def _get_metric_name(self, name: str, namespace: Optional[str] = None,
                         subsystem: Optional[str] = None) -> str:
        """Build full metric name with namespace and subsystem."""
        parts = []
        if namespace or self.default_namespace:
            parts.append(namespace or self.default_namespace)
        if subsystem or self.default_subsystem:
            parts.append(subsystem or self.default_subsystem)
        parts.append(name)
        return '_'.join(parts)

    # ============================================================================
    # Metric Creation
    # ============================================================================

    def create_counter(self, name: str, description: str,
                      labels: Optional[List[str]] = None,
                      namespace: Optional[str] = None,
                      subsystem: Optional[str] = None) -> str:
        """
        Create a Counter metric.

        Args:
            name: Metric name
            description: Metric description
            labels: Label names for multi-dimensional metrics
            namespace: Metric namespace (default: from config)
            subsystem: Metric subsystem (default: from config)

        Returns:
            Metric identifier
        """
        try:
            metric_name = self._get_metric_name(name, namespace, subsystem)

            if metric_name in self._metrics:
                return metric_name

            counter = Counter(
                name=metric_name,
                documentation=description,
                labelnames=labels or [],
                registry=self._registry
            )

            self._metrics[metric_name] = {
                'type': 'counter',
                'metric': counter,
                'labels': labels or []
            }

            return metric_name
        except Exception as e:
            raise RuntimeError(f"Failed to create counter: {e}")

    def create_gauge(self, name: str, description: str,
                    labels: Optional[List[str]] = None,
                    namespace: Optional[str] = None,
                    subsystem: Optional[str] = None) -> str:
        """
        Create a Gauge metric.

        Args:
            name: Metric name
            description: Metric description
            labels: Label names for multi-dimensional metrics
            namespace: Metric namespace
            subsystem: Metric subsystem

        Returns:
            Metric identifier
        """
        try:
            metric_name = self._get_metric_name(name, namespace, subsystem)

            if metric_name in self._metrics:
                return metric_name

            gauge = Gauge(
                name=metric_name,
                documentation=description,
                labelnames=labels or [],
                registry=self._registry
            )

            self._metrics[metric_name] = {
                'type': 'gauge',
                'metric': gauge,
                'labels': labels or []
            }

            return metric_name
        except Exception as e:
            raise RuntimeError(f"Failed to create gauge: {e}")

    def create_histogram(self, name: str, description: str,
                        buckets: Optional[List[float]] = None,
                        labels: Optional[List[str]] = None,
                        namespace: Optional[str] = None,
                        subsystem: Optional[str] = None) -> str:
        """
        Create a Histogram metric.

        Args:
            name: Metric name
            description: Metric description
            buckets: Histogram buckets (default: [.005, .01, .025, .05, .075, .1, .25, .5, .75, 1.0, 2.5, 5.0, 7.5, 10.0, +Inf])
            labels: Label names
            namespace: Metric namespace
            subsystem: Metric subsystem

        Returns:
            Metric identifier
        """
        try:
            metric_name = self._get_metric_name(name, namespace, subsystem)

            if metric_name in self._metrics:
                return metric_name

            histogram = Histogram(
                name=metric_name,
                documentation=description,
                labelnames=labels or [],
                buckets=buckets or (.005, .01, .025, .05, .075, .1, .25, .5, .75, 1.0, 2.5, 5.0, 7.5, 10.0),
                registry=self._registry
            )

            self._metrics[metric_name] = {
                'type': 'histogram',
                'metric': histogram,
                'labels': labels or [],
                'buckets': buckets
            }

            return metric_name
        except Exception as e:
            raise RuntimeError(f"Failed to create histogram: {e}")

    def create_summary(self, name: str, description: str,
                      labels: Optional[List[str]] = None,
                      namespace: Optional[str] = None,
                      subsystem: Optional[str] = None) -> str:
        """
        Create a Summary metric.

        Args:
            name: Metric name
            description: Metric description
            labels: Label names
            namespace: Metric namespace
            subsystem: Metric subsystem

        Returns:
            Metric identifier
        """
        try:
            metric_name = self._get_metric_name(name, namespace, subsystem)

            if metric_name in self._metrics:
                return metric_name

            summary = Summary(
                name=metric_name,
                documentation=description,
                labelnames=labels or [],
                registry=self._registry
            )

            self._metrics[metric_name] = {
                'type': 'summary',
                'metric': summary,
                'labels': labels or []
            }

            return metric_name
        except Exception as e:
            raise RuntimeError(f"Failed to create summary: {e}")

    # ============================================================================
    # Metric Operations
    # ============================================================================

    def counter_inc(self, metric_name: str, value: float = 1.0,
                   labels: Optional[Dict[str, str]] = None):
        """
        Increment a counter.

        Args:
            metric_name: Counter name
            value: Increment value (default: 1.0)
            labels: Label values
        """
        try:
            if metric_name not in self._metrics:
                raise ValueError(f"Metric '{metric_name}' not found")

            metric_info = self._metrics[metric_name]
            if metric_info['type'] != 'counter':
                raise ValueError(f"Metric '{metric_name}' is not a counter")

            counter = metric_info['metric']

            if labels:
                counter.labels(**labels).inc(value)
            else:
                counter.inc(value)
        except Exception as e:
            raise RuntimeError(f"Failed to increment counter: {e}")

    def gauge_set(self, metric_name: str, value: float,
                 labels: Optional[Dict[str, str]] = None):
        """
        Set gauge value.

        Args:
            metric_name: Gauge name
            value: Gauge value
            labels: Label values
        """
        try:
            if metric_name not in self._metrics:
                raise ValueError(f"Metric '{metric_name}' not found")

            metric_info = self._metrics[metric_name]
            if metric_info['type'] != 'gauge':
                raise ValueError(f"Metric '{metric_name}' is not a gauge")

            gauge = metric_info['metric']

            if labels:
                gauge.labels(**labels).set(value)
            else:
                gauge.set(value)
        except Exception as e:
            raise RuntimeError(f"Failed to set gauge: {e}")

    def gauge_inc(self, metric_name: str, value: float = 1.0,
                 labels: Optional[Dict[str, str]] = None):
        """Increment gauge value."""
        try:
            if metric_name not in self._metrics:
                raise ValueError(f"Metric '{metric_name}' not found")

            metric_info = self._metrics[metric_name]
            if metric_info['type'] != 'gauge':
                raise ValueError(f"Metric '{metric_name}' is not a gauge")

            gauge = metric_info['metric']

            if labels:
                gauge.labels(**labels).inc(value)
            else:
                gauge.inc(value)
        except Exception as e:
            raise RuntimeError(f"Failed to increment gauge: {e}")

    def gauge_dec(self, metric_name: str, value: float = 1.0,
                 labels: Optional[Dict[str, str]] = None):
        """Decrement gauge value."""
        try:
            if metric_name not in self._metrics:
                raise ValueError(f"Metric '{metric_name}' not found")

            metric_info = self._metrics[metric_name]
            if metric_info['type'] != 'gauge':
                raise ValueError(f"Metric '{metric_name}' is not a gauge")

            gauge = metric_info['metric']

            if labels:
                gauge.labels(**labels).dec(value)
            else:
                gauge.dec(value)
        except Exception as e:
            raise RuntimeError(f"Failed to decrement gauge: {e}")

    def histogram_observe(self, metric_name: str, value: float,
                         labels: Optional[Dict[str, str]] = None):
        """
        Record observation in histogram.

        Args:
            metric_name: Histogram name
            value: Observed value
            labels: Label values
        """
        try:
            if metric_name not in self._metrics:
                raise ValueError(f"Metric '{metric_name}' not found")

            metric_info = self._metrics[metric_name]
            if metric_info['type'] != 'histogram':
                raise ValueError(f"Metric '{metric_name}' is not a histogram")

            histogram = metric_info['metric']

            if labels:
                histogram.labels(**labels).observe(value)
            else:
                histogram.observe(value)
        except Exception as e:
            raise RuntimeError(f"Failed to observe histogram: {e}")

    def summary_observe(self, metric_name: str, value: float,
                       labels: Optional[Dict[str, str]] = None):
        """
        Record observation in summary.

        Args:
            metric_name: Summary name
            value: Observed value
            labels: Label values
        """
        try:
            if metric_name not in self._metrics:
                raise ValueError(f"Metric '{metric_name}' not found")

            metric_info = self._metrics[metric_name]
            if metric_info['type'] != 'summary':
                raise ValueError(f"Metric '{metric_name}' is not a summary")

            summary = metric_info['metric']

            if labels:
                summary.labels(**labels).observe(value)
            else:
                summary.observe(value)
        except Exception as e:
            raise RuntimeError(f"Failed to observe summary: {e}")

    def histogram_time(self, metric_name: str, labels: Optional[Dict[str, str]] = None):
        """
        Get context manager for timing code blocks.

        Args:
            metric_name: Histogram name
            labels: Label values

        Returns:
            Context manager for timing
        """
        if metric_name not in self._metrics:
            raise ValueError(f"Metric '{metric_name}' not found")

        metric_info = self._metrics[metric_name]
        if metric_info['type'] != 'histogram':
            raise ValueError(f"Metric '{metric_name}' is not a histogram")

        histogram = metric_info['metric']

        if labels:
            return histogram.labels(**labels).time()
        else:
            return histogram.time()

    # ============================================================================
    # Metric Exposition
    # ============================================================================

    def start_http_server(self, port: Optional[int] = None, addr: Optional[str] = None):
        """
        Start HTTP server to expose metrics for Prometheus scraping.

        Args:
            port: HTTP port (default: from config)
            addr: Bind address (default: from config)
        """
        try:
            if self._http_server_started:
                return

            port = port or self.exposition_port
            addr = addr or self.exposition_addr

            start_http_server(port, addr, registry=self._registry)
            self._http_server_started = True
        except Exception as e:
            raise RuntimeError(f"Failed to start HTTP server: {e}")

    def get_metrics(self) -> bytes:
        """
        Get current metrics in Prometheus exposition format.

        Returns:
            Metrics in text format
        """
        try:
            return generate_latest(self._registry)
        except Exception as e:
            raise RuntimeError(f"Failed to generate metrics: {e}")

    # ============================================================================
    # Pushgateway Operations
    # ============================================================================

    def push_to_gateway(self, job: Optional[str] = None,
                       grouping_key: Optional[Dict[str, str]] = None,
                       gateway_url: Optional[str] = None):
        """
        Push metrics to Prometheus Pushgateway.

        Args:
            job: Job name (default: from config)
            grouping_key: Additional grouping labels
            gateway_url: Pushgateway URL (default: from config)
        """
        try:
            job = job or self.pushgateway_job
            gateway_url = gateway_url or self.pushgateway_url

            push_to_gateway(
                gateway=gateway_url,
                job=job,
                registry=self._registry,
                grouping_key=grouping_key
            )
        except Exception as e:
            raise RuntimeError(f"Failed to push to gateway: {e}")

    def delete_from_gateway(self, job: Optional[str] = None,
                           grouping_key: Optional[Dict[str, str]] = None,
                           gateway_url: Optional[str] = None):
        """
        Delete metrics from Pushgateway.

        Args:
            job: Job name
            grouping_key: Grouping labels
            gateway_url: Pushgateway URL
        """
        try:
            job = job or self.pushgateway_job
            gateway_url = gateway_url or self.pushgateway_url

            delete_from_gateway(
                gateway=gateway_url,
                job=job,
                grouping_key=grouping_key
            )
        except Exception as e:
            raise RuntimeError(f"Failed to delete from gateway: {e}")

    # ============================================================================
    # PromQL Queries
    # ============================================================================

    def query(self, promql: str) -> List[Dict[str, Any]]:
        """
        Execute instant PromQL query.

        Args:
            promql: PromQL query string

        Returns:
            Query results
        """
        try:
            result = self.prometheus_client.custom_query(query=promql)
            return result
        except Exception as e:
            raise RuntimeError(f"Query failed: {e}")

    def query_range(self, promql: str, start_time: Union[str, float],
                   end_time: Union[str, float], step: str) -> List[Dict[str, Any]]:
        """
        Execute range PromQL query.

        Args:
            promql: PromQL query string
            start_time: Start time (timestamp or RFC3339)
            end_time: End time (timestamp or RFC3339)
            step: Query resolution step width

        Returns:
            Query results
        """
        try:
            result = self.prometheus_client.custom_query_range(
                query=promql,
                start_time=start_time,
                end_time=end_time,
                step=step
            )
            return result
        except Exception as e:
            raise RuntimeError(f"Range query failed: {e}")

    def get_metric_range_data(self, metric_name: str,
                             label_config: Optional[Dict[str, str]] = None,
                             start_time: Optional[Union[str, float]] = None,
                             end_time: Optional[Union[str, float]] = None,
                             step: str = '1m') -> List[Dict[str, Any]]:
        """
        Get range data for specific metric.

        Args:
            metric_name: Metric name
            label_config: Label matchers
            start_time: Start time
            end_time: End time
            step: Query step

        Returns:
            Metric data
        """
        try:
            result = self.prometheus_client.get_metric_range_data(
                metric_name=metric_name,
                label_config=label_config,
                start_time=start_time,
                end_time=end_time,
                step=step
            )
            return result
        except Exception as e:
            raise RuntimeError(f"Failed to get metric range data: {e}")

    def get_current_metric_value(self, metric_name: str,
                                 label_config: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """
        Get current value of metric.

        Args:
            metric_name: Metric name
            label_config: Label matchers

        Returns:
            Current metric values
        """
        try:
            result = self.prometheus_client.get_current_metric_value(
                metric_name=metric_name,
                label_config=label_config
            )
            return result
        except Exception as e:
            raise RuntimeError(f"Failed to get current metric value: {e}")

    # ============================================================================
    # Utility Methods
    # ============================================================================

    def list_metrics(self) -> List[str]:
        """List all registered metrics."""
        return list(self._metrics.keys())

    def get_metric_info(self, metric_name: str) -> Dict[str, Any]:
        """
        Get metric information.

        Args:
            metric_name: Metric name

        Returns:
            Metric information
        """
        if metric_name not in self._metrics:
            raise ValueError(f"Metric '{metric_name}' not found")

        info = self._metrics[metric_name].copy()
        info.pop('metric')  # Don't expose internal metric object
        return info

    def metric_exists(self, metric_name: str) -> bool:
        """Check if metric exists."""
        return metric_name in self._metrics

    def get_registry(self):
        """Get the metric registry."""
        return self._registry

    # ============================================================================
    # Module Metadata
    # ============================================================================

    @classmethod
    def get_metadata(cls):
        """Get module metadata for compiler prompt generation."""
        from nl2py.modules.module_base import ModuleMetadata
        return ModuleMetadata(
            name="Prometheus",
            task_type="prometheus",
            description="Prometheus monitoring and observability with metric collection (Counter, Gauge, Histogram, Summary), HTTP exposition, PromQL queries, Pushgateway support, and multi-dimensional labels",
            version="1.0.0",
            keywords=["prometheus", "monitoring", "metrics", "observability", "counter", "gauge", "histogram", "summary", "promql", "pushgateway", "labels", "scraping", "time-series", "alerting"],
            dependencies=["prometheus-client>=0.14.0", "prometheus-api-client>=0.5.0"]
        )

    @classmethod
    def get_usage_notes(cls):
        """Get usage notes and best practices."""
        return [
            "Module uses singleton pattern - one instance per application",
            "Supports four metric types: Counter (monotonic), Gauge (up/down), Histogram (distributions), Summary (quantiles)",
            "Metrics can have multi-dimensional labels for flexible querying",
            "Counter metrics only increase - never use for values that can decrease",
            "Gauge metrics can go up and down - use for current values like temperature, memory usage",
            "Histogram metrics track distributions with configurable buckets - use for request durations, response sizes",
            "Summary metrics calculate quantiles - similar to histograms but computed on client side",
            "Metric names automatically prefixed with namespace and subsystem if configured",
            "Configure PROMETHEUS_NAMESPACE to prefix all metrics with application namespace",
            "Configure PROMETHEUS_SUBSYSTEM for additional metric categorization",
            "HTTP server exposes metrics on /metrics endpoint for Prometheus scraping",
            "Start HTTP server with start_http_server() or set PROMETHEUS_AUTO_START_HTTP=true",
            "Default exposition port is 8000, configure with PROMETHEUS_EXPOSITION_PORT",
            "Pushgateway allows pushing metrics from short-lived jobs or batch jobs",
            "Use custom registry (PROMETHEUS_CUSTOM_REGISTRY=true) to isolate metrics from global registry",
            "PromQL queries require PROMETHEUS_URL pointing to Prometheus server",
            "Instant queries with query() return current metric values",
            "Range queries with query_range() return time-series data over time period",
            "Labels must be declared at metric creation time - cannot add new labels later",
            "Label values should have low cardinality to avoid high memory usage",
            "Histogram buckets should be chosen based on expected value distribution",
            "Use histogram_time() context manager for automatic duration tracking",
            "Metric names must match regex [a-zA-Z_:][a-zA-Z0-9_:]* according to Prometheus conventions",
            "Label names must match regex [a-zA-Z_][a-zA-Z0-9_]* (no colons in labels)",
        ]

    @classmethod
    def get_methods_info(cls):
        """Get information about available methods."""
        from nl2py.modules.module_base import MethodInfo
        return [
            MethodInfo(
                name="create_counter",
                description="Create a Counter metric that only increases (monotonic)",
                parameters={
                    "name": "str - Metric name (without namespace/subsystem prefix)",
                    "description": "str - Metric description for documentation",
                    "labels": "list[str] (optional) - Label names for multi-dimensional metrics",
                    "namespace": "str (optional) - Override default namespace",
                    "subsystem": "str (optional) - Override default subsystem"
                },
                returns="str - Full metric identifier (name with namespace/subsystem)",
                examples=[
                    {"text": "Create counter {{requests_total}} for {{Total HTTP requests}}", "code": "create_counter(name='{{requests_total}}', description='{{Total HTTP requests}}')"},
                    {"text": "Create counter {{errors}} with labels {{method}} and {{status}}", "code": "create_counter(name='{{errors}}', description='{{Error count}}', labels=['{{method}}', '{{status}}'])"},
                    {"text": "Create counter {{jobs_completed}} with namespace {{batch}} and subsystem {{processing}}", "code": "create_counter(name='{{jobs_completed}}', description='{{Completed jobs}}', namespace='{{batch}}', subsystem='{{processing}}')"}
                ]
            ),
            MethodInfo(
                name="create_gauge",
                description="Create a Gauge metric that can increase or decrease",
                parameters={
                    "name": "str - Metric name",
                    "description": "str - Metric description",
                    "labels": "list[str] (optional) - Label names",
                    "namespace": "str (optional) - Override namespace",
                    "subsystem": "str (optional) - Override subsystem"
                },
                returns="str - Metric identifier",
                examples=[
                    {"text": "Create gauge {{temperature}} for {{Current temperature in Celsius}}", "code": "create_gauge(name='{{temperature}}', description='{{Current temperature in Celsius}}')"},
                    {"text": "Create gauge {{memory_usage}} with labels {{host}} and {{process}}", "code": "create_gauge(name='{{memory_usage}}', description='{{Memory usage in bytes}}', labels=['{{host}}', '{{process}}'])"},
                    {"text": "Create gauge {{queue_size}} for {{Current queue depth}}", "code": "create_gauge(name='{{queue_size}}', description='{{Current queue depth}}')"}
                ]
            ),
            MethodInfo(
                name="create_histogram",
                description="Create a Histogram metric for tracking distributions",
                parameters={
                    "name": "str - Metric name",
                    "description": "str - Metric description",
                    "buckets": "list[float] (optional) - Histogram bucket boundaries (default: [.005, .01, .025, .05, .075, .1, .25, .5, .75, 1.0, 2.5, 5.0, 7.5, 10.0])",
                    "labels": "list[str] (optional) - Label names",
                    "namespace": "str (optional) - Override namespace",
                    "subsystem": "str (optional) - Override subsystem"
                },
                returns="str - Metric identifier",
                examples=[
                    {"text": "Create histogram {{request_duration_seconds}} for {{HTTP request duration}}", "code": "create_histogram(name='{{request_duration_seconds}}', description='{{HTTP request duration}}')"},
                    {"text": "Create histogram {{response_size_bytes}} with buckets {{100}}, {{1000}}, {{10000}}, {{100000}}", "code": "create_histogram(name='{{response_size_bytes}}', description='{{Response size}}', buckets=[{{100}}, {{1000}}, {{10000}}, {{100000}}])"},
                    {"text": "Create histogram {{query_duration}} with labels {{database}} and {{query_type}}", "code": "create_histogram(name='{{query_duration}}', description='{{Query time}}', labels=['{{database}}', '{{query_type}}'])"}
                ]
            ),
            MethodInfo(
                name="create_summary",
                description="Create a Summary metric for calculating quantiles",
                parameters={
                    "name": "str - Metric name",
                    "description": "str - Metric description",
                    "labels": "list[str] (optional) - Label names",
                    "namespace": "str (optional) - Override namespace",
                    "subsystem": "str (optional) - Override subsystem"
                },
                returns="str - Metric identifier",
                examples=[
                    {"text": "Create summary {{request_latency}} for {{Request latency in seconds}}", "code": "create_summary(name='{{request_latency}}', description='{{Request latency in seconds}}')"},
                    {"text": "Create summary {{batch_size}} with label {{job_type}}", "code": "create_summary(name='{{batch_size}}', description='{{Batch processing size}}', labels=['{{job_type}}'])"}
                ]
            ),
            MethodInfo(
                name="counter_inc",
                description="Increment a Counter metric",
                parameters={
                    "metric_name": "str - Counter identifier returned from create_counter",
                    "value": "float (optional) - Increment amount (default: 1.0)",
                    "labels": "dict[str, str] (optional) - Label values matching declared label names"
                },
                returns="None",
                examples=[
                    {"text": "Increment counter {{aibasic_requests_total}} by 1", "code": "counter_inc(metric_name='{{aibasic_requests_total}}')"},
                    {"text": "Increment counter {{aibasic_requests_total}} by {{5}}", "code": "counter_inc(metric_name='{{aibasic_requests_total}}', value={{5}})"},
                    {"text": "Increment counter {{aibasic_errors}} with labels method={{GET}} status={{500}}", "code": "counter_inc(metric_name='{{aibasic_errors}}', labels={'method': '{{GET}}', 'status': '{{500}}'})"}
                ]
            ),
            MethodInfo(
                name="gauge_set",
                description="Set Gauge metric to specific value",
                parameters={
                    "metric_name": "str - Gauge identifier",
                    "value": "float - New gauge value",
                    "labels": "dict[str, str] (optional) - Label values"
                },
                returns="None",
                examples=[
                    {"text": "Set gauge {{aibasic_temperature}} to value {{23.5}}", "code": "gauge_set(metric_name='{{aibasic_temperature}}', value={{23.5}})"},
                    {"text": "Set gauge {{aibasic_memory_usage}} to {{1024000000}} with labels host={{server1}} process={{worker}}", "code": "gauge_set(metric_name='{{aibasic_memory_usage}}', value={{1024000000}}, labels={'host': '{{server1}}', 'process': '{{worker}}'})"}
                ]
            ),
            MethodInfo(
                name="gauge_inc",
                description="Increment Gauge metric",
                parameters={
                    "metric_name": "str - Gauge identifier",
                    "value": "float (optional) - Increment amount (default: 1.0)",
                    "labels": "dict[str, str] (optional) - Label values"
                },
                returns="None",
                examples=[
                    {"text": "Increment gauge {{aibasic_active_connections}} by 1", "code": "gauge_inc(metric_name='{{aibasic_active_connections}}')"},
                    {"text": "Increment gauge {{aibasic_queue_size}} by {{10}}", "code": "gauge_inc(metric_name='{{aibasic_queue_size}}', value={{10}})"}
                ]
            ),
            MethodInfo(
                name="gauge_dec",
                description="Decrement Gauge metric",
                parameters={
                    "metric_name": "str - Gauge identifier",
                    "value": "float (optional) - Decrement amount (default: 1.0)",
                    "labels": "dict[str, str] (optional) - Label values"
                },
                returns="None",
                examples=[
                    {"text": "Decrement gauge {{aibasic_active_connections}} by 1", "code": "gauge_dec(metric_name='{{aibasic_active_connections}}')"},
                    {"text": "Decrement gauge {{aibasic_queue_size}} by {{5}}", "code": "gauge_dec(metric_name='{{aibasic_queue_size}}', value={{5}})"}
                ]
            ),
            MethodInfo(
                name="histogram_observe",
                description="Record observation in Histogram metric",
                parameters={
                    "metric_name": "str - Histogram identifier",
                    "value": "float - Observed value",
                    "labels": "dict[str, str] (optional) - Label values"
                },
                returns="None",
                examples=[
                    {"text": "Observe value {{0.235}} in histogram {{aibasic_request_duration_seconds}}", "code": "histogram_observe(metric_name='{{aibasic_request_duration_seconds}}', value={{0.235}})"},
                    {"text": "Observe value {{4096}} in histogram {{aibasic_response_size_bytes}}", "code": "histogram_observe(metric_name='{{aibasic_response_size_bytes}}', value={{4096}})"},
                    {"text": "Observe value {{0.142}} in histogram {{aibasic_query_duration}} with labels database={{users}} query_type={{select}}", "code": "histogram_observe(metric_name='{{aibasic_query_duration}}', value={{0.142}}, labels={'database': '{{users}}', 'query_type': '{{select}}'})"}
                ]
            ),
            MethodInfo(
                name="summary_observe",
                description="Record observation in Summary metric",
                parameters={
                    "metric_name": "str - Summary identifier",
                    "value": "float - Observed value",
                    "labels": "dict[str, str] (optional) - Label values"
                },
                returns="None",
                examples=[
                    {"text": "Observe value {{0.125}} in summary {{aibasic_request_latency}}", "code": "summary_observe(metric_name='{{aibasic_request_latency}}', value={{0.125}})"},
                    {"text": "Observe value {{500}} in summary {{aibasic_batch_size}} with label job_type={{import}}", "code": "summary_observe(metric_name='{{aibasic_batch_size}}', value={{500}}, labels={'job_type': '{{import}}'})"}
                ]
            ),
            MethodInfo(
                name="start_http_server",
                description="Start HTTP server to expose metrics for Prometheus scraping",
                parameters={
                    "port": "int (optional) - HTTP port (default: from PROMETHEUS_EXPOSITION_PORT or 8000)",
                    "addr": "str (optional) - Bind address (default: from PROMETHEUS_EXPOSITION_ADDR or 0.0.0.0)"
                },
                returns="None",
                examples=[
                    {"text": "Start HTTP metrics server with default settings", "code": "start_http_server()"},
                    {"text": "Start HTTP metrics server on port {{9090}}", "code": "start_http_server(port={{9090}})"},
                    {"text": "Start HTTP metrics server on port {{8080}} at address {{127.0.0.1}}", "code": "start_http_server(port={{8080}}, addr='{{127.0.0.1}}')"}
                ]
            ),
            MethodInfo(
                name="get_metrics",
                description="Get current metrics in Prometheus text exposition format",
                parameters={},
                returns="bytes - Metrics in Prometheus text format",
                examples=[
                    {"text": "Get all current metrics in Prometheus format", "code": "get_metrics()"}
                ]
            ),
            MethodInfo(
                name="push_to_gateway",
                description="Push metrics to Prometheus Pushgateway for batch/short-lived jobs",
                parameters={
                    "job": "str (optional) - Job name (default: from PROMETHEUS_PUSHGATEWAY_JOB or 'aibasic')",
                    "grouping_key": "dict[str, str] (optional) - Additional grouping labels",
                    "gateway_url": "str (optional) - Pushgateway URL (default: from PROMETHEUS_PUSHGATEWAY_URL or 'localhost:9091')"
                },
                returns="None",
                examples=[
                    {"text": "Push metrics to Pushgateway with default job name", "code": "push_to_gateway()"},
                    {"text": "Push metrics to Pushgateway with job {{batch_import}}", "code": "push_to_gateway(job='{{batch_import}}')"},
                    {"text": "Push metrics with job {{backup}} and grouping key instance={{server1}}", "code": "push_to_gateway(job='{{backup}}', grouping_key={'instance': '{{server1}}'})"},
                    {"text": "Push metrics with job {{ETL}} to gateway {{pushgateway.example.com:9091}}", "code": "push_to_gateway(job='{{ETL}}', gateway_url='{{pushgateway.example.com:9091}}')"}
                ]
            ),
            MethodInfo(
                name="delete_from_gateway",
                description="Delete metrics from Prometheus Pushgateway",
                parameters={
                    "job": "str (optional) - Job name",
                    "grouping_key": "dict[str, str] (optional) - Grouping labels",
                    "gateway_url": "str (optional) - Pushgateway URL"
                },
                returns="None",
                examples=[
                    {"text": "Delete metrics for job {{batch_import}} from Pushgateway", "code": "delete_from_gateway(job='{{batch_import}}')"},
                    {"text": "Delete metrics for job {{backup}} with grouping key instance={{server1}}", "code": "delete_from_gateway(job='{{backup}}', grouping_key={'instance': '{{server1}}'})"}
                ]
            ),
            MethodInfo(
                name="query",
                description="Execute instant PromQL query against Prometheus server",
                parameters={
                    "promql": "str - PromQL query expression"
                },
                returns="list[dict] - Query results with metric labels and values",
                examples=[
                    {"text": "Query PromQL {{up}} to check service health", "code": "query(promql='{{up}}')"},
                    {"text": "Query PromQL {{rate(http_requests_total[5m])}} for request rate", "code": "query(promql='{{rate(http_requests_total[5m])}}')"},
                    {"text": "Query PromQL {{sum(rate(requests_total[1m])) by (method)}} for aggregated rate by method", "code": "query(promql='{{sum(rate(requests_total[1m])) by (method)}}')"},
                    {"text": "Query PromQL {{avg_over_time(cpu_usage[1h])}} for average CPU usage", "code": "query(promql='{{avg_over_time(cpu_usage[1h])}}')"}
                ]
            ),
            MethodInfo(
                name="query_range",
                description="Execute range PromQL query to get time-series data",
                parameters={
                    "promql": "str - PromQL query expression",
                    "start_time": "str|float - Start time (Unix timestamp or RFC3339 string)",
                    "end_time": "str|float - End time (Unix timestamp or RFC3339 string)",
                    "step": "str - Query resolution step width (e.g., '15s', '1m', '1h')"
                },
                returns="list[dict] - Time-series results with timestamps and values",
                examples=[
                    {"text": "Query range {{cpu_usage}} from {{2024-01-01T00:00:00Z}} to {{2024-01-01T23:59:59Z}} step {{1m}}", "code": "query_range(promql='{{cpu_usage}}', start_time='{{2024-01-01T00:00:00Z}}', end_time='{{2024-01-01T23:59:59Z}}', step='{{1m}}')"},
                    {"text": "Query range {{rate(requests_total[5m])}} from {{1704067200}} to {{1704153600}} step {{15s}}", "code": "query_range(promql='{{rate(requests_total[5m])}}', start_time={{1704067200}}, end_time={{1704153600}}, step='{{15s}}')"}
                ]
            ),
            MethodInfo(
                name="get_metric_range_data",
                description="Get time-series data for specific metric with optional label filtering",
                parameters={
                    "metric_name": "str - Metric name to query",
                    "label_config": "dict[str, str] (optional) - Label matchers for filtering",
                    "start_time": "str|float (optional) - Start time",
                    "end_time": "str|float (optional) - End time",
                    "step": "str (optional) - Query step (default: '1m')"
                },
                returns="list[dict] - Metric time-series data",
                examples=[
                    {"text": "Get range data for metric {{cpu_usage}}", "code": "get_metric_range_data(metric_name='{{cpu_usage}}')"},
                    {"text": "Get range data for {{http_requests_total}} with labels method={{GET}} status={{200}}", "code": "get_metric_range_data(metric_name='{{http_requests_total}}', label_config={'method': '{{GET}}', 'status': '{{200}}'})"},
                    {"text": "Get range data for {{memory_usage}} from {{1704067200}} to {{1704153600}} step {{5m}}", "code": "get_metric_range_data(metric_name='{{memory_usage}}', start_time={{1704067200}}, end_time={{1704153600}}, step='{{5m}}')"}
                ]
            ),
            MethodInfo(
                name="get_current_metric_value",
                description="Get current (latest) value of specific metric",
                parameters={
                    "metric_name": "str - Metric name",
                    "label_config": "dict[str, str] (optional) - Label matchers"
                },
                returns="list[dict] - Current metric values",
                examples=[
                    {"text": "Get current value of metric {{up}}", "code": "get_current_metric_value(metric_name='{{up}}')"},
                    {"text": "Get current value of {{cpu_usage}} with label instance={{server1}}", "code": "get_current_metric_value(metric_name='{{cpu_usage}}', label_config={'instance': '{{server1}}'})"}
                ]
            ),
            MethodInfo(
                name="list_metrics",
                description="List all registered metric names",
                parameters={},
                returns="list[str] - Metric names",
                examples=[
                    {"text": "List all registered metrics", "code": "list_metrics()"}
                ]
            ),
            MethodInfo(
                name="get_metric_info",
                description="Get information about specific metric",
                parameters={
                    "metric_name": "str - Metric identifier"
                },
                returns="dict - Metric info with type, labels, buckets (for histogram)",
                examples=[
                    {"text": "Get information about metric {{aibasic_requests_total}}", "code": "get_metric_info(metric_name='{{aibasic_requests_total}}')"}
                ]
            ),
            MethodInfo(
                name="metric_exists",
                description="Check if metric exists",
                parameters={
                    "metric_name": "str - Metric identifier"
                },
                returns="bool - True if metric exists",
                examples=[
                    {"text": "Check if metric {{aibasic_requests_total}} exists", "code": "metric_exists(metric_name='{{aibasic_requests_total}}')"}
                ]
            )
        ]

