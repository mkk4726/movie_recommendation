import subprocess
from pathlib import Path


def test_ruff_lint():
    """Run ruff check to verify code quality."""
    # 프로젝트 루트 디렉토리 찾기
    project_root = Path(__file__).parent.parent

    # ruff check 실행
    result = subprocess.run(["ruff", "check", "."], cwd=project_root, capture_output=True, text=True)

    # 실패 시 에러 메시지 출력
    if result.returncode != 0:
        print("\n" + "=" * 40)
        print("Ruff Linting Failures:")
        print("=" * 40)
        print(result.stdout)
        print(result.stderr)

    assert result.returncode == 0, "Ruff linting failed. See output above for details."


def test_ruff_format():
    """Run ruff format --check to verify code formatting."""
    # 프로젝트 루트 디렉토리 찾기
    project_root = Path(__file__).parent.parent

    # ruff format --check 실행
    result = subprocess.run(["ruff", "format", "--check", "."], cwd=project_root, capture_output=True, text=True)

    if result.returncode != 0:
        print("\n" + "=" * 40)
        print("Ruff Formatting Issues:")
        print("=" * 40)
        print(result.stdout)
        print(result.stderr)
        print("Run 'uv run ruff format .' to fix formatting issues.")

    assert result.returncode == 0, "Code is not formatted correctly. Run 'uv run ruff format .'"
