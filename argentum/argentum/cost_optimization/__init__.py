"""
Argentum Cost Optimization: Comprehensive toolkit for reducing AI agent costs.

This package provides utilities for token management, caching, model selection,
and other cost optimization strategies for multi-agent systems.

Quick Start:
    >>> from argentum.cost_optimization import CostOptimizationOrchestrator
    >>> 
    >>> orchestrator = CostOptimizationOrchestrator(
    ...     total_budget_tokens=1000000,
    ...     enable_caching=True,
    ...     enable_model_selection=True
    ... )
    >>> 
    >>> # Use orchestrator to optimize all operations
    >>> result = orchestrator.optimize_request(
    ...     prompt="What is AI?",
    ...     context=agent_context,
    ...     agent_id="researcher"
    ... )

Advanced Usage:
    >>> from argentum.cost_optimization import (
    ...     TokenBudgetManager,
    ...     CacheLayer,
    ...     ContextOptimizer,
    ...     CostTracker
    ... )
    >>> 
    >>> budget = TokenBudgetManager(budget_tokens=50000)
    >>> cache = CacheLayer(ttl=3600)
    >>> optimizer = ContextOptimizer(max_tokens=4000)
    >>> tracker = CostTracker()
"""

# Core cost management
from .token_budget import TokenBudgetManager, BudgetExceededError, BudgetStatus
from .cost_tracker import CostTracker, CostReport, CostBreakdown
from .token_counter import TokenCounter, TokenUsage, TokenizerType

# Optimization strategies
from .cache import CacheLayer, CacheConfig, CacheHit, CacheMiss
from .context_optimizer import ContextOptimizer, OptimizationStrategy
from .model_selector import ModelSelector, ModelRecommendation, ModelConfig
from .prompt_optimizer import PromptOptimizer, PromptOptimizationResult

# Advanced optimizations
from .batch_optimizer import BatchOptimizer, BatchRequest
from .deduplicator import RequestDeduplicator, DuplicateDetectionResult
from .context_pruner import ContextPruner, PruningStrategy
from .budget_allocator import BudgetAllocator, AllocationStrategy

# Orchestration
from .orchestrator import CostOptimizationOrchestrator, OptimizationConfig

__all__ = [
    # Core cost management
    "TokenBudgetManager",
    "BudgetExceededError",
    "BudgetStatus",
    "CostTracker",
    "CostReport",
    "CostBreakdown",
    "TokenCounter",
    "TokenUsage",
    "TokenizerType",
    
    # Optimization strategies
    "CacheLayer",
    "CacheConfig",
    "CacheHit",
    "CacheMiss",
    "ContextOptimizer",
    "OptimizationStrategy",
    "ModelSelector",
    "ModelRecommendation",
    "ModelConfig",
    "PromptOptimizer",
    "PromptOptimizationResult",
    
    # Advanced optimizations
    "BatchOptimizer",
    "BatchRequest",
    "RequestDeduplicator",
    "DuplicateDetectionResult",
    "ContextPruner",
    "PruningStrategy",
    "BudgetAllocator",
    "AllocationStrategy",
    
    # Orchestration
    "CostOptimizationOrchestrator",
    "OptimizationConfig",
]

__version__ = "0.1.0"

