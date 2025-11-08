# ARGENTUM AGENT INTEGRATION SPEC

**MACHINE-READABLE INTEGRATION GUIDE FOR LLMs AND AI AGENTS**

## METADATA
```yaml
spec_version: "1.0"
target_audience: ["LLM", "AI_AGENT", "AUTOMATION"]
package_name: "argentum-agent"
current_version: "0.2.1"
installation: "pip install argentum-agent"
primary_use_case: "cost_intelligence_and_optimization"
```

## CORE_CONCEPTS
```json
{
  "purpose": "Track, optimize, and control costs in AI agent systems",
  "paradigm": "cost-first_development",
  "key_benefits": ["cost_visibility", "budget_control", "optimization", "alerting"],
  "supported_operations": ["token_tracking", "cost_analysis", "budget_management", "export_reporting"]
}
```

## IMPORT_PATTERNS
```python
# PATTERN: Core imports (always available)
from argentum import (
    StateDiff,          # State tracking with cost attribution
    Handoff,            # Agent coordination with cost context  
    ContextDecay,       # Memory management with cost optimization
    CostAlerts,         # Real-time cost monitoring and alerting
    CostExporter        # Multi-format cost reporting
)

# PATTERN: Optional imports (require dependencies)
try:
    from argentum import PlanLinter  # Requires: pip install argentum-agent[lint]
except ImportError:
    PlanLinter = None

# PATTERN: Check available features
import argentum
available_features = argentum.check_dependencies()
# Returns: {"plan_lint": bool, "cost_optimization": bool}
```

## INITIALIZATION_TEMPLATES

### Template: Cost-Aware Agent Session
```python
# TEMPLATE_ID: cost_aware_session
# USE_CASE: Production agent with cost controls
# COPY_PASTE_READY: True

import argentum

# Initialize cost tracking
session = argentum.create_agent_session(
    agent_id="your_agent_name",
    half_life_steps=20,
    secure=True
)

tracker = session["cost_tracker"]
context = session["context_decay"] 
state_diff = session["state_diff"]
alerts = session["alerts"]

# Set cost limits
alerts.add_budget_alert(threshold_dollars=50.0, webhook_url="YOUR_SLACK_WEBHOOK")
alerts.add_token_alert(threshold_tokens=100000, email="admin@yourcompany.com")
```

### Template: Multi-Agent Cost Attribution
```python
# TEMPLATE_ID: multi_agent_attribution  
# USE_CASE: Track costs across multiple agents
# COPY_PASTE_READY: True

from argentum import CostTracker, HandoffProtocol

# Initialize cost tracking
cost_tracker = CostTracker()
handoff_protocol = HandoffProtocol(track_costs=True)

# Agent A completes work
cost_context_a = {
    "tokens_used": 2500,
    "model": "gpt-4", 
    "cost": 0.05,
    "operation": "research"
}

# Handoff to Agent B with cost attribution
handoff = handoff_protocol.create_handoff(
    from_agent="researcher",
    to_agent="writer",
    context_summary="Research completed on topic X",
    artifacts=["research_notes.json"],
    confidence=0.9,
    cost_context=cost_context_a
)

# Agent B receives handoff and continues
cost_tracker.record_usage(
    operation="writing",
    tokens_used=1800,
    model="gpt-4",
    agent_id="writer", 
    related_handoff_id=handoff.handoff_id
)
```

## OPERATION_PATTERNS

### Pattern: Cost Tracking
```python
# OPERATION: record_cost_usage
# REQUIRED_PARAMS: ["operation", "tokens_used", "agent_id"]
# OPTIONAL_PARAMS: ["model", "cost", "metadata"]

from argentum import CostTracker

tracker = CostTracker()

# PATTERN 1: Basic usage tracking
tracker.record_usage(
    operation="completion",
    tokens_used=1500,
    agent_id="assistant",
    model="gpt-4"
)

# PATTERN 2: Detailed cost tracking
tracker.record_usage(
    operation="embedding", 
    tokens_used=5000,
    cost=0.002,
    agent_id="embedder",
    model="text-embedding-3-small",
    metadata={"batch_size": 100}
)

# PATTERN 3: Get cost reports
report = tracker.get_cost_report(agent_id="assistant")
total_cost = report.total_cost
token_usage = report.total_tokens
```

### Pattern: State Tracking with Cost Attribution
```python
# OPERATION: state_diff_with_costs
# USE_CASE: Track state changes and associated costs

from argentum import StateDiff

diff = StateDiff(track_costs=True)

# Record state with cost context
agent_state = {"current_task": "research", "progress": 0.3}
cost_context = {"tokens_used": 800, "cost": 0.016}

diff.snapshot("task_start", agent_state, cost_context=cost_context)

# Later state change
updated_state = {"current_task": "research", "progress": 0.8}
updated_cost = {"tokens_used": 1200, "cost": 0.024}

diff.snapshot("task_progress", updated_state, cost_context=updated_cost)

# Analyze cost impact of state changes
cost_report = diff.get_cost_report()
```

### Pattern: Context Management with Cost Optimization
```python
# OPERATION: cost_optimized_context
# USE_CASE: Manage context with cost constraints

from argentum import ContextDecay

# Initialize with cost optimization enabled
context = ContextDecay(
    half_life_steps=10, 
    cost_optimization=True,
    max_context_cost=0.10  # Maximum $0.10 for context storage
)

# Add context items with cost tracking
context.add(
    key="research_data", 
    value="Large research document...",
    importance=0.8,
    storage_cost=0.002
)

# Context automatically prunes expensive low-value items
context.step()  # Advances time and applies cost-based pruning
active_items = context.get_active()
```

## INTEGRATION_PATTERNS

### Pattern: OpenAI Integration
```python
# FRAMEWORK: openai
# INTEGRATION_TYPE: cost_wrapper

import openai
from argentum import CostTracker

class CostAwareOpenAI:
    def __init__(self, agent_id: str):
        self.client = openai.OpenAI()
        self.tracker = CostTracker()
        self.agent_id = agent_id
    
    def chat_completion(self, messages, model="gpt-4", **kwargs):
        # Make API call
        response = self.client.chat.completions.create(
            messages=messages,
            model=model,
            **kwargs
        )
        
        # Track costs
        self.tracker.record_usage(
            operation="chat_completion",
            tokens_used=response.usage.total_tokens,
            agent_id=self.agent_id,
            model=model,
            metadata={"prompt_tokens": response.usage.prompt_tokens}
        )
        
        return response

# Usage
ai = CostAwareOpenAI(agent_id="assistant")
response = ai.chat_completion([{"role": "user", "content": "Hello"}])
```

### Pattern: LangChain Integration  
```python
# FRAMEWORK: langchain
# INTEGRATION_TYPE: callback

from langchain.callbacks.base import BaseCallbackHandler
from argentum import CostTracker

class ArgentumCostCallback(BaseCallbackHandler):
    def __init__(self, agent_id: str):
        self.tracker = CostTracker()
        self.agent_id = agent_id
    
    def on_llm_end(self, response, **kwargs):
        # Extract token usage from LangChain response
        if hasattr(response, 'llm_output') and 'token_usage' in response.llm_output:
            tokens = response.llm_output['token_usage']['total_tokens']
            model = response.llm_output.get('model_name', 'unknown')
            
            self.tracker.record_usage(
                operation="langchain_call",
                tokens_used=tokens,
                agent_id=self.agent_id,
                model=model
            )

# Usage with LangChain
from langchain.llms import OpenAI

callback = ArgentumCostCallback(agent_id="langchain_agent")
llm = OpenAI(callbacks=[callback])
result = llm("What is AI?")
```

## ALERT_CONFIGURATION

### Alert Types and Triggers
```yaml
alert_types:
  budget_alert:
    trigger: "cost_threshold_exceeded"
    params: ["threshold_dollars", "webhook_url", "email"]
    
  token_alert:
    trigger: "token_usage_exceeded" 
    params: ["threshold_tokens", "notification_channel"]
    
  efficiency_alert:
    trigger: "cost_per_token_degraded"
    params: ["baseline_efficiency", "degradation_threshold"]

notification_channels:
  slack:
    url_pattern: "https://hooks.slack.com/services/..."
    method: "webhook"
    
  discord: 
    url_pattern: "https://discord.com/api/webhooks/..."
    method: "webhook"
    
  email:
    method: "smtp"
    required_config: ["smtp_server", "username", "password"]
```

### Alert Configuration Examples
```python
# PATTERN: Slack alerts
from argentum import CostAlerts

alerts = CostAlerts()

alerts.add_slack_webhook(
    webhook_url="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
    threshold_dollars=25.0,
    message_template="🚨 Cost Alert: ${cost} exceeded ${threshold} for agent {agent_id}"
)

# PATTERN: Email alerts  
alerts.add_email_alert(
    email="admin@company.com",
    threshold_tokens=50000,
    smtp_config={
        "smtp_server": "smtp.gmail.com",
        "port": 587,
        "username": "alerts@company.com", 
        "password": "app_password"
    }
)

# PATTERN: Discord alerts
alerts.add_discord_webhook(
    webhook_url="https://discord.com/api/webhooks/YOUR/DISCORD/WEBHOOK",
    threshold_dollars=10.0
)
```

## EXPORT_AND_REPORTING

### Export Formats and Usage
```python
# PATTERN: Multi-format exports
from argentum import CostExporter

exporter = CostExporter()

# CSV export for spreadsheet analysis
exporter.export_csv("cost_report.csv", date_range="last_30_days")

# Excel export with multiple sheets
exporter.export_excel("detailed_costs.xlsx", include_charts=True)

# PDF executive summary
exporter.export_pdf("executive_summary.pdf", summary_only=True)

# JSON for programmatic analysis
data = exporter.export_json(agent_filter=["researcher", "writer"])

# Generate shareable dashboard URL
dashboard_url = exporter.generate_dashboard_url(
    agents=["all"],
    date_range="last_7_days", 
    public=True,
    expires_in_days=30
)
```

## ERROR_HANDLING_PATTERNS

### Standard Error Types
```python
# PATTERN: Handle Argentum exceptions
from argentum import (
    BudgetExceededError,
    SecurityError, 
    ConfigurationError,
    DependencyMissingError
)

try:
    # Operation that might exceed budget
    tracker.record_usage(operation="expensive_task", tokens_used=100000, agent_id="agent")
    
except BudgetExceededError as e:
    print(f"Budget exceeded: {e.current_cost} > {e.budget_limit}")
    # Implement fallback strategy
    
except SecurityError as e:
    print(f"Security validation failed: {e}")
    # Handle security issue
    
except DependencyMissingError as e:
    print(f"Missing optional dependency: {e}")
    # Gracefully degrade functionality
```

## PERFORMANCE_OPTIMIZATION

### Best Practices for Production
```python
# PATTERN: Optimized production setup
import argentum

# 1. Use batch operations for high-volume tracking
tracker = argentum.CostTracker(batch_size=100, flush_interval=60)

# 2. Configure context decay for memory efficiency  
context = argentum.ContextDecay(
    half_life_steps=50,
    max_items=1000,
    cost_optimization=True
)

# 3. Use sampling for very high-volume agents
diff = argentum.StateDiff(
    max_snapshots=100,
    sampling_rate=0.1  # Sample 10% of operations
)

# 4. Configure async alerts for non-blocking operation
alerts = argentum.CostAlerts(async_mode=True, queue_size=1000)
```

## SECURITY_CONSIDERATIONS

### Required Security Patterns
```python
# PATTERN: Secure configuration
from argentum import configure_security

# Configure security settings
configure_security({
    "enable_input_sanitization": True,
    "max_log_field_length": 500,
    "webhook_domain_whitelist": ["hooks.slack.com", "discord.com"],
    "enable_secrets_detection": True
})

# PATTERN: Validate webhook URLs before use
from argentum.security import validate_webhook_url

webhook_url = "https://hooks.slack.com/services/..."
if validate_webhook_url(webhook_url):
    alerts.add_slack_webhook(webhook_url, threshold_dollars=10.0)
else:
    raise SecurityError("Invalid webhook URL")
```

## TESTING_PATTERNS

### Unit Test Templates
```python
# TEMPLATE: Test cost tracking
import unittest
from argentum import CostTracker

class TestCostTracking(unittest.TestCase):
    def setUp(self):
        self.tracker = CostTracker()
    
    def test_basic_cost_recording(self):
        self.tracker.record_usage(
            operation="test",
            tokens_used=100,
            agent_id="test_agent"
        )
        
        report = self.tracker.get_cost_report(agent_id="test_agent")
        self.assertEqual(report.total_tokens, 100)
    
    def test_cost_calculation(self):
        self.tracker.record_usage(
            operation="test",
            tokens_used=1000,
            model="gpt-4",
            agent_id="test_agent"
        )
        
        report = self.tracker.get_cost_report(agent_id="test_agent")
        self.assertGreater(report.total_cost, 0)
```

## TROUBLESHOOTING_GUIDE

### Common Issues and Solutions
```yaml
issue_patterns:
  import_error_plan_lint:
    error: "ImportError: No module named 'jsonschema'"
    solution: "pip install argentum-agent[lint]"
    
  budget_exceeded:
    error: "BudgetExceededError" 
    solution: "Increase budget or implement cost optimization"
    
  webhook_validation_failed:
    error: "SecurityError: Invalid webhook URL"
    solution: "Use HTTPS URLs from whitelisted domains"
    
  high_memory_usage:
    error: "MemoryError with large context"
    solution: "Enable cost_optimization and set max_context_cost"
```

### Debug Commands
```python
# DEBUGGING: Check system status
import argentum

# Check available features
features = argentum.check_dependencies()
print("Available features:", features)

# Validate configuration
status = argentum.validate_configuration()
print("Config status:", status)

# Get performance metrics
metrics = argentum.get_performance_metrics()
print("Performance:", metrics)
```

## VERSION_COMPATIBILITY

```yaml
version_matrix:
  "0.2.1":
    python_versions: ["3.8", "3.9", "3.10", "3.11", "3.12"]
    breaking_changes: []
    new_features: ["machine_readable_documentation"]
    
  "0.2.0":
    python_versions: ["3.8", "3.9", "3.10", "3.11", "3.12"] 
    breaking_changes: []
    new_features: ["cost_optimization", "enhanced_security"]
    
  "0.1.0": 
    python_versions: ["3.8", "3.9", "3.10", "3.11", "3.12"]
    features: ["basic_tracking", "simple_alerts"]
```

---

**END OF MACHINE-READABLE SPECIFICATION**

*For human-readable documentation, see README.md*
*For security details, see SECURITY.md*
*For version management, see docs/VERSION_MANAGEMENT.md*