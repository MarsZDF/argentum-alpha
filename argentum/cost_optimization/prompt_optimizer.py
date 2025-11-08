"""
Prompt optimization for reducing token usage.
"""
from typing import List, Optional, Dict
from dataclasses import dataclass
from .token_counter import TokenCounter, TokenizerType
import re

@dataclass
class PromptOptimizationResult:
    original_prompt: str
    optimized_prompt: str
    original_tokens: int
    optimized_tokens: int
    reduction_percentage: float
    optimizations_applied: List[str]
    quality_preserved: bool = True

class PromptOptimizer:
    def __init__(self, tokenizer_type: TokenizerType = TokenizerType.APPROXIMATE, aggressive: bool = False):
        self.token_counter = TokenCounter(tokenizer_type)
        self.aggressive = aggressive
    
    def optimize(self, prompt: str) -> PromptOptimizationResult:
        original_tokens = self.token_counter.count(prompt).total_tokens
        optimizations_applied = []
        optimized = prompt
        optimized = re.sub(r' +', ' ', optimized)
        optimizations_applied.append("removed_redundant_whitespace")
        if self.aggressive:
            replacements = {"please ": "", "kindly ": "", "I would like you to ": "", "Could you please ": ""}
            for old, new in replacements.items():
                optimized = optimized.replace(old, new)
            optimizations_applied.append("removed_unnecessary_words")
        replacements = {"in order to": "to", "due to the fact that": "because", "for the purpose of": "for"}
        for old, new in replacements.items():
            optimized = optimized.replace(old, new)
        optimizations_applied.append("simplified_phrases")
        optimized_tokens = self.token_counter.count(optimized).total_tokens
        reduction = ((original_tokens - optimized_tokens) / original_tokens * 100) if original_tokens > 0 else 0.0
        return PromptOptimizationResult(prompt, optimized, original_tokens, optimized_tokens, reduction,
                                       optimizations_applied, not self.aggressive or reduction < 30)
