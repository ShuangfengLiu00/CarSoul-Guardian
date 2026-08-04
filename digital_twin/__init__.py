"""CarSoul OS Digital Twin.

The digital twin layer sits between the simulator and the agent runtime.
It ingests TelemetryFrame data, evolves component-level state machines,
and produces explainable health assessments.

Sub-packages:
  - ``component_model`` — BatteryTwin / MotorTwin / ChassisTwin state machines
"""
