# Argentum

**Agent state tracking, debugging, and coordination utilities for AI systems**

[![PyPI version](https://img.shields.io/pypi/v/argentum-agent)](https://pypi.org/project/argentum-agent/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/MarsZDF/argentum/workflows/CI/badge.svg)](https://github.com/MarsZDF/argentum/actions)

Argentum provides a comprehensive toolkit for debugging, monitoring, and coordinating AI agents in production environments. It helps developers understand agent behavior, prevent common errors, and optimize performance.

## 🚀 Quick Start

```bash
pip install argentum-agent
```

```python
from argentum import StateDiff, Handoff, ContextDecay, PlanLinter

# Track agent state changes
diff = StateDiff()
diff.snapshot("start", {"memory": [], "goals": ["task1"]})
# ... agent processes ...
diff.snapshot("after_search", {"memory": ["fact1"], "goals": ["task1"]})
changes = diff.get_changes("start", "after_search")

# Create agent handoffs
handoff = Handoff(
    from_agent="researcher",
    to_agent="writer", 
    context_summary="Found 5 sources on topic",
    artifacts=["research/sources.json"],
    confidence=0.85
)

# Manage context decay
decay = ContextDecay(half_life_steps=10)
decay.add("user_preference", "casual_tone", importance=0.8)
decay.step()  # advance time
active_context = decay.get_active(threshold=0.5)

# Validate execution plans
linter = PlanLinter()
result = linter.lint(agent_plan, tool_specs)
if result.has_errors():
    print("Plan has errors:", result.issues)
```

## 🧠 Core Components

### StateDiff - Agent State Evolution Tracking
Track and analyze how agent state changes over time. Perfect for debugging unexpected behavior and understanding decision-making processes.

```python
from argentum import StateDiff

diff = StateDiff()
diff.snapshot("initialization", initial_state)
diff.snapshot("after_reasoning", updated_state)

# See exactly what changed
changes = diff.get_changes("initialization", "after_reasoning")
# {'goals': {'removed': ['understand_task']}, 'confidence': {'from': 0.3, 'to': 0.8}}
```

### Handoff - Multi-Agent Coordination
Standardized protocol for agent-to-agent context transfer with built-in validation and serialization.

```python
from argentum import HandoffProtocol

protocol = HandoffProtocol()
handoff = protocol.create_handoff(
    from_agent="data_collector",
    to_agent="data_analyzer", 
    context_summary="Collected 1000 records from API",
    artifacts=["raw_data.json"],
    confidence=0.95
)

# Serialize for network transfer
json_data = protocol.to_json(handoff)
```

### ContextDecay - Temporal Memory Management
Manage agent memory with natural forgetting - important information stays, old context fades away.

```python
from argentum import ContextDecay

decay = ContextDecay(half_life_steps=20)

# Add context with importance scores
decay.add("user_name", "Alice", importance=0.9)
decay.add("session_data", temp_data, importance=0.3)

# Time passes...
for _ in range(10):
    decay.step()

# Get currently relevant context
active = decay.get_active(threshold=0.5)
# Important info persists, temporary data fades
```

### PlanLinter - Execution Plan Validation
Static analysis for agent execution plans. Catch errors before expensive execution begins.

```python
from argentum import PlanLinter

linter = PlanLinter()
result = linter.lint(
    plan=agent_generated_plan,
    tool_specs=available_tools,
    secrets=["api_key", "sk-", "password"],
    auto_fix=True
)

if result.has_errors():
    print("Issues found:")
    for issue in result.issues:
        print(f"  {issue.code}: {issue.message}")
    
    # Apply automatic fixes
    fixed_plan = result.apply_patch(plan)
```

## 🛡️ Security Features

Argentum includes comprehensive security controls for production deployments:

- **Input Validation**: Automatic sanitization and size limits
- **Secrets Detection**: Scan for exposed API keys and credentials  
- **Resource Limits**: Prevent memory exhaustion and DoS attacks
- **Safe Serialization**: JSON-only, no unsafe pickle/eval

```python
from argentum import configure_security

# Production security settings
configure_security(
    max_state_size_mb=5,
    max_context_items=5000,
    enable_all_protections=True
)
```

## 📦 Installation Options

```bash
# Core functionality
pip install argentum-agent

# With plan linting features
pip install argentum-agent[lint]

# Development dependencies
pip install argentum-agent[dev]

# Everything included
pip install argentum-agent[all]
```

## 🎯 Use Cases

### Multi-Agent Systems
- **Agent Coordination**: Standardized handoffs between specialized agents
- **State Synchronization**: Track state changes across agent boundaries
- **Error Propagation**: Understand how errors flow through agent pipelines

### Production Debugging
- **Behavior Analysis**: See exactly how agent state evolves during execution
- **Performance Monitoring**: Track context usage and memory patterns
- **Error Investigation**: Replay state changes to understand failures

### Agent Development
- **Plan Validation**: Catch errors in agent plans before execution
- **Security Scanning**: Prevent credential leaks and injection attacks
- **Memory Optimization**: Automatic context cleanup and decay management

### Research & Analysis
- **Agent Behavior Studies**: Analyze how agents make decisions over time
- **A/B Testing**: Compare agent performance with different configurations
- **Failure Analysis**: Deep dive into agent failures with complete state history

## 📚 Examples

Check out the [examples/](examples/) directory for complete working examples:

- **[state_diff_example.py](examples/state_diff_example.py)** - Query processing with state tracking
- **[handoff_example.py](examples/handoff_example.py)** - Content creation pipeline
- **[context_decay_example.py](examples/context_decay_example.py)** - Conversational AI memory
- **[plan_lint_example.py](examples/plan_lint_example.py)** - ML pipeline validation

## 🏗️ Framework Integration

Argentum works with any agent framework:

```python
# LangChain
from langchain.agents import Agent
agent = Agent(...)
session = create_agent_session("langchain_agent")
session['state_diff'].snapshot("start", agent.memory)

# Custom frameworks
class MyAgent:
    def process(self, input_data):
        session['state_diff'].snapshot("before", self.state)
        result = self._internal_process(input_data)
        session['state_diff'].snapshot("after", self.state)
        return result
```

## 🔧 Configuration

### Basic Setup
```python
from argentum import create_agent_session

# Quick setup with security enabled
session = create_agent_session(
    agent_id="my_agent",
    half_life_steps=20,
    secure=True  # Applies security defaults
)
```

### Advanced Configuration
```python
from argentum.security import SecurityConfig, set_security_config

# Custom security policy
config = SecurityConfig(
    max_state_size=5 * 1024 * 1024,  # 5MB limit
    max_context_items=5000,
    enable_injection_protection=True,
    sanitize_log_data=True
)
set_security_config(config)
```

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=argentum

# Run performance benchmarks
pytest tests/test_performance.py --benchmark-only
```

## 📖 Documentation

- **[API Documentation](https://argentum-agent.readthedocs.io)** - Complete API reference
- **[Security Guide](SECURITY.md)** - Security features and best practices
- **[Changelog](CHANGELOG.md)** - Version history and updates

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup

```bash
git clone https://github.com/MarsZDF/argentum.git
cd argentum
pip install -e .[dev]
pre-commit install
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Claude Code](https://claude.ai/code)
- Inspired by the need for better agent debugging tools
- Thanks to the AI agent developer community for feedback and ideas

---

**Argentum** - *Making AI agents observable, debuggable, and reliable.*