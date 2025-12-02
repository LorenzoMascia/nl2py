"""
Elasticsearch Module for NL2Py

This module provides integration with Elasticsearch, a distributed search and analytics engine
for full-text search, log analytics, and real-time data processing.

Features:
- Index management (create, delete, update settings)
- Document operations (index, update, delete, get)
- Search with Query DSL
- Bulk operations for high performance
- Aggregations and analytics
- Mapping management
- Alias management
- DataFrame integration
- Template management
- Snapshot and restore

Author: NL2Py Team
Version: 1.0
"""

import threading
from typing import Any, Dict, List, Optional, Union
import pandas as pd
import json
from .module_base import NL2PyModuleBase


class ElasticsearchModule(NL2PyModuleBase):
    """
    Elasticsearch module for NL2Py programs.

    Provides integration with Elasticsearch for full-text search,
    log analytics, and real-time data processing.

    This class implements the singleton pattern to ensure only one instance
    exists per process, with thread-safe initialization.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """
        Create or return the singleton instance (thread-safe).
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        hosts: Union[str, List[str]] = "http://localhost:9200",
        username: str = None,
        password: str = None,
        api_key: str = None,
        verify_certs: bool = True,
        ca_certs: str = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_on_timeout: bool = True,
        **kwargs
    ):
        """
        Initialize the Elasticsearch module.

        Args:
            hosts: Elasticsearch host(s) URL(s)
            username: Username for authentication
            password: Password for authentication
            api_key: API key for authentication (alternative to username/password)
            verify_certs: Verify SSL certificates
            ca_certs: Path to CA certificate bundle
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
            retry_on_timeout: Retry on timeout
            **kwargs: Additional Elasticsearch client parameters
        """
        if self._initialized:
            return

        try:
            from elasticsearch import Elasticsearch
            from elasticsearch.exceptions import (
                ConnectionError,
                AuthenticationException,
                NotFoundError
            )
        except ImportError:
            raise ImportError(
                "elasticsearch package is required. Install with: pip install elasticsearch"
            )

        # Store exception classes
        self.ConnectionError = ConnectionError
        self.AuthenticationException = AuthenticationException
        self.NotFoundError = NotFoundError

        # Parse hosts
        if isinstance(hosts, str):
            hosts = [hosts]

        # Setup authentication
        auth_params = {}
        if api_key:
            auth_params['api_key'] = api_key
        elif username and password:
            auth_params['basic_auth'] = (username, password)

        # Create Elasticsearch client
        self.client = Elasticsearch(
            hosts=hosts,
            verify_certs=verify_certs,
            ca_certs=ca_certs,
            timeout=timeout,
            max_retries=max_retries,
            retry_on_timeout=retry_on_timeout,
            **auth_params,
            **kwargs
        )

        # State variables
        self.last_query = None
        self.last_result = None

        self._initialized = True

    def ping(self) -> bool:
        """
        Check if Elasticsearch cluster is accessible.

        Returns:
            True if cluster responds, False otherwise
        """
        try:
            return self.client.ping()
        except Exception:
            return False

    def info(self) -> Dict[str, Any]:
        """
        Get cluster information.

        Returns:
            Dictionary with cluster info
        """
        try:
            return self.client.info()
        except Exception as e:
            return {'error': str(e)}

    def create_index(
        self,
        index: str,
        mappings: Optional[Dict[str, Any]] = None,
        settings: Optional[Dict[str, Any]] = None,
        aliases: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create an index.

        Args:
            index: Index name
            mappings: Index mappings (field types)
            settings: Index settings (shards, replicas, etc.)
            aliases: Index aliases

        Returns:
            Dictionary with creation result
        """
        try:
            body = {}
            if mappings:
                body['mappings'] = mappings
            if settings:
                body['settings'] = settings
            if aliases:
                body['aliases'] = aliases

            result = self.client.indices.create(index=index, body=body if body else None)
            return {'success': True, 'acknowledged': result.get('acknowledged', False)}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def delete_index(self, index: str) -> Dict[str, Any]:
        """
        Delete an index.

        Args:
            index: Index name (supports wildcards)

        Returns:
            Dictionary with deletion result
        """
        try:
            result = self.client.indices.delete(index=index)
            return {'success': True, 'acknowledged': result.get('acknowledged', False)}
        except self.NotFoundError:
            return {'success': False, 'error': f'Index {index} not found'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def index_exists(self, index: str) -> bool:
        """
        Check if an index exists.

        Args:
            index: Index name

        Returns:
            True if exists, False otherwise
        """
        try:
            return self.client.indices.exists(index=index)
        except Exception:
            return False

    def index_document(
        self,
        index: str,
        document: Dict[str, Any],
        doc_id: Optional[str] = None,
        refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Index a document.

        Args:
            index: Index name
            document: Document to index
            doc_id: Document ID (auto-generated if None)
            refresh: Refresh index after operation

        Returns:
            Dictionary with index result
        """
        try:
            result = self.client.index(
                index=index,
                document=document,
                id=doc_id,
                refresh=refresh
            )
            return {
                'success': True,
                'id': result['_id'],
                'version': result['_version'],
                'result': result['result']
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def bulk_index(
        self,
        index: str,
        documents: List[Dict[str, Any]],
        id_field: Optional[str] = None,
        refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Bulk index multiple documents.

        Args:
            index: Index name
            documents: List of documents
            id_field: Field to use as document ID (optional)
            refresh: Refresh index after operation

        Returns:
            Dictionary with bulk result
        """
        try:
            from elasticsearch.helpers import bulk

            actions = []
            for doc in documents:
                action = {
                    '_index': index,
                    '_source': doc
                }
                if id_field and id_field in doc:
                    action['_id'] = doc[id_field]

                actions.append(action)

            success, failed = bulk(
                self.client,
                actions,
                refresh=refresh,
                raise_on_error=False
            )

            return {
                'success': True,
                'successful': success,
                'failed': failed,
                'total': len(documents)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_document(
        self,
        index: str,
        doc_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a document by ID.

        Args:
            index: Index name
            doc_id: Document ID

        Returns:
            Document if found, None otherwise
        """
        try:
            result = self.client.get(index=index, id=doc_id)
            return result['_source']
        except self.NotFoundError:
            return None
        except Exception as e:
            return {'error': str(e)}

    def update_document(
        self,
        index: str,
        doc_id: str,
        document: Dict[str, Any],
        refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Update a document.

        Args:
            index: Index name
            doc_id: Document ID
            document: Fields to update
            refresh: Refresh index after operation

        Returns:
            Dictionary with update result
        """
        try:
            result = self.client.update(
                index=index,
                id=doc_id,
                doc=document,
                refresh=refresh
            )
            return {
                'success': True,
                'version': result['_version'],
                'result': result['result']
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def delete_document(
        self,
        index: str,
        doc_id: str,
        refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Delete a document.

        Args:
            index: Index name
            doc_id: Document ID
            refresh: Refresh index after operation

        Returns:
            Dictionary with deletion result
        """
        try:
            result = self.client.delete(
                index=index,
                id=doc_id,
                refresh=refresh
            )
            return {
                'success': True,
                'result': result['result']
            }
        except self.NotFoundError:
            return {'success': False, 'error': 'Document not found'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def search(
        self,
        index: str,
        query: Optional[Dict[str, Any]] = None,
        size: int = 10,
        from_: int = 0,
        sort: Optional[List] = None,
        source: Optional[Union[bool, List[str]]] = None,
        aggs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search documents.

        Args:
            index: Index name (supports wildcards)
            query: Query DSL (match_all if None)
            size: Number of results to return
            from_: Offset for pagination
            sort: Sort specification
            source: Fields to return
            aggs: Aggregations

        Returns:
            Dictionary with search results
        """
        try:
            body = {}

            if query:
                body['query'] = query
            else:
                body['query'] = {'match_all': {}}

            if aggs:
                body['aggs'] = aggs

            result = self.client.search(
                index=index,
                body=body,
                size=size,
                from_=from_,
                sort=sort,
                _source=source
            )

            self.last_query = body
            self.last_result = result

            hits = [hit['_source'] for hit in result['hits']['hits']]

            response = {
                'success': True,
                'hits': hits,
                'total': result['hits']['total']['value'],
                'max_score': result['hits'].get('max_score')
            }

            if aggs:
                response['aggregations'] = result.get('aggregations', {})

            return response

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def search_df(
        self,
        index: str,
        query: Optional[Dict[str, Any]] = None,
        size: int = 10000
    ) -> pd.DataFrame:
        """
        Search and return results as DataFrame.

        Args:
            index: Index name
            query: Query DSL
            size: Maximum number of results

        Returns:
            pandas DataFrame with results
        """
        result = self.search(index, query, size=size)
        if result.get('success'):
            return pd.DataFrame(result['hits'])
        else:
            return pd.DataFrame()

    def count(
        self,
        index: str,
        query: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count documents matching query.

        Args:
            index: Index name
            query: Query DSL (all documents if None)

        Returns:
            Number of matching documents
        """
        try:
            body = {}
            if query:
                body['query'] = query

            result = self.client.count(index=index, body=body if body else None)
            return result['count']
        except Exception:
            return 0

    def delete_by_query(
        self,
        index: str,
        query: Dict[str, Any],
        refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Delete documents matching query.

        Args:
            index: Index name
            query: Query DSL
            refresh: Refresh index after operation

        Returns:
            Dictionary with deletion result
        """
        try:
            result = self.client.delete_by_query(
                index=index,
                body={'query': query},
                refresh=refresh
            )
            return {
                'success': True,
                'deleted': result['deleted'],
                'total': result['total']
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def update_by_query(
        self,
        index: str,
        query: Dict[str, Any],
        script: Dict[str, Any],
        refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Update documents matching query.

        Args:
            index: Index name
            query: Query DSL
            script: Update script
            refresh: Refresh index after operation

        Returns:
            Dictionary with update result
        """
        try:
            result = self.client.update_by_query(
                index=index,
                body={
                    'query': query,
                    'script': script
                },
                refresh=refresh
            )
            return {
                'success': True,
                'updated': result['updated'],
                'total': result['total']
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def put_mapping(
        self,
        index: str,
        properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update index mapping.

        Args:
            index: Index name
            properties: Field mappings

        Returns:
            Dictionary with result
        """
        try:
            result = self.client.indices.put_mapping(
                index=index,
                body={'properties': properties}
            )
            return {'success': True, 'acknowledged': result.get('acknowledged', False)}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def refresh_index(self, index: str) -> Dict[str, Any]:
        """
        Refresh an index to make recent changes searchable.

        Args:
            index: Index name

        Returns:
            Dictionary with refresh result
        """
        try:
            self.client.indices.refresh(index=index)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def create_alias(
        self,
        index: str,
        alias: str
    ) -> Dict[str, Any]:
        """
        Create an alias for an index.

        Args:
            index: Index name
            alias: Alias name

        Returns:
            Dictionary with result
        """
        try:
            result = self.client.indices.put_alias(index=index, name=alias)
            return {'success': True, 'acknowledged': result.get('acknowledged', False)}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_cluster_health(self) -> Dict[str, Any]:
        """
        Get cluster health status.

        Returns:
            Dictionary with cluster health information
        """
        try:
            return self.client.cluster.health()
        except Exception as e:
            return {'error': str(e)}

    def get_index_stats(self, index: str) -> Dict[str, Any]:
        """
        Get index statistics.

        Args:
            index: Index name

        Returns:
            Dictionary with index stats
        """
        try:
            return self.client.indices.stats(index=index)
        except Exception as e:
            return {'error': str(e)}

    def close(self):
        """
        Close the Elasticsearch client connection.
        """
        if hasattr(self, 'client'):
            self.client.close()

    @classmethod
    def get_metadata(cls):
        """Get module metadata."""
        from nl2py.modules.module_base import ModuleMetadata
        return ModuleMetadata(
            name="Elasticsearch",
            task_type="elasticsearch",
            description="Distributed search and analytics engine for full-text search, log analytics, and real-time data processing with Query DSL support",
            version="1.0.0",
            keywords=["elasticsearch", "search", "analytics", "fulltext", "logs", "query-dsl", "aggregations", "index", "document", "bulk"],
            dependencies=[
                "elasticsearch>=8.0.0",
                "pandas>=1.3.0"
            ]
        )

    @classmethod
    def get_usage_notes(cls):
        """Get detailed usage notes."""
        return [
            "Module uses singleton pattern - one instance shared across operations",
            "Supports multiple authentication methods: basic auth (username/password) or API key",
            "Can connect to single node or cluster with multiple hosts for high availability",
            "All document operations support optional 'refresh' parameter to make changes immediately searchable",
            "Index names support wildcards (e.g., 'logs-*') for multi-index operations",
            "Query DSL uses nested dictionaries matching Elasticsearch JSON syntax",
            "Bulk operations are highly efficient - use for indexing large numbers of documents",
            "Aggregations run alongside search queries to compute metrics, statistics, and analytics",
            "Document IDs are auto-generated if not provided during indexing",
            "The 'size' parameter controls pagination - max recommended is 10,000 per request",
            "Use 'from_' parameter for pagination offset (0-based)",
            "SSL certificate verification can be disabled for development but should be enabled in production",
            "Mappings define field types (text, keyword, integer, date, etc.) and cannot be changed for existing fields",
            "Aliases provide abstraction over index names - useful for zero-downtime reindexing",
            "Use search_df() method to get results as pandas DataFrame for data analysis",
            "The module stores last_query and last_result for debugging and inspection",
            "Refresh operation makes recent changes searchable but has performance cost - use sparingly",
            "Count operations are faster than search when you only need document counts"
        ]

    @classmethod
    def get_methods_info(cls):
        """Get information about module methods."""
        from nl2py.modules.module_base import MethodInfo
        return [
            MethodInfo(
                name="ping",
                description="Check if Elasticsearch cluster is accessible and responding",
                parameters={},
                returns="Boolean: True if cluster responds, False otherwise",
                examples=[
                    {"text": "ping cluster", "code": "ping()"},
                    {"text": "check if elasticsearch is available", "code": "ping()"}
                ]
            ),
            MethodInfo(
                name="info",
                description="Get detailed cluster information including version, name, and configuration",
                parameters={},
                returns="Dictionary with cluster information",
                examples=[
                    {"text": "get cluster info", "code": "info()"},
                    {"text": "show elasticsearch version and details", "code": "info()"}
                ]
            ),
            MethodInfo(
                name="create_index",
                description="Create a new index with optional mappings, settings, and aliases",
                parameters={
                    "index": "Index name to create",
                    "mappings": "Field type definitions (optional, dict with 'properties' defining field types)",
                    "settings": "Index settings like number of shards and replicas (optional, dict)",
                    "aliases": "Index aliases (optional, dict)"
                },
                returns="Dictionary with success status and acknowledgement",
                examples=[
                    {"text": "create index {{products}}", "code": "create_index(index='{{products}}')"},
                    {"text": "create index {{logs}} with mappings for timestamp and message fields", "code": "create_index(index='{{logs}}', mappings={{'properties': {{'timestamp': {{'type': 'date'}}, 'message': {{'type': 'text'}}}})"},
                    {"text": "create index {{users}} with custom shards and replicas settings", "code": "create_index(index='{{users}}', settings={{'number_of_shards': {{3}}, 'number_of_replicas': {{2}}}})"},
                    {"text": "create index {{events}} with mappings and aliases", "code": "create_index(index='{{events}}', mappings={{'properties': {{'level': {{'type': 'keyword'}}}}}}, aliases={{'current': {{}}}})"}
                ]
            ),
            MethodInfo(
                name="delete_index",
                description="Delete an index (supports wildcards for deleting multiple indices)",
                parameters={
                    "index": "Index name to delete (supports wildcards like 'logs-*')"
                },
                returns="Dictionary with success status and acknowledgement",
                examples=[
                    {"text": "delete index {{old-logs}}", "code": "delete_index(index='{{old-logs}}')"},
                    {"text": "delete all test indices using wildcard {{test-*}}", "code": "delete_index(index='{{test-*}}')"},
                    {"text": "remove index {{temporary}}", "code": "delete_index(index='{{temporary}}')"}
                ]
            ),
            MethodInfo(
                name="index_exists",
                description="Check if an index exists in the cluster",
                parameters={
                    "index": "Index name to check"
                },
                returns="Boolean: True if index exists, False otherwise",
                examples=[
                    {"text": "check if index {{products}} exists", "code": "index_exists(index='{{products}}')"},
                    {"text": "does index {{users}} exist", "code": "index_exists(index='{{users}}')"}
                ]
            ),
            MethodInfo(
                name="index_document",
                description="Index a single document into an index (create or update)",
                parameters={
                    "index": "Index name",
                    "document": "Document data as dictionary",
                    "doc_id": "Document ID (optional, auto-generated if not provided)",
                    "refresh": "Refresh index immediately to make document searchable (default: False)"
                },
                returns="Dictionary with document ID, version, and result (created/updated)",
                examples=[
                    {"text": "index document with name {{John}} and age {{30}} into {{users}} index", "code": "index_document(index='{{users}}', document={{'name': '{{John}}', 'age': {{30}}}})"},
                    {"text": "index product document with specific ID {{prod-123}}", "code": "index_document(index='{{products}}', document={{'product': '{{laptop}}', 'price': {{999}}}}, doc_id='{{prod-123}}')"},
                    {"text": "index log message with immediate refresh", "code": "index_document(index='{{logs}}', document={{'message': '{{error occurred}}', 'level': '{{ERROR}}'}}, refresh={{True}})"}
                ]
            ),
            MethodInfo(
                name="bulk_index",
                description="Bulk index multiple documents efficiently in a single request",
                parameters={
                    "index": "Index name",
                    "documents": "List of document dictionaries to index",
                    "id_field": "Field name to use as document ID (optional)",
                    "refresh": "Refresh index after bulk operation (default: False)"
                },
                returns="Dictionary with successful count, failed count, and total",
                examples=[
                    {"text": "bulk index multiple user documents", "code": "bulk_index(index='{{users}}', documents={{[{'name': 'Alice'}, {'name': 'Bob'}]}})"},
                    {"text": "bulk index documents using {{user_id}} field as ID", "code": "bulk_index(index='{{accounts}}', documents={{documents_list}}, id_field='{{user_id}}')"},
                    {"text": "bulk index documents with refresh enabled", "code": "bulk_index(index='{{logs}}', documents={{documents_list}}, refresh={{True}})"}
                ]
            ),
            MethodInfo(
                name="get_document",
                description="Retrieve a document by its ID from an index",
                parameters={
                    "index": "Index name",
                    "doc_id": "Document ID to retrieve"
                },
                returns="Document dictionary if found, None if not found, or error dict",
                examples=[
                    {"text": "get document {{user-123}} from {{users}} index", "code": "get_document(index='{{users}}', doc_id='{{user-123}}')"},
                    {"text": "retrieve document with id {{prod-456}} from {{products}}", "code": "get_document(index='{{products}}', doc_id='{{prod-456}}')"},
                    {"text": "fetch document {{event-789}} from {{events}} index", "code": "get_document(index='{{events}}', doc_id='{{event-789}}')"}
                ]
            ),
            MethodInfo(
                name="update_document",
                description="Update specific fields of an existing document",
                parameters={
                    "index": "Index name",
                    "doc_id": "Document ID to update",
                    "document": "Dictionary with fields to update (partial document)",
                    "refresh": "Refresh index immediately (default: False)"
                },
                returns="Dictionary with version and result status",
                examples=[
                    {"text": "update user age field to {{31}}", "code": "update_document(index='{{users}}', doc_id='{{user-123}}', document={{'age': {{31}}}})"},
                    {"text": "update product price to {{899}} and stock to {{50}}", "code": "update_document(index='{{products}}', doc_id='{{prod-456}}', document={{'price': {{899}}, 'stock': {{50}}}})"},
                    {"text": "update event status to {{processed}} with refresh", "code": "update_document(index='{{events}}', doc_id='{{event-789}}', document={{'status': '{{processed}}'}}, refresh={{True}})"}
                ]
            ),
            MethodInfo(
                name="delete_document",
                description="Delete a document by its ID from an index",
                parameters={
                    "index": "Index name",
                    "doc_id": "Document ID to delete",
                    "refresh": "Refresh index immediately (default: False)"
                },
                returns="Dictionary with success status and result",
                examples=[
                    {"text": "delete document {{user-123}} from {{users}} index", "code": "delete_document(index='{{users}}', doc_id='{{user-123}}')"},
                    {"text": "remove document {{old-event}} from {{events}}", "code": "delete_document(index='{{events}}', doc_id='{{old-event}}')"},
                    {"text": "delete document {{temp-456}} with refresh enabled", "code": "delete_document(index='{{temporary}}', doc_id='{{temp-456}}', refresh={{True}})"}
                ]
            ),
            MethodInfo(
                name="search",
                description="Search documents using Elasticsearch Query DSL with support for pagination, sorting, and aggregations",
                parameters={
                    "index": "Index name (supports wildcards like 'logs-*')",
                    "query": "Query DSL dictionary (optional, defaults to match_all)",
                    "size": "Number of results to return (default: 10, max recommended: 10000)",
                    "from_": "Offset for pagination (default: 0)",
                    "sort": "Sort specification list (optional)",
                    "source": "Fields to return - True/False or list of field names (optional)",
                    "aggs": "Aggregations dictionary (optional)"
                },
                returns="Dictionary with hits list, total count, max_score, and optional aggregations",
                examples=[
                    {"text": "search all documents in {{products}} index", "code": "search(index='{{products}}')"},
                    {"text": "search {{users}} matching name {{john}}", "code": "search(index='{{users}}', query={{'match': {{'name': '{{john}}'}}}})"},
                    {"text": "search {{logs}} from {{2024-01-01}} with size limit {{100}}", "code": "search(index='{{logs}}', query={{'range': {{'timestamp': {{'gte': '{{2024-01-01}}'}}}}}}, size={{100}})"},
                    {"text": "search {{events}} with {{ERROR}} level and aggregate by type", "code": "search(index='{{events}}', query={{'term': {{'level': '{{ERROR}}'}}}}, aggs={{'by_type': {{'terms': {{'field': '{{type.keyword}}'}}}}}})"},
                    {"text": "search {{products}} sorted by price ascending with size {{20}}", "code": "search(index='{{products}}', sort={{[{'price': 'asc'}]}}, size={{20}})"},
                    {"text": "search {{users}} with pagination from {{50}} size {{10}} and specific fields", "code": "search(index='{{users}}', from_={{50}}, size={{10}}, source={{['name', 'email']}})"}
                ]
            ),
            MethodInfo(
                name="search_df",
                description="Search documents and return results as pandas DataFrame for data analysis",
                parameters={
                    "index": "Index name",
                    "query": "Query DSL dictionary (optional, defaults to match_all)",
                    "size": "Maximum number of results (default: 10000)"
                },
                returns="pandas DataFrame with search results",
                examples=[
                    {"text": "search {{products}} as dataframe", "code": "search_df(index='{{products}}')"},
                    {"text": "search {{ERROR}} logs as dataframe", "code": "search_df(index='{{logs}}', query={{'match': {{'level': '{{ERROR}}'}}}})"},
                    {"text": "get all {{users}} as dataframe with custom size {{50000}}", "code": "search_df(index='{{users}}', size={{50000}})"}
                ]
            ),
            MethodInfo(
                name="count",
                description="Count documents matching a query (faster than search when only count is needed)",
                parameters={
                    "index": "Index name",
                    "query": "Query DSL dictionary (optional, counts all documents if omitted)"
                },
                returns="Integer: number of matching documents",
                examples=[
                    {"text": "count all documents in {{users}} index", "code": "count(index='{{users}}')"},
                    {"text": "count {{ERROR}} level logs", "code": "count(index='{{logs}}', query={{'term': {{'level': '{{ERROR}}'}}}})"},
                    {"text": "count {{products}} with price less than {{100}}", "code": "count(index='{{products}}', query={{'range': {{'price': {{'lt': {{100}}}}}}})"}
                ]
            ),
            MethodInfo(
                name="delete_by_query",
                description="Delete all documents matching a query",
                parameters={
                    "index": "Index name",
                    "query": "Query DSL dictionary specifying which documents to delete",
                    "refresh": "Refresh index immediately (default: False)"
                },
                returns="Dictionary with deleted count and total processed",
                examples=[
                    {"text": "delete old {{logs}} before {{2023-01-01}}", "code": "delete_by_query(index='{{logs}}', query={{'range': {{'timestamp': {{'lt': '{{2023-01-01}}'}}}}}})"},
                    {"text": "delete {{inactive}} users", "code": "delete_by_query(index='{{users}}', query={{'term': {{'status': '{{inactive}}'}}}})"},
                    {"text": "delete all documents from {{temp}} with refresh", "code": "delete_by_query(index='{{temp}}', query={{'match_all': {{}}}}, refresh={{True}})"}
                ]
            ),
            MethodInfo(
                name="update_by_query",
                description="Update all documents matching a query using a script",
                parameters={
                    "index": "Index name",
                    "query": "Query DSL dictionary specifying which documents to update",
                    "script": "Update script dictionary (e.g., {'source': 'ctx._source.field++'})",
                    "refresh": "Refresh index immediately (default: False)"
                },
                returns="Dictionary with updated count and total processed",
                examples=[
                    {"text": "increase price by 10% for {{electronics}} products", "code": "update_by_query(index='{{products}}', query={{'term': {{'category': '{{electronics}}'}}}}, script={{'source': '{{ctx._source.price *= 1.1}}'}})"},
                    {"text": "update all {{users}} with timestamp parameter {{2024-01-01}}", "code": "update_by_query(index='{{users}}', query={{'match_all': {{}}}}, script={{'source': '{{ctx._source.updated_at = params.now}}', 'params': {{'now': '{{2024-01-01}}'}}}})"},
                    {"text": "reset views to zero for low view count {{documents}}", "code": "update_by_query(index='{{documents}}', query={{'range': {{'views': {{'lt': {{10}}}}}}}, script={{'source': '{{ctx._source.views = 0}}'}}, refresh={{True}})"}
                ]
            ),
            MethodInfo(
                name="put_mapping",
                description="Add new fields to index mapping (cannot modify existing field types)",
                parameters={
                    "index": "Index name",
                    "properties": "Dictionary defining new field mappings"
                },
                returns="Dictionary with success status and acknowledgement",
                examples=[
                    {"text": "add phone field mapping to {{users}} index", "code": "put_mapping(index='{{users}}', properties={{'phone': {{'type': 'keyword'}}}})"},
                    {"text": "add tags and rating fields to {{products}}", "code": "put_mapping(index='{{products}}', properties={{'tags': {{'type': 'keyword'}}, 'rating': {{'type': 'float'}}}})"},
                    {"text": "add source_ip field with ip type to {{logs}}", "code": "put_mapping(index='{{logs}}', properties={{'source_ip': {{'type': 'ip'}}}})"}
                ]
            ),
            MethodInfo(
                name="refresh_index",
                description="Refresh index to make recent changes immediately searchable (has performance cost)",
                parameters={
                    "index": "Index name to refresh"
                },
                returns="Dictionary with success status",
                examples=[
                    {"text": "refresh {{products}} index", "code": "refresh_index(index='{{products}}')"},
                    {"text": "refresh {{logs}} index to make changes searchable", "code": "refresh_index(index='{{logs}}')"},
                    {"text": "force refresh on {{users}} index", "code": "refresh_index(index='{{users}}')"}
                ]
            ),
            MethodInfo(
                name="create_alias",
                description="Create an alias pointing to an index (useful for zero-downtime reindexing)",
                parameters={
                    "index": "Index name",
                    "alias": "Alias name to create"
                },
                returns="Dictionary with success status and acknowledgement",
                examples=[
                    {"text": "create alias {{current_products}} for index {{products_v2}}", "code": "create_alias(index='{{products_v2}}', alias='{{current_products}}')"},
                    {"text": "add alias {{active_logs}} to index {{logs-2024-01}}", "code": "create_alias(index='{{logs-2024-01}}', alias='{{active_logs}}')"},
                    {"text": "create alias {{users}} pointing to {{users_production}} index", "code": "create_alias(index='{{users_production}}', alias='{{users}}')"}
                ]
            ),
            MethodInfo(
                name="get_cluster_health",
                description="Get cluster health status including status color (green/yellow/red), node counts, and shard information",
                parameters={},
                returns="Dictionary with cluster health details",
                examples=[
                    {"text": "get cluster health", "code": "get_cluster_health()"},
                    {"text": "check cluster status", "code": "get_cluster_health()"},
                    {"text": "show cluster health information", "code": "get_cluster_health()"}
                ]
            ),
            MethodInfo(
                name="get_index_stats",
                description="Get detailed statistics for an index including document count, storage size, and performance metrics",
                parameters={
                    "index": "Index name"
                },
                returns="Dictionary with comprehensive index statistics",
                examples=[
                    {"text": "get stats for {{products}} index", "code": "get_index_stats(index='{{products}}')"},
                    {"text": "show index statistics for {{logs}}", "code": "get_index_stats(index='{{logs}}')"},
                    {"text": "get {{users}} index stats and metrics", "code": "get_index_stats(index='{{users}}')"}
                ]
            )
        ]

# Singleton instance getter
def get_elasticsearch_module(**kwargs) -> ElasticsearchModule:
    """
    Get the singleton Elasticsearch module instance.

    Args:
        **kwargs: Configuration parameters

    Returns:
        ElasticsearchModule instance
    """
    return ElasticsearchModule(**kwargs)
