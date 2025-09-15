# This script runs entirely within the Pyodide Web Worker.
# It has no direct access to the DOM. All UI updates are done
# by calling the synchronized functions registered from the main thread.

from pyscript import sync
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import base64
import json

def generate_matplotlib_plot(df):
    """Generates a Matplotlib plot and returns it as a Base64 encoded PNG."""
    fig, ax = plt.subplots()
    df.plot(kind='line', ax=ax)
    ax.set_title("Data Analysis Result (Matplotlib)")
    ax.set_xlabel("Index")
    ax.set_ylabel("Value")

    # Save the plot to an in-memory buffer. [32]
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)

    # Encode the image to Base64 to be sent as a string.
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return f"data:image/png;base64,{img_str}"

def perform_analysis(csv_data):
    """
    The main computational function executed in the worker.
    1. Parses the input data.
    2. Performs a sample analysis.
    3. Periodically reports progress back to the main thread.
    4. Generates outputs (a table and a plot).
    5. Sends the outputs back to the main thread for display.
    """
    try:
        # 1. Load data using pandas.
        sync.update_progress(0.1)
        df = pd.read_csv(io.StringIO(csv_data))

        # 2. Perform some sample data manipulation.
        # This loop simulates a long-running process.
        sync.update_progress(0.3)
        processed_df = df.copy()
        num_cols = len(processed_df.columns)
        for i, col in enumerate(processed_df.columns):
            if pd.api.types.is_numeric_dtype(processed_df[col]):
                processed_df[col] = processed_df[col] * np.sin(processed_df.index / 10)

            # 3. Report progress back to the main thread.
            sync.update_progress(0.3 + (0.5 * (i + 1) / num_cols))

        # 4. Generate outputs.
        # Create an HTML table from the processed DataFrame.
        table_html = processed_df.head().to_html(classes='table', border=0)

        # Create a plot using Matplotlib.
        # NOTE: For interactive plots, one would generate a Plotly JSON spec here.
        # This example uses Matplotlib to demonstrate static image generation.
        plot_data_url = generate_matplotlib_plot(processed_df)

        # 5. Send results back to the main thread for display.
        # For Matplotlib, we create a simple JSON structure to pass the image URL.
        # For Plotly, this would be the `fig.to_json()` string.
        plot_spec = json.dumps({
            'data': [{'type': 'image', 'src': plot_data_url}],
            'layout': {'title': 'Matplotlib Plot Rendered as Image'}
        })

        # We need a custom JS function to handle this image data URL.
        # For simplicity in this template, we will just display the table.
        # A full implementation would have a `displayImage` function in bridge.js.
        sync.display_table(table_html)

        # Let's pretend we made a plotly plot for the bridge function
        # sync.display_plot(plotly_json_spec)

        sync.update_progress(1.0)

    except Exception as e:
        print(f"Error in worker: {e}")
        # Report the error back to the main thread's UI.
        sync.report_error(str(e))

# The main computational function must be exposed on the sync object
# so it can be called from the main thread.
sync.perform_analysis = perform_analysis
