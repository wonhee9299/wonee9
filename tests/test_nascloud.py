"""가짜 DSM 서버를 상대로 저장/추출 전체 흐름을 검증한다."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nascloud import archive, cli  # noqa: E402
from nascloud.client import NasClient  # noqa: E402
from nascloud.config import Config  # noqa: E402
from nascloud.errors import NasAuthError, NasError  # noqa: E402
from tests.dsm_stub import ACCOUNT, OTP, PASSWORD, DsmStub  # noqa: E402

BASE = "/home/work"


class NasTestCase(unittest.TestCase):
    """가짜 NAS 와 임시 로컬 폴더를 준비하는 공통 베이스."""

    require_otp = False

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.nas_root = self.tmp / "nas"
        (self.nas_root / BASE.lstrip("/")).mkdir(parents=True)
        self.local = self.tmp / "local"
        self.local.mkdir()

        self.stub = DsmStub(self.nas_root, require_otp=self.require_otp)
        self.stub.__enter__()
        self.addCleanup(self.stub.__exit__, None, None, None)
        self.addCleanup(self._tmp.cleanup)

    def config(self, **overrides):
        params = dict(
            url=self.stub.url, user=ACCOUNT, password=PASSWORD,
            base_path=BASE, verify_ssl=True, timeout=10,
        )
        params.update(overrides)
        return Config(**params)

    def client(self):
        client = NasClient(self.config())
        client.login()
        self.addCleanup(client.logout)
        return client

    def nas_file(self, relative):
        return self.nas_root / BASE.lstrip("/") / relative


class TestAuth(NasTestCase):
    def test_login_succeeds_and_discovers_api_paths(self):
        client = self.client()
        self.assertEqual(client._paths["SYNO.FileStation.List"], "entry.cgi")
        self.assertEqual(client._paths["SYNO.API.Auth"], "auth.cgi")

    def test_wrong_password_raises_auth_error(self):
        client = NasClient(self.config(password="nope"))
        with self.assertRaises(NasAuthError) as ctx:
            client.login()
        self.assertIn("400", str(ctx.exception))
        self.assertIn("비밀번호", str(ctx.exception))

    def test_unreachable_host_gives_actionable_message(self):
        client = NasClient(self.config(url="http://127.0.0.1:1"))
        with self.assertRaises(NasError) as ctx:
            client.login()
        self.assertIn("연결할 수 없습니다", str(ctx.exception))


class TestTwoFactor(NasTestCase):
    require_otp = True

    def test_missing_otp_is_reported_clearly(self):
        client = NasClient(self.config())
        with self.assertRaises(NasAuthError) as ctx:
            client.login()
        self.assertIn("SYNOLOGY_OTP", str(ctx.exception))

    def test_otp_login_succeeds(self):
        client = NasClient(self.config(otp=OTP))
        client.login()
        self.addCleanup(client.logout)
        self.assertTrue(client.list_dir("") == [])


class TestPathResolution(NasTestCase):
    def test_relative_path_is_joined_to_base(self):
        client = NasClient(self.config())
        self.assertEqual(client.resolve("code"), f"{BASE}/code")
        self.assertEqual(client.resolve(""), BASE)

    def test_absolute_path_is_left_alone(self):
        client = NasClient(self.config())
        self.assertEqual(client.resolve("/volume1/other"), "/volume1/other")

    def test_windows_separators_are_normalised(self):
        client = NasClient(self.config())
        self.assertEqual(client.resolve("a\\b"), f"{BASE}/a/b")


class TestFileOperations(NasTestCase):
    def test_upload_then_download_preserves_bytes(self):
        source = self.local / "report.bin"
        payload = os.urandom(300_000)  # 청크 경계를 넘는 크기
        source.write_bytes(payload)

        client = self.client()
        remote = client.upload(source, "docs")
        self.assertEqual(remote, f"{BASE}/docs/report.bin")
        self.assertEqual(self.nas_file("docs/report.bin").read_bytes(), payload)

        back = self.local / "back.bin"
        client.download(remote, back)
        self.assertEqual(back.read_bytes(), payload)

    def test_upload_sends_file_part_last(self):
        source = self.local / "a.txt"
        source.write_text("hello")
        self.client().upload(source, "docs")
        record = self.stub.uploads[-1]
        self.assertEqual(record["filename"], "a.txt")
        self.assertEqual(record["fields"]["method"], "upload")
        self.assertEqual(record["fields"]["path"], f"{BASE}/docs")

    def test_upload_without_overwrite_fails_on_existing_file(self):
        source = self.local / "a.txt"
        source.write_text("hello")
        client = self.client()
        client.upload(source, "docs")
        with self.assertRaises(NasError):
            client.upload(source, "docs", overwrite=False)

    def test_makedirs_is_idempotent(self):
        client = self.client()
        client.makedirs("deep/nested")
        client.makedirs("deep/nested")
        self.assertTrue(self.nas_file("deep/nested").is_dir())

    def test_exists_reports_missing_and_present(self):
        client = self.client()
        self.assertFalse(client.exists("nope.txt"))
        source = self.local / "yes.txt"
        source.write_text("x")
        client.upload(source, "")
        self.assertTrue(client.exists("yes.txt"))

    def test_download_missing_file_raises(self):
        client = self.client()
        with self.assertRaises(NasError):
            client.download("missing.txt", self.local / "out.txt")

    def test_tree_round_trip_keeps_structure(self):
        tree = self.local / "project"
        (tree / "src" / "deep").mkdir(parents=True)
        (tree / "README.md").write_text("readme")
        (tree / "src" / "main.py").write_text("print(1)")
        (tree / "src" / "deep" / "util.py").write_text("x = 2")

        client = self.client()
        uploaded = client.upload_tree(tree, "project")
        self.assertEqual(uploaded, 3)

        restored = self.local / "restored"
        count = client.download_tree("project", restored)
        self.assertEqual(count, 3)
        self.assertEqual((restored / "README.md").read_text(), "readme")
        self.assertEqual((restored / "src" / "deep" / "util.py").read_text(), "x = 2")

    def test_upload_tree_handles_dot_suffixed_directory(self):
        tree = self.local / "proj"
        (tree / "v1.").mkdir(parents=True)
        (tree / "v1." / "a.txt").write_text("a")

        client = self.client()
        client.upload_tree(tree, "proj")
        self.assertEqual(self.nas_file("proj/v1./a.txt").read_text(), "a")

    def test_list_dir_marks_directories_and_sizes(self):
        client = self.client()
        source = self.local / "f.txt"
        source.write_text("12345")
        client.upload(source, "")
        client.makedirs("sub")
        entries = {e["name"]: e for e in client.list_dir("")}
        self.assertTrue(entries["sub"]["is_dir"])
        self.assertFalse(entries["f.txt"]["is_dir"])
        self.assertEqual(entries["f.txt"]["size"], 5)


class TestArchive(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_default_excludes_skip_generated_dirs(self):
        work = self.tmp / "work"
        (work / ".git").mkdir(parents=True)
        (work / "node_modules" / "pkg").mkdir(parents=True)
        (work / ".git" / "HEAD").write_text("ref")
        (work / "node_modules" / "pkg" / "index.js").write_text("x")
        (work / "keep.txt").write_text("keep")

        out = self.tmp / "snap.tar.gz"
        count = archive.create(work, out)
        self.assertEqual(count, 1)

        restored = self.tmp / "restored"
        archive.extract(out, restored)
        self.assertTrue((restored / "keep.txt").is_file())
        self.assertFalse((restored / ".git").exists())

    def test_nasignore_adds_patterns(self):
        work = self.tmp / "work"
        work.mkdir()
        (work / "keep.txt").write_text("keep")
        (work / "secret.key").write_text("nope")
        (work / ".nasignore").write_text("# 주석\n*.key\n")
        patterns = archive.load_excludes(work)
        self.assertIn("*.key", patterns)
        self.assertTrue(archive.is_excluded("secret.key", patterns))
        self.assertFalse(archive.is_excluded("keep.txt", patterns))

    def test_empty_selection_raises_instead_of_silent_empty_archive(self):
        work = self.tmp / "work"
        (work / "__pycache__").mkdir(parents=True)
        (work / "__pycache__" / "a.pyc").write_text("x")
        with self.assertRaises(NasError):
            archive.create(work, self.tmp / "snap.tar.gz")

    def test_extract_rejects_path_traversal(self):
        import tarfile
        evil = self.tmp / "evil.tar.gz"
        payload = self.tmp / "payload.txt"
        payload.write_text("pwned")
        with tarfile.open(evil, "w:gz") as tar:
            tar.add(payload, arcname="../escaped.txt")
        with self.assertRaises(NasError) as ctx:
            archive.extract(evil, self.tmp / "dest")
        self.assertIn("안전하지 않은 경로", str(ctx.exception))

    def test_extract_rejects_symlink_escaping_destination(self):
        import tarfile
        evil = self.tmp / "evil.tar.gz"
        with tarfile.open(evil, "w:gz") as tar:
            link = tarfile.TarInfo("escape")
            link.type = tarfile.SYMTYPE
            link.linkname = "../../etc"
            tar.addfile(link)
        with self.assertRaises(NasError):
            archive.extract(evil, self.tmp / "dest")

    def test_extract_rejects_absolute_symlink(self):
        import tarfile
        evil = self.tmp / "abs.tar.gz"
        with tarfile.open(evil, "w:gz") as tar:
            link = tarfile.TarInfo("escape")
            link.type = tarfile.SYMTYPE
            link.linkname = "/etc/passwd"
            tar.addfile(link)
        with self.assertRaises(NasError):
            archive.extract(evil, self.tmp / "dest")

    def test_extract_keeps_symlink_inside_destination(self):
        work = self.tmp / "work"
        (work / "sub").mkdir(parents=True)
        (work / "real.txt").write_text("본문")
        (work / "sub" / "link.txt").symlink_to("../real.txt")

        out = self.tmp / "snap.tar.gz"
        archive.create(work, out)
        restored = self.tmp / "restored"
        archive.extract(out, restored)
        self.assertTrue((restored / "sub" / "link.txt").is_symlink())
        self.assertEqual((restored / "real.txt").read_text(), "본문")

    def test_snapshot_names_sort_newest_first(self):
        names = ["p-20240101-000000.tar.gz", "p-20250715-123000.tar.gz",
                 "p-20250101-000000.tar.gz"]
        ordered = sorted(names, key=archive.parse_stamp, reverse=True)
        self.assertEqual(ordered[0], "p-20250715-123000.tar.gz")


class TestCli(NasTestCase):
    """CLI 를 실제 인자로 호출해 명령 전체를 확인한다."""

    def setUp(self):
        super().setUp()
        env_file = self.tmp / "test.env"
        env_file.write_text(
            f"SYNOLOGY_URL={self.stub.url}\n"
            f"SYNOLOGY_USER={ACCOUNT}\n"
            f"SYNOLOGY_PASS={PASSWORD}\n"
            f"NAS_BASE_PATH={BASE}\n"
        )
        self.env_file = str(env_file)
        # 실제 환경변수가 테스트에 새어 들어오지 않게 한다.
        for key in ("SYNOLOGY_URL", "SYNOLOGY_USER", "SYNOLOGY_PASS",
                    "NAS_BASE_PATH", "SYNOLOGY_OTP", "SYNOLOGY_VERIFY_SSL"):
            if key in os.environ:
                value = os.environ.pop(key)
                self.addCleanup(os.environ.__setitem__, key, value)

    def run_cli(self, *args):
        return cli.main(["--env-file", self.env_file, *args])

    def test_check_succeeds(self):
        self.assertEqual(self.run_cli("check"), 0)

    def test_save_and_extract_file(self):
        source = self.local / "note.txt"
        source.write_text("내용")
        self.assertEqual(self.run_cli("save", str(source), "--to", "notes"), 0)
        self.assertTrue(self.nas_file("notes/note.txt").is_file())

        out = self.local / "out"
        out.mkdir()
        self.assertEqual(self.run_cli("extract", "notes/note.txt", "--to", str(out)), 0)
        self.assertEqual((out / "note.txt").read_text(), "내용")

    def test_save_and_extract_folder(self):
        tree = self.local / "proj"
        (tree / "sub").mkdir(parents=True)
        (tree / "a.txt").write_text("a")
        (tree / "sub" / "b.txt").write_text("b")

        self.assertEqual(self.run_cli("save", str(tree)), 0)
        out = self.local / "pull"
        out.mkdir()
        self.assertEqual(self.run_cli("extract", "proj", "--to", str(out)), 0)
        self.assertEqual((out / "proj" / "sub" / "b.txt").read_text(), "b")

    def test_snapshot_then_restore_round_trip(self):
        work = self.local / "myapp"
        (work / "src").mkdir(parents=True)
        (work / "src" / "main.py").write_text("print('hi')")
        (work / "README.md").write_text("# myapp")
        (work / "__pycache__").mkdir()
        (work / "__pycache__" / "x.pyc").write_text("junk")

        self.assertEqual(self.run_cli("snapshot", str(work)), 0)
        self.assertEqual(self.run_cli("snapshots", "--name", "myapp"), 0)

        restored = self.local / "restored"
        restored.mkdir()
        self.assertEqual(
            self.run_cli("restore", "--name", "myapp", "--to", str(restored)), 0
        )
        self.assertEqual((restored / "src" / "main.py").read_text(), "print('hi')")
        self.assertEqual((restored / "README.md").read_text(), "# myapp")
        self.assertFalse((restored / "__pycache__").exists())

    def test_restore_refuses_to_clobber_without_force(self):
        work = self.local / "myapp"
        work.mkdir()
        (work / "a.txt").write_text("a")
        self.run_cli("snapshot", str(work))

        busy = self.local / "busy"
        busy.mkdir()
        (busy / "existing.txt").write_text("소중한 파일")
        self.assertEqual(
            self.run_cli("restore", "--name", "myapp", "--to", str(busy)), 1
        )
        self.assertTrue((busy / "existing.txt").is_file())
        self.assertEqual(
            self.run_cli("restore", "--name", "myapp", "--to", str(busy), "--force"), 0
        )
        self.assertTrue((busy / "a.txt").is_file())

    def test_restore_without_snapshot_returns_error_code(self):
        self.assertEqual(self.run_cli("restore", "--name", "nothing"), 1)

    def test_ls_on_empty_base(self):
        self.assertEqual(self.run_cli("ls"), 0)

    def test_missing_source_is_reported(self):
        self.assertEqual(self.run_cli("save", str(self.local / "없는파일")), 1)


class TestConfig(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_missing_values_list_every_missing_key(self):
        from nascloud import config as config_module
        env = self.tmp / ".env"
        env.write_text("SYNOLOGY_URL=http://nas:5000\n")
        for key in ("SYNOLOGY_USER", "SYNOLOGY_PASS", "SYNOLOGY_URL"):
            if key in os.environ:
                value = os.environ.pop(key)
                self.addCleanup(os.environ.__setitem__, key, value)
        with self.assertRaises(NasError) as ctx:
            config_module.load(str(env))
        self.assertIn("SYNOLOGY_USER", str(ctx.exception))
        self.assertIn("SYNOLOGY_PASS", str(ctx.exception))

    def test_env_var_wins_over_env_file(self):
        from nascloud import config as config_module
        env = self.tmp / ".env"
        env.write_text(
            "SYNOLOGY_URL=http://file:5000\nSYNOLOGY_USER=file\nSYNOLOGY_PASS=file\n"
        )
        os.environ["SYNOLOGY_USER"] = "환경변수"
        self.addCleanup(os.environ.pop, "SYNOLOGY_USER", None)
        cfg = config_module.load(str(env))
        self.assertEqual(cfg.user, "환경변수")
        self.assertEqual(cfg.url, "http://file:5000")

    def test_quotes_and_comments_are_stripped(self):
        from nascloud import config as config_module
        env = self.tmp / ".env"
        env.write_text(
            '# 주석\nexport SYNOLOGY_URL="http://nas:5001"\n'
            "SYNOLOGY_USER='me'\nSYNOLOGY_PASS=pw\nSYNOLOGY_VERIFY_SSL=false\n"
        )
        for key in ("SYNOLOGY_URL", "SYNOLOGY_USER", "SYNOLOGY_PASS", "SYNOLOGY_VERIFY_SSL"):
            if key in os.environ:
                value = os.environ.pop(key)
                self.addCleanup(os.environ.__setitem__, key, value)
        cfg = config_module.load(str(env))
        self.assertEqual(cfg.url, "http://nas:5001")
        self.assertEqual(cfg.user, "me")
        self.assertFalse(cfg.verify_ssl)

    def test_repr_never_leaks_password(self):
        cfg = Config(url="http://nas", user="u", password="비밀번호")
        self.assertNotIn("비밀번호", repr(cfg))


if __name__ == "__main__":
    unittest.main()
