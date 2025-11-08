"""
Logging configuration and utilities for argentum package.

Provides consistent logging across all argentum modules with structured
logging support and performance-conscious defaults.
"""

import logging
import sys
from typing import Optional, Dict, Any, Union
from datetime import datetime


class ArgentumFormatter(logging.Formatter):
    """Custom formatter for argentum logs with structured output."""
    
    def __init__(self, include_module: bool = True, include_timestamp: bool = True):
        self.include_module = include_module
        self.include_timestamp = include_timestamp
        
        # Color codes for different log levels
        self.colors = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
            'RESET': '\033[0m'      # Reset
        }
        
        super().__init__()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with argentum-specific formatting."""
        
        # Build format string dynamically
        parts = []
        
        if self.include_timestamp:
            parts.append("%(asctime)s")
        
        # Add color for log level
        color = self.colors.get(record.levelname, '')
        reset = self.colors['RESET'] if color else ''
        parts.append(f"{color}%(levelname)-8s{reset}")
        
        if self.include_module:
            parts.append("%(name)s")
        
        parts.append("%(message)s")
        
        format_str = " | ".join(parts)
        
        # Set the format string
        self._style._fmt = format_str
        
        # Add custom fields to record
        if hasattr(record, 'agent_id'):
            record.message = f"[Agent:{record.agent_id}] {record.getMessage()}"
        elif hasattr(record, 'session_id'):
            record.message = f"[Session:{record.session_id}] {record.getMessage()}"
        else:
            record.message = record.getMessage()
        
        # Add context information if available
        if hasattr(record, 'context'):
            record.message += f" (Context: {record.context})"
        
        return super().format(record)


def setup_logging(
    level: Union[str, int] = logging.INFO,
    format_type: str = "standard",
    include_timestamp: bool = True,
    include_module: bool = True,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Set up logging configuration for argentum.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Format type ("standard", "structured", "minimal") 
        include_timestamp: Include timestamp in logs
        include_module: Include module name in logs
        log_file: Optional file to write logs to
        
    Returns:
        Configured logger instance
        
    Examples:
        >>> logger = setup_logging(level="DEBUG", format_type="structured")
        >>> logger.info("Agent initialized")
        
        >>> # With context
        >>> logger = setup_logging()
        >>> logger.info("State changed", extra={"agent_id": "agent_001", "context": "processing"})
    """
    # Get or create argentum logger
    logger = logging.getLogger("argentum")
    
    # Clear any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Set level
    if isinstance(level, str):
        level = getattr(logging, level.upper())
    logger.setLevel(level)
    
    # Create formatter based on type
    if format_type == "minimal":
        formatter = logging.Formatter("%(levelname)s: %(message)s")
    elif format_type == "structured":
        formatter = ArgentumFormatter(include_module=True, include_timestamp=True)
    else:  # standard
        formatter = ArgentumFormatter(
            include_module=include_module,
            include_timestamp=include_timestamp
        )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if requested
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module or component.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
        
    Examples:
        >>> logger = get_logger(__name__)
        >>> logger.info("Module initialized")
    """
    return logging.getLogger(f"argentum.{name}")


class PerformanceLogger:
    """Logger for performance metrics and timing."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or get_logger("performance")
        self._timers: Dict[str, float] = {}
    
    def start_timer(self, operation: str) -> None:
        """Start timing an operation."""
        import time
        self._timers[operation] = time.time()
        self.logger.debug(f"Started timer for: {operation}")
    
    def end_timer(self, operation: str, extra_context: Optional[Dict[str, Any]] = None) -> float:
        """End timing an operation and log the result."""
        import time
        
        if operation not in self._timers:
            self.logger.warning(f"Timer '{operation}' was not started")
            return 0.0
        
        elapsed = time.time() - self._timers[operation]
        del self._timers[operation]
        
        context = extra_context or {}
        context.update({"operation": operation, "elapsed_ms": elapsed * 1000})
        
        self.logger.info(
            f"Operation '{operation}' completed in {elapsed:.3f}s",
            extra={"context": context}
        )
        
        return elapsed
    
    def log_metric(self, metric_name: str, value: Union[int, float], unit: str = "", context: Optional[Dict[str, Any]] = None):
        """Log a performance metric."""
        context = context or {}
        context.update({"metric": metric_name, "value": value, "unit": unit})
        
        message = f"Metric {metric_name}: {value}"
        if unit:
            message += f" {unit}"
        
        self.logger.info(message, extra={"context": context})


class DebugLogger:
    """Logger for debugging agent state and behavior."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or get_logger("debug")
    
    def log_state_change(self, agent_id: str, old_state: Dict[str, Any], new_state: Dict[str, Any]):
        """Log a state change for debugging."""
        self.logger.debug(
            f"State change detected",
            extra={
                "agent_id": agent_id,
                "context": {
                    "old_state_keys": list(old_state.keys()),
                    "new_state_keys": list(new_state.keys()),
                    "state_size": len(str(new_state))
                }
            }
        )
    
    def log_handoff(self, from_agent: str, to_agent: str, confidence: float, artifacts_count: int):
        """Log an agent handoff for debugging."""
        self.logger.info(
            f"Agent handoff: {from_agent} → {to_agent}",
            extra={
                "context": {
                    "from_agent": from_agent,
                    "to_agent": to_agent,
                    "confidence": confidence,
                    "artifacts_count": artifacts_count
                }
            }
        )
    
    def log_context_decay(self, total_items: int, active_items: int, avg_decay: float):
        """Log context decay statistics."""
        self.logger.debug(
            f"Context decay: {active_items}/{total_items} active",
            extra={
                "context": {
                    "total_items": total_items,
                    "active_items": active_items,
                    "avg_decay": avg_decay,
                    "retention_rate": active_items / total_items if total_items > 0 else 0
                }
            }
        )
    
    def log_plan_lint_results(self, plan_id: str, errors: int, warnings: int, execution_time: float):
        """Log plan linting results."""
        level = logging.ERROR if errors > 0 else logging.WARNING if warnings > 0 else logging.INFO
        
        self.logger.log(
            level,
            f"Plan lint completed: {errors} errors, {warnings} warnings",
            extra={
                "context": {
                    "plan_id": plan_id,
                    "errors": errors,
                    "warnings": warnings,
                    "execution_time_ms": execution_time * 1000
                }
            }
        )


# Module-level logger instances
_main_logger: Optional[logging.Logger] = None
_performance_logger: Optional[PerformanceLogger] = None
_debug_logger: Optional[DebugLogger] = None


def get_main_logger() -> logging.Logger:
    """Get the main argentum logger."""
    global _main_logger
    if _main_logger is None:
        _main_logger = setup_logging()
    return _main_logger


def get_performance_logger() -> PerformanceLogger:
    """Get the performance logger."""
    global _performance_logger
    if _performance_logger is None:
        _performance_logger = PerformanceLogger()
    return _performance_logger


def get_debug_logger() -> DebugLogger:
    """Get the debug logger.""" 
    global _debug_logger
    if _debug_logger is None:
        _debug_logger = DebugLogger()
    return _debug_logger


def configure_logging_for_production(log_file: str = "argentum.log") -> None:
    """Configure logging for production environment."""
    setup_logging(
        level=logging.INFO,
        format_type="structured", 
        include_timestamp=True,
        include_module=True,
        log_file=log_file
    )


def configure_logging_for_development() -> None:
    """Configure logging for development environment."""
    setup_logging(
        level=logging.DEBUG,
        format_type="standard",
        include_timestamp=True,
        include_module=True
    )


def disable_logging() -> None:
    """Disable all argentum logging."""
    logging.getLogger("argentum").setLevel(logging.CRITICAL + 1)


def log_function_call(func):
    """Decorator to log function calls with timing."""
    import functools
    import time
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__ or "unknown")
        perf_logger = get_performance_logger()
        
        # Start timing
        start_time = time.time()
        
        # Log function entry
        logger.debug(f"Calling {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            
            # Log successful completion
            elapsed = time.time() - start_time
            logger.debug(f"{func.__name__} completed successfully in {elapsed:.3f}s")
            
            return result
            
        except Exception as e:
            # Log error
            elapsed = time.time() - start_time
            logger.error(f"{func.__name__} failed after {elapsed:.3f}s: {e}")
            raise
    
    return wrapper