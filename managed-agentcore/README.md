# Deep Insight: Managed-AgentCore Version

> Secure, customizable multi-agent system for large-scale data analysis on AWS Bedrock AgentCore

**Last Updated**: 2025-12-09

---

## 🎯 Overview

A Multi-Agent system built on AWS Bedrock AgentCore Runtime that analyzes large data files (CSV, log files up to 1GB, JSON metadata), extracts insights with text and charts, and automatically generates DOCX reports.

- **Security**: Enterprise-grade with 100% private VPC network (AgentCore ↔ ALB ↔ Fargate)
- **Customization**: Custom Docker images, extensible agents, flexible data sources for your requirements
- **Architecture**: Strands Agent Framework on serverless Fargate with concurrent processing, long-running tasks, and Infrastructure as Code

**Key Features**:

*Security*
- 🔒 **Enterprise-Grade Security** - 100% private VPC with no public internet access
- 🌐 **AgentCore VPC Mode** - Runtime deployed in private subnets with VPC networking
- 🔐 **VPC Endpoints** - Private connectivity to AWS services (Bedrock, ECR, S3, CloudWatch)
- 🛡️ **Security Groups** - Least-privilege rules for AgentCore, ALB, Fargate, and VPC Endpoints

*Customization*
- 💻 **Custom Code Interpreter** - Your own Fargate-based Python/Bash executor with custom Docker image (ECR + ALB + Fargate)
- 🐳 **Custom Docker Image** - Add your own fonts, system libraries, and Python packages
- 📂 **Flexible Data Sources** - Support for large CSV files, text, log files (i.e. 1 GB), and metadata (i.e. JSON)
- 🛠️ **Extensible Agents** - Modify prompts and add new agents to fit your requirements

*Architecture & Infrastructure*
- 🔄 **Strands Agent Framework** - Adapted to Bedrock AgentCore with custom code interpreter on serverless Fargate
- ⚡ **Concurrent Processing** - Multiple simultaneous requests via AgentCore Micro VM and Fargate containers
- ⏱️ **Long-Running Agent Tasks** - AgentCore and Fargate containers with adjustable vCPU/RAM for extended agent workflows
- ☁️ **Infrastructure as Code** - CloudFormation nested stacks for reproducible deployments

*Multi-Agent Workflow* (see [self-hosted](../self-hosted) for details)
- 📊 **Coder Agent** - Automated data analysis and calculations
- ✅ **Validator Agent** - Result validation and citation generation
- 📄 **Reporter Agent** - Automatic DOCX report generation
- 📋 **Tracker Agent** - Workflow progress monitoring and task tracking

> 📖 **[Compare with Self-Hosted →](production_deployment/docs/DEPLOYMENT_COMPARISON.md)** When to choose each option, feature comparison, and migration path

---

## 📊 Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────┐
│  User (Bedrock AgentCore API)                           │
└────────────────┬────────────────────────────────────────┘
                 │ invoke_runtime()
                 ▼
┌─────────────────────────────────────────────────────────┐
│  AgentCore Runtime (VPC Private)                        │
│  ┌───────────────────────────────────────────────┐      │
│  │ Coordinator (Strands Agent)                   │      │
│  │  - Coder Agent → Validator Agent → Reporter   │      │
│  │  - Multi-Agent Workflow Orchestration         │      │
│  └───────────────────────────────────────────────┘      │
└────────────────┬────────────────────────────────────────┘
                 │ HTTP (Private)
                 ▼
┌─────────────────────────────────────────────────────────┐
│  Custom Code Interpreter (ECR + ALB + Fargate)          │
│  ┌───────────────────────────────────────────────┐      │
│  │  Internal ALB → Fargate Containers            │      │
│  │  - Dynamic Python/Bash execution              │      │
│  │  - Custom Docker image (your libraries)       │      │
│  │  - Session-based with cookie management       │      │
│  └───────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────┘
```

### Network Architecture

**100% Private Network** - No public internet access required:
- VPC Endpoints for AWS services (Bedrock, ECR, S3, CloudWatch Logs)
- NAT Gateway optional (VPC Endpoints handle all traffic)
- Private subnets for Fargate tasks
- Internal ALB for container routing

---

## 🚀 Quick Start

### Prerequisites

| Tool | Version | Required For | Check Command |
|------|---------|--------------|---------------|
| AWS CLI | v2.x | All phases | `aws --version` |
| Docker | 20.x+ | Phase 2 | `docker --version` |
| jq | 1.6+ | Phase 3 | `jq --version` |
| uv | 0.4+ | Phase 3 | `uv --version` |
| Python | 3.12+ | Phase 4 | `python3 --version` |

```bash
# Quick verification (run from managed-agentcore/)
./production_deployment/scripts/check_prerequisites.sh

# Auto-install missing tools
./production_deployment/scripts/check_prerequisites.sh --install
```

> 📖 **[Detailed installation guide →](production_deployment/docs/PREREQUISITES.md)** Step-by-step instructions for all platforms (Linux x86_64, ARM64, macOS)

### Production Deployment

Four-phase deployment:
1. **Phase 1**: VPC Infrastructure (CloudFormation)
2. **Phase 2**: Fargate Runtime (CloudFormation + Docker)
3. **Phase 3**: Environment Preparation (UV, Dependencies, Config)
4. **Phase 4**: AgentCore Runtime (Creation, Verification, Cleanup)

**Quick commands**:
```bash
# Phase 1 + 2: Infrastructure (Automated), Any region is possible (i.e. us-west-2)
cd production_deployment/scripts
./deploy_phase1_phase2.sh prod us-west-2

# Phase 3: Environment Setup
cd phase3
./01_extract_env_vars_from_cf.sh prod us-west-2  # Specify your deployment region
./02_create_uv_env.sh deep-insight
./03_patch_dockerignore.sh

# Phase 4: Runtime Creation and Testing
cd ../../../
uv run 01_create_agentcore_runtime_vpc.py  # Create runtime
uv run 02_invoke_agentcore_runtime_vpc.py  # Test runtime
uv run 03_download_artifacts.py            # Download results
```

> 📦 **[What each script creates →](production_deployment/docs/DEPLOYMENT_OUTPUTS.md)** AWS resources, environment variables, and local files generated by each phase

---

## 🔑 What Each Phase Does

### Phase 1: Infrastructure (Nested CloudFormation Stacks)

```
phase1-main.yaml (Parent Stack)
├── NetworkStack           # VPC, 4 Subnets, NAT Gateway, Routes
├── SecurityGroupsStack    # 4 Security Groups + 15 Ingress/Egress Rules
├── VPCEndpointsStack      # Bedrock, ECR, Logs, S3 VPC Endpoints
├── ALBStack               # Internal ALB + Target Group + Listener
└── IAMStack               # Task Execution Role + Task Role + S3 Bucket
```

- **VPC**: 10.0.0.0/16 with Multi-AZ deployment
- **Security Groups**: 4 groups with least-privilege rules
- **VPC Endpoints**: 6 endpoints for private AWS service access
- **Internal ALB**: Private load balancer for Fargate containers
- **IAM Roles**: Task Role + Execution Role with minimal permissions

### Phase 2: Fargate Runtime
- **ECR Repository**: Private container registry
- **Docker Image**: Python 3.12 + Korean font support
- **ECS Cluster**: Fargate-based compute
- **Task Definition**: 2 vCPU, 4 GB RAM, auto-scaling ready

### Phase 3: Environment Preparation
- **UV Environment**: Python 3.12 + all dependencies
- **Korean Font Support**: Nanum fonts for chart generation
- **Install Tools**: Install additional tools as needed (e.g., Pandoc, TeXLive)
- **Toolkit Patch**: Include prompts in Docker builds
- **Symlinks**: Enable `uv run` from project root

### Phase 4: AgentCore Runtime
- **Runtime Creation**: Automated VPC runtime deployment (01_create_agentcore_runtime_vpc.py)
- **Runtime Testing**: End-to-end workflow testing with streaming output (02_invoke_agentcore_runtime_vpc.py)
- **Artifact Management**: S3 artifact download and organization (03_download_artifacts.py)
- **Cleanup**: Runtime deletion and resource cleanup (cleanup.sh)

---

## 📁 Project Structure

```
.
├── production_deployment/       # 🏗️ Deployment (CloudFormation + Scripts)
│   ├── cloudformation/          # Infrastructure templates
│   ├── scripts/                 # Phase 1-4 deployment scripts
│   └── docs/                    # Deployment documentation
│
├── src/                         # 🤖 Agent Source Code
│   ├── graph/                   # Workflow definitions
│   ├── tools/                   # Agent tools
│   ├── prompts/                 # System prompts
│   └── utils/                   # Utilities
│
├── fargate-runtime/             # 🐳 Fargate Container
│   ├── code_executor_server.py  # HTTP server for code execution
│   ├── Dockerfile               # Container image
│   └── requirements.txt         # Python dependencies
│
├── data/                        # 📂 Input data files
│
├── 01_create_agentcore_runtime_vpc.py  # Runtime creation
├── 02_invoke_agentcore_runtime_vpc.py  # Runtime testing
├── 03_download_artifacts.py            # Download results
└── README.md
```

---

## 🌍 Multi-Region Support

Supports deployment to **9 AWS regions**:
- 🇺🇸 US East (N. Virginia, Ohio), US West (Oregon)
- 🌏 Asia Pacific (Mumbai, Singapore, Sydney, Tokyo)
- 🇪🇺 Europe (Ireland, Frankfurt)

**Important**: AZ names are account-specific. Always verify AZ mappings before deploying to new accounts/regions.

**→ [docs/MULTI_REGION_DEPLOYMENT.md](production_deployment/docs/MULTI_REGION_DEPLOYMENT.md)**

---

## 🗑️ Cleanup

### Recommended: Two-Step Cleanup

Due to ENI (Elastic Network Interface) release timing, **cleanup requires two steps**:

```bash
# Step 1: Delete Phase 4 (AgentCore Runtime)
cd production_deployment/scripts/phase4
./cleanup.sh prod --region us-west-2

# Step 2: Wait ~6 hours for ENI release, then delete remaining phases
cd production_deployment/scripts
./cleanup_all.sh prod us-west-2
```

**⚠️ Why two steps?** AgentCore Runtime creates ENIs in your VPC. These ENIs take ~6 hours to be released after runtime deletion. Phase 1/2 cleanup will fail if ENIs are still attached.

### What Gets Deleted

- Phase 4: AgentCore Runtime + CloudWatch logs
- Phase 3: UV environment, .env file, symlinks
- Phase 2: ECS cluster, ECR repository, Docker images
- Phase 1: VPC, subnets, security groups, ALB, IAM roles
- S3 buckets (templates + session data)

### Manual Cleanup (Individual Phases)

```bash
# Phase 4: Delete Runtime
cd production_deployment/scripts/phase4
./cleanup.sh prod --region us-west-2

# ⏳ Wait ~6 hours for ENI release before proceeding

# Phase 3: Delete local environment (manual)
cd managed-agentcore
rm -rf .venv .env pyproject.toml
rm -rf production_deployment/scripts/phase3/.venv production_deployment/scripts/phase3/uv.lock

# Phase 2: Delete Fargate resources
cd production_deployment/scripts/phase2
./cleanup.sh prod --region us-west-2

# Phase 1: Delete VPC infrastructure
cd production_deployment/scripts/phase1
./cleanup.sh prod --region us-west-2
```

---

## 📚 Documentation

- **[production_deployment/docs/DEPLOYMENT_COMPARISON.md](production_deployment/docs/DEPLOYMENT_COMPARISON.md)** - Self-Hosted vs Managed AgentCore comparison
- **[production_deployment/docs/DEPLOYMENT_OUTPUTS.md](production_deployment/docs/DEPLOYMENT_OUTPUTS.md)** - What each script creates
- **[production_deployment/docs/MULTI_REGION_DEPLOYMENT.md](production_deployment/docs/MULTI_REGION_DEPLOYMENT.md)** - Multi-region deployment
- **[production_deployment/scripts/README.md](production_deployment/scripts/README.md)** - Scripts reference

---

## 📝 License

MIT License

---


