"""
Context pruning for aggressive token reduction.
"""
from typing import List, Tuple, Any, Optional
from enum import Enum
from dataclasses import dataclass
from .token_counter import TokenCounter, TokenizerType

class PruningStrategy(Enum):
    AGGRESSIVE = "aggressive"
    BALANCED = "balanced"
    CONSERVATIVE = "conservative"
    IMPORTANCE_ONLY = "importance_only"

@dataclass
class PruningResult:
    original_count: int
    pruned_count: int
    tokens_saved: int
    items_removed: int
    strategy_used: PruningStrategy

class ContextPruner:
    def __init__(self, strategy: PruningStrategy = PruningStrategy.BALANCED, max_items: int = 50,
                 min_importance: float = 0.3, tokenizer_type: TokenizerType = TokenizerType.APPROXIMATE):
        self.strategy = strategy
        self.max_items = max_items
        self.min_importance = min_importance
        self.token_counter = TokenCounter(tokenizer_type)
    
    def prune(self, context_items: List[Tuple[str, Any, float]], current_step: int = 0) -> Tuple[List[Tuple[str, Any, float]], PruningResult]:
        if not context_items:
            return [], PruningResult(0, 0, 0, 0, self.strategy)
        original_count = len(context_items)
        original_tokens = sum(self.token_counter.count(str(k) + str(v)).total_tokens for k, v, _ in context_items)
        filtered = [(k, v, imp) for k, v, imp in context_items if imp >= self.min_importance]
        filtered.sort(key=lambda x: x[2], reverse=True)
        pruned = filtered[:self.max_items]
        pruned_tokens = sum(self.token_counter.count(str(k) + str(v)).total_tokens for k, v, _ in pruned)
        tokens_saved = original_tokens - pruned_tokens
        return pruned, PruningResult(original_count, len(pruned), tokens_saved, original_count - len(pruned), self.strategy)
