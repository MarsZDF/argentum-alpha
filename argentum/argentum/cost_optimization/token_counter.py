"""
Token counting utilities for accurate token estimation and tracking.

Provides token counting for multiple tokenizers (OpenAI, Anthropic, etc.)
with accurate pre-call estimation and post-call verification.
"""

import re
from typing import Dict, Optional, Union, List, Any
from enum import Enum
from dataclasses import dataclass


class TokenizerType(Enum):
    """Supported tokenizer types."""
    OPENAI_GPT4 = "openai-gpt4"
    OPENAI_GPT35 = "openai-gpt35"
    ANTHROPIC_CLAUDE = "anthropic-claude"
    TIKTOKEN = "tiktoken"
    APPROXIMATE = "approximate"  # Fast approximation (4 chars = 1 token)


@dataclass
class TokenUsage:
    """Token usage information."""
    input_tokens: int
    output_tokens: int
    total_tokens: int
    tokenizer_type: TokenizerType
    estimated: bool = False  # True if estimated, False if actual
    
    @property
    def cost_estimate(self) -> float:
        """
        Estimate cost based on tokenizer type and typical pricing.
        
        Returns:
            Estimated cost in USD (rough estimates)
        """
        # Rough pricing estimates (as of 2024)
        pricing = {
            TokenizerType.OPENAI_GPT4: {"input": 0.00003, "output": 0.00006},
            TokenizerType.OPENAI_GPT35: {"input": 0.0000015, "output": 0.000002},
            TokenizerType.ANTHROPIC_CLAUDE: {"input": 0.000008, "output": 0.000024},
        }
        
        if self.tokenizer_type not in pricing:
            return 0.0
        
        rates = pricing[self.tokenizer_type]
        return (self.input_tokens * rates["input"] + 
                self.output_tokens * rates["output"])


class TokenCounter:
    """
    Accurate token counting for multiple tokenizer types.
    
    Supports OpenAI, Anthropic, and approximate counting methods.
    Provides pre-call estimation and post-call verification.
    """
    
    def __init__(self, tokenizer_type: TokenizerType = TokenizerType.APPROXIMATE):
        """
        Initialize token counter.
        
        Args:
            tokenizer_type: Type of tokenizer to use
        """
        self.tokenizer_type = tokenizer_type
        self._tokenizer_cache: Dict[str, Any] = {}
    
    def count(self, text: str, is_output: bool = False) -> TokenUsage:
        """
        Count tokens in text.
        
        Args:
            text: Text to count tokens for
            is_output: Whether this is output (for cost estimation)
            
        Returns:
            TokenUsage with token counts
        """
        if self.tokenizer_type == TokenizerType.APPROXIMATE:
            tokens = self._approximate_count(text)
        elif self.tokenizer_type in [TokenizerType.OPENAI_GPT4, TokenizerType.OPENAI_GPT35]:
            tokens = self._openai_count(text)
        elif self.tokenizer_type == TokenizerType.ANTHROPIC_CLAUDE:
            tokens = self._anthropic_count(text)
        else:
            tokens = self._approximate_count(text)
        
        if is_output:
            return TokenUsage(
                input_tokens=0,
                output_tokens=tokens,
                total_tokens=tokens,
                tokenizer_type=self.tokenizer_type,
                estimated=True
            )
        else:
            return TokenUsage(
                input_tokens=tokens,
                output_tokens=0,
                total_tokens=tokens,
                tokenizer_type=self.tokenizer_type,
                estimated=True
            )
    
    def estimate(self, text: str, max_output_tokens: int = 1000) -> TokenUsage:
        """
        Estimate token usage for a request.
        
        Args:
            text: Input text
            max_output_tokens: Maximum expected output tokens
            
        Returns:
            TokenUsage with estimated counts
        """
        input_usage = self.count(text, is_output=False)
        
        return TokenUsage(
            input_tokens=input_usage.input_tokens,
            output_tokens=max_output_tokens,  # Conservative estimate
            total_tokens=input_usage.input_tokens + max_output_tokens,
            tokenizer_type=self.tokenizer_type,
            estimated=True
        )
    
    def count_messages(self, messages: List[Dict[str, str]], 
                      max_output_tokens: int = 1000) -> TokenUsage:
        """
        Count tokens in chat messages (for chat-based APIs).
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            max_output_tokens: Maximum expected output tokens
            
        Returns:
            TokenUsage with total token counts
        """
        total_input = 0
        
        for message in messages:
            # Count role and content
            role_tokens = self.count(message.get("role", ""), is_output=False).input_tokens
            content_tokens = self.count(message.get("content", ""), is_output=False).input_tokens
            # Add overhead for message formatting (roughly 4 tokens per message)
            total_input += role_tokens + content_tokens + 4
        
        return TokenUsage(
            input_tokens=total_input,
            output_tokens=max_output_tokens,
            total_tokens=total_input + max_output_tokens,
            tokenizer_type=self.tokenizer_type,
            estimated=True
        )
    
    def verify(self, estimated: TokenUsage, actual_input: int, 
               actual_output: int) -> Dict[str, Any]:
        """
        Verify actual token usage against estimates.
        
        Args:
            estimated: Estimated token usage
            actual_input: Actual input tokens from API
            actual_output: Actual output tokens from API
            
        Returns:
            Dictionary with verification results
        """
        actual_total = actual_input + actual_output
        
        input_diff = actual_input - estimated.input_tokens
        output_diff = actual_output - estimated.output_tokens
        total_diff = actual_total - estimated.total_tokens
        
        input_error_pct = (input_diff / estimated.input_tokens * 100) if estimated.input_tokens > 0 else 0
        output_error_pct = (output_diff / estimated.output_tokens * 100) if estimated.output_tokens > 0 else 0
        
        return {
            "estimated": estimated,
            "actual": TokenUsage(
                input_tokens=actual_input,
                output_tokens=actual_output,
                total_tokens=actual_total,
                tokenizer_type=self.tokenizer_type,
                estimated=False
            ),
            "input_diff": input_diff,
            "output_diff": output_diff,
            "total_diff": total_diff,
            "input_error_pct": input_error_pct,
            "output_error_pct": output_error_pct,
            "accuracy": {
                "input_accuracy": 100 - abs(input_error_pct),
                "output_accuracy": 100 - abs(output_error_pct),
            }
        }
    
    def _approximate_count(self, text: str) -> int:
        """
        Approximate token count (4 characters ≈ 1 token).
        
        This is a fast approximation for when exact tokenization isn't needed.
        """
        # Remove whitespace for more accurate count
        cleaned = re.sub(r'\s+', ' ', text.strip())
        # Rough approximation: 4 chars = 1 token
        return max(1, len(cleaned) // 4)
    
    def _openai_count(self, text: str) -> int:
        """
        Count tokens using OpenAI tokenizer (tiktoken).
        
        Falls back to approximate if tiktoken not available.
        """
        try:
            import tiktoken
            
            # Use cl100k_base for GPT-4 and GPT-3.5
            encoding_name = "cl100k_base"
            
            if encoding_name not in self._tokenizer_cache:
                self._tokenizer_cache[encoding_name] = tiktoken.get_encoding(encoding_name)
            
            encoding = self._tokenizer_cache[encoding_name]
            return len(encoding.encode(text))
        except ImportError:
            # Fall back to approximate if tiktoken not installed
            return self._approximate_count(text)
    
    def _anthropic_count(self, text: str) -> int:
        """
        Count tokens using Anthropic tokenizer.
        
        Anthropic uses a different tokenizer. This is an approximation.
        Falls back to approximate counting.
        """
        # Anthropic tokenizer is not publicly available, so we use approximation
        # with adjustment factor (Anthropic tokens are slightly different)
        approximate = self._approximate_count(text)
        # Anthropic tokens tend to be slightly more efficient
        return int(approximate * 0.9)


def estimate_cost(tokens: int, tokenizer_type: TokenizerType, 
                  is_output: bool = False) -> float:
    """
    Estimate cost for given number of tokens.
    
    Args:
        tokens: Number of tokens
        tokenizer_type: Type of tokenizer/model
        is_output: Whether these are output tokens (usually more expensive)
        
    Returns:
        Estimated cost in USD
    """
    # Pricing as of 2024 (rough estimates)
    pricing = {
        TokenizerType.OPENAI_GPT4: {"input": 0.00003, "output": 0.00006},
        TokenizerType.OPENAI_GPT35: {"input": 0.0000015, "output": 0.000002},
        TokenizerType.ANTHROPIC_CLAUDE: {"input": 0.000008, "output": 0.000024},
    }
    
    if tokenizer_type not in pricing:
        return 0.0
    
    rate = pricing[tokenizer_type]["output" if is_output else "input"]
    return tokens * rate
