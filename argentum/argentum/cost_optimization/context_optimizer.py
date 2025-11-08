"""
Context optimization for reducing token usage.
"""
from typing import List, Tuple, Any, Optional
from enum import Enum
from dataclasses import dataclass
from argentum.cost_optimization.token_counter import TokenCounter, TokenUsage, TokenizerType

class OptimizationStrategy(Enum):
    AGGRESSIVE = "aggressive"
    BALANCED = "balanced"
    CONSERVATIVE = "conservative"

@dataclass
class OptimizationResult:
    original_tokens: int
    optimized_tokens: int
    reduction_percentage: float
    items_removed: int
    items_kept: int
    strategy_used: OptimizationStrategy
    quality_score: float = 1.0

class ContextOptimizer:
    def __init__(self, max_tokens: int = 4000, strategy: OptimizationStrategy = OptimizationStrategy.BALANCED,
                 min_importance: float = 0.3, tokenizer_type: TokenizerType = TokenizerType.APPROXIMATE):
        self.max_tokens = max_tokens
        self.strategy = strategy
        self.min_importance = min_importance
        self.token_counter = TokenCounter(tokenizer_type)
    
    def optimize(self, context_items: List[Tuple[str, Any, float]]) -> Tuple[List[Tuple[str, Any, float]], OptimizationResult]:
        if not context_items:
            return [], OptimizationResult(0, 0, 0.0, 0, 0, self.strategy, 1.0)
        original_tokens = sum(self.token_counter.count(str(k) + str(v)).total_tokens for k, v, _ in context_items)
        filtered = [(k, v, imp) for k, v, imp in context_items if imp >= self.min_importance]
        filtered.sort(key=lambda x: x[2], reverse=True)
        optimized = []
        current_tokens = 0
        for k, v, imp in filtered:
            item_tokens = self.token_counter.count(str(k) + str(v)).total_tokens
            if current_tokens + item_tokens <= self.max_tokens:
                optimized.append((k, v, imp))
                current_tokens += item_tokens
            else:
                break
        optimized_tokens = sum(self.token_counter.count(str(k) + str(v)).total_tokens for k, v, _ in optimized)
        reduction = ((original_tokens - optimized_tokens) / original_tokens * 100) if original_tokens > 0 else 0.0
        quality = sum(imp for _, _, imp in optimized) / sum(imp for _, _, imp in context_items) if context_items else 1.0
        return optimized, OptimizationResult(original_tokens, optimized_tokens, reduction, len(context_items) - len(optimized),
                                           len(optimized), self.strategy, quality)
