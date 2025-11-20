"""
Streamlit App for Semantic View Creation with Snowflake Cortex AI
"""

import streamlit as st
import json
from datetime import datetime
import pandas as pd
import warnings
import logging

# Suppress ScriptRunContext warnings
warnings.filterwarnings('ignore', message='.*ScriptRunContext.*')
logging.getLogger('streamlit.runtime.scriptrunner_utils.script_run_context').setLevel(logging.ERROR)

# Import custom modules
from snowflake_utils import (
    get_snowflake_connection,
    get_snowpark_session,
    get_databases,
    get_schemas,
    get_tables,
    get_table_schema,
    get_table_sample,
    get_table_stats,
    test_connection
)
from cortex_ai import (
    generate_semantic_view_with_cortex,
    create_basic_semantic_view,
    enhance_semantic_view_with_cortex
)
from yaml_handler import (
    save_semantic_view_to_yaml,
    load_semantic_view_from_yaml,
    list_saved_semantic_views,
    export_semantic_view_as_yaml_string,
    validate_semantic_view
)

# Page configuration
st.set_page_config(
    page_title="Semantic View Creator",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'connected' not in st.session_state:
    st.session_state.connected = False
if 'semantic_view' not in st.session_state:
    st.session_state.semantic_view = None
if 'selected_table' not in st.session_state:
    st.session_state.selected_table = None


def render_connection_sidebar():
    """Render the Snowflake connection configuration in sidebar."""
    with st.sidebar:
        st.header("Snowflake Connection")

        if not st.session_state.connected:
            with st.form("connection_form"):
                st.markdown("### Authentication")

                auth_method = st.radio(
                    "Authentication Method",
                    options=['OAuth/SSO', 'Password'],
                    help="Choose OAuth/SSO for browser-based authentication (Sign in using OAuth)"
                )

                st.markdown("### Connection Details")

                # Account input with better helper
                server_or_account = st.text_input(
                    "Server or Account",
                    placeholder="te8232002.north-europe.azure or full URL",
                    help="Enter account ID (e.g., te8232002.north-europe.azure) or full server URL"
                )

                # Parse the input to extract account identifier
                account = server_or_account.strip()
                if '.snowflakecomputing.com' in account:
                    # Extract account from full URL
                    account = account.replace('https://', '').replace('http://', '')
                    account = account.split('.snowflakecomputing.com')[0]

                # Show parsed account if different from input
                if account != server_or_account.strip():
                    st.caption(f"Using account: `{account}`")

                if auth_method == 'OAuth/SSO':
                    user = st.text_input(
                        "User",
                        placeholder="your.email@company.com",
                        help="Your Snowflake username (used to identify your account during SSO)"
                    )
                else:
                    user = st.text_input("User", help="Your email or username")

                # Only show password field if not using SSO
                password = ""
                if auth_method == 'Password':
                    password = st.text_input("Password", type="password")
                else:
                    st.info("🔐 Browser will open for OAuth/SSO authentication")

                st.markdown("### Optional Parameters")
                with st.expander("Advanced Settings", expanded=False):
                    warehouse = st.text_input("Warehouse")
                    database = st.text_input("Database")
                    schema = st.text_input("Schema")
                    role = st.text_input("Role", placeholder="e.g., PRD_VISUALISER")

                submit = st.form_submit_button("Sign In", type="primary")

                if submit:
                    authenticator = 'externalbrowser' if auth_method == 'OAuth/SSO' else 'password'

                    # Validate required fields
                    if not account or not user:
                        st.error("Please provide server/account and user.")
                    elif auth_method == 'Password' and not password:
                        st.error("Please provide password.")
                    else:
                        with st.spinner("Connecting to Snowflake..." +
                                      (" Opening browser for OAuth/SSO login..." if auth_method == 'OAuth/SSO' else "")):
                            if test_connection(account, user, password, warehouse, database, schema, role, authenticator):
                                # Build credentials dict
                                st.session_state.snowflake_credentials = {
                                    'account': account,
                                    'user': user,
                                    'warehouse': warehouse,
                                    'database': database,
                                    'schema': schema,
                                    'role': role,
                                    'authenticator': authenticator
                                }
                                # Only add password if it's not empty (OAuth/SSO doesn't need it)
                                if password:
                                    st.session_state.snowflake_credentials['password'] = password
                                st.session_state.connected = True
                                st.success("✅ Connected successfully!")
                                st.rerun()
                            else:
                                st.error("Connection failed. Please check your credentials and try again.")
        else:
            st.success("✅ Connected to Snowflake")
            creds = st.session_state.snowflake_credentials

            # Show connection info
            st.markdown("### Connection Info")
            st.text(f"Account: {creds['account']}")
            st.text(f"User: {creds['user']}")

            # Show auth method
            if creds.get('authenticator') == 'externalbrowser':
                st.text("Auth: OAuth/SSO")
            else:
                st.text("Auth: Password")

            if creds.get('warehouse'):
                st.text(f"Warehouse: {creds['warehouse']}")
            if creds.get('database'):
                st.text(f"Database: {creds['database']}")

            if st.button("Disconnect", type="secondary"):
                st.session_state.connected = False
                st.session_state.snowflake_credentials = None
                st.session_state.semantic_view = None
                st.session_state.selected_table = None
                st.rerun()


def render_table_selector(conn):
    """Render the table selection interface."""
    st.header("Select Table")

    col1, col2, col3 = st.columns(3)

    with col1:
        databases = get_databases(conn)
        if databases:
            selected_db = st.selectbox("Database", databases)
        else:
            st.warning("No databases found or insufficient permissions.")
            return None, None, None

    with col2:
        if selected_db:
            schemas = get_schemas(conn, selected_db)
            if schemas:
                selected_schema = st.selectbox("Schema", schemas)
            else:
                st.warning(f"No schemas found in {selected_db}")
                return None, None, None
        else:
            return None, None, None

    with col3:
        if selected_schema:
            tables = get_tables(conn, selected_db, selected_schema)
            if tables:
                selected_table = st.selectbox("Table", tables)
            else:
                st.warning(f"No tables found in {selected_db}.{selected_schema}")
                return None, None, None
        else:
            return None, None, None

    return selected_db, selected_schema, selected_table


def render_table_preview(conn, database, schema, table):
    """Render table preview with schema and sample data."""
    st.subheader(f"Table: {database}.{schema}.{table}")

    # Get table statistics
    stats = get_table_stats(conn, database, schema, table)
    if stats:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Row Count", f"{stats.get('row_count', 'N/A'):,}")
        with col2:
            bytes_size = stats.get('bytes', 0)
            if bytes_size:
                size_mb = bytes_size / (1024 * 1024)
                st.metric("Size", f"{size_mb:.2f} MB")
        with col3:
            if 'last_altered' in stats:
                st.metric("Last Modified", stats['last_altered'].strftime('%Y-%m-%d') if stats['last_altered'] else 'N/A')

    # Show schema
    with st.expander("Table Schema", expanded=True):
        schema_df = get_table_schema(conn, database, schema, table)
        if not schema_df.empty:
            st.dataframe(
                schema_df[['column_name', 'data_type', 'is_nullable', 'comment']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("Could not retrieve table schema.")

    # Show sample data
    with st.expander("Sample Data", expanded=False):
        sample_df = get_table_sample(conn, database, schema, table, limit=10)
        if not sample_df.empty:
            st.dataframe(sample_df, use_container_width=True, hide_index=True)
        else:
            st.warning("Could not retrieve sample data.")

    return schema_df, sample_df


def render_semantic_view_generator(session, conn, database, schema, table, schema_df, sample_df):
    """Render the semantic view generation interface."""
    st.header("Generate Semantic View")

    col1, col2 = st.columns([3, 1])

    with col1:
        st.info("Click the button below to generate a semantic view using Snowflake Cortex AI.")

    with col2:
        use_cortex = st.checkbox("Use Cortex AI", value=True, help="Uncheck to create basic structure without AI")

    if st.button("Generate Semantic View", type="primary", use_container_width=True):
        with st.spinner("Generating semantic view..."):
            if use_cortex and session:
                semantic_view = generate_semantic_view_with_cortex(
                    session, database, schema, table, schema_df, sample_df
                )
            else:
                semantic_view = create_basic_semantic_view(
                    database, schema, table, schema_df
                )

            st.session_state.semantic_view = semantic_view
            st.session_state.selected_table = {'database': database, 'schema': schema, 'table': table}
            st.success("Semantic view generated successfully!")
            st.rerun()


def render_semantic_view_editor():
    """Render the semantic view editor interface."""
    if not st.session_state.semantic_view:
        return

    st.header("Edit Semantic View")

    semantic_view = st.session_state.semantic_view

    # Display and edit basic information
    st.subheader("Basic Information")
    col1, col2 = st.columns(2)

    with col1:
        name = st.text_input("View Name", value=semantic_view.get('name', ''))
        if name != semantic_view.get('name', ''):
            semantic_view['name'] = name

    with col2:
        description = st.text_input("Description", value=semantic_view.get('description', ''))
        if description != semantic_view.get('description', ''):
            semantic_view['description'] = description

    # Edit dimensions
    st.subheader("Dimensions")
    if 'dimensions' in semantic_view and semantic_view['dimensions']:
        for idx, dim in enumerate(semantic_view['dimensions']):
            with st.expander(f"Dimension: {dim.get('name', f'dim_{idx}')}"):
                col1, col2 = st.columns(2)
                with col1:
                    dim['name'] = st.text_input(f"Name##dim_name_{idx}", value=dim.get('name', ''))
                    dim['column'] = st.text_input(f"Column##dim_col_{idx}", value=dim.get('column', ''))
                    dim['data_type'] = st.text_input(f"Data Type##dim_type_{idx}", value=dim.get('data_type', ''))

                with col2:
                    dim['description'] = st.text_area(f"Description##dim_desc_{idx}", value=dim.get('description', ''), height=100)

                    # Handle synonyms
                    synonyms_str = ', '.join(dim.get('synonyms', []))
                    new_synonyms = st.text_input(
                        f"Synonyms (comma-separated)##dim_syn_{idx}",
                        value=synonyms_str
                    )
                    dim['synonyms'] = [s.strip() for s in new_synonyms.split(',') if s.strip()]

                if st.button(f"Remove Dimension##remove_dim_{idx}"):
                    semantic_view['dimensions'].pop(idx)
                    st.rerun()
    else:
        st.info("No dimensions defined.")

    if st.button("Add Dimension"):
        if 'dimensions' not in semantic_view:
            semantic_view['dimensions'] = []
        semantic_view['dimensions'].append({
            'name': 'new_dimension',
            'column': '',
            'data_type': '',
            'description': '',
            'synonyms': []
        })
        st.rerun()

    # Edit measures
    st.subheader("Measures")
    if 'measures' in semantic_view and semantic_view['measures']:
        for idx, measure in enumerate(semantic_view['measures']):
            with st.expander(f"Measure: {measure.get('name', f'measure_{idx}')}"):
                col1, col2 = st.columns(2)
                with col1:
                    measure['name'] = st.text_input(f"Name##measure_name_{idx}", value=measure.get('name', ''))
                    measure['column'] = st.text_input(f"Column##measure_col_{idx}", value=measure.get('column', ''))
                    measure['aggregation'] = st.selectbox(
                        f"Aggregation##measure_agg_{idx}",
                        options=['sum', 'avg', 'count', 'min', 'max'],
                        index=['sum', 'avg', 'count', 'min', 'max'].index(measure.get('aggregation', 'sum'))
                    )

                with col2:
                    measure['data_type'] = st.text_input(f"Data Type##measure_type_{idx}", value=measure.get('data_type', ''))
                    measure['description'] = st.text_area(f"Description##measure_desc_{idx}", value=measure.get('description', ''), height=100)

                if st.button(f"Remove Measure##remove_measure_{idx}"):
                    semantic_view['measures'].pop(idx)
                    st.rerun()
    else:
        st.info("No measures defined.")

    if st.button("Add Measure"):
        if 'measures' not in semantic_view:
            semantic_view['measures'] = []
        semantic_view['measures'].append({
            'name': 'new_measure',
            'column': '',
            'aggregation': 'sum',
            'data_type': '',
            'description': ''
        })
        st.rerun()

    # Edit time dimensions
    st.subheader("Time Dimensions")
    if 'time_dimensions' in semantic_view and semantic_view['time_dimensions']:
        for idx, time_dim in enumerate(semantic_view['time_dimensions']):
            with st.expander(f"Time Dimension: {time_dim.get('name', f'time_dim_{idx}')}"):
                col1, col2 = st.columns(2)
                with col1:
                    time_dim['name'] = st.text_input(f"Name##time_name_{idx}", value=time_dim.get('name', ''))
                    time_dim['column'] = st.text_input(f"Column##time_col_{idx}", value=time_dim.get('column', ''))
                    time_dim['data_type'] = st.text_input(f"Data Type##time_type_{idx}", value=time_dim.get('data_type', ''))

                with col2:
                    granularities = time_dim.get('granularities', [])
                    selected_gran = st.multiselect(
                        f"Granularities##time_gran_{idx}",
                        options=['second', 'minute', 'hour', 'day', 'week', 'month', 'quarter', 'year'],
                        default=granularities
                    )
                    time_dim['granularities'] = selected_gran

                if st.button(f"Remove Time Dimension##remove_time_{idx}"):
                    semantic_view['time_dimensions'].pop(idx)
                    st.rerun()
    else:
        st.info("No time dimensions defined.")

    if st.button("Add Time Dimension"):
        if 'time_dimensions' not in semantic_view:
            semantic_view['time_dimensions'] = []
        semantic_view['time_dimensions'].append({
            'name': 'new_time_dimension',
            'column': '',
            'data_type': '',
            'granularities': ['day', 'month', 'year']
        })
        st.rerun()

    # Update session state
    st.session_state.semantic_view = semantic_view


def render_semantic_view_display():
    """Render the semantic view display and export options."""
    if not st.session_state.semantic_view:
        return

    st.header("Semantic View")

    semantic_view = st.session_state.semantic_view

    # Validate
    is_valid, errors = validate_semantic_view(semantic_view)

    if is_valid:
        st.success("Semantic view is valid!")
    else:
        st.error("Semantic view has validation errors:")
        for error in errors:
            st.error(f"- {error}")

    # Display as JSON
    with st.expander("View as JSON", expanded=False):
        st.json(semantic_view)

    # Display as YAML
    with st.expander("View as YAML", expanded=True):
        yaml_str = export_semantic_view_as_yaml_string(semantic_view)
        if yaml_str:
            st.code(yaml_str, language='yaml')

    # Save options
    st.subheader("Save Semantic View")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Save to File", type="primary", use_container_width=True):
            filepath = save_semantic_view_to_yaml(semantic_view)
            if filepath:
                st.success(f"Saved to: {filepath}")

    with col2:
        yaml_str = export_semantic_view_as_yaml_string(semantic_view)
        if yaml_str:
            st.download_button(
                label="Download YAML",
                data=yaml_str,
                file_name=f"{semantic_view.get('name', 'semantic_view')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml",
                mime="text/yaml",
                use_container_width=True
            )

    with col3:
        json_str = json.dumps(semantic_view, indent=2)
        st.download_button(
            label="Download JSON",
            data=json_str,
            file_name=f"{semantic_view.get('name', 'semantic_view')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )


def render_saved_views():
    """Render the saved semantic views browser."""
    st.header("Saved Semantic Views")

    saved_files = list_saved_semantic_views()

    if saved_files:
        selected_file = st.selectbox("Select a saved view to load", saved_files)

        col1, col2 = st.columns([1, 4])

        with col1:
            if st.button("Load View"):
                filepath = f"semantic_views/{selected_file}"
                loaded_view = load_semantic_view_from_yaml(filepath)
                if loaded_view:
                    st.session_state.semantic_view = loaded_view
                    st.success(f"Loaded: {selected_file}")
                    st.rerun()

        with col2:
            st.info(f"Selected: {selected_file}")
    else:
        st.info("No saved semantic views found.")


def main():
    """Main application function."""
    st.title("Semantic View Creator")
    st.markdown("Create and manage semantic views for your Snowflake tables using Cortex AI")

    # Render connection sidebar
    render_connection_sidebar()

    if not st.session_state.connected:
        st.info("Please connect to Snowflake using the sidebar to get started.")
        return

    # Get connections
    conn = get_snowflake_connection()
    session = get_snowpark_session()

    if not conn:
        st.error("Failed to establish Snowflake connection. Please check your credentials.")
        return

    # Create tabs for different sections
    tab1, tab2, tab3 = st.tabs(["Create New View", "Edit Current View", "Saved Views"])

    with tab1:
        # Table selection
        database, schema, table = render_table_selector(conn)

        if database and schema and table:
            # Table preview
            schema_df, sample_df = render_table_preview(conn, database, schema, table)

            # Generate semantic view
            if schema_df is not None:
                render_semantic_view_generator(session, conn, database, schema, table, schema_df, sample_df)

    with tab2:
        if st.session_state.semantic_view:
            # Editor
            render_semantic_view_editor()

            st.divider()

            # Display and export
            render_semantic_view_display()
        else:
            st.info("No semantic view loaded. Please create or load a view first.")

    with tab3:
        render_saved_views()

    # Close connections
    if conn:
        conn.close()
    if session:
        session.close()


if __name__ == "__main__":
    main()
