# Deep Insight: Managed-AgentCore Version

> Automated data analysis system built with AWS Bedrock AgentCore Runtime

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
│  │ Coordinator (Strands Agent)                       │      │
│  │  - Coder Agent → Validator Agent → Reporter  │      │
│  │  - Multi-Agent Workflow Orchestration         │      │
│  └───────────────────────────────────────────────┘      │
└────────────────┬────────────────────────────────────────┘
                 │ HTTP (Private)
                 ▼
┌─────────────────────────────────────────────────────────┐
│  Internal ALB (Private Subnets)                         │
│  - Target Group (Fargate Tasks)                         │
│  - Health Checks & Routing                              │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  Fargate Containers (Private Subnets)                   │
│  - Python Code Execution (Dynamic)                      │
│  - Session Management (Cookie-based)                    │
│  - Matplotlib, Pandas, Data Processing                  │
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

| Tool | Version | Required For |
|------|---------|--------------|
| AWS CLI | v2.x | All phases |
| Docker | 20.x+ | Phase 2 (build container image) |
| jq | 1.6+ | Phase 3 (parse CloudFormation outputs) |
| uv | 0.4+ | Phase 3 (Python environment) |
| Python | 3.12+ | Phase 4 (runtime scripts) |

```bash
# Check versions
aws --version        # aws-cli/2.x.x required
docker --version     # Docker 20.x+
jq --version         # jq-1.6+
uv --version         # uv 0.4+
python3 --version    # Python 3.12+

# Install missing tools (Ubuntu/Debian)
sudo apt-get update && sudo apt-get install -y jq
curl -LsSf https://astral.sh/uv/install.sh | sh

# Update AWS CLI if needed
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install --update
```

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

### Complete Cleanup (All Phases)

**Single command** to delete all resources in the correct order:

```bash
cd production_deployment/scripts
./cleanup_all.sh prod us-west-2
```

This will delete:
- Phase 4: AgentCore Runtime + CloudWatch logs
- Phase 3: UV environment, .env file, symlinks
- Phase 2: ECS cluster, ECR repository, Docker images
- Phase 1: VPC, subnets, security groups, ALB, IAM roles
- S3 buckets (templates + session data)

**⚠️ WARNING**: You must type "DELETE" to confirm. This action is irreversible!
- After the Phase 4 is finished, run the rest of them because ENI in AgentCore runtime will be deleted after about 6 hours.

### Manual Cleanup (Individual Phases)

If you need to clean up specific phases:

```bash
# Phase 4: Delete Runtime only (region REQUIRED)
cd production_deployment/scripts/phase4
./cleanup.sh prod --region us-west-2

# Phase 2: Delete Fargate resources (region REQUIRED)
cd production_deployment/scripts/phase2
./cleanup.sh prod --region us-west-2

# Phase 1: Delete VPC infrastructure (region REQUIRED)
cd production_deployment/scripts/phase1
./cleanup.sh prod --region us-west-2
```

**Important**: Always delete in reverse order (4 → 3 → 2 → 1)

For detailed cleanup instructions, see: [`production_deployment/scripts/README.md#cleanup`](production_deployment/scripts/README.md#-cleanup-order-enforcement)

---

## 📚 Documentation

- **[production_deployment/scripts/README.md](production_deployment/scripts/README.md)** - Scripts reference
- **[production_deployment/docs/DEPLOYMENT_OUTPUTS.md](production_deployment/docs/DEPLOYMENT_OUTPUTS.md)** - What each script creates
- **[production_deployment/docs/MULTI_REGION_DEPLOYMENT.md](production_deployment/docs/MULTI_REGION_DEPLOYMENT.md)** - Multi-region deployment

---

## 📝 License

MIT License

---

**Version**: 3.0.0
**Status**: ✅ Production Ready
**Last Updated**: 2025-11-08
