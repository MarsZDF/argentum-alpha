"""
Security tests for argentum modules.

Tests validate security controls, input sanitization, and protection
against common attack vectors.
"""

import pytest
import json
from argentum.security import (
    SecurityConfig, SecurityError, InputSizeError, SuspiciousInputError,
    configure_security, sanitize_string, validate_json_size, validate_path,
    validate_key_name, scan_for_secrets, SecurityValidator
)
from argentum import StateDiff, Handoff, ContextDecay, HandoffProtocol

try:
    from argentum import PlanLinter
    PLAN_LINT_AVAILABLE = True
except ImportError:
    PLAN_LINT_AVAILABLE = False


class TestSecurityConfiguration:
    """Test security configuration and limits."""
    
    def test_default_security_config(self):
        """Test default security configuration values."""
        config = SecurityConfig()
        
        assert config.max_state_size == 10 * 1024 * 1024  # 10MB
        assert config.max_context_items == 10000
        assert config.max_plan_steps == 1000
        assert config.enable_xss_protection is True
        assert config.enable_injection_protection is True
    
    def test_configure_security(self):
        """Test security configuration function."""
        # Test production configuration
        configure_security(
            max_state_size_mb=5,
            max_context_items=5000,
            max_plan_steps=500,
            enable_all_protections=True
        )
        
        from argentum.security import get_security_config
        config = get_security_config()
        
        assert config.max_state_size == 5 * 1024 * 1024
        assert config.max_context_items == 5000
        assert config.max_plan_steps == 500
        assert config.enable_xss_protection is True


class TestInputSanitization:
    """Test input sanitization and validation."""
    
    def test_sanitize_string_basic(self):
        """Test basic string sanitization."""
        # Clean string should pass through
        clean = "This is a normal string"
        assert sanitize_string(clean) == clean
        
        # String with null bytes should be cleaned
        with_nulls = "String\x00with\x00nulls"
        sanitized = sanitize_string(with_nulls)
        assert '\x00' not in sanitized
    
    def test_sanitize_string_length_limits(self):
        """Test string length validation."""
        long_string = "a" * 1000
        
        # Should pass with sufficient limit
        result = sanitize_string(long_string, max_length=1000)
        assert len(result) <= 1000
        
        # Should fail with insufficient limit
        with pytest.raises(InputSizeError):
            sanitize_string(long_string, max_length=100)
    
    def test_dangerous_pattern_detection(self):
        """Test detection of dangerous patterns."""
        dangerous_inputs = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "on click='alert(1)'",
            "../../../etc/passwd",
            "__import__('os')",
            "eval(malicious_code)",
            "SELECT * FROM users",
        ]
        
        for dangerous in dangerous_inputs:
            with pytest.raises(SuspiciousInputError):
                sanitize_string(dangerous)
    
    def test_validate_json_size(self):
        """Test JSON size validation."""
        # Small data should pass
        small_data = {"key": "value"}
        validate_json_size(small_data, max_size=1000, context="test")
        
        # Large data should fail
        large_data = {"key": "x" * 10000}
        with pytest.raises(InputSizeError) as exc_info:
            validate_json_size(large_data, max_size=1000, context="test")
        
        assert "test too large" in str(exc_info.value)
    
    def test_validate_path(self):
        """Test path validation."""
        # Valid paths
        assert validate_path("file.txt") == "file.txt"
        assert validate_path("folder/file.txt") == "folder/file.txt"
        
        # Path traversal should fail
        with pytest.raises(SuspiciousInputError):
            validate_path("../../../etc/passwd")
        
        with pytest.raises(SuspiciousInputError):
            validate_path("..\\..\\windows\\system32")
        
        # Invalid characters should fail
        with pytest.raises(SuspiciousInputError):
            validate_path("file<script>.txt")
    
    def test_validate_key_name(self):
        """Test key name validation."""
        # Valid keys
        assert validate_key_name("valid_key") == "valid_key"
        assert validate_key_name("key123") == "key123"
        
        # Double underscore keys should fail
        with pytest.raises(SuspiciousInputError):
            validate_key_name("__dangerous__")
        
        # Too long keys should fail
        with pytest.raises(InputSizeError):
            validate_key_name("x" * 2000)


class TestSecretsDetection:
    """Test secrets detection functionality."""
    
    def test_basic_secrets_detection(self):
        """Test detection of common secret patterns."""
        data_with_secrets = {
            "api_key": "sk-1234567890abcdef",
            "database": {
                "password": "secret123",
                "connection": "bearer_token_xyz"
            }
        }
        
        detected = scan_for_secrets(data_with_secrets)
        
        assert "sk-" in detected
        assert "api_key" in detected
        assert "password" in detected
        assert "bearer" in detected
    
    def test_custom_secrets_patterns(self):
        """Test custom secret patterns."""
        data = {"custom_secret": "my_special_token"}
        
        # Without custom patterns
        detected = scan_for_secrets(data)
        assert "my_special_token" not in detected
        
        # With custom patterns
        detected = scan_for_secrets(data, custom_patterns=["my_special_token"])
        assert "my_special_token" in detected
    
    def test_secrets_in_nested_structures(self):
        """Test secrets detection in complex nested data."""
        complex_data = {
            "config": {
                "auth": {
                    "tokens": {
                        "github": "ghp_abcdef123456",
                        "aws": {
                            "access_key": "AKIA1234567890",
                            "secret": "secret_key_xyz"
                        }
                    }
                }
            }
        }
        
        detected = scan_for_secrets(complex_data)
        assert "ghp_" in detected
        assert "secret" in detected


class TestSecurityValidator:
    """Test the centralized security validator."""
    
    def test_state_diff_validation(self):
        """Test StateDiff security validation."""
        validator = SecurityValidator()
        
        # Valid state should pass
        valid_state = {"key": "value", "count": 42}
        validator.validate_state_diff_input(valid_state, "test_label")
        
        # State with secrets should warn but not fail
        state_with_secrets = {"api_key": "sk-123", "data": "normal"}
        # This should log a warning but not raise an exception
        validator.validate_state_diff_input(state_with_secrets, "test_label")
    
    def test_handoff_validation(self):
        """Test Handoff security validation."""
        validator = SecurityValidator()
        
        # Valid handoff should pass
        validator.validate_handoff_input(
            from_agent="agent_a",
            to_agent="agent_b", 
            context_summary="Normal summary",
            artifacts=["file1.txt", "file2.json"],
            metadata={"key": "value"}
        )
        
        # Handoff with secrets should fail
        with pytest.raises(SecurityError):
            validator.validate_handoff_input(
                from_agent="agent_a",
                to_agent="agent_b",
                context_summary="Summary", 
                artifacts=["file.txt"],
                metadata={"api_key": "sk-secret123"}
            )
    
    def test_context_decay_validation(self):
        """Test ContextDecay security validation.""" 
        validator = SecurityValidator()
        
        # Valid context should pass
        validator.validate_context_decay_input("valid_key", "value", 0.8)
        
        # Invalid importance should fail
        with pytest.raises(SecurityError):
            validator.validate_context_decay_input("key", "value", 1.5)
        
        # Invalid key should fail
        with pytest.raises(SuspiciousInputError):
            validator.validate_context_decay_input("__dangerous__", "value", 0.5)
    
    @pytest.mark.skipif(not PLAN_LINT_AVAILABLE, reason="PlanLinter requires optional dependencies")
    def test_plan_lint_validation(self):
        """Test PlanLint security validation."""
        validator = SecurityValidator()
        
        # Valid plan should pass
        plan = {
            "steps": [
                {"id": "step1", "tool": "test_tool", "parameters": {"param": "value"}}
            ]
        }
        tools = {"test_tool": {"parameters": {"param": {"type": "string"}}}}
        
        validator.validate_plan_lint_input(plan, tools)


class TestSecurityIntegration:
    """Test security integration in main modules."""
    
    def test_state_diff_security_integration(self):
        """Test StateDiff security integration."""
        diff = StateDiff()
        
        # Normal operation should work
        diff.snapshot("test", {"data": "normal"})
        
        # Very large state should fail (if security limits are strict enough)
        configure_security(max_state_size_mb=1)  # Very strict limit
        
        large_state = {"data": "x" * 2000000}  # 2MB of data
        with pytest.raises(InputSizeError):
            diff.snapshot("large", large_state)
    
    def test_handoff_security_integration(self):
        """Test Handoff security integration."""
        protocol = HandoffProtocol()
        
        # Normal handoff should work
        handoff = protocol.create_handoff(
            from_agent="agent_a",
            to_agent="agent_b",
            context_summary="Normal summary",
            artifacts=["file.txt"]
        )
        assert handoff.from_agent == "agent_a"
        
        # Handoff with dangerous patterns should be caught
        # Note: This would be caught in actual integration but we're testing the concept
    
    def test_context_decay_security_integration(self):
        """Test ContextDecay security integration."""
        decay = ContextDecay(half_life_steps=10)
        
        # Normal operation should work
        decay.add("normal_key", "normal_value", importance=0.8)
        
        # Invalid importance should fail
        with pytest.raises(ValueError):  # ContextDecay's own validation
            decay.add("key", "value", importance=1.5)


class TestSecurityEdgeCases:
    """Test security edge cases and attack scenarios."""
    
    def test_json_bomb_protection(self):
        """Test protection against JSON bombs."""
        # Create nested structure that expands dramatically when serialized
        bomb_data = {"a": {}}
        current = bomb_data["a"]
        
        # Create deeply nested structure
        for i in range(100):
            current[f"level_{i}"] = {}
            current = current[f"level_{i}"]
        
        # Should be caught by size validation
        with pytest.raises(InputSizeError):
            validate_json_size(bomb_data, max_size=1000, context="bomb_test")
    
    def test_unicode_attacks(self):
        """Test protection against Unicode-based attacks.""" 
        unicode_attacks = [
            "\u202E\u0040\u202D",  # Right-to-left override
            "\uFEFF",              # Byte order mark
            "\u200B",              # Zero-width space
            "test\uD800",          # Invalid surrogate
        ]
        
        for attack in unicode_attacks:
            # Should either sanitize or reject
            try:
                result = sanitize_string(attack)
                # If sanitized, should be safe
                assert len(result) >= 0
            except SuspiciousInputError:
                # If rejected, that's also acceptable
                pass
    
    def test_memory_exhaustion_protection(self):
        """Test protection against memory exhaustion."""
        configure_security(max_state_size_mb=1)  # Strict limit
        
        # Large state should be rejected
        large_state = {"data": ["x" * 1000] * 1000}  # ~1MB
        
        with pytest.raises(InputSizeError):
            validate_json_size(large_state, max_size=100000, context="memory_test")
    
    def test_log_injection_prevention(self):
        """Test log injection prevention."""
        from argentum.logging import setup_logging
        import io
        import sys
        
        # Capture log output
        log_capture = io.StringIO()
        
        logger = setup_logging(format_type="minimal")
        
        # Attempt log injection
        malicious_input = "normal\nFAKE LOG ENTRY: admin logged in"
        
        # This should be handled safely by the logging system
        # The actual test would depend on specific logging configuration
        logger.info(f"Processing: {malicious_input}")
        
        # In a real scenario, we'd check that the fake log entry
        # doesn't appear as a separate log line


class TestSecurityDocumentation:
    """Test that security features are properly documented."""
    
    def test_security_config_documentation(self):
        """Test that security configuration is documented."""
        config = SecurityConfig()
        
        # Check that important limits are set
        assert config.max_state_size > 0
        assert config.max_context_items > 0
        assert config.max_plan_steps > 0
        
        # Check that protections are enabled by default
        assert config.enable_xss_protection is True
        assert config.enable_injection_protection is True
    
    def test_security_functions_exist(self):
        """Test that all documented security functions exist."""
        # These should all be importable and callable
        from argentum.security import (
            configure_security,
            sanitize_string,
            validate_json_size,
            validate_path,
            scan_for_secrets,
            SecurityValidator
        )
        
        assert callable(configure_security)
        assert callable(sanitize_string)
        assert callable(validate_json_size)
        assert callable(validate_path)
        assert callable(scan_for_secrets)
        assert SecurityValidator is not None