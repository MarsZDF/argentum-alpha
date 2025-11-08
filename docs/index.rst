Argentum: Agent State Tracking & Debugging
==========================================

Argentum provides a comprehensive toolkit for debugging, monitoring, and
coordinating AI agents in production environments. It helps developers
understand agent behavior, prevent common errors, and optimize performance.

.. image:: https://img.shields.io/pypi/v/argentum-agent
   :target: https://pypi.org/project/argentum-agent/
   :alt: PyPI version

.. image:: https://img.shields.io/github/workflow/status/MarsZDF/argentum/CI
   :target: https://github.com/MarsZDF/argentum/actions
   :alt: Build status

Quick Start
-----------

Install argentum:

.. code-block:: bash

    pip install argentum-agent

Basic usage:

.. code-block:: python

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

Core Components
---------------

.. toctree::
   :maxdepth: 2
   :caption: Main Modules:

   modules/state_diff
   modules/handoff
   modules/context_decay
   modules/plan_lint

.. toctree::
   :maxdepth: 2
   :caption: Utilities:

   modules/exceptions
   modules/logging

Examples & Tutorials
--------------------

.. toctree::
   :maxdepth: 2
   :caption: Examples:

   examples/index
   examples/debugging_workflows
   examples/multi_agent_systems
   examples/performance_optimization

API Reference
-------------

.. toctree::
   :maxdepth: 2
   :caption: API:

   api/argentum

Development
-----------

.. toctree::
   :maxdepth: 2
   :caption: Development:

   development/setup
   development/testing
   development/contributing

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`