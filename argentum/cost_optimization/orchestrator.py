"""
Cost optimization orchestrator.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from .token_budget import TokenBudgetManager, BudgetExceededError
from .cost_tracker import CostTracker
from .token_counter import TokenCounter, TokenUsage, TokenizerType
from .cache import CacheLayer, CacheConfig
from .context_optimizer import ContextOptimizer, OptimizationStrategy
from .model_selector import ModelSelector
from .prompt_optimizer import PromptOptimizer
from .batch_optimizer import BatchOptimizer
from .deduplicator import RequestDeduplicator
from .context_pruner import ContextPruner, PruningStrategy
from .budget_allocator import BudgetAllocator, AllocationStrategy

@dataclass
class OptimizationConfig:
    total_budget_tokens: int = 1000000
    per_agent_budget: Optional[int] = None
    alert_threshold: float = 0.8
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600
    enable_context_optimization: bool = True
    max_context_tokens: int = 4000
    context_optimization_strategy: OptimizationStrategy = OptimizationStrategy.BALANCED
    enable_model_selection: bool = True
    prefer_cheap_models: bool = True
    enable_prompt_optimization: bool = True
    aggressive_prompt_optimization: bool = False
    enable_batching: bool = False
    max_batch_size: int = 10
    batch_timeout_seconds: int = 5
    enable_deduplication: bool = True
    semantic_deduplication: bool = True
    enable_context_pruning: bool = False
    pruning_strategy: PruningStrategy = PruningStrategy.BALANCED
    max_context_items: int = 50
    enable_budget_allocation: bool = False
    allocation_strategy: AllocationStrategy = AllocationStrategy.EQUAL

@dataclass
class OptimizationResult:
    success: bool
    cost_saved: float
    tokens_saved: int
    optimizations_applied: List[str]
    model_used: Optional[str] = None
    cached: bool = False
    error: Optional[str] = None

class CostOptimizationOrchestrator:
    def __init__(self, config: Optional[OptimizationConfig] = None):
        self.config = config or OptimizationConfig()
        self.budget_manager = TokenBudgetManager(
            total_budget=self.config.total_budget_tokens,
            per_agent_budget=self.config.per_agent_budget,
            alert_threshold=self.config.alert_threshold
        )
        self.cost_tracker = CostTracker()
        self.token_counter = TokenCounter()
        self.cache = CacheLayer(CacheConfig(ttl_seconds=self.config.cache_ttl_seconds)) if self.config.enable_caching else None
        self.context_optimizer = ContextOptimizer(max_tokens=self.config.max_context_tokens, strategy=self.config.context_optimization_strategy) if self.config.enable_context_optimization else None
        self.model_selector = ModelSelector() if self.config.enable_model_selection else None
        self.prompt_optimizer = PromptOptimizer(aggressive=self.config.aggressive_prompt_optimization) if self.config.enable_prompt_optimization else None
        self.batch_optimizer = BatchOptimizer(max_batch_size=self.config.max_batch_size, timeout_seconds=self.config.batch_timeout_seconds) if self.config.enable_batching else None
        self.deduplicator = RequestDeduplicator(enable_semantic_matching=self.config.semantic_deduplication) if self.config.enable_deduplication else None
        self.context_pruner = ContextPruner(strategy=self.config.pruning_strategy, max_items=self.config.max_context_items) if self.config.enable_context_pruning else None
        self.budget_allocator = BudgetAllocator(total_budget=self.config.total_budget_tokens, strategy=self.config.allocation_strategy) if self.config.enable_budget_allocation else None
    
    def optimize_request(self, prompt: str, context: Optional[List] = None, agent_id: Optional[str] = None,
                        estimated_output_tokens: int = 500, model: Optional[str] = None) -> OptimizationResult:
        optimizations_applied = []
        cost_saved = 0.0
        tokens_saved = 0
        cached = False
        model_used = model
        try:
            if self.cache:
                cache_result = self.cache.get(prompt)
                if hasattr(cache_result, 'value'):
                    optimizations_applied.append("cache_hit")
                    cached = True
                    cost_saved = 0.01
                    return OptimizationResult(True, cost_saved, 0, optimizations_applied, None, True)
            if self.deduplicator:
                dup_result = self.deduplicator.check_duplicate(agent_id or "unknown", prompt)
                if dup_result.is_duplicate:
                    optimizations_applied.append("deduplication")
                    cached = True
                    cost_saved = 0.01
                    return OptimizationResult(True, cost_saved, 0, optimizations_applied, None, True)
            original_prompt = prompt
            if self.prompt_optimizer:
                prompt_result = self.prompt_optimizer.optimize(prompt)
                if prompt_result.reduction_percentage > 5:
                    prompt = prompt_result.optimized_prompt
                    tokens_saved += prompt_result.original_tokens - prompt_result.optimized_tokens
                    optimizations_applied.append("prompt_optimization")
            optimized_context = context
            if self.context_optimizer and context:
                optimized_context, opt_result = self.context_optimizer.optimize(context)
                if opt_result.reduction_percentage > 0:
                    tokens_saved += opt_result.original_tokens - opt_result.optimized_tokens
                    optimizations_applied.append("context_optimization")
            input_tokens = self.token_counter.count(prompt).total_tokens
            if optimized_context:
                input_tokens += sum(self.token_counter.count(str(v)).total_tokens for _, v, _ in optimized_context)
            if self.model_selector and not model:
                recommendation = self.model_selector.select_model(estimated_input_tokens=input_tokens,
                                                                estimated_output_tokens=estimated_output_tokens,
                                                                prefer_cheap=self.config.prefer_cheap_models)
                model_used = recommendation.recommended_model
                optimizations_applied.append("model_selection")
            total_tokens = input_tokens + estimated_output_tokens
            if not self.budget_manager.can_afford(total_tokens, agent_id):
                return OptimizationResult(False, 0.0, tokens_saved, optimizations_applied, None, False, "Budget exceeded")
            if tokens_saved > 0:
                cost_saved = tokens_saved * 0.00003
            return OptimizationResult(True, cost_saved, tokens_saved, optimizations_applied, model_used, cached)
        except Exception as e:
            return OptimizationResult(False, 0.0, tokens_saved, optimizations_applied, None, False, str(e))
    
    def record_cost(self, agent_id: Optional[str], operation: str, model: str, token_usage: TokenUsage, metadata: Optional[Dict] = None):
        self.cost_tracker.record_cost(agent_id, operation, model, token_usage, metadata)
        try:
            self.budget_manager.consume(token_usage.total_tokens, agent_id)
        except BudgetExceededError:
            pass
    
    def get_cost_report(self):
        return self.cost_tracker.get_report()
    
    def get_budget_status(self):
        return self.budget_manager.get_status()
