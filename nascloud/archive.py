"""작업 폴더를 tar.gz 스냅샷으로 묶고 되돌리는 기능.

'모든 작업을 NAS 에 저장하고 다시 추출한다'는 흐름의 핵심이다.
스냅샷 하나가 곧 특정 시점의 작업 전체이므로, 이름에 타임스탬프를 넣어
언제든 그 시점으로 되돌릴 수 있게 한다.
"""

import fnmatch
import re
import tarfile
import time
from pathlib import Path

from .errors import NasError

# 용량만 차지하고 재생성 가능한 것들은 기본으로 뺀다.
DEFAULT_EXCLUDES = [
    ".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "dist", "build", ".next", ".nuxt",
    "*.pyc", "*.pyo", "*.log", ".DS_Store", ".env", ".nascloud",
]

SNAPSHOT_SUFFIX = ".tar.gz"
_STAMP = re.compile(r"(\d{8}-\d{6})")


def load_excludes(root):
    """기본 제외 목록에 .nasignore 파일의 내용을 더한다."""
    patterns = list(DEFAULT_EXCLUDES)
    ignore_file = Path(root) / ".nasignore"
    if ignore_file.is_file():
        for line in ignore_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    return patterns


def is_excluded(relative_path, patterns):
    """경로의 어느 한 조각이라도 패턴에 걸리면 제외한다."""
    parts = Path(relative_path).parts
    for pattern in patterns:
        if fnmatch.fnmatch(relative_path, pattern):
            return True
        if any(fnmatch.fnmatch(part, pattern) for part in parts):
            return True
    return False


def timestamp(now=None):
    return time.strftime("%Y%m%d-%H%M%S", time.localtime(now))


def snapshot_name(project, now=None):
    return f"{project}-{timestamp(now)}{SNAPSHOT_SUFFIX}"


def parse_stamp(name):
    """스냅샷 파일 이름에서 타임스탬프를 뽑는다. 없으면 빈 문자열."""
    match = _STAMP.search(name or "")
    return match.group(1) if match else ""


def create(source_dir, output_path, patterns=None, on_add=None):
    """source_dir 을 tar.gz 로 묶는다. 담긴 파일 수를 돌려준다."""
    source_dir = Path(source_dir).resolve()
    if not source_dir.is_dir():
        raise NasError(f"묶을 폴더가 없습니다: {source_dir}")
    patterns = patterns if patterns is not None else load_excludes(source_dir)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with tarfile.open(output_path, "w:gz") as tar:
        for path in sorted(source_dir.rglob("*")):
            relative = path.relative_to(source_dir).as_posix()
            if is_excluded(relative, patterns):
                continue
            if path.is_symlink() or path.is_file():
                tar.add(path, arcname=relative, recursive=False)
                count += 1
                if on_add:
                    on_add(relative)
    if count == 0:
        raise NasError(
            f"{source_dir} 안에 담을 파일이 없습니다 (제외 규칙에 모두 걸렸을 수 있습니다)."
        )
    return count


def _within(destination, candidate):
    root = destination.resolve()
    resolved = (destination / candidate).resolve()
    return resolved == root or root in resolved.parents


def _is_safe(member, destination):
    """tar 안의 경로가 대상 폴더를 벗어나지 않는지 확인한다.

    파일 이름뿐 아니라 링크가 가리키는 곳까지 본다. 밖을 가리키는 심볼릭
    링크를 먼저 풀어 두면 그 뒤에 오는 파일이 링크를 따라 대상 폴더 밖에
    쓰일 수 있기 때문이다.
    """
    if member.name.startswith("/") or ".." in Path(member.name).parts:
        return False
    if not _within(destination, member.name):
        return False
    if member.issym() or member.islnk():
        target = member.linkname
        if target.startswith("/"):
            return False
        # 심볼릭 링크는 자신이 놓인 폴더 기준, 하드 링크는 아카이브 루트 기준이다.
        anchor = Path(member.name).parent if member.issym() else Path(".")
        return _within(destination, (anchor / target).as_posix())
    return True


def extract(archive_path, destination, on_extract=None):
    """tar.gz 를 destination 에 푼다. 경로 탈출 시도는 걸러낸다."""
    archive_path = Path(archive_path)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)

    count = 0
    with tarfile.open(archive_path, "r:gz") as tar:
        for member in tar.getmembers():
            if not _is_safe(member, destination):
                raise NasError(
                    f"안전하지 않은 경로가 들어 있어 중단했습니다: {member.name}"
                )
            if member.isdev():
                continue
            tar.extract(member, destination)
            count += 1
            if on_extract:
                on_extract(member.name)
    return count
