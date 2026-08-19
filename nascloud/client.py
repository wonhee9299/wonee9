"""Synology DSM FileStation API 클라이언트 (표준 라이브러리만 사용).

DSM 웹 API 흐름:
  1. SYNO.API.Info    - 각 API 의 경로/최대 버전을 조회
  2. SYNO.API.Auth    - 로그인하여 sid 획득
  3. SYNO.FileStation.* - 목록/업로드/다운로드/폴더생성
  4. SYNO.API.Auth    - 로그아웃

pip 설치 없이 동작하도록 urllib 만 사용한다. 업로드는 파일을 통째로
메모리에 올리지 않고 multipart 본문을 스트리밍한다.
"""

import io
import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from .errors import NasApiError, NasAuthError, NasError

CHUNK = 1024 * 256


class _MultipartBody:
    """multipart/form-data 본문을 스트리밍하는 파일류 객체.

    urllib 은 Content-Length 가 설정되어 있으면 data 객체의 read(n) 을
    반복 호출한다. 덕분에 큰 파일도 메모리에 다 올리지 않고 보낼 수 있다.
    """

    def __init__(self, fields, file_path, field_name="file", filename=None):
        self.boundary = uuid.uuid4().hex
        dash = f"--{self.boundary}".encode()
        head = io.BytesIO()
        # DSM 은 file 파트가 반드시 마지막에 오기를 요구한다.
        for key, value in fields.items():
            head.write(dash + b"\r\n")
            head.write(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
            head.write(f"{value}\r\n".encode())
        name = filename or Path(file_path).name
        head.write(dash + b"\r\n")
        head.write(
            f'Content-Disposition: form-data; name="{field_name}"; filename="{name}"\r\n'
            .encode("utf-8")
        )
        head.write(b"Content-Type: application/octet-stream\r\n\r\n")
        preamble = head.getvalue()
        epilogue = f"\r\n--{self.boundary}--\r\n".encode()

        self.content_type = f"multipart/form-data; boundary={self.boundary}"
        self.length = len(preamble) + os.path.getsize(file_path) + len(epilogue)
        self._file = open(file_path, "rb")
        self._parts = [io.BytesIO(preamble), self._file, io.BytesIO(epilogue)]
        self._index = 0

    def read(self, size=-1):
        if size is None or size < 0:
            return b"".join(iter(lambda: self.read(CHUNK), b""))
        while self._index < len(self._parts):
            data = self._parts[self._index].read(size)
            if data:
                return data
            self._index += 1
        return b""

    def close(self):
        try:
            self._file.close()
        except OSError:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class NasClient:
    """FileStation 을 통한 저장(save) / 추출(extract) 클라이언트."""

    def __init__(self, config):
        self.config = config
        self._sid = None
        self._paths = {}          # API 이름 -> cgi 경로
        self._versions = {}       # API 이름 -> 최대 버전
        self._ssl_context = None
        if not config.verify_ssl:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            self._ssl_context = context

    # ---------------------------------------------------------------- 저수준

    def _open(self, request):
        try:
            return urllib.request.urlopen(
                request, timeout=self.config.timeout, context=self._ssl_context
            )
        except urllib.error.HTTPError as exc:
            raise NasError(f"NAS 가 HTTP {exc.code} 를 반환했습니다: {exc.reason}") from exc
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, ssl.SSLCertVerificationError):
                raise NasError(
                    f"TLS 인증서 검증 실패: {reason}\n"
                    "  자체 서명 인증서를 쓰는 NAS 라면 SYNOLOGY_VERIFY_SSL=false 로 설정하세요."
                ) from exc
            raise NasError(
                f"NAS 에 연결할 수 없습니다 ({self.config.url}): {reason}\n"
                "  같은 네트워크에 있는지, 포트(5000/5001)가 맞는지 확인하세요."
            ) from exc

    def _url(self, api, params):
        path = self._paths.get(api, "entry.cgi")
        query = urllib.parse.urlencode(params)
        return f"{self.config.url}/webapi/{path}?{query}"

    def _decode(self, response, api):
        payload = json.loads(response.read().decode("utf-8"))
        if not payload.get("success"):
            code = (payload.get("error") or {}).get("code", 100)
            raise NasApiError(code, api=api)
        return payload.get("data", {})

    def _get(self, api, method, version=None, **params):
        query = {"api": api, "version": version or self._version(api), "method": method}
        query.update({k: v for k, v in params.items() if v is not None})
        if self._sid:
            query["_sid"] = self._sid
        return self._decode(self._open(urllib.request.Request(self._url(api, query))), api)

    def _version(self, api):
        return self._versions.get(api, 1)

    # ------------------------------------------------------------ 세션 관리

    def _discover(self):
        """SYNO.API.Info 로 각 API 의 경로와 사용 가능한 최대 버전을 조회한다."""
        url = (f"{self.config.url}/webapi/query.cgi?"
               "api=SYNO.API.Info&version=1&method=query&query=all")
        data = self._decode(self._open(urllib.request.Request(url)), "SYNO.API.Info")
        for name, info in data.items():
            self._paths[name] = info.get("path", "entry.cgi")
            self._versions[name] = info.get("maxVersion", 1)
        if "SYNO.FileStation.List" not in self._paths:
            raise NasError(
                "이 NAS 에서 FileStation API 를 찾을 수 없습니다.\n"
                "  DSM > 제어판 > 파일 서비스 에서 File Station 이 켜져 있는지 확인하세요."
            )

    def login(self):
        if self._sid:
            return
        self._discover()
        # 로그인은 버전 6 이상이 OTP 와 세션 분리를 지원한다.
        version = min(self._versions.get("SYNO.API.Auth", 6), 7)
        params = {
            "api": "SYNO.API.Auth",
            "version": max(version, 3),
            "method": "login",
            "account": self.config.user,
            "passwd": self.config.password,
            "session": "FileStation",
            "format": "sid",
        }
        if self.config.otp:
            params["otp_code"] = self.config.otp
        try:
            data = self._decode(
                self._open(urllib.request.Request(self._url("SYNO.API.Auth", params))),
                "SYNO.API.Auth",
            )
        except NasApiError as exc:
            raise NasAuthError(f"로그인 실패: {exc}") from exc
        self._sid = data.get("sid")
        if not self._sid:
            raise NasAuthError("로그인 응답에 sid 가 없습니다.")

    def logout(self):
        if not self._sid:
            return
        try:
            self._get("SYNO.API.Auth", "logout", session="FileStation")
        except NasError:
            pass  # 로그아웃 실패는 작업 결과에 영향을 주지 않는다.
        finally:
            self._sid = None

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, *exc):
        self.logout()

    # ------------------------------------------------------------ 파일 조작

    def resolve(self, path):
        """상대 경로를 NAS_BASE_PATH 기준 절대 경로로 바꾼다."""
        path = str(path).replace("\\", "/")
        if path.startswith("/"):
            return path.rstrip("/") or "/"
        joined = f"{self.config.base_path}/{path}".rstrip("/")
        return joined or "/"

    def list_dir(self, path):
        """폴더 내용을 [{name, path, is_dir, size}] 로 돌려준다."""
        target = self.resolve(path)
        data = self._get(
            "SYNO.FileStation.List", "list",
            folder_path=target, additional='["size","time"]',
        )
        entries = []
        for item in data.get("files", []):
            extra = item.get("additional") or {}
            entries.append({
                "name": item.get("name"),
                "path": item.get("path"),
                "is_dir": bool(item.get("isdir")),
                "size": extra.get("size", 0),
                "mtime": (extra.get("time") or {}).get("mtime"),
            })
        entries.sort(key=lambda e: (not e["is_dir"], e["name"] or ""))
        return entries

    def exists(self, path):
        target = self.resolve(path)
        try:
            data = self._get("SYNO.FileStation.List", "getinfo", path=json.dumps([target]))
        except NasApiError:
            return False
        files = data.get("files") or []
        return bool(files) and "code" not in files[0]

    def makedirs(self, path):
        """중간 폴더까지 모두 생성한다. 이미 있으면 조용히 넘어간다."""
        target = self.resolve(path)
        parent, _, name = target.rpartition("/")
        if not name:
            return target
        try:
            self._get(
                "SYNO.FileStation.CreateFolder", "create",
                folder_path=parent or "/", name=name, force_parent="true",
            )
        except NasApiError as exc:
            if exc.code not in (414, 1100):  # 이미 존재하는 경우
                raise
        return target

    def upload(self, local_path, remote_dir, overwrite=True, remote_name=None):
        """파일 하나를 NAS 폴더로 올린다. 올라간 전체 경로를 돌려준다."""
        local_path = Path(local_path)
        if not local_path.is_file():
            raise NasError(f"업로드할 파일이 없습니다: {local_path}")
        target_dir = self.makedirs(remote_dir)
        version = min(self._versions.get("SYNO.FileStation.Upload", 2), 3)
        fields = {
            "api": "SYNO.FileStation.Upload",
            "version": version,
            "method": "upload",
            "path": target_dir,
            "create_parents": "true",
            "overwrite": "true" if overwrite else "false",
        }
        body = _MultipartBody(fields, local_path, filename=remote_name or local_path.name)
        with body:
            url = self._url("SYNO.FileStation.Upload", {"_sid": self._sid})
            request = urllib.request.Request(url, data=body, method="POST")
            request.add_header("Content-Type", body.content_type)
            request.add_header("Content-Length", str(body.length))
            self._decode(self._open(request), "SYNO.FileStation.Upload")
        return f"{target_dir}/{remote_name or local_path.name}"

    def download(self, remote_path, local_path, progress=None):
        """NAS 의 파일 하나를 내려받는다. 저장된 로컬 경로를 돌려준다."""
        target = self.resolve(remote_path)
        params = {
            "api": "SYNO.FileStation.Download",
            "version": min(self._versions.get("SYNO.FileStation.Download", 2), 2),
            "method": "download",
            "path": json.dumps([target]),
            "mode": "download",
            "_sid": self._sid,
        }
        request = urllib.request.Request(self._url("SYNO.FileStation.Download", params))
        response = self._open(request)
        content_type = (response.headers.get("Content-Type") or "").lower()
        if "application/json" in content_type:
            # 성공이면 파일 바이트가 오고, 실패하면 JSON 오류가 온다.
            self._decode(response, "SYNO.FileStation.Download")
            raise NasError(f"다운로드에 실패했습니다: {target}")

        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        written = 0
        with response, open(local_path, "wb") as handle:
            while True:
                chunk = response.read(CHUNK)
                if not chunk:
                    break
                handle.write(chunk)
                written += len(chunk)
                if progress:
                    progress(written)
        return local_path

    def upload_tree(self, local_dir, remote_dir, overwrite=True, on_file=None):
        """폴더를 통째로, 구조를 유지한 채 업로드한다."""
        local_dir = Path(local_dir)
        count = 0
        for path in sorted(local_dir.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(local_dir).parent.as_posix()
            base = self.resolve(remote_dir)
            destination = base if relative == "." else f"{base}/{relative}"
            self.upload(path, destination, overwrite=overwrite)
            count += 1
            if on_file:
                on_file(path)
        return count

    def download_tree(self, remote_dir, local_dir, on_file=None):
        """NAS 폴더를 재귀적으로 내려받는다."""
        local_dir = Path(local_dir)
        count = 0
        for entry in self.list_dir(remote_dir):
            target = local_dir / entry["name"]
            if entry["is_dir"]:
                count += self.download_tree(entry["path"], target, on_file=on_file)
            else:
                self.download(entry["path"], target)
                count += 1
                if on_file:
                    on_file(target)
        return count
