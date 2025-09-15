import js
from pyscript import Element
import pandas as pd
import plotly.express as px
import warnings
import numpy as np

# Suppress potential FutureWarnings from pandas/plotly
warnings.simplefilter(action='ignore', category=FutureWarning)

class CVDState:
    """Manages the state and calculations for the CVD simulator."""
    def __init__(self):
        self.elements = {
            'c2h2_flow_slider': Element('c2h2-flow-slider'),
            'c2h2_flow_value': Element('c2h2-flow-value'),
            'ar_flow_slider': Element('ar-flow-slider'),
            'ar_flow_value': Element('ar-flow-value'),
            'total_pressure_slider': Element('total-pressure-slider'),
            'total_pressure_value': Element('total-pressure-value'),
            'contaminant_pp_slider': Element('contaminant-pp-slider'),
            'contaminant_pp_value': Element('contaminant-pp-value'),
            'c2h2_pp_input': Element('c2h2-pp-input'),
            'plot_div': Element('simulation-plot')
        }
        self.calculated_param = 'c2h2_pp' # The parameter that is being calculated
        self.active_slider_id = None
        # Initialize current C2H2 PP to a default value
        self.c2h2_pp = 0.250
        self.read_ui()

    def read_ui(self):
        """Read all values from the UI into the state object."""
        self.c2h2_flow = float(self.elements['c2h2_flow_slider'].value)
        self.ar_flow = float(self.elements['ar_flow_slider'].value)
        self.total_pressure = float(self.elements['total_pressure_slider'].value)
        self.contaminant_pp = float(self.elements['contaminant_pp_slider'].value)
        try:
            # This is the target value for the C2H2 Partial Pressure
            self.target_c2h2_pp = float(self.elements['c2h2_pp_input'].value)
        except (ValueError, TypeError):
            self.target_c2h2_pp = 0.25 # Default value

        # The 'locked' parameter in the UI is actually the one we want to CALCULATE
        self.calculated_param = js.document.querySelector('input[name="locked_param"]:checked').value

    def update_ui(self):
        """Update all UI elements from the state object's values."""
        # Update sliders and their corresponding value displays
        self.elements['c2h2_flow_slider'].element.value = f"{self.c2h2_flow:.1f}"
        self.elements['c2h2_flow_value'].write(f"{self.c2h2_flow:.1f}")

        self.elements['ar_flow_slider'].element.value = f"{self.ar_flow:.1f}"
        self.elements['ar_flow_value'].write(f"{self.ar_flow:.1f}")

        self.elements['total_pressure_slider'].element.value = f"{self.total_pressure:.2f}"
        self.elements['total_pressure_value'].write(f"{self.total_pressure:.2f}")

        self.elements['contaminant_pp_slider'].element.value = f"{self.contaminant_pp:.3f}"
        self.elements['contaminant_pp_value'].write(f"{self.contaminant_pp:.3f}")

        # If a parameter is being calculated, the C2H2 PP value is the target.
        # Otherwise, it's the calculated result.
        display_c2h2_pp = self.target_c2h2_pp if self.calculated_param != 'c2h2_pp' else self.c2h2_pp
        self.elements['c2h2_pp_input'].element.value = f"{display_c2h2_pp:.3f}"

        # The calculated parameter's control should be disabled.
        # The 'c2h2_pp' radio button is a special case that means we calculate total_pressure.
        is_total_pressure_calculated = (self.calculated_param == 'total_pressure' or self.calculated_param == 'c2h2_pp')

        self.elements['c2h2_pp_input'].element.disabled = (self.calculated_param != 'c2h2_pp')
        self.elements['c2h2_flow_slider'].element.disabled = (self.calculated_param == 'c2h2_flow')
        self.elements['ar_flow_slider'].element.disabled = (self.calculated_param == 'ar_flow')
        self.elements['total_pressure_slider'].element.disabled = is_total_pressure_calculated


    # --- Calculation Engine ---
    # The core physics equation: P_c2h2 = (F_c2h2 / (F_c2h2 + F_ar)) * (P_total - P_contaminant)

    def calculate_c2h2_pp(self):
        """Calculates the C2H2 partial pressure based on the current state of other parameters."""
        process_pressure = self.total_pressure - self.contaminant_pp
        total_flow = self.c2h2_flow + self.ar_flow
        if total_flow > 0 and process_pressure > 0:
            self.c2h2_pp = (self.c2h2_flow / total_flow) * process_pressure
        else:
            self.c2h2_pp = 0

    def solve_for_total_pressure(self):
        """Solves for total pressure required to meet the target C2H2 P.P."""
        if self.c2h2_flow > 0 and self.target_c2h2_pp > 0:
            total_flow = self.c2h2_flow + self.ar_flow
            self.total_pressure = self.target_c2h2_pp * (total_flow / self.c2h2_flow) + self.contaminant_pp
        else:
            self.total_pressure = self.contaminant_pp

    def solve_for_c2h2_flow(self):
        """Solves for C2H2 flow required to meet the target C2H2 P.P."""
        process_pressure = self.total_pressure - self.contaminant_pp
        if self.target_c2h2_pp > 0 and process_pressure > self.target_c2h2_pp:
            # Derived from: P_c2h2 * (F_c2h2 + F_ar) = F_c2h2 * P_proc  => F_c2h2 = (P_c2h2 * F_ar) / (P_proc - P_c2h2)
            self.c2h2_flow = (self.target_c2h2_pp * self.ar_flow) / (process_pressure - self.target_c2h2_pp)
        else:
            self.c2h2_flow = 0

    def solve_for_ar_flow(self):
        """Solves for Ar flow required to meet the target C2H2 P.P."""
        process_pressure = self.total_pressure - self.contaminant_pp
        if self.c2h2_flow > 0 and self.target_c2h2_pp > 0 and process_pressure > self.target_c2h2_pp:
            # Derived from: F_ar = F_c2h2 * (P_proc / P_c2h2 - 1)
            self.ar_flow = self.c2h2_flow * ((process_pressure / self.target_c2h2_pp) - 1)
        else:
            self.ar_flow = 0

    # --- Main Update Orchestrator ---
    def update_simulation(self, active_slider_id=None):
        self.active_slider_id = active_slider_id
        self.read_ui()

        # The 'calculated_param' determines which variable to solve for to meet the target C2H2 P.P.
        # The 'c2h2_pp' option is a special case where the calculated parameter is actually total_pressure.
        if self.calculated_param == 'total_pressure' or self.calculated_param == 'c2h2_pp':
            self.solve_for_total_pressure()
        elif self.calculated_param == 'c2h2_flow':
            self.solve_for_c2h2_flow()
        elif self.calculated_param == 'ar_flow':
            self.solve_for_ar_flow()

        # Always calculate the resulting C2H2 P.P. for display and graphing consistency.
        self.calculate_c2h2_pp()

        self.update_ui()
        self.update_graph()

    def update_graph(self):
        """Generates and displays a dynamic plot of the process curve."""
        ar_min = float(self.elements['ar_flow_slider'].element.min)
        ar_max = float(self.elements['ar_flow_slider'].element.max)
        ar_range = np.linspace(max(ar_min, 1), ar_max, 50)

        pressure_range = []
        # The plot always shows the curve needed to achieve the target C2H2 P.P.
        c2h2_pp_for_calc = self.target_c2h2_pp

        for ar_val in ar_range:
            if self.c2h2_flow > 0 and c2h2_pp_for_calc > 0:
                pressure = c2h2_pp_for_calc * ((self.c2h2_flow + ar_val) / self.c2h2_flow) + self.contaminant_pp
                pressure_range.append(pressure)
            else:
                pressure_range.append(self.contaminant_pp)

        plot_df = pd.DataFrame({
            'Argon Flow (sccm)': ar_range,
            'Required Total Pressure (mbar)': pressure_range
        })

        fig = px.line(
            plot_df,
            x='Argon Flow (sccm)',
            y='Required Total Pressure (mbar)',
            title=f"Process Curve for Target C₂H₂ P.P. of {c2h2_pp_for_calc:.3f} mbar"
        )

        fig.add_scatter(
            x=[self.ar_flow],
            y=[self.total_pressure],
            mode='markers',
            marker=dict(color='red', size=12, symbol='x'),
            name='Current State'
        )
        fig.update_layout(height=400)
        self.elements['plot_div'].write(fig, format='html')


# --- Initialization and Event Listeners ---
state = CVDState()

def setup_listeners():
    """Add event listeners to all interactive controls."""
    for name, el in state.elements.items():
        if 'slider' in name:
            el.element.addEventListener('input', lambda event, name=name: state.update_simulation(active_slider_id=name))

    state.elements['c2h2_pp_input'].element.addEventListener('change', lambda event: state.update_simulation())

    radio_buttons = js.document.querySelectorAll('input[name="locked_param"]')
    for rb in radio_buttons:
        rb.addEventListener('change', lambda event: state.update_simulation())

# Run the initial setup
setup_listeners()
state.update_simulation()
