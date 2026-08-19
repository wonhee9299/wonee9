"""테스트용 가짜 DSM 서버.

실제 NAS 없이 nascloud 클라이언트를 끝까지 검증하기 위해, FileStation
웹 API 중 이 프로젝트가 쓰는 부분만 임시 폴더 위에 흉내낸다.
"""

import json
import re
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SID = "test-sid-0001"
ACCOUNT = "tester"
PASSWORD = "s3cret"
OTP = "123456"

API_INFO = {
    "SYNO.API.Auth": {"path": "auth.cgi", "minVersion": 1, "maxVersion": 7},
    "SYNO.FileStation.List": {"path": "entry.cgi", "minVersion": 1, "maxVersion": 2},
    "SYNO.FileStation.Upload": {"path": "entry.cgi", "minVersion": 1, "maxVersion": 3},
    "SYNO.FileStation.Download": {"path": "entry.cgi", "minVersion": 1, "maxVersion": 2},
    "SYNO.FileStation.CreateFolder": {"path": "entry.cgi", "minVersion": 1, "maxVersion": 2},
}


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    # --------------------------------------------------------------- 유틸

    @property
    def root(self):
        return self.server.root

    def log_message(self, *args):
        pass  # 테스트 출력을 더럽히지 않는다.

    def _local(self, nas_path):
        """NAS 절대 경로를 임시 폴더 안의 실제 경로로 바꾼다."""
        relative = str(nas_path).lstrip("/")
        resolved = (self.root / relative).resolve()
        if self.root.resolve() != resolved and self.root.resolve() not in resolved.parents:
            raise ValueError("경로 탈출")
        return resolved

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _ok(self, data=None):
        self._send_json({"success": True, "data": data if data is not None else {}})

    def _fail(self, code):
        self._send_json({"success": False, "error": {"code": code}})

    def _authed(self, query):
        return query.get("_sid", [None])[0] == SID

    # ---------------------------------------------------------------- GET

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        api = query.get("api", [""])[0]
        method = query.get("method", [""])[0]

        if api == "SYNO.API.Info":
            return self._ok(API_INFO)
        if api == "SYNO.API.Auth":
            return self._auth(method, query)
        if not self._authed(query):
            return self._fail(119)
        if api == "SYNO.FileStation.List":
            return self._list(method, query)
        if api == "SYNO.FileStation.CreateFolder":
            return self._create_folder(query)
        if api == "SYNO.FileStation.Download":
            return self._download(query)
        return self._fail(102)

    def _auth(self, method, query):
        if method == "logout":
            return self._ok()
        if method != "login":
            return self._fail(103)
        if query.get("account", [""])[0] != ACCOUNT or query.get("passwd", [""])[0] != PASSWORD:
            return self._fail(400)
        if self.server.require_otp:
            code = query.get("otp_code", [None])[0]
            if code is None:
                return self._fail(403)
            if code != OTP:
                return self._fail(404)
        return self._ok({"sid": SID})

    def _list(self, method, query):
        if method == "getinfo":
            paths = json.loads(query.get("path", ["[]"])[0])
            files = []
            for nas_path in paths:
                local = self._local(nas_path)
                if local.exists():
                    files.append({"path": nas_path, "name": local.name,
                                  "isdir": local.is_dir()})
                else:
                    files.append({"path": nas_path, "code": 408})
            return self._ok({"files": files})
        if method != "list":
            return self._fail(103)

        folder = query.get("folder_path", [""])[0]
        local = self._local(folder)
        if not local.is_dir():
            return self._fail(408)
        files = []
        for child in sorted(local.iterdir()):
            files.append({
                "name": child.name,
                "path": f"{folder.rstrip('/')}/{child.name}",
                "isdir": child.is_dir(),
                "additional": {
                    "size": child.stat().st_size if child.is_file() else 0,
                    "time": {"mtime": int(child.stat().st_mtime)},
                },
            })
        return self._ok({"files": files, "total": len(files)})

    def _create_folder(self, query):
        parent = query.get("folder_path", [""])[0]
        name = query.get("name", [""])[0]
        force = query.get("force_parent", ["false"])[0] == "true"
        local_parent = self._local(parent)
        if not local_parent.exists() and not force:
            return self._fail(1101)
        target = local_parent / name
        if target.exists():
            return self._fail(414)
        target.mkdir(parents=True, exist_ok=True)
        return self._ok({"folders": [{"path": f"{parent.rstrip('/')}/{name}", "name": name}]})

    def _download(self, query):
        paths = json.loads(query.get("path", ["[]"])[0])
        if not paths:
            return self._fail(101)
        local = self._local(paths[0])
        if not local.is_file():
            return self._fail(408)
        data = local.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Disposition", f'attachment; filename="{local.name}"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # --------------------------------------------------------------- POST

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        if not self._authed(query):
            return self._fail(119)

        content_type = self.headers.get("Content-Type", "")
        match = re.search(r"boundary=([^;]+)", content_type)
        if not match:
            return self._fail(101)
        boundary = match.group(1).strip('"').encode()
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)

        fields, filename, payload = _parse_multipart(body, boundary)
        self.server.uploads.append({"fields": dict(fields), "filename": filename,
                                    "size": len(payload)})
        if fields.get("api") != "SYNO.FileStation.Upload":
            return self._fail(102)

        folder = fields.get("path", "")
        local_dir = self._local(folder)
        if not local_dir.is_dir():
            if fields.get("create_parents") == "true":
                local_dir.mkdir(parents=True, exist_ok=True)
            else:
                return self._fail(1802)
        target = local_dir / filename
        if target.exists() and fields.get("overwrite") != "true":
            return self._fail(1800)
        target.write_bytes(payload)
        return self._ok({"file": filename})


def _parse_multipart(body, boundary):
    """테스트에 필요한 만큼만 구현한 multipart 파서."""
    fields = {}
    filename = None
    payload = b""
    delimiter = b"--" + boundary
    for chunk in body.split(delimiter):
        if not chunk or chunk in (b"--\r\n", b"--"):
            continue
        chunk = chunk.lstrip(b"\r\n")
        header_blob, _, content = chunk.partition(b"\r\n\r\n")
        headers = header_blob.decode("utf-8", "replace")
        name_match = re.search(r'name="([^"]*)"', headers)
        if not name_match:
            continue
        content = content[:-2] if content.endswith(b"\r\n") else content
        file_match = re.search(r'filename="([^"]*)"', headers)
        if file_match:
            filename = file_match.group(1)
            payload = content
        else:
            fields[name_match.group(1)] = content.decode("utf-8", "replace")
    return fields, filename, payload


class DsmStub:
    """with 문으로 켜고 끄는 가짜 NAS."""

    def __init__(self, root, require_otp=False):
        self.root = Path(root)
        self.require_otp = require_otp
        self.server = None
        self.thread = None

    def __enter__(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.server.root = self.root
        self.server.require_otp = self.require_otp
        self.server.uploads = []
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    @property
    def url(self):
        host, port = self.server.server_address
        return f"http://{host}:{port}"

    @property
    def uploads(self):
        return self.server.uploads
