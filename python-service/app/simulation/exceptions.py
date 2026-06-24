class SimulationError(Exception):
    status_code = 400
    code = "SIMULATION_ERROR"


class SimulationConfigError(SimulationError):
    code = "INVALID_CONFIG"


class InvalidWeightError(SimulationConfigError):
    code = "INVALID_WEIGHT"


class InvalidProbabilityError(SimulationConfigError):
    code = "INVALID_PROBABILITY"


class SimulationEngineExecutionError(SimulationError):
    status_code = 500
    code = "SIMULATION_ENGINE_EXECUTION_ERROR"
