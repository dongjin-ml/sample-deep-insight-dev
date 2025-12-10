# Customization Guide

This guide covers how to customize the Managed AgentCore deployment for your specific needs.

---

## 1. Use Your Own Data

### Directory Structure

Add your data files under the `data/` directory:

```
data/
└── your_project/
    ├── your_data.csv              # Your data file
    └── column_definitions.json    # Column descriptions (optional)
```

### Column Definitions (Optional)

Create `column_definitions.json` to help the agent understand your data:

```json
{
  "columns": {
    "date": "Transaction date in YYYY-MM-DD format",
    "product_name": "Name of the product sold",
    "quantity": "Number of units sold",
    "revenue": "Total revenue in USD"
  }
}
```

### Update Your Query

Your prompt should include:
1. **Analysis perspective**: What angle to analyze (e.g., sales, marketing, operations)
2. **Data path**: Full path to your CSV and JSON files

Edit the `user_query` variable in `managed-agentcore/02_invoke_agentcore_runtime_vpc.py`:

```python
user_query = """
Analyze from sales and marketing perspectives, generate charts and extract insights.
The analysis target is './data/your_project/' directory.
your_data.csv is the data file, and column_definitions.json contains column descriptions.
"""
```

> 📖 **[Prompt writing guide (Korean) →](https://www.linkedin.com/pulse/%EB%8D%B0%EC%9D%B4%ED%84%B0-%EB%B6%84%EC%84%9D-%EB%A6%AC%ED%8F%AC%ED%8A%B8-2-3%EC%9D%BC%EC%97%90%EC%84%9C-15%EB%B6%84%EC%9C%BC%EB%A1%9C-agentic-ai-%EC%8B%A4%EC%A0%84-%EC%9C%A0%EC%8A%A4%EC%BC%80%EC%9D%B4%EC%8A%A4-gonsoo-moon-nhlac/)** How to write effective analysis prompts

---

## 2. Modify Fargate Dependencies

The Fargate container runs your Python code. To add custom Python packages:

### Edit requirements.txt

Modify `fargate-runtime/requirements.txt`:

```txt
# Existing dependencies
pandas>=2.0.0
matplotlib>=3.7.0
seaborn>=0.12.0

# Add your custom packages
scikit-learn>=1.3.0
plotly>=5.18.0
your-custom-package>=1.0.0
```

### Rebuild and Deploy

After modifying requirements.txt, rebuild the Docker image:

```bash
cd production_deployment/scripts/phase2
./deploy.sh prod --stage 2
```

Then update the runtime:

```bash
cd ../../../
uv run 01_create_agentcore_runtime_vpc.py
```

---

## 3. Customize Docker Image

For system-level customizations (fonts, libraries), modify the Dockerfile:

### Edit Dockerfile

Modify `fargate-runtime/Dockerfile`:

```dockerfile
# Add system packages
RUN apt-get update && apt-get install -y \
    your-system-package \
    && rm -rf /var/lib/apt/lists/*

# Add custom fonts
COPY fonts/ /usr/share/fonts/custom/
RUN fc-cache -fv
```

### Rebuild

```bash
cd production_deployment/scripts/phase2
./deploy.sh prod --stage 2
```

---

## 4. Modify Agent Prompts

System prompts are stored as markdown files in `src/prompts/`:

```
src/prompts/
├── coordinator.md    # Entry point agent
├── planner.md        # Planning agent
├── supervisor.md     # Task orchestration
├── coder.md          # Code execution
├── reporter.md       # Report generation
└── validator.md      # Result validation
```

Edit these files to customize agent behavior, then recreate the runtime:

```bash
cd managed-agentcore
uv run 01_create_agentcore_runtime_vpc.py
```

---

## Summary

| Customization | Files to Modify | Action Required |
|---------------|-----------------|-----------------|
| Use your own data | `data/`, query in `02_invoke_*.py` | None |
| Python packages | `fargate-runtime/requirements.txt` | Docker rebuild (`phase2/deploy.sh`) |
| System packages/fonts | `fargate-runtime/Dockerfile` | Docker rebuild (`phase2/deploy.sh`) |
| Agent behavior | `src/prompts/*.md` | Runtime recreate (`01_create_agentcore_runtime_vpc.py`) |
