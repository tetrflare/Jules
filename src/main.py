# This script runs on the main browser thread using MicroPython.
# Its primary role is to coordinate the UI and manage the Web Worker.

from pyscript import PyWorker, js
import json

# This is the main function called by the JavaScript bridge when the user clicks "Run Analysis".
async def run_analysis(csv_data):
    """
    Orchestrates the data analysis workflow.
    1. Shows a loading state in the UI.
    2. Spawns a Pyodide Web Worker to perform the heavy computation.
    3. Registers UI callback functions from the JS bridge onto the worker.
    4. Calls the main computation function on the worker, passing the data.
    5. Receives results and uses the JS bridge to display them.
    6. Handles any errors that occur during the process.
    """
    try:
        js.ui.setStatus("Initializing computational worker...")
        js.ui.updateProgress(0)

        # The configuration for the worker must be passed as a JSON string.
        # This defines the worker's independent Python environment.
        worker_config = json.dumps({
            "packages": ["numpy", "pandas", "matplotlib"]
        })

        # Create the Pyodide worker instance. [31]
        worker = PyWorker("./src/core/analysis.py", type="pyodide", config=worker_config)

        # Register the JavaScript UI functions as callbacks that the worker can invoke.
        # This is the core of the main-thread-to-worker communication pattern. [30]
        worker.sync.update_progress = js.ui.updateProgress
        worker.sync.display_plot = js.ui.displayPlot
        worker.sync.display_table = js.ui.displayTable
        worker.sync.report_error = js.ui.displayError

        js.ui.setStatus("Worker started. Sending data for processing...")

        # Call the main function in the worker script (`analysis.py`) and await its results.
        # The `csv_data` is passed to the worker. All data must be serializable.
        await worker.sync.perform_analysis(csv_data)

        js.ui.setStatus("Analysis complete.")

    except Exception as e:
        print(f"Error in main.py: {e}")
        js.ui.displayError(str(e))

# The function must be exposed to the global scope to be callable from JavaScript.
# In MicroPython, top-level functions are automatically in the global scope.
