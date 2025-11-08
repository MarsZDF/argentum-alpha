"""
Cost-aware model selection.
"""
from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field

class ModelTier(Enum):
    ULTRA_CHEAP = "ultra_cheap"
    CHEAP = "cheap"
    MEDIUM = "medium"
    EXPENSIVE = "expensive"
    ULTRA_EXPENSIVE = "ultra_expensive"

@dataclass
class ModelConfig:
    name: str
    tier: ModelTier
    input_cost_per_token: float
    output_cost_per_token: float
    max_tokens: int
    capabilities: List[str] = field(default_factory=list)
    quality_score: float = 1.0

@dataclass
class ModelRecommendation:
    recommended_model: str
    alternative_models: List[str] = field(default_factory=list)
    estimated_cost: float = 0.0
    confidence: float = 1.0
    reasoning: str = ""

class ModelSelector:
    def __init__(self):
        self._models: Dict[str, ModelConfig] = {}
        self._default_models()
    
    def _default_models(self):
        self.register_model(ModelConfig("gpt-4", ModelTier.EXPENSIVE, 0.00003, 0.00006, 8000, ["reasoning", "analysis"], 0.95))
        self.register_model(ModelConfig("gpt-3.5-turbo", ModelTier.CHEAP, 0.0000015, 0.000002, 16000, ["basic", "chat"], 0.75))
        self.register_model(ModelConfig("claude-3-haiku", ModelTier.CHEAP, 0.00000025, 0.00000125, 200000, ["basic", "fast"], 0.80))
    
    def register_model(self, config: ModelConfig):
        self._models[config.name] = config
    
    def select_model(self, task_complexity: str = "medium", required_capabilities: Optional[List[str]] = None,
                    estimated_input_tokens: int = 1000, estimated_output_tokens: int = 500,
                    max_cost: Optional[float] = None, prefer_cheap: bool = False, min_quality: float = 0.7) -> ModelRecommendation:
        required_capabilities = required_capabilities or []
        candidates = []
        for name, config in self._models.items():
            if required_capabilities and not all(c in config.capabilities for c in required_capabilities):
                continue
            if config.quality_score < min_quality or estimated_input_tokens > config.max_tokens:
                continue
            cost = estimated_input_tokens * config.input_cost_per_token + estimated_output_tokens * config.output_cost_per_token
            if max_cost and cost > max_cost:
                continue
            candidates.append((name, config, cost))
        if not candidates:
            if self._models:
                cheapest = min(self._models.items(), key=lambda x: x[1].input_cost_per_token)
                return ModelRecommendation(cheapest[0], [], 0.0, 0.3, "No suitable model found")
            raise ValueError("No models registered")
        if prefer_cheap:
            candidates.sort(key=lambda x: x[2])
        else:
            candidates.sort(key=lambda x: x[1].quality_score / max(x[2], 0.0001), reverse=True)
        recommended_name, recommended_config, estimated_cost = candidates[0]
        alternatives = [name for name, _, _ in candidates[1:3]]
        return ModelRecommendation(recommended_name, alternatives, estimated_cost, 0.9, f"Selected {recommended_name}")
