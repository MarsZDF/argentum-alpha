"""
Security utilities and configuration for argentum package.

This module provides security controls, input validation, and resource limits
to ensure safe operation in production environments.
"""

import json
import re
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Union
import logging

from .exceptions import ArgentumError


class SecurityError(ArgentumError):
    """Raised when security validation fails."""
    pass


class InputSizeError(SecurityError):
    """Raised when input exceeds size limits."""
    pass


class SuspiciousInputError(SecurityError):
    """Raised when input contains potentially malicious content."""
    pass


@dataclass
class SecurityConfig:
    """Security configuration for argentum operations."""
    
    # Size limits (in bytes)
    max_state_size: int = 10 * 1024 * 1024  # 10MB
    max_context_key_length: int = 1000
    max_context_value_size: int = 1024 * 1024  # 1MB
    max_handoff_size: int = 5 * 1024 * 1024  # 5MB
    max_plan_size: int = 2 * 1024 * 1024  # 2MB
    max_artifacts_count: int = 100
    max_artifact_path_length: int = 500
    
    # Context decay limits
    max_context_items: int = 10000
    max_half_life_steps: int = 100000
    
    # Plan limits
    max_plan_steps: int = 1000
    max_step_parameters: int = 50
    max_dependency_depth: int = 20
    
    # String validation
    enable_xss_protection: bool = True
    enable_injection_protection: bool = True
    enable_path_traversal_protection: bool = True
    
    # Logging security
    sanitize_log_data: bool = True
    max_log_field_length: int = 500
    
    # Known dangerous patterns
    dangerous_patterns: List[str] = None
    
    def __post_init__(self):
        """Initialize default dangerous patterns."""
        if self.dangerous_patterns is None:
            self.dangerous_patterns = [
                r'<script[^>]*>.*?</script>',  # XSS
                r'javascript:',               # JavaScript URLs
                r'on\w+\s*=',                # Event handlers
                r'\.\./',                     # Path traversal
                r'__import__',                # Python imports
                r'eval\s*\(',                 # Code evaluation
                r'exec\s*\(',                 # Code execution
                r'\b(union|select|insert|delete|update|drop)\s+',  # SQL injection
            ]


# Global security configuration
_security_config = SecurityConfig()


def get_security_config() -> SecurityConfig:
    """Get the current security configuration."""
    return _security_config


def set_security_config(config: SecurityConfig) -> None:
    """Set the security configuration."""
    global _security_config
    _security_config = config


def configure_security(
    max_state_size_mb: int = 10,
    max_context_items: int = 10000,
    max_plan_steps: int = 1000,
    enable_all_protections: bool = True
) -> None:
    """
    Configure security settings with reasonable defaults.
    
    Args:
        max_state_size_mb: Maximum state size in megabytes
        max_context_items: Maximum number of context items
        max_plan_steps: Maximum number of plan steps
        enable_all_protections: Enable all security protections
        
    Examples:
        >>> # Production configuration
        >>> configure_security(max_state_size_mb=5, max_context_items=5000)
        
        >>> # Development configuration (more permissive)
        >>> configure_security(max_state_size_mb=50, max_context_items=50000)
    """
    global _security_config
    _security_config.max_state_size = max_state_size_mb * 1024 * 1024
    _security_config.max_context_items = max_context_items
    _security_config.max_plan_steps = max_plan_steps
    _security_config.enable_xss_protection = enable_all_protections
    _security_config.enable_injection_protection = enable_all_protections
    _security_config.enable_path_traversal_protection = enable_all_protections


def sanitize_string(value: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize string input for safe processing and logging.
    
    Args:
        value: String to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
        
    Raises:
        SuspiciousInputError: If dangerous patterns detected
        InputSizeError: If string exceeds size limits
    """
    config = get_security_config()
    
    # Check size limits
    if max_length and len(value) > max_length:
        raise InputSizeError(f"String too long: {len(value)} > {max_length}")
    
    # Check for dangerous patterns
    if config.enable_injection_protection:
        for pattern in config.dangerous_patterns:
            if re.search(pattern, value, re.IGNORECASE | re.DOTALL):
                raise SuspiciousInputError(f"Potentially dangerous pattern detected: {pattern}")
    
    # Remove null bytes and control characters (except whitespace)
    sanitized = ''.join(char for char in value 
                       if ord(char) >= 32 or char in '\t\n\r')
    
    # Truncate if needed for logging
    if config.sanitize_log_data and max_length:
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length-3] + "..."
    
    return sanitized


def validate_json_size(data: Any, max_size: int, context: str = "data") -> None:
    """
    Validate that JSON-serializable data doesn't exceed size limits.
    
    Args:
        data: Data to validate
        max_size: Maximum size in bytes
        context: Context description for error messages
        
    Raises:
        InputSizeError: If data exceeds size limits
    """
    try:
        serialized = json.dumps(data, default=str)
        size = len(serialized.encode('utf-8'))
        
        if size > max_size:
            raise InputSizeError(
                f"{context} too large: {size} bytes > {max_size} bytes",
                {"size": size, "limit": max_size, "context": context}
            )
    except (TypeError, ValueError) as e:
        raise SecurityError(f"Cannot serialize {context} for size validation: {e}")


def validate_path(path: str, allow_relative: bool = False) -> str:
    """
    Validate and sanitize file paths to prevent path traversal attacks.
    
    Args:
        path: File path to validate
        allow_relative: Whether to allow relative paths
        
    Returns:
        Sanitized path
        
    Raises:
        SuspiciousInputError: If path contains dangerous patterns
        InputSizeError: If path too long
    """
    config = get_security_config()
    
    if len(path) > config.max_artifact_path_length:
        raise InputSizeError(f"Path too long: {len(path)} > {config.max_artifact_path_length}")
    
    # Check for path traversal
    if config.enable_path_traversal_protection:
        if '../' in path or '..\\' in path:
            raise SuspiciousInputError("Path traversal detected in path")
        
        if not allow_relative and not path.startswith('/'):
            # For artifacts, we generally want relative paths, so this is lenient
            pass
    
    # Remove null bytes
    sanitized_path = path.replace('\x00', '')
    
    # Basic path validation
    invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
    if any(char in sanitized_path for char in invalid_chars):
        raise SuspiciousInputError("Invalid characters in path")
    
    return sanitized_path


def validate_key_name(key: str) -> str:
    """
    Validate context keys and other identifier strings.
    
    Args:
        key: Key name to validate
        
    Returns:
        Validated key
        
    Raises:
        SecurityError: If key invalid or suspicious
    """
    config = get_security_config()
    
    if not key or not isinstance(key, str):
        raise SecurityError("Key must be a non-empty string")
    
    if len(key) > config.max_context_key_length:
        raise InputSizeError(f"Key too long: {len(key)} > {config.max_context_key_length}")
    
    # Sanitize the key
    sanitized_key = sanitize_string(key, config.max_context_key_length)
    
    # Check for potentially dangerous key patterns
    if sanitized_key.startswith('__') and sanitized_key.endswith('__'):
        raise SuspiciousInputError("Double underscore keys not allowed")
    
    if any(char in sanitized_key for char in ['/', '\\', '.', ' ']):
        logging.getLogger('argentum.security').warning(
            f"Key contains special characters: {sanitized_key[:50]}..."
        )
    
    return sanitized_key


def validate_collection_size(collection: Any, max_size: int, context: str) -> None:
    """
    Validate collection sizes to prevent resource exhaustion.
    
    Args:
        collection: Collection to validate (list, dict, etc.)
        max_size: Maximum allowed size
        context: Context description
        
    Raises:
        InputSizeError: If collection too large
    """
    if hasattr(collection, '__len__'):
        size = len(collection)
        if size > max_size:
            raise InputSizeError(f"{context} too large: {size} items > {max_size}")


def create_secure_secrets_list() -> List[str]:
    """
    Create a comprehensive list of secret patterns to detect.
    
    Returns:
        List of patterns that might indicate exposed secrets
    """
    return [
        # API Keys
        'sk-',                    # OpenAI
        'api_key',               # Generic
        'apikey',                # Generic
        'api-key',               # Generic
        
        # Authentication
        'password',              # Generic
        'passwd',                # Generic
        'secret',                # Generic
        'token',                 # Generic
        'bearer',                # Bearer tokens
        'auth',                  # Auth tokens
        'key',                   # Generic key
        
        # Cloud providers
        'aws_access_key',        # AWS
        'aws_secret',            # AWS
        'azure_client_secret',   # Azure
        'gcp_key',              # Google Cloud
        
        # Version control
        'ghp_',                  # GitHub Personal Access Token
        'github_token',          # GitHub
        'gitlab_token',          # GitLab
        
        # Databases
        'db_password',           # Database
        'database_url',          # Database connection
        'connection_string',     # Database
        
        # Common patterns
        'private_key',           # Private keys
        'cert',                  # Certificates
        'credential',            # Credentials
    ]


def scan_for_secrets(data: Any, custom_patterns: Optional[List[str]] = None) -> List[str]:
    """
    Scan data for potential secret exposure.
    
    Args:
        data: Data to scan (will be converted to string)
        custom_patterns: Additional patterns to check
        
    Returns:
        List of detected secret patterns
    """
    patterns = create_secure_secrets_list()
    if custom_patterns:
        patterns.extend(custom_patterns)
    
    # Convert data to string for scanning
    data_str = json.dumps(data, default=str).lower()
    
    detected = []
    for pattern in patterns:
        if pattern.lower() in data_str:
            detected.append(pattern)
    
    return detected


class SecurityValidator:
    """Centralized security validation for all argentum operations."""
    
    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or get_security_config()
        self.logger = logging.getLogger('argentum.security')
    
    def validate_state_diff_input(self, state: Dict[str, Any], label: str) -> None:
        """Validate StateDiff inputs."""
        # Validate label
        sanitize_string(label, 100)
        
        # Validate state size
        validate_json_size(state, self.config.max_state_size, "state")
        
        # Check for secrets in state
        secrets = scan_for_secrets(state)
        if secrets:
            self.logger.warning(f"Potential secrets detected in state: {secrets}")
    
    def validate_handoff_input(self, from_agent: str, to_agent: str, 
                              context_summary: str, artifacts: List[str], 
                              metadata: Optional[Dict[str, Any]] = None) -> None:
        """Validate Handoff inputs."""
        # Validate agent names
        sanitize_string(from_agent, 100)
        sanitize_string(to_agent, 100)
        
        # Validate context summary
        sanitize_string(context_summary, 5000)
        
        # Validate artifacts
        validate_collection_size(artifacts, self.config.max_artifacts_count, "artifacts list")
        for artifact in artifacts:
            validate_path(artifact, allow_relative=True)
        
        # Validate metadata size
        if metadata:
            validate_json_size(metadata, 1024 * 1024, "handoff metadata")  # 1MB limit
            
            # Check for secrets in metadata
            secrets = scan_for_secrets(metadata)
            if secrets:
                raise SecurityError(f"Secrets detected in handoff metadata: {secrets}")
    
    def validate_context_decay_input(self, key: str, value: Any, importance: float) -> None:
        """Validate ContextDecay inputs."""
        # Validate key
        validate_key_name(key)
        
        # Validate value size
        validate_json_size(value, self.config.max_context_value_size, "context value")
        
        # Validate importance
        if not isinstance(importance, (int, float)) or not 0 <= importance <= 1:
            raise SecurityError(f"Invalid importance value: {importance}")
    
    def validate_plan_lint_input(self, plan: Dict[str, Any], tool_specs: Dict[str, Any]) -> None:
        """Validate PlanLint inputs."""
        # Validate plan size
        validate_json_size(plan, self.config.max_plan_size, "plan")
        
        # Validate tool specs size
        validate_json_size(tool_specs, self.config.max_plan_size, "tool_specs")
        
        # Validate plan structure
        if 'steps' in plan:
            steps = plan['steps']
            validate_collection_size(steps, self.config.max_plan_steps, "plan steps")
            
            for i, step in enumerate(steps):
                if 'parameters' in step:
                    params = step['parameters']
                    validate_collection_size(params, self.config.max_step_parameters, 
                                           f"step {i} parameters")
                
                # Check for secrets in step parameters
                secrets = scan_for_secrets(step.get('parameters', {}))
                if secrets:
                    self.logger.error(f"Secrets detected in plan step {i}: {secrets}")


# Global validator instance
_validator = SecurityValidator()


def get_validator() -> SecurityValidator:
    """Get the global security validator."""
    return _validator


def set_validator(validator: SecurityValidator) -> None:
    """Set the global security validator."""
    global _validator
    _validator = validator


# Convenience functions for common validations
def secure_state_diff(state: Dict[str, Any], label: str) -> None:
    """Securely validate StateDiff inputs."""
    get_validator().validate_state_diff_input(state, label)


def secure_handoff(from_agent: str, to_agent: str, context_summary: str, 
                   artifacts: List[str], metadata: Optional[Dict[str, Any]] = None) -> None:
    """Securely validate Handoff inputs."""
    get_validator().validate_handoff_input(from_agent, to_agent, context_summary, 
                                         artifacts, metadata)


def secure_context_decay(key: str, value: Any, importance: float) -> None:
    """Securely validate ContextDecay inputs."""
    get_validator().validate_context_decay_input(key, value, importance)


def secure_plan_lint(plan: Dict[str, Any], tool_specs: Dict[str, Any]) -> None:
    """Securely validate PlanLint inputs."""
    get_validator().validate_plan_lint_input(plan, tool_specs)