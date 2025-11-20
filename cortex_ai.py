"""
Cortex AI integration for semantic view generation and analysis.
"""

import streamlit as st
from snowflake.snowpark import Session
from typing import Dict, Any, List
import json
import pandas as pd


def generate_semantic_view_with_cortex(
    session: Session,
    database: str,
    schema: str,
    table: str,
    table_schema: pd.DataFrame,
    sample_data: pd.DataFrame
) -> Dict[str, Any]:
    """
    Use Snowflake Cortex AI to analyze a table and generate a semantic view definition.

    Args:
        session: Snowpark session
        database: Database name
        schema: Schema name
        table: Table name
        table_schema: DataFrame with table schema information
        sample_data: DataFrame with sample data from the table

    Returns:
        Dictionary containing semantic view definition
    """
    try:
        # Prepare the context for Cortex AI
        schema_info = table_schema.to_dict('records')
        sample_info = sample_data.head(3).to_dict('records') if not sample_data.empty else []

        # Create a prompt for Cortex AI to generate semantic view
        prompt = f"""
Analyze the following database table and create a semantic view definition in JSON format.

Table: {database}.{schema}.{table}

Schema Information:
{json.dumps(schema_info, indent=2)}

Sample Data (first 3 rows):
{json.dumps(sample_info, indent=2)}

Please generate a semantic view definition with the following structure:
{{
    "name": "semantic_view_name",
    "description": "Description of what this view represents",
    "base_table": {{
        "database": "{database}",
        "schema": "{schema}",
        "table": "{table}"
    }},
    "dimensions": [
        {{
            "name": "dimension_name",
            "column": "column_name",
            "data_type": "data_type",
            "description": "Description of the dimension",
            "synonyms": ["synonym1", "synonym2"]
        }}
    ],
    "measures": [
        {{
            "name": "measure_name",
            "column": "column_name",
            "aggregation": "sum/avg/count/min/max",
            "data_type": "data_type",
            "description": "Description of the measure"
        }}
    ],
    "time_dimensions": [
        {{
            "name": "time_dimension_name",
            "column": "column_name",
            "data_type": "data_type",
            "granularities": ["day", "week", "month", "year"]
        }}
    ]
}}

Identify appropriate dimensions (categorical columns), measures (numeric columns for aggregation), and time dimensions (date/timestamp columns).
Provide meaningful descriptions and synonyms for natural language querying.
Return ONLY valid JSON without any additional text or markdown formatting.
"""

        # Use Cortex Complete function
        cortex_query = f"""
        SELECT SNOWFLAKE.CORTEX.COMPLETE(
            'mixtral-8x7b',
            [{{'role': 'user', 'content': {session.sql("SELECT ?", [prompt]).collect()[0][0]}}}]
        ) as response
        """

        result = session.sql(cortex_query).collect()

        if result and len(result) > 0:
            response_text = result[0]['RESPONSE']

            # Try to parse the JSON response
            try:
                # Clean up response if it has markdown code blocks
                cleaned_response = response_text.strip()
                if cleaned_response.startswith('```'):
                    # Remove markdown code blocks
                    lines = cleaned_response.split('\n')
                    cleaned_response = '\n'.join(
                        line for line in lines
                        if not line.strip().startswith('```')
                    )

                semantic_view = json.loads(cleaned_response)
                return semantic_view
            except json.JSONDecodeError:
                # If parsing fails, return a basic structure
                st.warning("Could not parse Cortex AI response as JSON. Creating basic structure.")
                return create_basic_semantic_view(database, schema, table, table_schema)
        else:
            st.warning("No response from Cortex AI. Creating basic structure.")
            return create_basic_semantic_view(database, schema, table, table_schema)

    except Exception as e:
        st.error(f"Error generating semantic view with Cortex AI: {str(e)}")
        # Fallback to basic structure
        return create_basic_semantic_view(database, schema, table, table_schema)


def create_basic_semantic_view(
    database: str,
    schema: str,
    table: str,
    table_schema: pd.DataFrame
) -> Dict[str, Any]:
    """
    Create a basic semantic view structure when Cortex AI is unavailable.

    Args:
        database: Database name
        schema: Schema name
        table: Table name
        table_schema: DataFrame with table schema information

    Returns:
        Dictionary containing basic semantic view definition
    """
    dimensions = []
    measures = []
    time_dimensions = []

    # Categorize columns based on data type
    for _, row in table_schema.iterrows():
        col_name = row['column_name']
        data_type = row['data_type'].upper()

        if 'DATE' in data_type or 'TIME' in data_type or 'TIMESTAMP' in data_type:
            time_dimensions.append({
                'name': col_name.lower(),
                'column': col_name,
                'data_type': data_type,
                'granularities': ['day', 'week', 'month', 'year']
            })
        elif any(numeric_type in data_type for numeric_type in ['NUMBER', 'INT', 'FLOAT', 'DECIMAL', 'DOUBLE']):
            # Check if it might be an ID or code (not a measure)
            if 'ID' not in col_name.upper() and 'CODE' not in col_name.upper():
                measures.append({
                    'name': col_name.lower(),
                    'column': col_name,
                    'aggregation': 'sum',
                    'data_type': data_type,
                    'description': f'Sum of {col_name}'
                })
            else:
                dimensions.append({
                    'name': col_name.lower(),
                    'column': col_name,
                    'data_type': data_type,
                    'description': col_name,
                    'synonyms': []
                })
        else:
            dimensions.append({
                'name': col_name.lower(),
                'column': col_name,
                'data_type': data_type,
                'description': col_name,
                'synonyms': []
            })

    return {
        'name': f'{table.lower()}_semantic_view',
        'description': f'Semantic view for {database}.{schema}.{table}',
        'base_table': {
            'database': database,
            'schema': schema,
            'table': table
        },
        'dimensions': dimensions,
        'measures': measures,
        'time_dimensions': time_dimensions
    }


def enhance_semantic_view_with_cortex(
    session: Session,
    semantic_view: Dict[str, Any],
    enhancement_type: str = 'descriptions'
) -> Dict[str, Any]:
    """
    Use Cortex AI to enhance an existing semantic view.

    Args:
        session: Snowpark session
        semantic_view: Existing semantic view definition
        enhancement_type: Type of enhancement ('descriptions', 'synonyms', 'relationships')

    Returns:
        Enhanced semantic view definition
    """
    try:
        if enhancement_type == 'descriptions':
            prompt = f"""
Given this semantic view definition:
{json.dumps(semantic_view, indent=2)}

Please enhance the descriptions for all dimensions, measures, and time dimensions to be more business-friendly and clear.
Return the complete semantic view JSON with improved descriptions.
Return ONLY valid JSON without any additional text or markdown formatting.
"""
        elif enhancement_type == 'synonyms':
            prompt = f"""
Given this semantic view definition:
{json.dumps(semantic_view, indent=2)}

Please add relevant synonyms for each dimension to improve natural language querying.
Consider common business terms, abbreviations, and alternative names.
Return the complete semantic view JSON with added synonyms.
Return ONLY valid JSON without any additional text or markdown formatting.
"""
        else:
            return semantic_view

        cortex_query = f"""
        SELECT SNOWFLAKE.CORTEX.COMPLETE(
            'mixtral-8x7b',
            [{{'role': 'user', 'content': {session.sql("SELECT ?", [prompt]).collect()[0][0]}}}]
        ) as response
        """

        result = session.sql(cortex_query).collect()

        if result and len(result) > 0:
            response_text = result[0]['RESPONSE']

            # Clean up and parse response
            cleaned_response = response_text.strip()
            if cleaned_response.startswith('```'):
                lines = cleaned_response.split('\n')
                cleaned_response = '\n'.join(
                    line for line in lines
                    if not line.strip().startswith('```')
                )

            enhanced_view = json.loads(cleaned_response)
            return enhanced_view

        return semantic_view

    except Exception as e:
        st.error(f"Error enhancing semantic view: {str(e)}")
        return semantic_view
