"""접속 설정을 환경변수와 .env 파일에서 읽어 온다.

우선순위는 실제 환경변수 > .env 파일이다. 비밀번호는 절대 저장소에
커밋되지 않도록 .env 는 .gitignore 에 들어 있다.
"""

import os
from pathlib import Path

from .errors import NasError

# 저장소 루트 (이 파일 기준 한 단계 위)
REPO_ROOT = Path(__file__).resolve().parent.parent

_TRUE = {"1", "true", "yes", "on", "y"}
_FALSE = {"0", "false", "no", "off", "n"}


def _parse_env_file(path):
    """아주 단순한 KEY=VALUE 파서. 따옴표와 # 주석만 처리한다."""
    values = {}
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return values
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def _bool(value, default):
    if value is None or value == "":
        return default
    lowered = str(value).strip().lower()
    if lowered in _TRUE:
        return True
    if lowered in _FALSE:
        return False
    raise NasError(f"불리언 값으로 해석할 수 없습니다: {value!r}")


class Config:
    """NAS 접속에 필요한 값 묶음."""

    def __init__(self, url, user, password, otp=None, base_path="/home/work",
                 verify_ssl=True, timeout=60):
        self.url = url.rstrip("/")
        self.user = user
        self.password = password
        self.otp = otp or None
        self.base_path = "/" + base_path.strip("/")
        self.verify_ssl = verify_ssl
        self.timeout = timeout

    def __repr__(self):  # 비밀번호는 절대 노출하지 않는다.
        return (f"Config(url={self.url!r}, user={self.user!r}, "
                f"base_path={self.base_path!r}, verify_ssl={self.verify_ssl})")


def load(env_file=None):
    """환경변수 + .env 를 합쳐 Config 를 만든다."""
    env_path = Path(env_file) if env_file else REPO_ROOT / ".env"
    file_values = _parse_env_file(env_path)

    def get(name, default=None):
        value = os.environ.get(name)
        if value is None or value == "":
            value = file_values.get(name)
        if value is None or value == "":
            return default
        return value

    url = get("SYNOLOGY_URL")
    user = get("SYNOLOGY_USER")
    password = get("SYNOLOGY_PASS")

    missing = [name for name, value in
               (("SYNOLOGY_URL", url), ("SYNOLOGY_USER", user), ("SYNOLOGY_PASS", password))
               if not value]
    if missing:
        raise NasError(
            "필수 설정이 비어 있습니다: " + ", ".join(missing) + "\n"
            f"  .env.example 을 {env_path} 로 복사한 뒤 값을 채우거나, "
            "같은 이름의 환경변수를 설정하세요."
        )

    timeout_raw = get("SYNOLOGY_TIMEOUT", "60")
    try:
        timeout = int(timeout_raw)
    except (TypeError, ValueError):
        raise NasError(f"SYNOLOGY_TIMEOUT 은 정수여야 합니다: {timeout_raw!r}")

    return Config(
        url=url,
        user=user,
        password=password,
        otp=get("SYNOLOGY_OTP"),
        base_path=get("NAS_BASE_PATH", "/home/work"),
        verify_ssl=_bool(get("SYNOLOGY_VERIFY_SSL"), True),
        timeout=timeout,
    )
