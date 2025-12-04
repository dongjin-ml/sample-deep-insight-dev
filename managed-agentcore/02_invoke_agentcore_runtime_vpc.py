#!/usr/bin/env python3
"""
invoke_agentcore_runtime_vpc.py

Purpose:
    Client script to test and invoke AgentCore Runtime deployed in VPC mode.

Usage:
    # Use environment variables or defaults
    python3 02_invoke_agentcore_runtime_vpc.py

    # Override with command-line arguments
    python3 02_invoke_agentcore_runtime_vpc.py --user_query "Analyze sales data" --data_directory "./my_data"

    # Mix CLI args and environment variables
    python3 02_invoke_agentcore_runtime_vpc.py --user_query "Custom query"

Configuration Priority:
    1. Command-line arguments (--user_query, --data_directory)
    2. Environment variables (USER_QUERY, DATA_DIRECTORY)
    3. Default values (hardcoded Korean prompt, "./data")

Features:
    - Invokes AgentCore Runtime
    - Processes streaming responses
    - Displays results in real-time
    - Flexible input via CLI arguments or environment variables

Execution Order:
    create_agentcore_runtime_vpc.py → agentcore_runtime.py (entrypoint) → invoke_agentcore_runtime_vpc.py (test)
"""

import json
import sys
import os
import argparse
from datetime import datetime
import textwrap
import traceback
from dotenv import load_dotenv

# Terminal color codes
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

# Path configuration
current_dir = os.path.dirname(os.path.abspath(__file__))
utils_dir = os.path.abspath(os.path.join(current_dir, '.'))
sys.path.insert(0, utils_dir)

import boto3
from botocore.config import Config
from src.utils.strands_sdk_utils import strands_utils

# ============================================================
# Command-Line Argument Parsing
# ============================================================

def parse_arguments():
    """Parse command-line arguments for user query and data directory"""
    parser = argparse.ArgumentParser(
        description="Invoke AgentCore Runtime with custom query and data directory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use environment variables or defaults
  python3 02_invoke_agentcore_runtime_vpc.py

  # Override user query
  python3 02_invoke_agentcore_runtime_vpc.py --user_query "Analyze sales data"

  # Override both query and directory
  python3 02_invoke_agentcore_runtime_vpc.py --user_query "Calculate revenue" --data_directory "./my_data"
        """
    )

    parser.add_argument(
        '--user_query',
        type=str,
        default=None,
        help='User query to send to AgentCore Runtime (overrides USER_QUERY env var)'
    )

    parser.add_argument(
        '--data_directory',
        type=str,
        default=None,
        help='Data directory path to upload (overrides DATA_DIRECTORY env var, default: ./data)'
    )

    return parser.parse_args()

# ============================================================
# Configuration Loading
# ============================================================

# Load .env file
env_file = os.path.join(current_dir, ".env")
if not os.path.exists(env_file):
    print(f"{RED}❌ .env file not found: {env_file}{NC}")
    print(f"{YELLOW}⚠️  Deploy Phase 1, 2, 3 first{NC}")
    print(f"{YELLOW}⚠️  Or run ./production_deployment/scripts/setup_env.sh{NC}")
    sys.exit(1)

load_dotenv(env_file, override=True)

# Parse command-line arguments
args = parse_arguments()

# Read configuration from environment variables
AGENT_ARN = os.getenv("RUNTIME_ARN")
REGION = os.getenv("AWS_REGION", "us-east-1")

# Validation
if not AGENT_ARN:
    print(f"{RED}❌ RUNTIME_ARN is not set{NC}")
    print(f"{YELLOW}⚠️  Run create_agentcore_runtime_vpc.py first{NC}")
    sys.exit(1)

# simple version for debugging
#DEFAULT_PROMPT = "데이터 디렉토리의 모든 CSV 파일을 분석하고 총 매출액을 계산해줘. 보고서는 만들지 마."
# simple version - bill expectation :$2.137 
# DEFAULT_PROMPT = "데이터 디렉토리의 모든 CSV 파일을 분석하고,이 Moon Market 데이터의 핵심 지표를 요약해줘" # Simple Version
# complex version
# User prompt with priority: CLI args > env var > default
#DEFAULT_PROMPT = "데이터 디렉토리의 모든 CSV 파일을 분석하고 총 매출액을 계산해줘. PDF 보고서는 만들지 마."
#DEFAULT_PROMPT = "데이터 디렉토리의 모든 CSV 파일을 분석하고 총 매출액을 계산해줘, 아주 자세히 분석해줘." 
#DEFAULT_PROMPT = "데이터 디렉토리의 모든 CSV 파일을 분석하고 이 Moon Market 데이터에서 비즈니스 성장 기회를 발굴해줘: 숨겨진 고객 패턴과 세그먼트를 발견하고, 수익 최적화 방안을 제시하며, 마케팅과 운영 효율성을 높일 수 있는 개선점을 찾고, 다음 달 매출을 크게 늘릴 수 있는 실행 가능한 전략 3가지를 우선순위와 기대 효과를 포함해서 제안해줘." 

DEFAULT_PROMPT = textwrap.dedent("""
                분석대상은 ‘./data/moon_market/kr/’ 디렉토리 입니다.
                moon-market-fresh-food-sales.csv 는 분석 파일이고,
                column_definitions.json은 컬럼에 대한 설명입니다.
                데이터에서 비즈니스 성장 기회를 발굴해줘: 
                숨겨진 고객 패턴과 세그먼트를 발견하고, 수익 최적화 방안을 제시하며, 
                마케팅과 운영 효율성을 높일 수 있는 개선점을 찾고, 
                다음 달 매출을 크게 늘릴 수 있는 실행 가능한 전략 3가지를 우선순위와 기대 효과를 포함해서 제안해줘.
            """).strip()

# DEFAULT_PROMPT = "데이터 디렉토리의 모든 CSV 파일을 로드하고 먼저 데이터 품질을 검증한 후, Moon Market의 비즈니스를 다각도로 분석해줘. 총 주문 건수, 매출액, 평균 주문 금액, 고객 수, 제품 수를 파악하고, RFM 분석을 통해 최근 구매일, 구매 빈도, 구매 금액을 기준으로 고객을 5-8개 세그먼트로 분류한 뒤 각 세그먼트의 특성, 규모, 매출 기여도, 이탈 위험도를 분석해줘. 성별과 연령대를 교차 분석하여 각 그룹의 구매 패턴, 선호 제품, 평균 주문 금액을 비교하고, 지역별로도 동일한 분석을 수행해서 각 세그먼트의 고객 생애 가치를 추정해줘. 일회성 구매 고객과 재구매 고객을 구분하고, 제품 카테고리 선호도로 클러스터링하며, 프로모션 반응도를 분석해서 행동 기반의 숨겨진 고객 세그먼트를 발굴해줘.제품별로 판매량, 매출액, 평균 주문 가치, 재구매율, 성장률을 계산하고 ABC 분석으로 상위 20% 제품이 전체 매출의 몇 퍼센트를 차지하는지 확인해줘. 장바구니 분석과 연관 규칙 마이닝을 통해 함께 구매되는 제품 조합을 찾아서 교차판매와 번들링 기회를 구체적으로 제시하고, 저성과 제품을 식별해서 개선 또는 단종 여부를 제안해줘. 일별, 주별, 월별 매출 추이를 분석하고 계절성 패턴과 요일별 주문 패턴을 파악하며, MoM과 WoW 성장률을 계산하고 매출이 급증하거나 급감한 시점과 그 원인을 찾아줘. 프로모션 코드별로 사용률, 매출 기여도, ROI를 추정하고, 프로모션 사용 고객과 미사용 고객의 구매 행동 차이를 분석해서 가장 효과적인 프로모션 타입과 타겟 고객을 식별해줘. 할인 없이도 구매할 가능성이 높은 고객을 찾아서 프로모션 의존도를 분석하고, 지역별로 매출 분포와 성장 잠재력을 평가하며, 배송지 우편번호를 기반으로 핫스팟을 찾아서 물류 효율성과 지역 맞춤형 재고 배치 전략을 제안해줘. 월별 신규 고객 코호트의 재구매율을 추적하고 코호트별 리텐션 곡선과 이탈 시점을 파악하며, 초기 구매 제품이 재구매율에 미치는 영향을 분석해줘. 사이즈와 수량별 가격 민감도를 분석하고, 더 큰 사이즈나 대량 구매를 유도할 수 있는 업셀링 기회를 찾으며, 고마진 제품과 저마진 제품의 믹스를 최적화해서 고객당 평균 주문 금액을 증대시킬 방안을 제시해줘. 시계열 모델로 다음 달 매출을 예측하고, 고객 이탈 위험을 예측하며, 제품별 수요를 예측하고, 고객별로 다음 구매 시기와 추천 제품을 도출해줘. 이 모든 분석을 바탕으로 다음 달 매출을 크게 늘릴 수 있는 실행 가능한 전략을 최소 5개 이상 제시하되, 각 전략마다 전략명과 한 줄 요약, 근거가 되는 데이터 인사이트를 구체적인 수치와 함께 제공하고, 타겟 고객이나 제품이나 채널을 명시하며, 3-5단계의 구체적인 실행 방법과 필요한 리소스 및 예산 규모를 추정해줘. 각 전략의 예상 매출 또는 수익 증대 효과를 퍼센트와 금액으로 제시하고, 성공을 측정할 KPI와 실행 난이도, 예상 소요 기간, 리스크 및 대응 방안을 포함해서 우선순위를 매겨줘. 핵심 인사이트를 보여주는 시각화 5-7개를 생성하고 경영진용 원페이지 요약 대시보드를 구성하며, 더 나은 분석을 위해 필요한 추가 데이터 항목과 데이터 품질 개선을 위한 수집 프로세스도 제안해줘. 모든 인사이트는 데이터에 근거한 구체적인 수치를 포함하고, 통계적 유의성을 확인하며, 샘플 사이즈가 작은 경우 명시하고, 실무에서 바로 적용 가능한 수준의 구체성을 유지하면서 단순 기술통계를 넘어 왜 그런 현상이 발생했는지와 무엇을 해야 하는지에 명확히 답해줘."

#DEFAULT_PROMPT = "데이터 디렉토리의 모든 CSV 파일을 분석하고 총 매출액을 계산해줘, 카테고리별 매출 비중도 함께 보여줘. 결과물을 docx로 만들어줘" 
PROMPT = args.user_query or os.getenv("USER_QUERY", DEFAULT_PROMPT)

# Data directory with priority: CLI args > env var > default
DATA_DIRECTORY = args.data_directory or os.getenv("DATA_DIRECTORY", "./data")


def parse_sse_data(sse_bytes):
    """Parse Server-Sent Events (SSE) data from streaming response"""
    if not sse_bytes or len(sse_bytes) == 0:
        return None

    try:
        text = sse_bytes.decode('utf-8').strip()
        if not text or text == '':
            return None

        if text.startswith('data: '):
            json_text = text[6:].strip()
            if json_text:
                return json.loads(json_text)
        else:
            return json.loads(text)

    except Exception as e:
        pass

    return None

def build_payload():
    """Build request payload with directory support"""
    return {
        "prompt": PROMPT,
        "data_directory": DATA_DIRECTORY  # Required for data upload
    }

def main():
    """Invoke AgentCore Runtime and process streaming response"""
    start_time = datetime.now()
    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{BLUE}🚀 AgentCore Runtime Job Started{NC}")
    print(f"{BLUE}📅 Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}{NC}")
    print(f"{BLUE}🎯 Agent ARN: {AGENT_ARN}{NC}")
    print(f"{BLUE}🌐 Region: {REGION}{NC}")
    print(f"{BLUE}{'='*60}{NC}\n")

    # Display input sources
    print(f"📝 Input Configuration:")
    if args.user_query:
        print(f"   💬 User Query: [CLI argument] {PROMPT}")
    elif os.getenv("USER_QUERY"):
        print(f"   💬 User Query: [Environment variable] {PROMPT}")
    else:
        print(f"   💬 User Query: [Default] {PROMPT}")

    if args.data_directory:
        print(f"   📂 Upload Directory: [CLI argument] {DATA_DIRECTORY}")
    elif os.getenv("DATA_DIRECTORY"):
        print(f"   📂 Upload Directory: [Environment variable] {DATA_DIRECTORY}")
    else:
        print(f"   📂 Upload Directory: [Default] {DATA_DIRECTORY}")
    print(f"   🎯 Analysis Target: (specified in prompt)")
    print()

    # Create boto3 client with extended timeouts
    my_config = Config(
        connect_timeout=6000,
        read_timeout=3600,  # 1 hour for long-running jobs
        retries={'max_attempts': 0}  # Disable retries to avoid duplicate requests
    )

    agentcore_client = boto3.client(
        'bedrock-agentcore',
        region_name=REGION,
        config=my_config,
    )

    # Invoke AgentCore Runtime
    print(f"📤 Sending request...")

    try:
        payload = build_payload()
        print(f"📦 Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}\n")

        boto3_response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            qualifier="DEFAULT",
            payload=json.dumps(payload)
        )

        # Process streaming response
        if "text/event-stream" in boto3_response.get("contentType", ""):
            print(f"📥 Receiving streaming response...\n")

            for event in boto3_response["response"].iter_lines(chunk_size=1):
                event_data = parse_sse_data(event)
                if event_data is None:
                    continue
                else:
                    strands_utils.process_event_for_display(event_data)

        end_time = datetime.now()
        elapsed_time = (end_time - start_time).total_seconds()

        print(f"\n{GREEN}{'='*60}{NC}")
        print(f"{GREEN}✅ AgentCore Runtime Job Completed{NC}")
        print(f"{GREEN}📅 End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}{NC}")
        print(f"{GREEN}⏱️  Total Duration: {elapsed_time:.2f}s ({elapsed_time/60:.2f}min){NC}")
        print(f"{GREEN}{'='*60}{NC}\n")

    except Exception as e:
        error_message = str(e)
        error_type = type(e).__name__

        # Get full traceback
        full_traceback = traceback.format_exc()

        # Print to terminal
        print(f"\n{RED}❌ Error occurred: {error_message}{NC}")
        print(f"{RED}📛 Error type: {error_type}{NC}")
        print(f"\nTraceback:")
        print(full_traceback)

        sys.exit(1)

if __name__ == "__main__":
    main()
