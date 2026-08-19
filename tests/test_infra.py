"""인프라 설정 파일이 의도한 성질을 지키는지 검증한다.

컨테이너를 실제로 띄우지 않고도 확인할 수 있는 것들이다.
- compose 파일이 문법적으로 유효한가
- 데이터베이스가 실수로 외부에 노출되지 않는가
- 데이터 망이 정말 격리되어 있는가
- Caddy 설정이 두 모드 모두에서 유효한가
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INFRA = REPO / "infra"

# 검증용 더미 값. 실제 비밀번호가 아니다.
TEST_ENV = {
    "DOCKER_ROOT": "./data",
    "POSTGRES_PASSWORD": "test-password-1234",
    "REDIS_PASSWORD": "test-password-1234",
    "TS_AUTHKEY": "tskey-test",
}


def _docker_compose_available():
    if not shutil.which("docker"):
        return False
    result = subprocess.run(["docker", "compose", "version"],
                            capture_output=True, text=True)
    return result.returncode == 0


def _caddy_available():
    return shutil.which("caddy") is not None


@unittest.skipUnless(_docker_compose_available(), "docker compose 없음")
class TestComposeConfig(unittest.TestCase):
    """docker compose 파서로 실제 검증한다."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        env_file = Path(cls._tmp.name) / ".env"
        base = (INFRA / ".env.example").read_text(encoding="utf-8")
        lines = []
        for line in base.splitlines():
            key = line.split("=", 1)[0].strip()
            if key in TEST_ENV:
                lines.append(f"{key}={TEST_ENV[key]}")
            else:
                lines.append(line)
        env_file.write_text("\n".join(lines), encoding="utf-8")
        cls.env_file = env_file
        cls.config = cls._resolve(["--profile", "full"])

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    @classmethod
    def _run(cls, args, check=True):
        return subprocess.run(
            ["docker", "compose", "-f", str(INFRA / "docker-compose.yml"),
             "--env-file", str(cls.env_file), *args],
            capture_output=True, text=True, check=check, cwd=INFRA,
        )

    @classmethod
    def _resolve(cls, profiles):
        out = cls._run([*profiles, "config", "--format", "json"]).stdout
        return json.loads(out)

    def test_compose_file_is_valid(self):
        self.assertIn("services", self.config)
        self.assertEqual(self.config.get("name"), "wonee9-infra")

    def test_default_profile_starts_only_the_entry_point(self):
        services = self._run(["config", "--services"]).stdout.split()
        self.assertEqual(services, ["caddy"])

    def test_full_profile_includes_every_service(self):
        services = set(self._run(["--profile", "full", "config", "--services"]).stdout.split())
        self.assertEqual(
            services,
            {"caddy", "postgres", "redis", "uptime-kuma", "dozzle", "tailscale"},
        )

    def test_only_caddy_publishes_ports(self):
        publishing = {
            name for name, service in self.config["services"].items()
            if service.get("ports")
        }
        self.assertEqual(publishing, {"caddy"},
                         "Caddy 외의 서비스가 외부에 포트를 열고 있습니다")

    def test_databases_are_not_on_the_edge_network(self):
        for name in ("postgres", "redis"):
            networks = set((self.config["services"][name].get("networks") or {}))
            self.assertEqual(networks, {"data"},
                             f"{name} 이 데이터 망 밖에 붙어 있습니다: {networks}")

    def test_data_network_is_internal(self):
        self.assertTrue(self.config["networks"]["data"].get("internal"),
                        "data 망이 internal 이 아니어서 외부로 나갈 수 있습니다")

    def test_every_service_restarts_and_caps_its_logs(self):
        for name, service in self.config["services"].items():
            self.assertEqual(service.get("restart"), "unless-stopped", name)
            options = (service.get("logging") or {}).get("options") or {}
            self.assertIn("max-size", options, f"{name} 로그 크기 제한 없음")

    def test_docker_socket_is_mounted_read_only(self):
        for name, service in self.config["services"].items():
            for volume in service.get("volumes") or []:
                if volume.get("source") == "/var/run/docker.sock":
                    self.assertTrue(volume.get("read_only"),
                                    f"{name} 이 도커 소켓을 쓰기 가능하게 붙였습니다")

    def test_unused_profiles_do_not_block_startup(self):
        """쓰지 않는 프로필의 빈 값이 스택 전체를 막으면 안 된다.

        compose 는 프로필과 무관하게 파일 전체를 해석하므로, 비밀번호에
        ${VAR:?} 를 걸면 Tailscale 을 쓰지 않는 사람도 TS_AUTHKEY 를 채워야
        'caddy 만 띄우기' 가 되어 버린다.
        """
        env = os.environ.copy()
        for key in ("POSTGRES_PASSWORD", "REDIS_PASSWORD", "TS_AUTHKEY"):
            env.pop(key, None)
        for profiles in ([], ["--profile", "monitor"], ["--profile", "full"]):
            with self.subTest(profiles=profiles or ["(기본)"]):
                result = subprocess.run(
                    ["docker", "compose", "-f", str(INFRA / "docker-compose.yml"),
                     *profiles, "config"],
                    capture_output=True, text=True, env=env, cwd=INFRA,
                )
                self.assertEqual(result.returncode, 0, result.stderr)


class TestProfileValidation(unittest.TestCase):
    """./infra 가 요청된 프로필에 필요한 값만 요구하는지 확인한다."""

    def _check(self, profiles, **values):
        """require_profile_vars 를 셸에서 직접 호출한다."""
        assignments = "".join(f'{key}={value}; ' for key, value in values.items())
        script = (
            "INFRA_LIB_ONLY=1 source ./infra\n"
            f"{assignments}\n"
            f"require_profile_vars {' '.join(profiles)}\n"
        )
        env = os.environ.copy()
        for key in ("POSTGRES_PASSWORD", "REDIS_PASSWORD", "TS_AUTHKEY"):
            env.pop(key, None)
        return subprocess.run(["bash", "-c", script.replace("\\n", "\n")],
                              capture_output=True, text=True, cwd=INFRA, env=env)

    def test_entry_point_only_needs_nothing(self):
        self.assertEqual(self._check([]).returncode, 0)

    def test_monitor_profile_needs_nothing(self):
        self.assertEqual(self._check(["monitor"]).returncode, 0)

    def test_data_profile_requires_passwords(self):
        result = self._check(["data"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("POSTGRES_PASSWORD", result.stderr)
        self.assertIn("REDIS_PASSWORD", result.stderr)

    def test_data_profile_accepts_strong_passwords(self):
        result = self._check(["data"], POSTGRES_PASSWORD="abcdefghijkl",
                             REDIS_PASSWORD="abcdefghijkl")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_short_passwords_are_rejected(self):
        result = self._check(["data"], POSTGRES_PASSWORD="short",
                             REDIS_PASSWORD="short")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("짧습니다", result.stderr)

    def test_remote_profile_requires_auth_key(self):
        result = self._check(["remote"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("TS_AUTHKEY", result.stderr)

    def test_remote_profile_accepts_auth_key(self):
        self.assertEqual(self._check(["remote"], TS_AUTHKEY="tskey-x").returncode, 0)

    def test_full_profile_requires_everything(self):
        result = self._check(["full"])
        self.assertNotEqual(result.returncode, 0)
        for name in ("POSTGRES_PASSWORD", "REDIS_PASSWORD", "TS_AUTHKEY"):
            self.assertIn(name, result.stderr)


@unittest.skipUnless(_caddy_available(), "caddy 바이너리 없음")
class TestCaddyConfig(unittest.TestCase):
    """Caddy 설정이 두 운영 모드 모두에서 유효한지 확인한다."""

    def _validate(self, **env_overrides):
        env = os.environ.copy()
        env.update(env_overrides)
        return subprocess.run(
            ["caddy", "validate", "--config", str(INFRA / "caddy" / "Caddyfile"),
             "--adapter", "caddyfile"],
            capture_output=True, text=True, env=env,
        )

    def test_internal_http_mode_is_valid(self):
        result = self._validate(SITE_SCHEME="http", BASE_DOMAIN="nas.local")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_public_https_mode_is_valid(self):
        result = self._validate(SITE_SCHEME="https", BASE_DOMAIN="nas.example.com",
                                ACME_EMAIL="me@example.com")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_health_endpoint_is_not_host_bound(self):
        """헬스체크는 호스트 이름을 요구하지 않는 별도 포트를 써야 한다.

        호스트 기반 사이트로 헬스체크를 하면, Host 헤더가 맞지 않는 요청에
        Caddy 가 빈 200 을 돌려주므로 설정이 깨져도 통과해 버린다.
        """
        text = (INFRA / "caddy" / "Caddyfile").read_text(encoding="utf-8")
        self.assertIn(":2020 {", text)
        self.assertIn('respond /healthz "ok" 200', text)


class TestInfraFiles(unittest.TestCase):
    """실행 권한과 자격 증명 보호 같은 기본 사항."""

    def test_scripts_are_executable(self):
        for name in ("infra", "scripts/bootstrap.sh", "scripts/backup.sh",
                     "scripts/restore.sh"):
            path = INFRA / name
            self.assertTrue(path.exists(), f"{name} 없음")
            self.assertTrue(os.access(path, os.X_OK), f"{name} 실행 권한 없음")

    def test_env_file_is_ignored_by_git(self):
        ignored = (REPO / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("infra/.env", ignored)

    def test_env_example_has_no_real_secrets(self):
        """예시 파일의 비밀번호 항목은 비어 있어야 한다."""
        for line in (INFRA / ".env.example").read_text(encoding="utf-8").splitlines():
            for key in ("POSTGRES_PASSWORD", "REDIS_PASSWORD", "TS_AUTHKEY"):
                if line.startswith(f"{key}="):
                    self.assertEqual(line, f"{key}=",
                                     f"{key} 에 값이 채워져 있습니다")

    def test_no_env_file_is_committed(self):
        result = subprocess.run(["git", "ls-files", "infra/.env"],
                                capture_output=True, text=True, cwd=REPO)
        self.assertEqual(result.stdout.strip(), "", ".env 가 저장소에 추적되고 있습니다")


if __name__ == "__main__":
    unittest.main()
