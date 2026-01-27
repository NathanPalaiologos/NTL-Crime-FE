# Dashboard

This guide provides instructions on how to install dependencies and run the dashboard application.

## Prerequisites

Ensure you have Python installed on your system. It is recommended to use a virtual environment to manage dependencies.

## Installation

1.  Navigate to the project directory:
    ```bash
    cd dashboard
    ```

2.  Install the required Python packages using `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    ```
    If you do not have a `requirements.txt` file, you can install the necessary packages individually. For example:
    ```bash
    pip install streamlit pandas geopandas plotly pyarrow fastparquet
    ```

## Running the Dashboard

To start the dashboard application, run the main application file:
1. From the `dashboard` directory, execute:
    ```bash
    steamlit run app.py
    ```
2. From the root directory, execute:
    ```bash
    streamlit run dashboard/app.py
    ```

Check the terminal output for the local URL (usually `http://localhost:8523` or similar) to view the dashboard in your web browser.