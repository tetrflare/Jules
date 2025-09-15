// This "bridge" module is the sole owner of DOM interactions.
// Python code calls these functions to update the UI, ensuring a clean separation of concerns.

// We attach our UI API to the global `window` object so it's accessible from Python via `js.ui`.
window.ui = {
    // Displays a status message and optionally shows/hides the loading state.
    setStatus: (message) => {
        document.getElementById('status-message').textContent = message;
        document.getElementById('progress-bar').style.display = 'none';
        document.getElementById('run-button').disabled = false;
    },

    // Updates the progress bar's value.
    updateProgress: (value) => {
        const progressBar = document.getElementById('progress-bar');
        progressBar.style.display = 'block';
        progressBar.value = value;
    },

    // Renders a plot using Plotly.js from a JSON specification.
    displayPlot: (spec) => {
        const plotDiv = document.getElementById('plot-output');
        try {
            Plotly.newPlot(plotDiv, JSON.parse(spec));
        } catch (e) {
            window.ui.displayError(`Failed to render plot: ${e}`);
        }
    },

    // Renders an HTML table from a string.
    displayTable: (html) => {
        document.getElementById('table-output').innerHTML = html;
    },

    // Displays an error message to the user.
    displayError: (errorMsg) => {
        document.getElementById('error-display').textContent = `ERROR: ${errorMsg}`;
        window.ui.setStatus("An error occurred. Please check the console for details.");
    }
};

// This function reads the content of the user-selected file.
// It returns a Promise that resolves with the file content as a string.
async function getFileInputContent() {
    const fileInput = document.getElementById('file-input');
    if (fileInput.files.length === 0) {
        return null;
    }
    const file = fileInput.files[0];
    return await file.text();
}

// Main setup logic runs after the DOM is fully loaded.
document.addEventListener('DOMContentLoaded', () => {
    const runButton = document.getElementById('run-button');

    runButton.addEventListener('click', async () => {
        // Disable the button to prevent multiple clicks.
        runButton.disabled = true;
        document.getElementById('error-display').textContent = ''; // Clear previous errors.

        try {
            // 1. Get the data from the file input via our async helper.
            const fileContent = await getFileInputContent();
            if (!fileContent) {
                window.ui.displayError("Please select a data file first.");
                return;
            }

            // 2. Get a proxy for the main Python function.
            //    This function is defined in `src/main.py`.
            const run_analysis_py = pyscript.interpreter.globals.get('run_analysis');

            // 3. Call the Python function, passing the file content.
            await run_analysis_py(fileContent);

        } catch (e) {
            console.error("Error calling Python from JavaScript:", e);
            window.ui.displayError(e.message);
        } finally {
            // Re-enable the button regardless of success or failure.
            runButton.disabled = false;
        }
    });
});
