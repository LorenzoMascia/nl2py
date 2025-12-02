"""
TimescaleDB Module for NL2Py

This module provides integration with TimescaleDB, a PostgreSQL extension
optimized for time-series data with fast ingest, complex queries, and automatic partitioning.

Features:
- Hypertable management (time-series optimized tables)
- Continuous aggregates (materialized views that auto-update)
- Data retention policies (automatic data deletion)
- Compression policies (automatic compression of old data)
- Time-bucket queries for efficient aggregation
- Downsampling and rollups
- Gap filling for missing time-series data
- PostgreSQL compatibility (all PostgreSQL features available)

Author: NL2Py Team
Version: 1.0
"""

import threading
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
import pandas as pd
from .module_base import NL2PyModuleBase


class TimescaleDBModule(NL2PyModuleBase):
    """
    TimescaleDB module for NL2Py programs.

    Provides integration with TimescaleDB for time-series data storage,
    analysis, and efficient querying with automatic partitioning.

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
        host: str = "localhost",
        port: int = 5432,
        database: str = "tsdb",
        user: str = "postgres",
        password: str = "password",
        pool_size: int = 5,
        max_overflow: int = 10,
        **kwargs
    ):
        """
        Initialize the TimescaleDB module.

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Username
            password: Password
            pool_size: Connection pool size
            max_overflow: Maximum overflow connections
            **kwargs: Additional psycopg2 parameters
        """
        if self._initialized:
            return

        try:
            import psycopg2
            import psycopg2.pool
            import psycopg2.extras
        except ImportError:
            raise ImportError(
                "psycopg2-binary package is required. Install with: pip install psycopg2-binary"
            )

        # Create connection pool
        self.pool = psycopg2.pool.ThreadedConnectionPool(
            pool_size,
            pool_size + max_overflow,
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            **kwargs
        )

        # Store psycopg2 for exception handling
        self.psycopg2 = psycopg2

        self._initialized = True

    def get_connection(self):
        """Get a connection from the pool."""
        return self.pool.getconn()

    def release_connection(self, conn):
        """Release a connection back to the pool."""
        self.pool.putconn(conn)

    def execute_query(
        self,
        query: str,
        params: Optional[tuple] = None,
        fetch: bool = True
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Execute a query and return results.

        Args:
            query: SQL query
            params: Query parameters
            fetch: Whether to fetch results

        Returns:
            List of dictionaries (rows) or None
        """
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=self.psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                if fetch:
                    return [dict(row) for row in cur.fetchall()]
                conn.commit()
                return None
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self.release_connection(conn)

    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """
        Execute query multiple times with different parameters.

        Args:
            query: SQL query
            params_list: List of parameter tuples

        Returns:
            Number of affected rows
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.executemany(query, params_list)
                conn.commit()
                return cur.rowcount
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self.release_connection(conn)

    def query_to_dataframe(self, query: str, params: Optional[tuple] = None) -> pd.DataFrame:
        """
        Execute query and return results as DataFrame.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            pandas DataFrame
        """
        conn = self.get_connection()
        try:
            df = pd.read_sql_query(query, conn, params=params)
            return df
        finally:
            self.release_connection(conn)

    # ========================================================================
    # Hypertable Management
    # ========================================================================

    def create_hypertable(
        self,
        table_name: str,
        time_column: str = "time",
        chunk_time_interval: str = "1 day",
        if_not_exists: bool = True,
        partitioning_column: Optional[str] = None,
        number_partitions: Optional[int] = None,
        create_default_indexes: bool = True
    ) -> Dict[str, Any]:
        """
        Convert a regular table to a hypertable.

        Args:
            table_name: Name of the table
            time_column: Name of the time column
            chunk_time_interval: Chunk interval (e.g., '1 day', '1 week')
            if_not_exists: Don't error if already a hypertable
            partitioning_column: Additional partitioning column
            number_partitions: Number of space partitions
            create_default_indexes: Create default indexes

        Returns:
            Dictionary with result
        """
        try:
            query = f"""
            SELECT create_hypertable(
                '{table_name}',
                '{time_column}',
                chunk_time_interval => INTERVAL '{chunk_time_interval}',
                if_not_exists => {if_not_exists},
                create_default_indexes => {create_default_indexes}
            """

            if partitioning_column and number_partitions:
                query += f",\n                partitioning_column => '{partitioning_column}'"
                query += f",\n                number_partitions => {number_partitions}"

            query += "\n            );"

            self.execute_query(query, fetch=False)
            return {'success': True, 'table': table_name}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def drop_hypertable(
        self,
        table_name: str,
        cascade: bool = False
    ) -> Dict[str, Any]:
        """
        Drop a hypertable.

        Args:
            table_name: Name of the hypertable
            cascade: Drop dependent objects

        Returns:
            Dictionary with result
        """
        try:
            cascade_str = "CASCADE" if cascade else ""
            query = f"DROP TABLE {table_name} {cascade_str};"
            self.execute_query(query, fetch=False)
            return {'success': True, 'table': table_name}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def add_retention_policy(
        self,
        table_name: str,
        drop_after: str,
        if_not_exists: bool = True
    ) -> Dict[str, Any]:
        """
        Add automatic data retention policy.

        Args:
            table_name: Name of the hypertable
            drop_after: Drop data older than this (e.g., '7 days', '3 months')
            if_not_exists: Don't error if policy exists

        Returns:
            Dictionary with result
        """
        try:
            query = f"""
            SELECT add_retention_policy(
                '{table_name}',
                INTERVAL '{drop_after}',
                if_not_exists => {if_not_exists}
            );
            """
            self.execute_query(query, fetch=False)
            return {'success': True, 'table': table_name, 'drop_after': drop_after}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def remove_retention_policy(
        self,
        table_name: str,
        if_exists: bool = True
    ) -> Dict[str, Any]:
        """
        Remove retention policy from hypertable.

        Args:
            table_name: Name of the hypertable
            if_exists: Don't error if policy doesn't exist

        Returns:
            Dictionary with result
        """
        try:
            query = f"""
            SELECT remove_retention_policy('{table_name}', if_exists => {if_exists});
            """
            self.execute_query(query, fetch=False)
            return {'success': True, 'table': table_name}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def add_compression_policy(
        self,
        table_name: str,
        compress_after: str,
        if_not_exists: bool = True
    ) -> Dict[str, Any]:
        """
        Add automatic compression policy.

        Args:
            table_name: Name of the hypertable
            compress_after: Compress chunks older than this (e.g., '7 days')
            if_not_exists: Don't error if policy exists

        Returns:
            Dictionary with result
        """
        try:
            # First enable compression on the hypertable
            query1 = f"ALTER TABLE {table_name} SET (timescaledb.compress);"
            self.execute_query(query1, fetch=False)

            # Then add the policy
            query2 = f"""
            SELECT add_compression_policy(
                '{table_name}',
                INTERVAL '{compress_after}',
                if_not_exists => {if_not_exists}
            );
            """
            self.execute_query(query2, fetch=False)
            return {'success': True, 'table': table_name, 'compress_after': compress_after}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def remove_compression_policy(
        self,
        table_name: str,
        if_exists: bool = True
    ) -> Dict[str, Any]:
        """
        Remove compression policy from hypertable.

        Args:
            table_name: Name of the hypertable
            if_exists: Don't error if policy doesn't exist

        Returns:
            Dictionary with result
        """
        try:
            query = f"""
            SELECT remove_compression_policy('{table_name}', if_exists => {if_exists});
            """
            self.execute_query(query, fetch=False)
            return {'success': True, 'table': table_name}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ========================================================================
    # Continuous Aggregates
    # ========================================================================

    def create_continuous_aggregate(
        self,
        view_name: str,
        hypertable: str,
        time_column: str,
        bucket_interval: str,
        select_query: str,
        with_data: bool = True
    ) -> Dict[str, Any]:
        """
        Create a continuous aggregate (auto-updating materialized view).

        Args:
            view_name: Name for the continuous aggregate
            hypertable: Source hypertable name
            time_column: Time column name
            bucket_interval: Bucket size (e.g., '1 hour', '1 day')
            select_query: Aggregation query (SELECT columns, AGG() FROM ... GROUP BY ...)
            with_data: Populate with existing data

        Returns:
            Dictionary with result
        """
        try:
            with_data_str = "WITH DATA" if with_data else "WITH NO DATA"

            query = f"""
            CREATE MATERIALIZED VIEW {view_name}
            WITH (timescaledb.continuous) AS
            SELECT time_bucket(INTERVAL '{bucket_interval}', {time_column}) AS bucket,
                   {select_query}
            {with_data_str};
            """
            self.execute_query(query, fetch=False)
            return {'success': True, 'view': view_name}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def drop_continuous_aggregate(
        self,
        view_name: str,
        cascade: bool = False
    ) -> Dict[str, Any]:
        """
        Drop a continuous aggregate.

        Args:
            view_name: Name of the continuous aggregate
            cascade: Drop dependent objects

        Returns:
            Dictionary with result
        """
        try:
            cascade_str = "CASCADE" if cascade else ""
            query = f"DROP MATERIALIZED VIEW {view_name} {cascade_str};"
            self.execute_query(query, fetch=False)
            return {'success': True, 'view': view_name}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def refresh_continuous_aggregate(
        self,
        view_name: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Manually refresh a continuous aggregate.

        Args:
            view_name: Name of the continuous aggregate
            start_time: Start time for refresh (optional)
            end_time: End time for refresh (optional)

        Returns:
            Dictionary with result
        """
        try:
            if start_time and end_time:
                query = f"""
                CALL refresh_continuous_aggregate(
                    '{view_name}',
                    '{start_time}'::timestamptz,
                    '{end_time}'::timestamptz
                );
                """
            else:
                query = f"CALL refresh_continuous_aggregate('{view_name}', NULL, NULL);"

            self.execute_query(query, fetch=False)
            return {'success': True, 'view': view_name}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def add_continuous_aggregate_policy(
        self,
        view_name: str,
        start_offset: str,
        end_offset: str,
        schedule_interval: str
    ) -> Dict[str, Any]:
        """
        Add automatic refresh policy for continuous aggregate.

        Args:
            view_name: Name of the continuous aggregate
            start_offset: How far back to refresh (e.g., '1 month')
            end_offset: How recent to refresh (e.g., '1 hour')
            schedule_interval: How often to refresh (e.g., '1 hour')

        Returns:
            Dictionary with result
        """
        try:
            query = f"""
            SELECT add_continuous_aggregate_policy(
                '{view_name}',
                start_offset => INTERVAL '{start_offset}',
                end_offset => INTERVAL '{end_offset}',
                schedule_interval => INTERVAL '{schedule_interval}'
            );
            """
            self.execute_query(query, fetch=False)
            return {'success': True, 'view': view_name}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ========================================================================
    # Time-Series Query Helpers
    # ========================================================================

    def time_bucket_query(
        self,
        table_name: str,
        time_column: str,
        bucket_interval: str,
        aggregations: Dict[str, str],
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        where_clause: Optional[str] = None,
        order_by: str = "bucket ASC"
    ) -> pd.DataFrame:
        """
        Execute time-bucket aggregation query.

        Args:
            table_name: Name of the hypertable
            time_column: Time column name
            bucket_interval: Bucket size (e.g., '5 minutes', '1 hour')
            aggregations: Dict of column: function (e.g., {'value': 'AVG', 'count': 'COUNT(*)'})
            start_time: Start time filter
            end_time: End time filter
            where_clause: Additional WHERE conditions
            order_by: ORDER BY clause

        Returns:
            pandas DataFrame with results
        """
        # Build aggregation part
        agg_parts = []
        for col, func in aggregations.items():
            if func.upper() == 'COUNT(*)':
                agg_parts.append(f"COUNT(*) AS {col}")
            else:
                agg_parts.append(f"{func}({col}) AS {col}")

        agg_str = ", ".join(agg_parts)

        # Build WHERE clause
        where_parts = []
        if start_time:
            where_parts.append(f"{time_column} >= '{start_time}'")
        if end_time:
            where_parts.append(f"{time_column} < '{end_time}'")
        if where_clause:
            where_parts.append(where_clause)

        where_str = ""
        if where_parts:
            where_str = "WHERE " + " AND ".join(where_parts)

        query = f"""
        SELECT time_bucket(INTERVAL '{bucket_interval}', {time_column}) AS bucket,
               {agg_str}
        FROM {table_name}
        {where_str}
        GROUP BY bucket
        ORDER BY {order_by};
        """

        return self.query_to_dataframe(query)

    def fill_gaps(
        self,
        table_name: str,
        time_column: str,
        bucket_interval: str,
        start_time: str,
        end_time: str,
        columns: List[str],
        fill_method: str = "locf"  # locf, linear, or NULL
    ) -> pd.DataFrame:
        """
        Fill gaps in time-series data.

        Args:
            table_name: Name of the hypertable
            time_column: Time column name
            bucket_interval: Bucket size
            start_time: Start time
            end_time: End time
            columns: Columns to include
            fill_method: Fill method (locf=last observation carried forward, linear, NULL)

        Returns:
            pandas DataFrame with filled gaps
        """
        cols_str = ", ".join(columns)

        if fill_method.lower() == "locf":
            fill_func = "locf"
        elif fill_method.lower() == "linear":
            fill_func = "interpolate"
        else:
            fill_func = "NULL"

        query = f"""
        SELECT
            time_bucket_gapfill(INTERVAL '{bucket_interval}', {time_column}) AS bucket,
            {fill_func}(AVG({cols_str})) AS value
        FROM {table_name}
        WHERE {time_column} >= '{start_time}'
          AND {time_column} < '{end_time}'
        GROUP BY bucket
        ORDER BY bucket;
        """

        return self.query_to_dataframe(query)

    def get_hypertable_stats(self, table_name: str) -> Dict[str, Any]:
        """
        Get statistics about a hypertable.

        Args:
            table_name: Name of the hypertable

        Returns:
            Dictionary with statistics
        """
        try:
            query = f"""
            SELECT *
            FROM timescaledb_information.hypertables
            WHERE hypertable_name = '{table_name}';
            """
            result = self.execute_query(query)

            if result:
                return {'success': True, 'stats': result[0]}
            else:
                return {'success': False, 'error': 'Hypertable not found'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_chunk_info(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get information about chunks for a hypertable.

        Args:
            table_name: Name of the hypertable

        Returns:
            List of chunk information
        """
        query = f"""
        SELECT *
        FROM timescaledb_information.chunks
        WHERE hypertable_name = '{table_name}'
        ORDER BY range_start DESC;
        """
        return self.execute_query(query)

    def compress_chunk(self, chunk_name: str) -> Dict[str, Any]:
        """
        Manually compress a specific chunk.

        Args:
            chunk_name: Name of the chunk

        Returns:
            Dictionary with result
        """
        try:
            query = f"SELECT compress_chunk('{chunk_name}');"
            self.execute_query(query, fetch=False)
            return {'success': True, 'chunk': chunk_name}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def decompress_chunk(self, chunk_name: str) -> Dict[str, Any]:
        """
        Manually decompress a specific chunk.

        Args:
            chunk_name: Name of the chunk

        Returns:
            Dictionary with result
        """
        try:
            query = f"SELECT decompress_chunk('{chunk_name}');"
            self.execute_query(query, fetch=False)
            return {'success': True, 'chunk': chunk_name}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def close(self):
        """Close all connections in the pool."""
        if hasattr(self, 'pool'):
            self.pool.closeall()

    @classmethod
    def get_metadata(cls):
        """Get module metadata for compiler prompt generation."""
        from nl2py.modules.module_base import ModuleMetadata
        return ModuleMetadata(
            name="TimescaleDB",
            task_type="timescaledb",
            description="TimescaleDB time-series database (PostgreSQL extension) with hypertables, continuous aggregates, compression, and retention policies",
            version="1.0.0",
            keywords=[
                "timescaledb", "time-series", "postgresql", "hypertable", "continuous-aggregate",
                "compression", "retention", "iot", "metrics", "monitoring"
            ],
            dependencies=["psycopg2-binary>=2.9.0", "pandas>=1.0.0"]
        )

    @classmethod
    def get_usage_notes(cls):
        """Get detailed usage notes for this module."""
        return [
            "Module uses singleton pattern - one instance per application",
            "Built on PostgreSQL - all PostgreSQL features available",
            "Hypertables automatically partition data by time for fast queries",
            "Default chunk interval is 1 day, configurable per hypertable",
            "Continuous aggregates are auto-updating materialized views",
            "Retention policies automatically delete old data",
            "Compression policies reduce storage for old data (10x+ reduction typical)",
            "time_bucket() function aggregates data into time intervals",
            "time_bucket_gapfill() fills missing data points with locf, linear, or NULL",
            "Supports additional space partitioning for high-cardinality data",
            "create_default_indexes=True creates indexes on time column",
            "Compression must be enabled before adding compression policy",
            "Continuous aggregate policies auto-refresh on schedule",
            "start_offset and end_offset control refresh window",
            "Chunks are individual table partitions (view with get_chunk_info)",
            "Manual compression/decompression available per chunk",
            "Connection pooling with ThreadedConnectionPool for concurrency",
            "query_to_dataframe() integrates seamlessly with pandas",
            "All PostgreSQL data types and functions supported",
            "Requires TimescaleDB extension installed in PostgreSQL database"
        ]

    @classmethod
    def get_methods_info(cls):
        """Get information about all methods in this module."""
        from nl2py.modules.module_base import MethodInfo
        return [
            MethodInfo(
                name="create_hypertable",
                description="Convert regular table to hypertable with automatic time-based partitioning",
                parameters={
                    "table_name": "str (required) - Table name",
                    "time_column": "str (optional) - Time column name (default 'time')",
                    "chunk_time_interval": "str (optional) - Chunk size (default '1 day')",
                    "if_not_exists": "bool (optional) - Don't error if exists (default True)",
                    "partitioning_column": "str (optional) - Additional partition column",
                    "number_partitions": "int (optional) - Number of space partitions"
                },
                returns="dict - Result with success status",
                examples=[
                    {
                        "text": "Convert table {{metrics}} to hypertable with time column {{timestamp}} and chunk interval {{1 hour}}",
                        "code": "create_hypertable(table_name='{{metrics}}', time_column='{{timestamp}}', chunk_time_interval='{{1 hour}}')"
                    }
                ]
            ),
            MethodInfo(
                name="add_retention_policy",
                description="Automatically delete data older than specified interval",
                parameters={
                    "table_name": "str (required) - Hypertable name",
                    "drop_after": "str (required) - Drop data older than (e.g., '7 days', '3 months')",
                    "if_not_exists": "bool (optional) - Don't error if exists (default True)"
                },
                returns="dict - Result with success status",
                examples=[
                    {
                        "text": "Add retention policy to {{metrics}} to delete data older than {{30 days}}",
                        "code": "add_retention_policy(table_name='{{metrics}}', drop_after='{{30 days}}')"
                    }
                ]
            ),
            MethodInfo(
                name="add_compression_policy",
                description="Automatically compress old data to save storage",
                parameters={
                    "table_name": "str (required) - Hypertable name",
                    "compress_after": "str (required) - Compress data older than (e.g., '7 days')",
                    "if_not_exists": "bool (optional) - Don't error if exists (default True)"
                },
                returns="dict - Result with success status",
                examples=[
                    {
                        "text": "Add compression policy to {{metrics}} to compress data older than {{7 days}}",
                        "code": "add_compression_policy(table_name='{{metrics}}', compress_after='{{7 days}}')"
                    }
                ]
            ),
            MethodInfo(
                name="create_continuous_aggregate",
                description="Create auto-updating materialized view for pre-computed aggregations",
                parameters={
                    "view_name": "str (required) - View name",
                    "hypertable": "str (required) - Source hypertable",
                    "time_column": "str (required) - Time column",
                    "bucket_interval": "str (required) - Bucket size (e.g., '1 hour')",
                    "select_query": "str (required) - Aggregation columns",
                    "with_data": "bool (optional) - Populate immediately (default True)"
                },
                returns="dict - Result with success status",
                examples=[
                    {
                        "text": "Create continuous aggregate {{metrics_hourly}} from {{metrics}} with {{1 hour}} bucket and aggregations {{AVG(value), MAX(value)}}",
                        "code": "create_continuous_aggregate(view_name='{{metrics_hourly}}', hypertable='{{metrics}}', time_column='{{timestamp}}', bucket_interval='{{1 hour}}', select_query='{{AVG(value), MAX(value)}}')"
                    }
                ]
            ),
            MethodInfo(
                name="time_bucket_query",
                description="Execute time-bucketed aggregation query with optional filters",
                parameters={
                    "table_name": "str (required) - Hypertable name",
                    "time_column": "str (required) - Time column",
                    "bucket_interval": "str (required) - Bucket size (e.g., '5 minutes')",
                    "aggregations": "dict (required) - Column: function mappings",
                    "start_time": "str (optional) - Start time filter",
                    "end_time": "str (optional) - End time filter",
                    "where_clause": "str (optional) - Additional WHERE conditions"
                },
                returns="DataFrame - Results as pandas DataFrame",
                examples=[
                    {
                        "text": "Query {{metrics}} with {{1 hour}} buckets aggregating {{AVG(value)}} and {{COUNT(*)}}",
                        "code": "time_bucket_query(table_name='{{metrics}}', time_column='{{timestamp}}', bucket_interval='{{1 hour}}', aggregations={{'value': 'AVG', 'count': 'COUNT(*)'}})"
                    }
                ]
            ),
            MethodInfo(
                name="fill_gaps",
                description="Fill missing data points in time-series using locf, linear, or NULL",
                parameters={
                    "table_name": "str (required) - Hypertable name",
                    "time_column": "str (required) - Time column",
                    "bucket_interval": "str (required) - Bucket size",
                    "start_time": "str (required) - Start time",
                    "end_time": "str (required) - End time",
                    "columns": "list (required) - Columns to fill",
                    "fill_method": "str (optional) - Method: locf, linear, NULL (default locf)"
                },
                returns="DataFrame - Results with filled gaps",
                examples=[
                    {
                        "text": "Fill gaps in {{metrics}} with {{5 minutes}} buckets from {{2023-01-01}} to {{2023-01-02}} using {{locf}} method",
                        "code": "fill_gaps(table_name='{{metrics}}', time_column='{{timestamp}}', bucket_interval='{{5 minutes}}', start_time='{{2023-01-01}}', end_time='{{2023-01-02}}', columns={{['value']}}, fill_method='{{locf}}')"
                    }
                ]
            ),
            MethodInfo(
                name="execute_query",
                description="Execute SQL query and return results as list of dictionaries",
                parameters={
                    "query": "str (required) - SQL query",
                    "params": "tuple (optional) - Query parameters",
                    "fetch": "bool (optional) - Fetch results (default True)"
                },
                returns="list[dict] - Query results",
                examples=[
                    {
                        "text": "Execute query {{SELECT * FROM metrics WHERE timestamp > NOW() - INTERVAL '1 hour'}}",
                        "code": "execute_query(query='{{SELECT * FROM metrics WHERE timestamp > NOW() - INTERVAL \\'1 hour\\'}}')"
                    }
                ]
            ),
            MethodInfo(
                name="query_to_dataframe",
                description="Execute query and return results as pandas DataFrame",
                parameters={
                    "query": "str (required) - SQL query",
                    "params": "tuple (optional) - Query parameters"
                },
                returns="DataFrame - pandas DataFrame",
                examples=[
                    {
                        "text": "Query to DataFrame: {{SELECT time_bucket('1 hour', timestamp) as hour, AVG(value) FROM metrics GROUP BY hour}}",
                        "code": "query_to_dataframe(query='{{SELECT time_bucket(\\'1 hour\\', timestamp) as hour, AVG(value) FROM metrics GROUP BY hour}}')"
                    }
                ]
            ),
            MethodInfo(
                name="get_hypertable_stats",
                description="Get statistics and configuration for hypertable",
                parameters={"table_name": "str (required) - Hypertable name"},
                returns="dict - Hypertable statistics",
                examples=[
                    {
                        "text": "Get statistics for hypertable {{metrics}}",
                        "code": "get_hypertable_stats(table_name='{{metrics}}')"
                    }
                ]
            ),
            MethodInfo(
                name="get_chunk_info",
                description="Get information about all chunks (partitions) for hypertable",
                parameters={"table_name": "str (required) - Hypertable name"},
                returns="list[dict] - Chunk information",
                examples=[
                    {
                        "text": "Get chunk information for hypertable {{metrics}}",
                        "code": "get_chunk_info(table_name='{{metrics}}')"
                    }
                ]
            ),
            MethodInfo(
                name="compress_chunk",
                description="Manually compress a specific chunk for storage optimization",
                parameters={"chunk_name": "str (required) - Chunk name (from get_chunk_info)"},
                returns="dict - Result with success status and chunk name",
                examples=[
                    {
                        "text": "Compress chunk {{_timescaledb_internal._hyper_1_1_chunk}}",
                        "code": "compress_chunk(chunk_name='{{_timescaledb_internal._hyper_1_1_chunk}}')"
                    }
                ]
            ),
            MethodInfo(
                name="decompress_chunk",
                description="Decompress a previously compressed chunk for modification",
                parameters={"chunk_name": "str (required) - Chunk name"},
                returns="dict - Result with success status and chunk name",
                examples=[
                    {
                        "text": "Decompress chunk {{_timescaledb_internal._hyper_1_1_chunk}}",
                        "code": "decompress_chunk(chunk_name='{{_timescaledb_internal._hyper_1_1_chunk}}')"
                    }
                ]
            )
        ]

# Singleton instance getter
def get_timescaledb_module(**kwargs) -> TimescaleDBModule:
    """
    Get the singleton TimescaleDB module instance.

    Args:
        **kwargs: Configuration parameters

    Returns:
        TimescaleDBModule instance
    """
    return TimescaleDBModule(**kwargs)
