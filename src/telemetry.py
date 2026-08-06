import logging
import time
from functools import wraps
from typing import Any, Callable

# Simulated Telemetry Logger
# In a real Azure environment, this would be wired to Azure Application Insights via OpenTelemetry
telemetry_logger = logging.getLogger("IDP_Telemetry")
telemetry_logger.setLevel(logging.INFO)

# Create console handler for demonstration
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
telemetry_logger.addHandler(ch)

def track_performance(agent_name: str) -> Callable:
    """
    Decorator to track the performance and latency of an AI Agent.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                latency = time.time() - start_time
                telemetry_logger.info(
                    f"Agent: {agent_name} | Status: Success | Latency: {latency:.4f}s"
                )
                return result
            except Exception as e:
                latency = time.time() - start_time
                telemetry_logger.error(
                    f"Agent: {agent_name} | Status: Failed | Latency: {latency:.4f}s | Error: {str(e)}"
                )
                raise
        return wrapper
    return decorator
