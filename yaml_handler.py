"""
YAML handler for saving and loading semantic view definitions.
"""

import yaml
import os
from typing import Dict, Any, List
from datetime import datetime
import streamlit as st


def save_semantic_view_to_yaml(semantic_view: Dict[str, Any], output_dir: str = 'semantic_views') -> str:
    """
    Save a semantic view definition to a YAML file.

    Args:
        semantic_view: Dictionary containing the semantic view definition
        output_dir: Directory to save the YAML file

    Returns:
        Path to the saved YAML file
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Generate filename from view name and timestamp
        view_name = semantic_view.get('name', 'semantic_view')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{view_name}_{timestamp}.yaml"
        filepath = os.path.join(output_dir, filename)

        # Add metadata
        yaml_content = {
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'version': '1.0'
            },
            'semantic_view': semantic_view
        }

        # Write to YAML file
        with open(filepath, 'w') as f:
            yaml.dump(yaml_content, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

        return filepath

    except Exception as e:
        st.error(f"Error saving semantic view to YAML: {str(e)}")
        return None


def load_semantic_view_from_yaml(filepath: str) -> Dict[str, Any]:
    """
    Load a semantic view definition from a YAML file.

    Args:
        filepath: Path to the YAML file

    Returns:
        Dictionary containing the semantic view definition
    """
    try:
        with open(filepath, 'r') as f:
            yaml_content = yaml.safe_load(f)

        # Extract semantic view from metadata wrapper
        if 'semantic_view' in yaml_content:
            return yaml_content['semantic_view']
        else:
            # Assume the entire content is the semantic view
            return yaml_content

    except Exception as e:
        st.error(f"Error loading semantic view from YAML: {str(e)}")
        return None


def list_saved_semantic_views(directory: str = 'semantic_views') -> List[str]:
    """
    List all saved semantic view YAML files in a directory.

    Args:
        directory: Directory containing the YAML files

    Returns:
        List of filenames
    """
    try:
        if not os.path.exists(directory):
            return []

        files = [f for f in os.listdir(directory) if f.endswith('.yaml') or f.endswith('.yml')]
        return sorted(files, reverse=True)  # Most recent first

    except Exception as e:
        st.error(f"Error listing semantic views: {str(e)}")
        return []


def export_semantic_view_as_yaml_string(semantic_view: Dict[str, Any]) -> str:
    """
    Convert a semantic view definition to a YAML string.

    Args:
        semantic_view: Dictionary containing the semantic view definition

    Returns:
        YAML string representation
    """
    try:
        yaml_content = {
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'version': '1.0'
            },
            'semantic_view': semantic_view
        }

        return yaml.dump(yaml_content, default_flow_style=False, sort_keys=False, allow_unicode=True)

    except Exception as e:
        st.error(f"Error exporting semantic view as YAML string: {str(e)}")
        return None


def validate_semantic_view(semantic_view: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate a semantic view definition.

    Args:
        semantic_view: Dictionary containing the semantic view definition

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Check required fields
    if 'name' not in semantic_view:
        errors.append("Missing required field: 'name'")

    if 'base_table' not in semantic_view:
        errors.append("Missing required field: 'base_table'")
    else:
        base_table = semantic_view['base_table']
        if 'database' not in base_table:
            errors.append("Missing 'database' in base_table")
        if 'schema' not in base_table:
            errors.append("Missing 'schema' in base_table")
        if 'table' not in base_table:
            errors.append("Missing 'table' in base_table")

    # Check that at least one of dimensions, measures, or time_dimensions exists
    if not any(key in semantic_view for key in ['dimensions', 'measures', 'time_dimensions']):
        errors.append("Semantic view must have at least one of: dimensions, measures, or time_dimensions")

    # Validate dimensions structure
    if 'dimensions' in semantic_view:
        for idx, dim in enumerate(semantic_view['dimensions']):
            if 'name' not in dim:
                errors.append(f"Dimension {idx}: missing 'name'")
            if 'column' not in dim:
                errors.append(f"Dimension {idx}: missing 'column'")

    # Validate measures structure
    if 'measures' in semantic_view:
        for idx, measure in enumerate(semantic_view['measures']):
            if 'name' not in measure:
                errors.append(f"Measure {idx}: missing 'name'")
            if 'column' not in measure:
                errors.append(f"Measure {idx}: missing 'column'")

    # Validate time_dimensions structure
    if 'time_dimensions' in semantic_view:
        for idx, time_dim in enumerate(semantic_view['time_dimensions']):
            if 'name' not in time_dim:
                errors.append(f"Time dimension {idx}: missing 'name'")
            if 'column' not in time_dim:
                errors.append(f"Time dimension {idx}: missing 'column'")

    return (len(errors) == 0, errors)


def merge_semantic_views(base_view: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge updates into a base semantic view.

    Args:
        base_view: Original semantic view
        updates: Dictionary with updates to apply

    Returns:
        Merged semantic view
    """
    import copy
    merged = copy.deepcopy(base_view)

    for key, value in updates.items():
        if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
            merged[key].update(value)
        else:
            merged[key] = value

    return merged
