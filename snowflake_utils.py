"""
Snowflake connection and data utilities for Semantic View creation.
"""

import streamlit as st
import snowflake.connector
from snowflake.snowpark import Session
import pandas as pd
from typing import List, Dict, Any, Optional


def get_snowflake_connection():
    """
    Create Snowflake connection using credentials from Streamlit secrets or session state.
    Supports both password and Azure SSO authentication.
    """
    try:
        # Try to get credentials from Streamlit secrets first
        if hasattr(st, 'secrets') and 'snowflake' in st.secrets:
            conn_params = {
                'account': st.secrets['snowflake']['account'],
                'user': st.secrets['snowflake']['user'],
            }

            # Check authentication method
            auth_method = st.secrets['snowflake'].get('authenticator', 'password')
            if auth_method == 'externalbrowser':
                conn_params['authenticator'] = 'externalbrowser'
            else:
                conn_params['password'] = st.secrets['snowflake']['password']

            # Add optional parameters
            if st.secrets['snowflake'].get('warehouse'):
                conn_params['warehouse'] = st.secrets['snowflake']['warehouse']
            if st.secrets['snowflake'].get('database'):
                conn_params['database'] = st.secrets['snowflake']['database']
            if st.secrets['snowflake'].get('schema'):
                conn_params['schema'] = st.secrets['snowflake']['schema']
            if st.secrets['snowflake'].get('role'):
                conn_params['role'] = st.secrets['snowflake']['role']

            conn = snowflake.connector.connect(**conn_params)

        elif 'snowflake_credentials' in st.session_state:
            creds = st.session_state['snowflake_credentials']
            conn_params = {
                'account': creds['account'],
                'user': creds['user'],
            }

            # Check authentication method
            if creds.get('authenticator') == 'externalbrowser':
                conn_params['authenticator'] = 'externalbrowser'
            else:
                conn_params['password'] = creds['password']

            # Add optional parameters
            if creds.get('warehouse'):
                conn_params['warehouse'] = creds['warehouse']
            if creds.get('database'):
                conn_params['database'] = creds['database']
            if creds.get('schema'):
                conn_params['schema'] = creds['schema']
            if creds.get('role'):
                conn_params['role'] = creds['role']

            conn = snowflake.connector.connect(**conn_params)
        else:
            return None

        return conn
    except Exception as e:
        st.error(f"Failed to connect to Snowflake: {str(e)}")
        return None


def get_snowpark_session():
    """
    Create Snowpark session for Cortex AI operations.
    Supports both password and Azure SSO authentication.
    """
    try:
        if hasattr(st, 'secrets') and 'snowflake' in st.secrets:
            connection_parameters = {
                "account": st.secrets['snowflake']['account'],
                "user": st.secrets['snowflake']['user'],
            }

            # Check authentication method
            auth_method = st.secrets['snowflake'].get('authenticator', 'password')
            if auth_method == 'externalbrowser':
                connection_parameters['authenticator'] = 'externalbrowser'
            else:
                connection_parameters['password'] = st.secrets['snowflake']['password']

            # Add optional parameters
            if st.secrets['snowflake'].get('warehouse'):
                connection_parameters['warehouse'] = st.secrets['snowflake']['warehouse']
            if st.secrets['snowflake'].get('database'):
                connection_parameters['database'] = st.secrets['snowflake']['database']
            if st.secrets['snowflake'].get('schema'):
                connection_parameters['schema'] = st.secrets['snowflake']['schema']
            if st.secrets['snowflake'].get('role'):
                connection_parameters['role'] = st.secrets['snowflake']['role']

        elif 'snowflake_credentials' in st.session_state:
            creds = st.session_state['snowflake_credentials']
            connection_parameters = {
                "account": creds['account'],
                "user": creds['user'],
            }

            # Check authentication method
            if creds.get('authenticator') == 'externalbrowser':
                connection_parameters['authenticator'] = 'externalbrowser'
            else:
                connection_parameters['password'] = creds['password']

            # Add optional parameters
            if creds.get('warehouse'):
                connection_parameters['warehouse'] = creds['warehouse']
            if creds.get('database'):
                connection_parameters['database'] = creds['database']
            if creds.get('schema'):
                connection_parameters['schema'] = creds['schema']
            if creds.get('role'):
                connection_parameters['role'] = creds['role']
        else:
            return None

        session = Session.builder.configs(connection_parameters).create()
        return session
    except Exception as e:
        st.error(f"Failed to create Snowpark session: {str(e)}")
        return None


def get_databases(conn) -> List[str]:
    """Get list of available databases."""
    try:
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES")
        databases = [row[1] for row in cursor.fetchall()]
        cursor.close()
        return databases
    except Exception as e:
        st.error(f"Error fetching databases: {str(e)}")
        return []


def get_schemas(conn, database: str) -> List[str]:
    """Get list of schemas in a database."""
    try:
        cursor = conn.cursor()
        cursor.execute(f"SHOW SCHEMAS IN DATABASE {database}")
        schemas = [row[1] for row in cursor.fetchall()]
        cursor.close()
        return schemas
    except Exception as e:
        st.error(f"Error fetching schemas: {str(e)}")
        return []


def get_tables(conn, database: str, schema: str) -> List[str]:
    """Get list of tables in a schema."""
    try:
        cursor = conn.cursor()
        cursor.execute(f"SHOW TABLES IN {database}.{schema}")
        tables = [row[1] for row in cursor.fetchall()]
        cursor.close()
        return tables
    except Exception as e:
        st.error(f"Error fetching tables: {str(e)}")
        return []


def get_table_schema(conn, database: str, schema: str, table: str) -> pd.DataFrame:
    """Get table schema information including column names, types, and constraints."""
    try:
        cursor = conn.cursor()
        query = f"""
        SELECT
            COLUMN_NAME,
            DATA_TYPE,
            IS_NULLABLE,
            COLUMN_DEFAULT,
            CHARACTER_MAXIMUM_LENGTH,
            NUMERIC_PRECISION,
            NUMERIC_SCALE,
            COMMENT
        FROM {database}.INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = '{schema}'
        AND TABLE_NAME = '{table}'
        ORDER BY ORDINAL_POSITION
        """
        cursor.execute(query)
        columns = ['column_name', 'data_type', 'is_nullable', 'default_value',
                   'char_length', 'numeric_precision', 'numeric_scale', 'comment']
        df = pd.DataFrame(cursor.fetchall(), columns=columns)
        cursor.close()
        return df
    except Exception as e:
        st.error(f"Error fetching table schema: {str(e)}")
        return pd.DataFrame()


def get_table_sample(conn, database: str, schema: str, table: str, limit: int = 5) -> pd.DataFrame:
    """Get sample data from a table."""
    try:
        cursor = conn.cursor()
        query = f"SELECT * FROM {database}.{schema}.{table} LIMIT {limit}"
        cursor.execute(query)
        df = pd.DataFrame(cursor.fetchall(), columns=[col[0] for col in cursor.description])
        cursor.close()
        return df
    except Exception as e:
        st.error(f"Error fetching table sample: {str(e)}")
        return pd.DataFrame()


def get_table_stats(conn, database: str, schema: str, table: str) -> Dict[str, Any]:
    """Get table statistics including row count and size."""
    try:
        cursor = conn.cursor()

        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {database}.{schema}.{table}")
        row_count = cursor.fetchone()[0]

        # Get table info
        cursor.execute(f"""
        SELECT
            ROW_COUNT,
            BYTES,
            CREATED,
            LAST_ALTERED
        FROM {database}.INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = '{schema}'
        AND TABLE_NAME = '{table}'
        """)
        result = cursor.fetchone()

        cursor.close()

        if result:
            return {
                'row_count': row_count,
                'bytes': result[1],
                'created': result[2],
                'last_altered': result[3]
            }
        return {'row_count': row_count}
    except Exception as e:
        st.error(f"Error fetching table stats: {str(e)}")
        return {}


def test_connection(account: str, user: str, password: str = '', warehouse: str = '',
                    database: str = '', schema: str = '', role: str = '',
                    authenticator: str = 'password') -> bool:
    """
    Test Snowflake connection with provided credentials.
    Supports both password and Azure SSO authentication.
    """
    try:
        conn_params = {
            'account': account,
            'user': user,
        }

        # Add authentication method
        if authenticator == 'externalbrowser':
            conn_params['authenticator'] = 'externalbrowser'
        else:
            conn_params['password'] = password

        if warehouse:
            conn_params['warehouse'] = warehouse
        if database:
            conn_params['database'] = database
        if schema:
            conn_params['schema'] = schema
        if role:
            conn_params['role'] = role

        conn = snowflake.connector.connect(**conn_params)
        conn.close()
        return True
    except Exception as e:
        st.error(f"Connection test failed: {str(e)}")
        return False
