"""
Argentum: Agent state tracking and debugging utilities for AI systems.

Argentum provides a comprehensive toolkit for debugging, monitoring, and
coordinating AI agents in production environments. It helps developers
understand agent behavior, prevent common errors, and optimize performance.

Main Components:
    - StateDiff: Track and analyze changes in agent state over time
    - Handoff: Standardized protocol for agent-to-agent context transfer
    - ContextDecay: Temporal decay management for agent memory
    - PlanLinter: Static analysis and validation of agent execution plans

Quick Start:
    >>> from argentum import StateDiff, Handoff, ContextDecay, PlanLinter
    
    # Track agent state changes
    >>> diff = StateDiff()
    >>> diff.snapshot("start", {"memory": [], "goals": ["task1"]})
    >>> # ... agent processes ...
    >>> diff.snapshot("after_search", {"memory": ["fact1"], "goals": ["task1"]})
    >>> changes = diff.get_changes("start", "after_search")
    
    # Create agent handoffs
    >>> handoff = Handoff(
    ...     from_agent="researcher",
    ...     to_agent="writer", 
    ...     context_summary="Found 5 sources on topic",
    ...     artifacts=["research/sources.json"],
    ...     confidence=0.85
    ... )
    
    # Manage context decay
    >>> decay = ContextDecay(half_life_steps=10)
    >>> decay.add("user_preference", "casual_tone", importance=0.8)
    >>> decay.step()  # advance time
    >>> active_context = decay.get_active(threshold=0.5)
    
    # Validate execution plans
    >>> linter = PlanLinter()
    >>> result = linter.lint(agent_plan, tool_specs)
    >>> if result.has_errors():
    ...     print("Plan has errors:", result.issues)

For more examples and documentation, visit: https://github.com/MarsZDF/argentum
"""

from argentum.__version__ import __version__, __version_info__, get_version

# Core classes - import with error handling for optional dependencies
from argentum.state_diff import StateDiff
from argentum.handoff import Handoff, HandoffProtocol
from argentum.context_decay import ContextDecay

# Security utilities
from argentum.security import configure_security, SecurityConfig

# Plan linting with graceful degradation for missing dependencies
try:
    from argentum.plan_lint import PlanLinter, LintResult, Issue
    _PLAN_LINT_AVAILABLE = True
except ImportError as e:
    _PLAN_LINT_AVAILABLE = False
    _plan_lint_error = str(e)
    
    # Create stub classes that provide helpful error messages
    class PlanLinter:
        def __init__(self, *args, **kwargs):
            raise ImportError(
                f"PlanLinter requires optional dependencies. "
                f"Install with: pip install 'argentum-agent[lint]'. "
                f"Original error: {_plan_lint_error}"
            )
    
    class LintResult:
        def __init__(self, *args, **kwargs):
            raise ImportError("LintResult requires 'argentum-agent[lint]' dependencies")
    
    class Issue:
        def __init__(self, *args, **kwargs):
            raise ImportError("Issue requires 'argentum-agent[lint]' dependencies")


# Cost optimization (always available)
try:
    from argentum.cost_optimization import (
        CostOptimizationOrchestrator,
        TokenBudgetManager,
        CostTracker,
        TokenCounter,
        CacheLayer,
        ContextOptimizer,
        ModelSelector,
    )
    _COST_OPTIMIZATION_AVAILABLE = True
except ImportError as e:
    _COST_OPTIMIZATION_AVAILABLE = False
    _cost_opt_error = str(e)

# Public API
__all__ = [
    # Version info
    "__version__",
    "__version_info__", 
    "get_version",
    
    # Core functionality (always available)
    "StateDiff",
    "Handoff", 
    "HandoffProtocol",
    "ContextDecay",
    
    # Security utilities
    "configure_security",
    "SecurityConfig",
    
    # Plan linting (optional dependencies)
    "PlanLinter",
    "LintResult", 
    "Issue",
    
    # Cost optimization
    "CostOptimizationOrchestrator",
    "TokenBudgetManager",
    "CostTracker",
    "TokenCounter",
    "CacheLayer",
    "ContextOptimizer",
    "ModelSelector",
]

def check_dependencies() -> dict:
    """
    Check availability of optional dependencies.
    
    Returns:
        Dictionary showing which optional features are available
        
    Examples:
        >>> deps = check_dependencies()
        >>> if deps['plan_lint']:
        ...     linter = PlanLinter()
        >>> else:
        ...     print("Install argentum-agent[lint] for plan linting features")
    """
    return {
        "plan_lint": _PLAN_LINT_AVAILABLE,
        "cost_optimization": _COST_OPTIMIZATION_AVAILABLE,
    }

# Convenience function for common use cases
def create_agent_session(agent_id: str, half_life_steps: int = 20, secure: bool = True) -> dict:
    """
    Create a complete agent debugging session with all tools.
    
    Args:
        agent_id: Unique identifier for this agent session
        half_life_steps: Context decay half-life for memory management
        secure: Whether to apply security configuration (recommended: True)
        
    Returns:
        Dictionary with initialized debugging tools
        
    Examples:
        >>> session = create_agent_session("researcher_v1")
        >>> session['state_diff'].snapshot("init", initial_state)
        >>> session['context_decay'].add("user_name", "Alice", importance=0.8)
        >>> # ... later ...
        >>> changes = session['state_diff'].get_changes("init", "current")
    """
    # Configure security if requested
    if secure:
        configure_security(
            max_state_size_mb=10,      # 10MB state limit
            max_context_items=10000,   # 10K context items
            max_plan_steps=1000,       # 1K plan steps
            enable_all_protections=True
        )
    
    return {
        "agent_id": agent_id,
        "state_diff": StateDiff(),
        "context_decay": ContextDecay(half_life_steps=half_life_steps),
        "handoff_protocol": HandoffProtocol(),
        "plan_linter": PlanLinter() if _PLAN_LINT_AVAILABLE else None,
        "security_config": "enabled" if secure else "disabled",
    }