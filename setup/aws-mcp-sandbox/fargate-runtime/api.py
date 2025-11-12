#!/usr/bin/env python3
"""
AWS Fargate Runtime API Server
코드 실행을 위한 HTTP API 서버
"""

import json
import os
import subprocess
import sys
import time
import traceback
from io import StringIO
from flask import Flask, request, jsonify

app = Flask(__name__)

# 세션 상태 유지를 위한 전역 변수
python_globals = {'__builtins__': __builtins__}
python_locals = {}

# 설치된 패키지 추적
installed_packages = set()

@app.route('/health', methods=['GET'])
def health():
    """헬스체크 엔드포인트"""
    return jsonify({
        "status": "healthy",
        "timestamp": int(time.time()),
        "python_version": sys.version,
        "installed_packages": list(installed_packages)
    })

@app.route('/execute', methods=['POST'])
def execute():
    """코드 실행 엔드포인트"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        code = data.get('code', '').strip()
        exec_type = data.get('type', 'python')
        timeout = data.get('timeout', 300)  # 기본 5분
        
        if not code:
            return jsonify({"error": "No code provided"}), 400
        
        if exec_type == 'python':
            return execute_python(code, timeout)
        elif exec_type == 'bash':
            return execute_bash(code, timeout)
        else:
            return jsonify({"error": f"Unsupported execution type: {exec_type}"}), 400
            
    except Exception as e:
        return jsonify({
            "error": f"Request processing error: {str(e)}",
            "status": "error"
        }), 500

def execute_python(code, timeout):
    """Python 코드 실행"""
    global python_globals, python_locals
    
    # stdout, stderr 캡처
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    captured_stdout = StringIO()
    captured_stderr = StringIO()
    
    sys.stdout = captured_stdout
    sys.stderr = captured_stderr
    
    start_time = time.time()
    
    try:
        # uv add 명령어 처리 - 안전한 패키지 설치 (권장)
        if code.strip().startswith('!uv add') or code.strip().startswith('uv add'):
            clean_code = code.strip()
            if clean_code.startswith('!'):
                clean_code = clean_code[1:]
            
            # 입력 검증: uv add 명령어만 허용
            cmd_parts = clean_code.split()
            if len(cmd_parts) < 3 or cmd_parts[0] != 'uv' or cmd_parts[1] != 'add':
                return jsonify({
                    "output": "Error: Only 'uv add' commands are allowed",
                    "status": "error",
                    "execution_time": time.time() - start_time
                })
            
            # 위험한 패키지 차단
            dangerous_packages = ['os', 'subprocess', 'sys', 'importlib', '__import__']
            package_name = cmd_parts[2].split('==')[0].split('>=')[0].split('<=')[0]
            if any(dangerous in package_name.lower() for dangerous in dangerous_packages):
                return jsonify({
                    "output": f"Error: Package '{package_name}' is not allowed for security reasons",
                    "status": "error",
                    "execution_time": time.time() - start_time
                })
            
            # 안전한 uv add 실행
            result = subprocess.run(
                ['uv', 'add'] + cmd_parts[2:],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            output = result.stdout + result.stderr
            
            return jsonify({
                "output": output,
                "status": "success" if result.returncode == 0 else "error",
                "execution_time": time.time() - start_time,
                "return_code": result.returncode
            })

        # pip install 명령어 처리 - uv 사용 권장 안내
        if code.strip().startswith('!pip install') or code.strip().startswith('pip install'):
            return jsonify({
                "output": "Note: This environment uses uv for package management. Please use 'uv add <package>' for better dependency management, or pip install will work but is not recommended.",
                "status": "info",
                "execution_time": time.time() - start_time
            })
        if code.strip().startswith('!pip install') or code.strip().startswith('pip install'):
            clean_code = code.strip()
            if clean_code.startswith('!'):
                clean_code = clean_code[1:]
            
            # 입력 검증: pip install 명령어만 허용
            cmd_parts = clean_code.split()
            if len(cmd_parts) < 3 or cmd_parts[0] != 'pip' or cmd_parts[1] != 'install':
                return jsonify({
                    "output": "Error: Only 'pip install' commands are allowed",
                    "status": "error",
                    "execution_time": time.time() - start_time
                })
            
            # 위험한 패키지 차단
            dangerous_packages = ['os', 'subprocess', 'sys', 'importlib', '__import__']
            package_name = cmd_parts[2].split('==')[0].split('>=')[0].split('<=')[0]
            if any(dangerous in package_name.lower() for dangerous in dangerous_packages):
                return jsonify({
                    "output": f"Error: Package '{package_name}' is not allowed for security reasons",
                    "status": "error",
                    "execution_time": time.time() - start_time
                })
            
            # 안전한 pip install 실행
            result = subprocess.run(
                ['pip', 'install'] + cmd_parts[2:],
                capture_output=True,
                text=True,
                timeout=timeout
            )
                package_name = extract_package_name(clean_code)
                if package_name:
                    installed_packages.add(package_name)
            
            return jsonify({
                "output": output,
                "status": "success" if result.returncode == 0 else "error",
                "execution_time": time.time() - start_time,
                "return_code": result.returncode
            })
        
        # apt 명령어 처리 - 보안상 비활성화
        elif code.strip().startswith('!apt') or code.strip().startswith('apt'):
            return jsonify({
                "output": "apt commands are disabled for security reasons",
                "status": "error",
                "execution_time": time.time() - start_time
            })
            
            return jsonify({
                "output": output,
                "status": "success" if result.returncode == 0 else "error",
                "execution_time": time.time() - start_time,
                "return_code": result.returncode
            })
        
        # 일반 Python 코드 실행
        else:
            # exec 사용 제거 - 보안상 Python 코드 실행 비활성화
            return jsonify({
                "output": "Python code execution is disabled for security reasons. Please use pip install or bash commands only.",
                "status": "error",
                "execution_time": time.time() - start_time
            })
            
            output = captured_stdout.getvalue()
            error_output = captured_stderr.getvalue()
            
            if error_output:
                output += "\n" + error_output
            
            return jsonify({
                "output": output,
                "status": "success",
                "execution_time": time.time() - start_time
            })
            
    except subprocess.TimeoutExpired:
        return jsonify({
            "output": f"Code execution timed out after {timeout} seconds",
            "status": "timeout",
            "execution_time": time.time() - start_time
        })
    except Exception as e:
        error_msg = traceback.format_exc()
        return jsonify({
            "output": error_msg,
            "status": "error",
            "execution_time": time.time() - start_time,
            "error_type": type(e).__name__
        })
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

def execute_bash(command, timeout):
    """Bash 명령어 실행 - 보안상 비활성화"""
    return jsonify({
        "output": "Bash command execution is disabled for security reasons",
        "status": "error",
        "execution_time": 0
    })

def extract_package_name(install_command):
    """pip install 명령에서 패키지명 추출"""
    try:
        parts = install_command.split()
        if 'install' in parts:
            install_idx = parts.index('install')
            if install_idx + 1 < len(parts):
                package = parts[install_idx + 1]
                # 버전 제거 (예: pandas==1.5.0 -> pandas)
                return package.split('==')[0].split('>=')[0].split('<=')[0]
    except:
        pass
    return None

@app.route('/status', methods=['GET'])
def status():
    """현재 세션 상태 조회"""
    return jsonify({
        "python_globals_keys": list(python_globals.keys()),
        "python_locals_keys": list(python_locals.keys()),
        "installed_packages": list(installed_packages),
        "working_directory": os.getcwd(),
        "environment_variables": dict(os.environ)
    })

@app.route('/session', methods=['POST'])
def session():
    """세션 관리 엔드포인트"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        action = data.get('action')
        
        if action == 'get_or_create':
            # 세션 생성/조회 로직
            return jsonify({
                'status': 'success',
                'session_id': session_id,
                'message': f'Session {session_id} is ready',
                'endpoint': request.url_root,
                'container_id': os.environ.get('HOSTNAME', 'unknown'),
                'timestamp': int(time.time())
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Unknown action: {action}'
            }), 400
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/reset', methods=['POST'])
def reset_session():
    """세션 상태 초기화"""
    global python_globals, python_locals, installed_packages
    
    python_globals = {'__builtins__': __builtins__}
    python_locals = {}
    installed_packages = set()
    
    return jsonify({
        "status": "success",
        "message": "Session reset completed"
    })

if __name__ == '__main__':
    print(f"Starting Fargate Runtime API Server...")
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    
    app.run(
        host='0.0.0.0',
        port=8080,
        debug=False,
        threaded=True
    )