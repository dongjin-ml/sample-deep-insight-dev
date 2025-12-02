# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Deep Insight is a hierarchical multi-agent reporting framework built on Strands SDK and Amazon Bedrock. It transforms natural language queries into comprehensive data analysis reports with visualizations and insights. The framework supports two deployment models:

- **Self-Hosted**: Full code access in your AWS VPC with complete customization
- **Managed AgentCore**: AWS-managed infrastructure with simplified configuration

## Repository Structure

```
.
├── self-hosted/              # Self-hosted deployment with UV environment
│   ├── main.py              # Entry point for agent execution
│   ├── src/                 # Agent source code
│   │   ├── graph/           # Multi-agent workflow definitions
│   │   ├── tools/           # Tool agent implementations
│   │   ├── prompts/         # System prompts (*.md files)
│   │   └── utils/           # Utilities (event queue, strands utils)
│   ├── setup/               # Environment setup with pyproject.toml
│   ├── app/                 # Streamlit web interface
│   ├── data/                # Sample CSV data files
│   └── gepa-optimizer/      # Prompt optimization toolkit
│
└── managed-agentcore/       # Managed AgentCore deployment
    ├── 01_create_agentcore_runtime_vpc.py   # Create VPC runtime
    ├── 02_invoke_agentcore_runtime_vpc.py   # Test runtime invocation
    ├── 03_download_artifacts.py              # Download S3 artifacts
    ├── src/                                  # Agent source code (similar to self-hosted)
    ├── fargate-runtime/                      # Fargate container code
    └── production_deployment/                # CloudFormation + scripts
        ├── cloudformation/
        │   ├── phase1-infrastructure.yaml   # VPC, ALB, Security Groups, IAM
        │   └── phase2-fargate.yaml          # ECR, ECS, Docker image
        └── scripts/
            ├── deploy_phase1_phase2.sh      # Automated deployment
            ├── cleanup_all.sh               # Complete cleanup
            ├── phase1/, phase2/, phase3/, phase4/
            └── README.md                    # Detailed script reference
```

## Common Commands

### Self-Hosted Deployment

**Environment Setup**:
```bash
cd self-hosted/setup
./create-uv-env.sh deep-insight 3.12
cd ..
```

**Running the Agent**:
```bash
# With custom query
uv run python main.py --user_query "Your analysis request here"

# Default demo (Korean sales analysis)
uv run python main.py

# Streamlit web app
uv run streamlit run app/app.py
```

### Managed AgentCore Deployment

**Phase 1 + 2: Infrastructure (30-40 min)**:
```bash
cd managed-agentcore/production_deployment/scripts
./deploy_phase1_phase2.sh prod us-west-2
```

**Phase 3: Environment Setup**:
```bash
cd phase3
./01_extract_env_vars_from_cf.sh prod us-west-2
./02_create_uv_env.sh deep-insight
./03_patch_dockerignore.sh
cd ../../../
```

**Phase 4: Runtime Creation and Testing**:
```bash
# Create runtime (10-15 min)
uv run 01_create_agentcore_runtime_vpc.py

# Test runtime (5-10 min)
uv run 02_invoke_agentcore_runtime_vpc.py

# Download artifacts
uv run 03_download_artifacts.py

# Verify runtime status
cd production_deployment/scripts/phase4
./verify.sh
```

**Cleanup (all resources)**:
```bash
cd production_deployment/scripts
./cleanup_all.sh prod us-west-2
```

## Architecture

### Three-Tier Agent Hierarchy

Both deployment options use the same hierarchical agent architecture:

```
User Query
    ↓
COORDINATOR (Entry Point)
  - Handles initial requests
  - Routes simple queries directly
  - Hands off complex tasks to Planner
  - Model: Claude Sonnet 4 (no reasoning)
    ↓ (if complex)
PLANNER (Strategic Thinking)
  - Analyzes task complexity
  - Creates detailed execution plan
  - Model: Claude Sonnet 4 (reasoning enabled)
    ↓
SUPERVISOR (Task Orchestrator)
  - Delegates to specialized tool agents
  - Monitors progress and coordinates workflow
  - Aggregates results
  - Model: Claude Sonnet 4 (prompt caching)
    ↓
TOOL AGENTS (Coder, Reporter, Validator, Tracker)
  - Execute specific tasks (Python, Bash, reporting, validation)
```

### Graph Workflow Implementation

**Key Files**:
- `src/graph/builder.py` - Builds the workflow graph using Strands SDK's `GraphBuilder`
- `src/graph/nodes.py` - Defines agent nodes (coordinator, planner, supervisor)
- `src/utils/event_queue.py` - Async event streaming for real-time updates

**Graph Flow**:
```python
Coordinator → (should_handoff_to_planner?) → Planner → Supervisor → [Tool Agents]
```

The `should_handoff_to_planner` condition checks for "handoff_to_planner" in the coordinator's response.

### Managed AgentCore: VPC Private Network

The managed deployment runs entirely in a private VPC network:

```
AgentCore Runtime (VPC)
    ↓ (orchestrates)
Internal ALB (Private Subnets)
    ↓ (routes to)
Fargate Containers (Private Subnets)
    - Dynamic Python code execution
    - Session management (cookie-based)
    - Data processing (Pandas, Matplotlib)
```

**Network Architecture**:
- 100% private network (no public internet access)
- VPC Endpoints for AWS services (Bedrock, ECR, S3, CloudWatch)
- Security Groups with least-privilege rules
- Internal ALB for container routing

**Key Environment Variables** (17 total):
- `FARGATE_SUBNET_IDS`, `FARGATE_SECURITY_GROUP_IDS` - Fargate network config
- `ECS_CLUSTER_NAME`, `TASK_DEFINITION_ARN`, `CONTAINER_NAME` - ECS config
- `ALB_DNS`, `ALB_TARGET_GROUP_ARN` - Load balancer config
- `S3_BUCKET_NAME` - Artifact storage
- `OTEL_*` (6 vars) - OpenTelemetry observability

## Configuration

### Environment Variables

**Self-Hosted** (`.env` in `self-hosted/`):
- `AWS_REGION` / `AWS_DEFAULT_REGION` - AWS region (tested: us-west-2)
- AWS credentials via `aws configure` or environment variables
- Model overrides: `DEFAULT_MODEL_ID`, `COORDINATOR_MODEL_ID`, `PLANNER_MODEL_ID`, `SUPERVISOR_MODEL_ID`

**Managed AgentCore** (`.env` in `managed-agentcore/`):
- Auto-generated by `phase3/01_extract_env_vars_from_cf.sh` from CloudFormation outputs
- Contains 35+ environment variables for VPC, ECS, ALB, and observability configuration

### AWS Credentials

**Option 1: AWS CLI** (recommended):
```bash
aws configure
# Region: us-west-2 for both deployments
```

**Option 2: Environment Variables**:
```bash
export AWS_REGION=us-west-2
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
```

**Option 3: .env File**:
```bash
cp .env.example .env
# Edit .env with credentials
```

## Key Components

### Prompts
System prompts are stored as markdown files in `src/prompts/*.md` and loaded via `src/prompts/template.py`. Each agent (Coordinator, Planner, Supervisor, tool agents) has its own prompt file.

**When modifying prompts**: Both `self-hosted/src/prompts/` and `managed-agentcore/src/prompts/` maintain separate copies. Keep them in sync when making changes.

### Tools
Located in `src/tools/`:
- **Coder Agent** - Python/Bash execution for data analysis
- **Reporter Agent** - Report formatting and DOCX generation
- **Validator Agent** - Quality validation and verification
- **Tracker Agent** - Progress monitoring

For managed-agentcore, Fargate-specific versions exist (e.g., `coder_agent_fargate_tool.py`) that communicate with remote containers.

### Streaming Events
The framework uses an async event queue (`src/utils/event_queue.py`) for real-time streaming:
- Graph execution runs in background
- Events are queued and yielded to consumers
- Token usage tracked via `TokenTracker` in `src/utils/strands_sdk_utils.py`

### Global State
Shared state between nodes is managed via `_global_node_states` dictionary in `src/graph/nodes.py`. This includes conversation history and token usage.

## Development Workflow

### Working with Managed AgentCore

When making code changes to managed-agentcore:

1. **Update source code** in `managed-agentcore/src/`
2. **Rebuild Docker image**:
   ```bash
   cd managed-agentcore/production_deployment/scripts/phase2
   ./deploy.sh prod --stage 2
   ```
3. **Update runtime**:
   ```bash
   cd managed-agentcore
   uv run 01_create_agentcore_runtime_vpc.py  # auto-update enabled
   ```
4. **Test changes**:
   ```bash
   uv run 02_invoke_agentcore_runtime_vpc.py
   ```

### Common Development Tasks

**Run a single test** (self-hosted):
```bash
cd self-hosted
uv run python main.py --user_query "test query"
```

**Check CloudWatch logs** (managed):
```bash
# Get runtime ID from .env
aws logs tail /aws/bedrock-agentcore/runtimes/deep_insight_runtime_vpc-<ID>-DEFAULT --follow
```

**Debug Fargate container issues** (managed):
```bash
# Check ECS tasks
aws ecs list-tasks --cluster <cluster-name>

# Check ALB target health
aws elbv2 describe-target-health --target-group-arn <tg-arn>
```

## Managed AgentCore: Critical Implementation Details

### Fargate Container Management

**Two Container Types**:
1. **AgentCore Runtime Container** - Created by `01_create_agentcore_runtime_vpc.py`
   - Orchestrates agent workflow
   - Spawns Fargate containers on-demand

2. **ECS Fargate Containers** - Spawned by the runtime
   - Execute actual tasks (Python code, tools)
   - Managed by `src/tools/fargate_container_controller.py`

**Key Files**:
- `src/tools/fargate_container_controller.py` - ECS Task lifecycle management (lines 25, 38, 51-58 for env var handling)
- `src/tools/global_fargate_coordinator.py` - Session coordination and ALB health checks (line 457-464 for ALB wait time)
- `fargate-runtime/dynamic_executor_v2.py` - Flask server for code execution
- `src/tools/cookie_acquisition_subprocess.py` - Cookie management (line 61 for HTTP scheme)

### Environment Variable Handling

**Critical**: Task Definition and Container Name must not be hardcoded. Parameters should default to `None` to allow environment variable fallback:
```python
# In fargate_container_controller.py
TASK_DEFINITION_ARN = os.getenv("TASK_DEFINITION_ARN")
CONTAINER_NAME = os.getenv("CONTAINER_NAME")

# Parameters default to None (not empty string) to allow env var fallback
def __init__(self, task_definition: str = None, container_name: str = None, ...):
    self.task_definition = task_definition or TASK_DEFINITION_ARN or "fargate-dynamic-task"
    self.container_name = container_name or CONTAINER_NAME or "dynamic-executor"
```

**Common Pitfall**: Using non-None default values (e.g., `task_definition: str = "fargate-dynamic-task"`) prevents environment variables from being used.

### HTTP Scheme in URLs

**Critical**: All HTTP requests to ALB must include the `http://` scheme:
```python
# ✅ Correct
response = session.get(f"http://{alb_dns}/container-info", ...)

# ❌ Incorrect - causes MissingSchema error
response = session.get(f"{alb_dns}/container-info", ...)
```

**Files to check**:
- `src/tools/cookie_acquisition_subprocess.py:61`
- `src/tools/fargate_container_controller.py:320`

### IAM Permissions

**Task Role** (runs agent code) requires:
- `ecs:RunTask`, `ecs:DescribeTaskDefinition` - Launch Fargate containers
- `elasticloadbalancing:RegisterTargets`, `DescribeTargetHealth` - ALB management
- `ec2:DescribeNetworkInterfaces` - Query private IPs of Fargate tasks
- `s3:PutObject`, `s3:GetObject` - Artifact storage
- `bedrock:InvokeModel*` - Bedrock API access

**Execution Role** (pulls images) requires:
- `ecr:GetAuthorizationToken`, `ecr:BatchGetImage` - ECR access
- `logs:CreateLogStream`, `PutLogEvents` - CloudWatch logging

### Observability

Per-invocation log streams via OpenTelemetry:
- Log group: `/aws/bedrock-agentcore/runtimes/{runtime_name}-DEFAULT`
- Log stream: `YYYY/MM/DD/[runtime-logs]{session_id}`
- Enable by setting OTEL environment variables in `.env`

### Troubleshooting

**Runtime fails to start**:
- Verify `FARGATE_SUBNET_IDS` and `FARGATE_SECURITY_GROUP_IDS` in `.env`
- Check Security Group rules (VPC Endpoint → ECR HTTPS access)
- Verify IAM permissions (especially `ecs:DescribeTaskDefinition`, `logs:CreateDelivery`)
- Ensure prompts are included in Docker image: run `phase3/03_patch_dockerignore.sh` before runtime creation

**Container health checks fail**:
- Check ALB wait time (60 seconds for initial health checks in `global_fargate_coordinator.py:457-464`)
- Verify Flask dependency in `fargate-runtime/requirements.txt` (must include `flask>=3.0.0`)
- Ensure HTTP scheme (`http://`) in URL requests (not just hostname)
- Check CloudWatch logs for ModuleNotFoundError

**Cookie acquisition fails**:
- Verify HTTP scheme is present: `f"http://{alb_dns}/container-info"` not `f"{alb_dns}/container-info"`
- Check ALB target group has healthy targets
- Verify Fargate tasks are running and registered with ALB

**ECR access denied**:
- Verify VPC Endpoint Security Group allows HTTPS from VPC CIDR
- Check route tables point to NAT Gateway (if not using 100% private setup)

**Task Definition not found**:
- Verify `TASK_DEFINITION_ARN` is set in `.env`
- Check that `fargate_container_controller.py` uses `None` as default parameter, not hardcoded string
- Run `phase3/01_extract_env_vars_from_cf.sh` to regenerate `.env` from CloudFormation outputs

## Important Code Patterns

### Graph Workflow Pattern

The graph uses a conditional edge pattern for coordinator-to-planner handoff:

```python
# In src/graph/builder.py
builder.add_edge("coordinator", "planner", condition=should_handoff_to_planner)

# In src/graph/nodes.py
def should_handoff_to_planner(_):
    # Checks coordinator's last message for "handoff_to_planner" keyword
    history = shared_state.get('history', [])
    for entry in reversed(history):
        if entry.get('agent') == 'coordinator':
            return 'handoff_to_planner' in entry.get('message', '')
    return False
```

### Streaming Response Pattern

Use the async generator pattern for streaming responses:

```python
# In src/graph/builder.py - StreamableGraph class
async def stream_async(self, task):
    # Run workflow in background
    workflow_task = asyncio.create_task(run_workflow())

    # Yield events from global queue
    while not workflow_task.done():
        async for event in self._yield_pending_events():
            yield event
        await asyncio.sleep(0.005)
```

### Global State Management

Nodes share state via `_global_node_states` dictionary:

```python
# In src/graph/nodes.py
_global_node_states = {}

# Store shared state
if 'shared' not in _global_node_states:
    _global_node_states['shared'] = {}
shared_state = _global_node_states['shared']

# Access: messages, history, full_plan, csv_file_path
shared_state['messages'] = agent.messages
shared_state['history'].append({"agent": "coordinator", "message": response["text"]})
```

**Important**: State persists across all nodes in a single workflow execution but is reset between invocations.

## Multi-Region Support

Managed AgentCore supports 9 AWS regions:
- US: us-east-1, us-east-2, us-west-2
- Asia: ap-south-1, ap-southeast-1, ap-southeast-2, ap-northeast-1
- Europe: eu-west-1, eu-central-1

**Important**: Availability Zone names are account-specific. Always verify AZ mappings:
```bash
cd production_deployment/scripts/phase1
./verify_agentcore_azs.sh us-west-2
```

## Dependencies

**Self-Hosted**:
- `strands-agents` (1.17.0) - Multi-agent orchestration
- `boto3` (1.40.75) - AWS SDK
- `python-docx` (1.2.0) - DOCX report generation
- `matplotlib`, `seaborn`, `plotly` - Visualizations
- `pandas` (2.3.3) - Data analysis
- Python 3.12+

**Managed AgentCore** (additional):
- `bedrock-agentcore` (1.0.6+) - AgentCore SDK
- `bedrock-agentcore-starter-toolkit` (0.1.33+) - Runtime creation
- `aws-opentelemetry-distro` (0.12.0) - Observability
- `flask` (3.0.0+) - Fargate container server

## Testing

**Self-Hosted**:
```bash
cd self-hosted
uv run python main.py --user_query "Analyze ./data/Dat-fresh-food-claude.csv"
```

**Managed AgentCore**:
```bash
cd managed-agentcore

# Create runtime
uv run 01_create_agentcore_runtime_vpc.py

# Test with default query
uv run 02_invoke_agentcore_runtime_vpc.py

# Download and inspect artifacts
uv run 03_download_artifacts.py
```

## Cost Considerations

**Managed AgentCore Monthly Costs** (24/7 operation):
- VPC Endpoints: ~$36/month (6 endpoints)
- Internal ALB: ~$20-25/month
- Fargate: Pay per second of task execution
- NAT Gateway: ~$32/month (optional - can use 100% private with VPC endpoints)

**Estimated Total**: ~$56-93/month depending on configuration

## File Location Context

The repository contains two main deployment options at the root:
- `self-hosted/` - Self-hosted deployment with UV environment
- `managed-agentcore/` - AWS-managed AgentCore deployment

When user refers to files without explicit paths, determine context from the conversation:
- For self-hosted: `main.py` is in `self-hosted/`, source code in `self-hosted/src/`
- For managed-agentcore: Python scripts (01_*.py, 02_*.py, 03_*.py) are in `managed-agentcore/`
- Phase scripts are in `managed-agentcore/production_deployment/scripts/phase{1,2,3,4}/`
- CloudFormation templates are in `managed-agentcore/production_deployment/cloudformation/`

## Documentation References

- **Production Deployment**: See `managed-agentcore/production_deployment/README.md` for complete deployment workflow
- **Script Reference**: See `managed-agentcore/production_deployment/scripts/README.md` for detailed script documentation
- **Multi-Region Guide**: See `managed-agentcore/production_deployment/docs/MULTI_REGION_DEPLOYMENT.md`
- **GEPA Optimizer**: See `self-hosted/gepa-optimizer/README.md` for prompt optimization toolkit

## Related Files

**Self-hosted commonly modified files**:
- Entry point: `self-hosted/main.py`
- Agent nodes: `self-hosted/src/graph/nodes.py` (coordinator, planner, supervisor)
- Graph builder: `self-hosted/src/graph/builder.py` (workflow definition)
- Tool agents: `self-hosted/src/tools/` (coder, reporter, validator, tracker)
- System prompts: `self-hosted/src/prompts/*.md`
- Streamlit app: `self-hosted/app/app.py`

**Managed-agentcore commonly modified files**:
- Agent nodes: `managed-agentcore/src/graph/nodes.py` (coordinator, planner, supervisor)
- Graph builder: `managed-agentcore/src/graph/builder.py` (workflow definition)
- Fargate controller: `managed-agentcore/src/tools/fargate_container_controller.py` (container lifecycle)
- Cookie management: `managed-agentcore/src/tools/cookie_acquisition_subprocess.py` (ALB communication)
- Runtime creation: `managed-agentcore/01_create_agentcore_runtime_vpc.py` (runtime deployment)
- Runtime invocation: `managed-agentcore/02_invoke_agentcore_runtime_vpc.py` (testing)
- Fargate executor: `managed-agentcore/fargate-runtime/dynamic_executor_v2.py` (code execution server)
