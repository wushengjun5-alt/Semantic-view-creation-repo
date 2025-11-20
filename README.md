# Semantic View Creator

A Streamlit application that enables users to create, edit, and manage semantic views for Snowflake tables using Cortex AI.

## Features

- **Snowflake Integration**: Connect to your Snowflake account and browse databases, schemas, and tables
- **AI-Powered Analysis**: Use Snowflake Cortex AI to automatically analyze tables and generate semantic view definitions
- **Interactive Editor**: Edit dimensions, measures, and time dimensions with an intuitive UI
- **YAML Export**: Save semantic views as YAML files for version control and deployment
- **Table Preview**: View table schemas, statistics, and sample data before creating semantic views
- **Validation**: Built-in validation to ensure semantic views are properly structured

## Prerequisites

- Python 3.8 or higher
- Snowflake account with:
  - Access to tables you want to analyze
  - Cortex AI enabled (for AI-powered generation)
  - Appropriate warehouse, database, and schema permissions

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd Semantic-view-creation-repo
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

### Option 1: Azure SSO Authentication (Recommended for Enterprise)

For organizations using Azure Active Directory/Entra ID with Snowflake, you can use browser-based SSO:

Create a `.streamlit/secrets.toml` file:

```toml
[snowflake]
account = "your-account-identifier"  # e.g., "xy12345.east-us-2.azure"
user = "your-email@company.com"
authenticator = "externalbrowser"
warehouse = "your-warehouse"  # Optional
database = "your-database"    # Optional
schema = "your-schema"        # Optional
role = "your-role"            # Optional
```

**Benefits:**
- ✅ No password required - uses your company's SSO
- ✅ Multi-factor authentication supported
- ✅ Automatically uses your existing Azure session
- ✅ More secure - no credentials stored

### Option 2: Password Authentication (Traditional)

Create a `.streamlit/secrets.toml` file:

```toml
[snowflake]
account = "your-account-identifier"
user = "your-username"
password = "your-password"
warehouse = "your-warehouse"
database = "your-database"
schema = "your-schema"
role = "your-role"
```

### Option 3: In-App Configuration (Interactive)

Launch the app and enter your credentials in the sidebar connection form:
- Choose "Azure SSO" or "Password" authentication
- Enter your account and user details
- For Azure SSO: A browser window will open for authentication
- For Password: Enter your password in the form

## Usage

1. Start the Streamlit app:
```bash
streamlit run app.py
```

2. Connect to Snowflake:
   - Use the sidebar to select authentication method (Azure SSO or Password)
   - Enter your Snowflake account identifier and user
   - For **Azure SSO**: Click "Connect" and a browser window will open for authentication
   - For **Password**: Enter your password and click "Connect"

3. Create a Semantic View:
   - Navigate to the "Create New View" tab
   - Select a database, schema, and table
   - Review the table schema and sample data
   - Click "Generate Semantic View" to use Cortex AI or create a basic structure
   - The semantic view will be generated automatically

4. Edit the Semantic View:
   - Switch to the "Edit Current View" tab
   - Modify the view name, description, dimensions, measures, and time dimensions
   - Add or remove elements as needed
   - View the result as JSON or YAML

5. Save the Semantic View:
   - Click "Save to File" to save locally in the `semantic_views/` directory
   - Or use "Download YAML" or "Download JSON" to download the file

6. Load Saved Views:
   - Navigate to the "Saved Views" tab
   - Select a previously saved semantic view
   - Click "Load View" to edit or review it

## Semantic View Structure

A semantic view consists of:

### Basic Information
- **name**: Unique identifier for the view
- **description**: Human-readable description
- **base_table**: Reference to the source Snowflake table

### Dimensions
Categorical attributes used for grouping and filtering:
```yaml
dimensions:
  - name: customer_segment
    column: SEGMENT
    data_type: VARCHAR
    description: Customer segmentation category
    synonyms: [segment, category, group]
```

### Measures
Numeric values that can be aggregated:
```yaml
measures:
  - name: total_revenue
    column: REVENUE
    aggregation: sum
    data_type: NUMBER
    description: Total revenue amount
```

### Time Dimensions
Date/timestamp fields for temporal analysis:
```yaml
time_dimensions:
  - name: order_date
    column: ORDER_DATE
    data_type: DATE
    granularities: [day, week, month, quarter, year]
```

## Project Structure

```
Semantic-view-creation-repo/
├── app.py                  # Main Streamlit application
├── snowflake_utils.py      # Snowflake connection and data utilities
├── cortex_ai.py           # Cortex AI integration for semantic view generation
├── yaml_handler.py        # YAML file operations and validation
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── .gitignore            # Git ignore rules
└── semantic_views/       # Directory for saved semantic views (created at runtime)
```

## Features in Detail

### Cortex AI Integration

The app uses Snowflake Cortex AI's `COMPLETE` function to:
- Analyze table schemas and sample data
- Identify appropriate dimensions, measures, and time dimensions
- Generate meaningful descriptions and synonyms
- Provide business-friendly naming conventions

### Manual Editing

All aspects of the semantic view can be manually edited:
- Change names and descriptions
- Add/remove dimensions, measures, and time dimensions
- Modify data types and aggregation functions
- Add synonyms for natural language querying
- Adjust time granularities

### Validation

The app validates semantic views to ensure:
- Required fields are present
- Base table information is complete
- At least one dimension, measure, or time dimension exists
- All elements have required properties

## Troubleshooting

### Connection Issues

If you can't connect to Snowflake:
- Verify your account identifier is correct (should include region and cloud provider)
- Check that your user has appropriate permissions
- Ensure the warehouse is running
- Verify network connectivity and firewall settings

### Cortex AI Not Available

If Cortex AI generation fails:
- Verify Cortex AI is enabled in your Snowflake account
- Check that you have the required privileges
- The app will fallback to basic structure generation if Cortex AI is unavailable

### Permission Errors

Ensure your Snowflake role has:
- USAGE on the warehouse
- USAGE on the database and schema
- SELECT on tables you want to analyze
- EXECUTE on Cortex functions (for AI features)

## Security Best Practices

- Never commit credentials to version control
- Use Snowflake's role-based access control
- Store credentials in `.streamlit/secrets.toml` (which is gitignored)
- Consider using environment variables or secret management systems in production
- Regularly rotate passwords and access keys

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions:
- Check the troubleshooting section
- Review Snowflake Cortex AI documentation
- Open an issue in the repository

## Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Powered by [Snowflake Cortex AI](https://docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions)
- Uses [snowflake-connector-python](https://docs.snowflake.com/en/user-guide/python-connector) and [snowflake-snowpark-python](https://docs.snowflake.com/en/developer-guide/snowpark/python/index)
