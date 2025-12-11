# Human-in-the-Loop (HITL) S3 Feedback System

## 개요

S3를 통한 Human-in-the-Loop 피드백 시스템은 AgentCore Runtime에서 사용자가 생성된 플랜을 검토하고 승인/수정 요청을 할 수 있게 합니다.

## 아키텍처

```
┌─────────────────┐     plan_review_request      ┌─────────────────┐
│  AgentCore      │ ─────────────────────────────▶│    Client       │
│  Runtime        │                               │ (02_invoke...)  │
│                 │                               │                 │
│  plan_reviewer  │     S3 feedback file          │  사용자 입력    │
│  node           │ ◀───────────────────────────── │                 │
└─────────────────┘                               └─────────────────┘
         │                                                │
         │         ┌─────────────────┐                    │
         └────────▶│      S3         │◀───────────────────┘
                   │  feedback/      │
                   │  {request_id}   │
                   │  .json          │
                   └─────────────────┘
```

## 워크플로우

### Graph 구조 (builder.py)

```
Coordinator → Planner → PlanReviewer → Supervisor
                 ↑           │
                 └───────────┘ (feedback loop if user requests revision)
```

### 상세 흐름

1. **Coordinator** → 사용자 요청 분석, Planner로 핸드오프
2. **Planner** → 실행 계획 생성
3. **PlanReviewer** → 사용자 피드백 대기 (S3 polling)
   - 승인 시 → Supervisor로 진행
   - 수정 요청 시 → Planner로 돌아감 (최대 10회)
4. **Supervisor** → 계획 실행 (Coder, Validator, Reporter 호출)

## 핵심 컴포넌트

### 1. S3 Utility Functions (`src/utils/s3_utils.py`)

```python
def get_s3_feedback_key(request_id: str) -> str:
    """Generate S3 key for feedback file."""
    return f"deep-insight/feedback/{request_id}.json"

def check_s3_feedback(request_id: str) -> dict:
    """Check S3 for feedback file from client."""
    # S3에서 피드백 파일 확인, 없으면 None 반환

def delete_s3_feedback(request_id: str) -> bool:
    """Delete feedback file from S3 after processing."""
    # 피드백 처리 후 파일 삭제
```

### 2. Plan Reviewer Node (`src/graph/nodes.py`)

```python
async def plan_reviewer_node(task=None, **kwargs):
    """
    Plan reviewer node that allows user to review and provide feedback.

    1. Emitting 'plan_review_request' event via event queue
    2. Polling S3 for feedback file
    3. Processing feedback (approve/revision)
    """
```

**주요 기능:**
- `plan_review_request` 이벤트 발행 (클라이언트에게 플랜 전달)
- S3 polling으로 피드백 대기 (3초 간격)
- 타임아웃 시 자동 승인 (기본 300초)
- 최대 수정 횟수 도달 시 자동 승인 (기본 10회)

### 3. Conditional Functions (`src/graph/nodes.py`)

```python
def should_revise_plan(_):
    """Check if user requested plan revision."""
    return shared_state.get('plan_revision_requested', False)

def should_proceed_to_supervisor(_):
    """Check if plan is approved and should proceed."""
    return not shared_state.get('plan_revision_requested', False)
```

### 4. Client-side Handler (`02_invoke_agentcore_runtime_vpc.py`)

```python
def handle_plan_review_request(event_data):
    """Handle plan_review_request event from runtime."""
    # 플랜 표시, 사용자 입력 받기, S3에 피드백 업로드

def upload_feedback_to_s3(request_id, approved, feedback=""):
    """Upload feedback JSON to S3."""
    # S3에 피드백 JSON 업로드
```

## S3 피드백 파일 형식

**경로:** `s3://{bucket}/deep-insight/feedback/{request_id}.json`

**내용:**
```json
{
    "approved": true/false,
    "feedback": "optional revision notes",
    "timestamp": "2025-12-10T08:00:00.000000"
}
```

## 환경 변수

`.env` 또는 `.env.example`에 추가:

```bash
# Human-in-the-Loop (Plan Feedback) Configuration
# Maximum number of plan revision attempts before auto-approval
MAX_PLAN_REVISIONS=10
# Timeout in seconds to wait for user feedback before auto-approval
PLAN_FEEDBACK_TIMEOUT=300
# Polling interval in seconds to check S3 for feedback file
PLAN_FEEDBACK_POLL_INTERVAL=3
```

## 이벤트 타입

### 1. plan_review_request (Runtime → Client)

```python
{
    "type": "plan_review_request",
    "event_type": "plan_review_request",
    "plan": "...",                    # 생성된 플랜 텍스트
    "revision_count": 0,              # 현재 수정 횟수
    "max_revisions": 10,              # 최대 수정 횟수
    "request_id": "uuid...",          # 요청 ID
    "feedback_s3_path": "s3://...",   # 피드백 업로드 경로
    "timeout_seconds": 300,           # 타임아웃 시간
    "message": "Please review..."     # 안내 메시지
}
```

### 2. plan_review_keepalive (Runtime → Client)

```python
{
    "type": "plan_review_keepalive",
    "event_type": "plan_review_keepalive",
    "message": "Waiting for plan feedback... (30s elapsed)",
    "elapsed_seconds": 30,
    "timeout_seconds": 300
}
```

## 필요한 Import 및 설정

### nodes.py 상단

```python
import time
import asyncio
from src.utils.s3_utils import get_s3_feedback_key, check_s3_feedback, delete_s3_feedback
from src.utils.event_queue import put_event

# Plan feedback configuration
MAX_PLAN_REVISIONS = int(os.getenv("MAX_PLAN_REVISIONS", "10"))
PLAN_FEEDBACK_TIMEOUT = int(os.getenv("PLAN_FEEDBACK_TIMEOUT", "300"))
PLAN_FEEDBACK_POLL_INTERVAL = int(os.getenv("PLAN_FEEDBACK_POLL_INTERVAL", "3"))
```

### builder.py

```python
from .nodes import (
    plan_reviewer_node,
    should_revise_plan,
    should_proceed_to_supervisor,
)

# Graph 구성
builder.add_node(plan_reviewer, "plan_reviewer")
builder.add_edge("planner", "plan_reviewer")
builder.add_edge("plan_reviewer", "planner", condition=should_revise_plan)
builder.add_edge("plan_reviewer", "supervisor", condition=should_proceed_to_supervisor)
```

## 주의사항

1. **S3 버킷 권한**: Runtime과 Client 모두 S3 읽기/쓰기 권한 필요
2. **타임아웃**: 너무 짧으면 사용자가 검토할 시간 부족, 너무 길면 대기 시간 증가
3. **동시성**: request_id로 구분하므로 여러 요청이 동시에 진행 가능
4. **정리**: 피드백 파일은 처리 후 삭제되어 S3 공간 절약

## 관련 파일

- `src/graph/nodes.py` - plan_reviewer_node, conditional functions
- `src/graph/builder.py` - graph 구성
- `src/utils/s3_utils.py` - S3 헬퍼 함수
- `02_invoke_agentcore_runtime_vpc.py` - 클라이언트 핸들러
- `.env.example` - 환경 변수 템플릿
- `production_deployment/scripts/phase3/01_extract_env_vars_from_cf.sh` - .env 생성 스크립트
