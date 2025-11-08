#!/usr/bin/env python3
"""
Real example: Plan linting for agent execution validation

This demonstrates actual PlanLinter usage in realistic agent planning
scenarios, showing error detection and auto-fix capabilities.
"""

try:
    from argentum import PlanLinter
    PLAN_LINT_AVAILABLE = True
except ImportError:
    print("⚠️  PlanLinter requires optional dependencies.")
    print("   Install with: pip install 'argentum-agent[lint]'")
    PLAN_LINT_AVAILABLE = False
    exit(1)


# Real tool specifications for a data analysis agent
DATA_ANALYSIS_TOOLS = {
    "fetch_data": {
        "parameters": {
            "source": {"type": "string", "required": True},
            "query": {"type": "string", "required": True},
            "limit": {"type": "integer", "required": False, "default": 1000}
        }
    },
    "clean_data": {
        "parameters": {
            "input_file": {"type": "string", "required": True},
            "remove_nulls": {"type": "boolean", "required": False, "default": True},
            "normalize": {"type": "boolean", "required": False, "default": False}
        }
    },
    "analyze_trends": {
        "parameters": {
            "data": {"type": "string", "required": True},
            "method": {"type": "string", "required": False, "default": "regression"},
            "confidence_level": {"type": "number", "required": False, "default": 0.95}
        }
    },
    "create_visualization": {
        "parameters": {
            "data": {"type": "string", "required": True},
            "chart_type": {"type": "string", "required": True},
            "title": {"type": "string", "required": False}
        }
    },
    "send_report": {
        "parameters": {
            "content": {"type": "string", "required": True},
            "recipients": {"type": "array", "required": True},
            "subject": {"type": "string", "required": True}
        }
    }
}


def create_valid_plan():
    """Create a well-formed analysis plan."""
    return {
        "description": "Analyze sales trends and generate report",
        "steps": [
            {
                "id": "fetch",
                "tool": "fetch_data",
                "parameters": {
                    "source": "sales_database",
                    "query": "SELECT * FROM sales WHERE date >= '2024-01-01'",
                    "limit": 5000
                },
                "outputs": ["raw_sales_data"]
            },
            {
                "id": "clean",
                "tool": "clean_data", 
                "parameters": {
                    "input_file": "{fetch.raw_sales_data}",
                    "remove_nulls": True,
                    "normalize": True
                },
                "depends_on": ["fetch"],
                "outputs": ["cleaned_data"]
            },
            {
                "id": "analyze",
                "tool": "analyze_trends",
                "parameters": {
                    "data": "{clean.cleaned_data}",
                    "method": "regression",
                    "confidence_level": 0.95
                },
                "depends_on": ["clean"],
                "outputs": ["trend_analysis"]
            },
            {
                "id": "visualize",
                "tool": "create_visualization",
                "parameters": {
                    "data": "{analyze.trend_analysis}",
                    "chart_type": "line",
                    "title": "Sales Trends 2024"
                },
                "depends_on": ["analyze"],
                "outputs": ["sales_chart"]
            },
            {
                "id": "report",
                "tool": "send_report",
                "parameters": {
                    "content": "Sales analysis complete. See attached chart: {visualize.sales_chart}",
                    "recipients": ["manager@company.com", "team@company.com"],
                    "subject": "Q1 2024 Sales Trend Analysis"
                },
                "depends_on": ["visualize"]
            }
        ]
    }


def create_problematic_plan():
    """Create a plan with various errors for testing."""
    return {
        "description": "Problematic analysis plan with multiple issues",
        "steps": [
            {
                "id": "fetch",
                "tool": "fetch_data",
                "parameters": {
                    "source": "sales_database",
                    # Missing required 'query' parameter
                    "max_rows": 5000  # Wrong parameter name (should be 'limit')
                },
                "outputs": ["raw_sales_data"]
            },
            {
                "id": "clean",
                "tool": "clean_data_v2",  # Tool doesn't exist (typo)
                "parameters": {
                    "input_file": "{fetch.raw_sales_data}",
                    "api_key": "sk-1234567890abcdef"  # Secret in parameters!
                },
                "depends_on": ["fetch"],
                "outputs": ["cleaned_data"]
            },
            {
                "id": "analyze",
                "tool": "analyze_trends",
                "parameters": {
                    "data": "{clean.cleaned_data}",
                    "method": "neural_network"  # Invalid method
                },
                "depends_on": ["clean"],
                "outputs": ["trend_analysis", "unused_output"]  # unused_output never referenced
            },
            {
                "id": "visualize",
                "tool": "create_visualization",
                "parameters": {
                    "data": "{analyze.trend_analysis}",
                    "chart_type": "line"
                    # Missing required 'chart_type' - wait, it's there but title is missing
                },
                "depends_on": ["clean"],  # Wrong dependency - should depend on analyze
                "outputs": ["sales_chart"]
            },
            {
                "id": "duplicate_viz",
                "tool": "create_visualization",
                "parameters": {
                    "data": "{analyze.trend_analysis}",
                    "chart_type": "line"  # Duplicate of visualize step
                },
                "depends_on": ["analyze"],
                "outputs": ["duplicate_chart"]
            }
        ]
    }


def create_circular_dependency_plan():
    """Create a plan with circular dependencies."""
    return {
        "description": "Plan with circular dependency issue",
        "steps": [
            {
                "id": "step_a",
                "tool": "fetch_data",
                "parameters": {
                    "source": "database",
                    "query": "SELECT * FROM table"
                },
                "depends_on": ["step_c"],  # Depends on step_c
                "outputs": ["data_a"]
            },
            {
                "id": "step_b", 
                "tool": "clean_data",
                "parameters": {
                    "input_file": "{step_a.data_a}"
                },
                "depends_on": ["step_a"],
                "outputs": ["data_b"]
            },
            {
                "id": "step_c",
                "tool": "analyze_trends",
                "parameters": {
                    "data": "{step_b.data_b}"
                },
                "depends_on": ["step_b"],  # Creates circular dependency: step_a -> step_c -> step_b -> step_a
                "outputs": ["data_c"]
            }
        ]
    }


def demonstrate_basic_linting():
    """Demonstrate basic plan linting functionality."""
    print("Basic Plan Linting")
    print("="*40)
    
    linter = PlanLinter()
    
    # Test valid plan
    print("🔍 Linting valid plan...")
    valid_plan = create_valid_plan()
    result = linter.lint(valid_plan, DATA_ANALYSIS_TOOLS)
    
    print(f"✅ Valid plan results:")
    print(f"   Errors: {len([i for i in result.issues if i.severity == 'error'])}")
    print(f"   Warnings: {len([i for i in result.issues if i.severity == 'warning'])}")
    
    if result.issues:
        print("   Issues found:")
        for issue in result.issues:
            print(f"     {issue.code}: {issue.message}")
    else:
        print("   No issues found!")


def demonstrate_error_detection():
    """Show detection of various error types."""
    print(f"\n{'='*40}")
    print("Error Detection Examples")
    print("="*40)
    
    linter = PlanLinter()
    
    # Test problematic plan
    print("🐛 Linting problematic plan...")
    problematic_plan = create_problematic_plan()
    
    # Include secrets to test secret detection
    secrets = ["sk-", "api_key", "password", "secret"]
    result = linter.lint(problematic_plan, DATA_ANALYSIS_TOOLS, secrets=secrets)
    
    print(f"\n{result}")  # Use the human-readable format
    
    # Categorize issues
    errors = [i for i in result.issues if i.severity == "error"]
    warnings = [i for i in result.issues if i.severity == "warning"]
    
    print(f"\nDetailed breakdown:")
    print(f"  Errors found: {len(errors)}")
    for error in errors:
        print(f"    {error.code}: {error.message} (at {error.location})")
    
    print(f"  Warnings found: {len(warnings)}")
    for warning in warnings:
        print(f"    {warning.code}: {warning.message} (at {warning.location})")


def demonstrate_auto_fix():
    """Show automatic fix generation and application."""
    print(f"\n{'='*40}")
    print("Auto-Fix Demonstration")
    print("="*40)
    
    linter = PlanLinter()
    
    # Create a plan with fixable issues
    fixable_plan = {
        "steps": [
            {
                "id": "step1",
                "tool": "fetch_dataa",  # Typo: should be fetch_data
                "parameters": {
                    "source": "db",
                    "query": "SELECT * FROM sales"
                }
            }
        ]
    }
    
    print("🔧 Original plan with typo:")
    print(f"   Tool name: {fixable_plan['steps'][0]['tool']}")
    
    # Lint with auto-fix
    result = linter.lint(fixable_plan, DATA_ANALYSIS_TOOLS, auto_fix=True)
    
    print(f"\n🔍 Linting results:")
    for issue in result.issues:
        print(f"   {issue.code}: {issue.message}")
        if issue.fix:
            print(f"   💡 Suggested fix: {issue.fix}")
    
    # Apply fixes
    if result.issues and any(i.fix for i in result.issues):
        print(f"\n🛠️  Applying automatic fixes...")
        fixed_plan = result.apply_patch(fixable_plan)
        
        print(f"   Fixed tool name: {fixed_plan['steps'][0]['tool']}")
        
        # Verify fix worked
        recheck = linter.lint(fixed_plan, DATA_ANALYSIS_TOOLS)
        tool_errors = [i for i in recheck.issues if i.code == "E001"]
        
        if len(tool_errors) == 0:
            print("   ✅ Fix successful - no more tool errors!")
        else:
            print("   ❌ Fix didn't resolve the issue")


def demonstrate_dependency_validation():
    """Show circular dependency detection."""
    print(f"\n{'='*40}")
    print("Dependency Validation")
    print("="*40)
    
    linter = PlanLinter()
    
    print("🔄 Testing plan with circular dependencies...")
    circular_plan = create_circular_dependency_plan()
    
    result = linter.lint(circular_plan, DATA_ANALYSIS_TOOLS)
    
    # Show dependency chain
    print("Plan dependency chain:")
    for step in circular_plan["steps"]:
        depends = step.get("depends_on", [])
        print(f"  {step['id']} depends on: {depends}")
    
    # Show detected issues
    dependency_errors = [i for i in result.issues if i.code == "E003"]
    
    if dependency_errors:
        print(f"\n🚨 Dependency issues detected:")
        for error in dependency_errors:
            print(f"   {error.message}")
    else:
        print("\n✅ No dependency issues found")


def demonstrate_security_scanning():
    """Show security vulnerability detection."""
    print(f"\n{'='*40}")
    print("Security Scanning")
    print("="*40)
    
    linter = PlanLinter()
    
    # Create plan with potential security issues
    security_plan = {
        "steps": [
            {
                "id": "fetch",
                "tool": "fetch_data",
                "parameters": {
                    "source": "api_endpoint",
                    "query": "SELECT * FROM users",
                    "api_key": "sk-1234567890abcdef",  # Exposed secret
                    "password": "admin123"  # Another secret
                }
            },
            {
                "id": "process",
                "tool": "clean_data",
                "parameters": {
                    "input_file": "{fetch.data}",
                    "secret_token": "ghp_xxxxxxxxxxxxxxxxxxxx"  # GitHub token
                }
            }
        ]
    }
    
    # Define security patterns to detect
    security_patterns = [
        "sk-",           # OpenAI API keys
        "api_key",       # Generic API keys
        "password",      # Passwords
        "secret",        # Generic secrets
        "token",         # Tokens
        "ghp_"           # GitHub personal access tokens
    ]
    
    print("🔒 Scanning for exposed secrets...")
    print(f"   Patterns: {security_patterns}")
    
    result = linter.lint(security_plan, DATA_ANALYSIS_TOOLS, secrets=security_patterns)
    
    # Show security issues
    security_issues = [i for i in result.issues if i.code == "E004"]
    
    if security_issues:
        print(f"\n🚨 Security vulnerabilities found:")
        for issue in security_issues:
            print(f"   {issue.message} (at {issue.location})")
        
        print(f"\n💡 Recommendations:")
        print(f"   - Use environment variables for secrets")
        print(f"   - Implement secure credential management")
        print(f"   - Never commit secrets to version control")
    else:
        print("\n✅ No security issues detected")


def demonstrate_sarif_output():
    """Show SARIF format for CI/CD integration."""
    print(f"\n{'='*40}")
    print("SARIF Output for CI/CD")
    print("="*40)
    
    linter = PlanLinter()
    problematic_plan = create_problematic_plan()
    
    result = linter.lint(problematic_plan, DATA_ANALYSIS_TOOLS, secrets=["api_key"])
    
    # Generate SARIF report
    sarif_data = result.to_sarif()
    
    print("📊 SARIF report generated:")
    print(f"   Schema: {sarif_data['$schema']}")
    print(f"   Tool: {sarif_data['runs'][0]['tool']['driver']['name']}")
    print(f"   Results: {len(sarif_data['runs'][0]['results'])}")
    
    # Show a sample result
    if sarif_data['runs'][0]['results']:
        sample = sarif_data['runs'][0]['results'][0]
        print(f"\n📋 Sample result:")
        print(f"   Rule ID: {sample['ruleId']}")
        print(f"   Level: {sample['level']}")
        print(f"   Message: {sample['message']['text']}")
    
    print(f"\n💡 This SARIF data can be uploaded to:")
    print(f"   - GitHub Security tab (Code Scanning)")
    print(f"   - GitLab Security Dashboard")
    print(f"   - Azure DevOps Security reports")
    print(f"   - Any SARIF-compatible security tool")


def create_realistic_ml_pipeline():
    """Create a realistic ML pipeline plan."""
    return {
        "description": "End-to-end ML model training pipeline",
        "steps": [
            {
                "id": "data_ingestion",
                "tool": "fetch_data",
                "parameters": {
                    "source": "feature_store",
                    "query": "SELECT features, target FROM ml_dataset WHERE split = 'train'",
                    "limit": 100000
                },
                "outputs": ["training_data"]
            },
            {
                "id": "data_validation",
                "tool": "clean_data",
                "parameters": {
                    "input_file": "{data_ingestion.training_data}",
                    "remove_nulls": True,
                    "normalize": True
                },
                "depends_on": ["data_ingestion"],
                "outputs": ["validated_data", "validation_report"]
            },
            {
                "id": "feature_engineering", 
                "tool": "analyze_trends",  # Using analyze_trends as feature engineering
                "parameters": {
                    "data": "{data_validation.validated_data}",
                    "method": "feature_selection"
                },
                "depends_on": ["data_validation"],
                "outputs": ["engineered_features"]
            },
            {
                "id": "model_training",
                "tool": "analyze_trends",  # Reusing for model training
                "parameters": {
                    "data": "{feature_engineering.engineered_features}",
                    "method": "random_forest",
                    "confidence_level": 0.95
                },
                "depends_on": ["feature_engineering"],
                "outputs": ["trained_model", "training_metrics"]
            },
            {
                "id": "model_evaluation",
                "tool": "create_visualization",
                "parameters": {
                    "data": "{model_training.training_metrics}",
                    "chart_type": "confusion_matrix",
                    "title": "Model Performance Evaluation"
                },
                "depends_on": ["model_training"],
                "outputs": ["evaluation_charts"]
            },
            {
                "id": "deployment_report",
                "tool": "send_report",
                "parameters": {
                    "content": "Model training completed. Accuracy: 94.2%. Ready for deployment. Charts: {model_evaluation.evaluation_charts}",
                    "recipients": ["ml-team@company.com", "devops@company.com"],
                    "subject": "ML Model Training Complete - Ready for Deployment"
                },
                "depends_on": ["model_evaluation"]
            }
        ]
    }


def demonstrate_complex_pipeline_validation():
    """Validate a complex, realistic ML pipeline."""
    print(f"\n{'='*40}")
    print("Complex Pipeline Validation")
    print("="*40)
    
    linter = PlanLinter()
    ml_pipeline = create_realistic_ml_pipeline()
    
    print("🧠 Validating ML training pipeline...")
    print(f"   Steps: {len(ml_pipeline['steps'])}")
    print(f"   Description: {ml_pipeline['description']}")
    
    result = linter.lint(ml_pipeline, DATA_ANALYSIS_TOOLS)
    
    if result.has_errors():
        print(f"\n❌ Pipeline has {len([i for i in result.issues if i.severity == 'error'])} errors:")
        for issue in result.issues:
            if issue.severity == "error":
                print(f"   {issue.code}: {issue.message}")
    
    if result.has_warnings():
        print(f"\n⚠️  Pipeline has {len([i for i in result.issues if i.severity == 'warning'])} warnings:")
        for issue in result.issues:
            if issue.severity == "warning":
                print(f"   {issue.code}: {issue.message}")
    
    if not result.has_errors() and not result.has_warnings():
        print("✅ Pipeline validation passed!")
        print("   Ready for execution in production")
    else:
        print(f"\n📊 Overall assessment:")
        print(f"   Errors: {len([i for i in result.issues if i.severity == 'error'])}")
        print(f"   Warnings: {len([i for i in result.issues if i.severity == 'warning'])}")
        print(f"   Critical issues: {len([i for i in result.issues if i.code.startswith('E')])}")


def main():
    """Run all plan linting examples."""
    print("Plan Linting Real Usage Examples")
    print("="*60)
    
    # Basic functionality
    demonstrate_basic_linting()
    
    # Error detection
    demonstrate_error_detection()
    
    # Auto-fix capabilities
    demonstrate_auto_fix()
    
    # Dependency validation
    demonstrate_dependency_validation()
    
    # Security scanning
    demonstrate_security_scanning()
    
    # SARIF output
    demonstrate_sarif_output()
    
    # Complex pipeline
    demonstrate_complex_pipeline_validation()
    
    print(f"\n{'='*60}")
    print("💡 Plan Linting Use Cases Demonstrated:")
    print("   ✅ Pre-execution plan validation")
    print("   ✅ Tool reference verification")
    print("   ✅ Parameter validation against schemas")
    print("   ✅ Dependency cycle detection")
    print("   ✅ Security vulnerability scanning")
    print("   ✅ Automatic error correction suggestions")
    print("   ✅ CI/CD integration via SARIF format")
    print("   ✅ Complex workflow validation")


if __name__ == "__main__":
    main()