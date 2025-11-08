"""
Custom exceptions and error handling for argentum package.

This module provides specific exception types for better error handling
and debugging across all argentum modules.
"""

from typing import Any, Dict, List, Optional, Union


class ArgentumError(Exception):
    """Base exception for all argentum-specific errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class StateDiffError(ArgentumError):
    """Errors related to state diff operations."""
    pass


class SnapshotNotFoundError(StateDiffError):
    """Raised when a requested snapshot label doesn't exist."""
    
    def __init__(self, label: str, available_labels: Optional[List[str]] = None):
        self.label = label
        self.available_labels = available_labels or []
        
        message = f"Snapshot '{label}' not found"
        if available_labels:
            message += f". Available: {', '.join(available_labels)}"
        
        super().__init__(message, {"label": label, "available": available_labels})


class InvalidStateError(StateDiffError):
    """Raised when state data is invalid or malformed."""
    
    def __init__(self, reason: str, state_data: Optional[Any] = None):
        self.reason = reason
        self.state_data = state_data
        
        message = f"Invalid state: {reason}"
        details = {"reason": reason}
        
        if state_data is not None:
            details["state_type"] = type(state_data).__name__
        
        super().__init__(message, details)


class HandoffError(ArgentumError):
    """Errors related to agent handoff operations."""
    pass


class HandoffValidationError(HandoffError):
    """Raised when handoff validation fails."""
    
    def __init__(self, field: str, reason: str, value: Optional[Any] = None):
        self.field = field
        self.reason = reason
        self.value = value
        
        message = f"Handoff validation failed for '{field}': {reason}"
        details = {"field": field, "reason": reason}
        
        if value is not None:
            details["value"] = value
        
        super().__init__(message, details)


class HandoffSerializationError(HandoffError):
    """Raised when handoff serialization/deserialization fails."""
    
    def __init__(self, operation: str, reason: str, data: Optional[str] = None):
        self.operation = operation  # "serialize" or "deserialize"
        self.reason = reason
        self.data = data
        
        message = f"Handoff {operation} failed: {reason}"
        details = {"operation": operation, "reason": reason}
        
        if data:
            details["data_preview"] = data[:100] + "..." if len(data) > 100 else data
        
        super().__init__(message, details)


class ContextDecayError(ArgentumError):
    """Errors related to context decay operations."""
    pass


class InvalidImportanceError(ContextDecayError):
    """Raised when importance value is outside valid range."""
    
    def __init__(self, importance: float):
        self.importance = importance
        
        message = f"Importance must be between 0.0 and 1.0, got {importance}"
        super().__init__(message, {"importance": importance, "valid_range": "(0.0, 1.0)"})


class InvalidHalfLifeError(ContextDecayError):
    """Raised when half-life value is invalid."""
    
    def __init__(self, half_life: Union[int, float]):
        self.half_life = half_life
        
        message = f"Half-life must be positive, got {half_life}"
        super().__init__(message, {"half_life": half_life})


class ContextItemNotFoundError(ContextDecayError):
    """Raised when trying to access a context item that doesn't exist."""
    
    def __init__(self, key: str, available_keys: Optional[List[str]] = None):
        self.key = key
        self.available_keys = available_keys or []
        
        message = f"Context item '{key}' not found"
        if available_keys:
            message += f". Available: {', '.join(available_keys[:5])}"
            if len(available_keys) > 5:
                message += f" (and {len(available_keys) - 5} more)"
        
        super().__init__(message, {"key": key, "available_count": len(available_keys)})


class PlanLintError(ArgentumError):
    """Errors related to plan linting operations."""
    pass


class InvalidPlanError(PlanLintError):
    """Raised when a plan structure is fundamentally invalid."""
    
    def __init__(self, reason: str, plan_data: Optional[Dict[str, Any]] = None):
        self.reason = reason
        self.plan_data = plan_data
        
        message = f"Invalid plan structure: {reason}"
        details = {"reason": reason}
        
        if plan_data:
            details["has_steps"] = "steps" in plan_data
            details["plan_keys"] = list(plan_data.keys()) if isinstance(plan_data, dict) else None
        
        super().__init__(message, details)


class ToolSpecificationError(PlanLintError):
    """Raised when tool specifications are invalid or missing."""
    
    def __init__(self, tool_name: str, reason: str):
        self.tool_name = tool_name
        self.reason = reason
        
        message = f"Tool specification error for '{tool_name}': {reason}"
        super().__init__(message, {"tool_name": tool_name, "reason": reason})


class LintingDependencyError(PlanLintError):
    """Raised when required linting dependencies are missing."""
    
    def __init__(self, missing_packages: List[str], feature: str):
        self.missing_packages = missing_packages
        self.feature = feature
        
        packages_str = "', '".join(missing_packages)
        message = f"Missing dependencies for {feature}: '{packages_str}'"
        install_cmd = f"pip install 'argentum-agent[lint]'"
        
        super().__init__(
            f"{message}. Install with: {install_cmd}",
            {"missing_packages": missing_packages, "feature": feature, "install_command": install_cmd}
        )


class ConfigurationError(ArgentumError):
    """Errors related to argentum configuration."""
    pass


class UnsupportedOperationError(ArgentumError):
    """Raised when an operation is not supported in the current context."""
    
    def __init__(self, operation: str, reason: str, context: Optional[str] = None):
        self.operation = operation
        self.reason = reason
        self.context = context
        
        message = f"Unsupported operation '{operation}': {reason}"
        if context:
            message += f" (Context: {context})"
        
        details = {"operation": operation, "reason": reason}
        if context:
            details["context"] = context
        
        super().__init__(message, details)


def handle_json_error(error: Exception, operation: str, data: Optional[str] = None) -> HandoffSerializationError:
    """
    Convert JSON errors to HandoffSerializationError with better context.
    
    Args:
        error: The original JSON error
        operation: "serialize" or "deserialize"
        data: The data that caused the error (optional)
        
    Returns:
        HandoffSerializationError with improved error message
    """
    import json
    
    reason = str(error)
    
    # Provide more specific error messages for common JSON issues
    if isinstance(error, json.JSONDecodeError):
        reason = f"Invalid JSON format at line {error.lineno}, column {error.colno}: {error.msg}"
    elif isinstance(error, TypeError):
        reason = f"Data type not JSON serializable: {reason}"
    elif isinstance(error, ValueError):
        reason = f"Value error during JSON processing: {reason}"
    
    return HandoffSerializationError(operation, reason, data)


def validate_importance(importance: float, context: str = "importance") -> None:
    """
    Validate importance value and raise appropriate error if invalid.
    
    Args:
        importance: The importance value to validate
        context: Context description for error message
        
    Raises:
        InvalidImportanceError: If importance is outside valid range
    """
    if not isinstance(importance, (int, float)) or not (0.0 <= importance <= 1.0):
        raise InvalidImportanceError(importance)


def validate_half_life(half_life: Union[int, float], context: str = "half_life") -> None:
    """
    Validate half-life value and raise appropriate error if invalid.
    
    Args:
        half_life: The half-life value to validate
        context: Context description for error message
        
    Raises:
        InvalidHalfLifeError: If half-life is not positive
    """
    if not isinstance(half_life, (int, float)) or half_life <= 0:
        raise InvalidHalfLifeError(half_life)


def wrap_external_error(error: Exception, context: str, operation: str) -> ArgentumError:
    """
    Wrap external library errors in argentum-specific exceptions.
    
    Args:
        error: The original error
        context: Context where error occurred
        operation: Operation that was being performed
        
    Returns:
        Appropriate ArgentumError subclass
    """
    error_type = type(error).__name__
    message = f"{error_type} in {context} during {operation}: {str(error)}"
    
    details = {
        "original_error": error_type,
        "context": context,
        "operation": operation,
        "original_message": str(error)
    }
    
    # Map to specific error types based on context
    if "handoff" in context.lower():
        return HandoffError(message, details)
    elif "state" in context.lower() or "diff" in context.lower():
        return StateDiffError(message, details)
    elif "context" in context.lower() or "decay" in context.lower():
        return ContextDecayError(message, details)
    elif "plan" in context.lower() or "lint" in context.lower():
        return PlanLintError(message, details)
    else:
        return ArgentumError(message, details)