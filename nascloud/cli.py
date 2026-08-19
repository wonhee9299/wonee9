"""nascloud 명령줄 인터페이스.

사용 예:
    ./nas check                    # 연결/로그인 확인
    ./nas save ./report.pdf        # 파일 하나를 NAS 에 저장
    ./nas save ./src --to code     # 폴더를 NAS 에 저장
    ./nas snapshot                 # 작업 폴더 전체를 스냅샷으로 저장
    ./nas ls                       # NAS 내용 보기
    ./nas extract code ./받은코드   # NAS 에서 꺼내오기
    ./nas restore                  # 가장 최근 스냅샷으로 되돌리기
"""

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

from . import archive, config as config_module
from .client import NasClient
from .errors import NasError

SNAPSHOT_DIR = "snapshots"


def _human(size):
    size = float(size or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f}{unit}" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def _project_name(path):
    resolved = Path(path).resolve()
    return resolved.name or "work"


def _client(args):
    return NasClient(config_module.load(args.env_file))


# ------------------------------------------------------------------ 명령들

def cmd_check(args):
    cfg = config_module.load(args.env_file)
    print(f"접속 대상 : {cfg.url}")
    print(f"계정      : {cfg.user}")
    print(f"기본 경로 : {cfg.base_path}")
    print(f"TLS 검증  : {'켜짐' if cfg.verify_ssl else '꺼짐'}")
    with NasClient(cfg) as client:
        print("로그인    : 성공")
        client.makedirs(cfg.base_path)
        entries = client.list_dir(cfg.base_path)
        print(f"기본 경로 확인 : 항목 {len(entries)}개")
    return 0


def cmd_ls(args):
    with _client(args) as client:
        entries = client.list_dir(args.path)
        if not entries:
            print("(비어 있음)")
            return 0
        for entry in entries:
            kind = "d" if entry["is_dir"] else "-"
            size = "-" if entry["is_dir"] else _human(entry["size"])
            print(f"{kind} {size:>9}  {entry['name']}")
    return 0


def cmd_save(args):
    source = Path(args.source)
    if not source.exists():
        raise NasError(f"저장할 경로가 없습니다: {source}")
    destination = args.to or ""
    with _client(args) as client:
        if source.is_dir():
            target = client.resolve(destination or source.name)
            print(f"폴더 업로드: {source} -> {target}")
            count = client.upload_tree(
                source, target, overwrite=not args.no_overwrite,
                on_file=lambda p: print(f"  + {p.name}") if args.verbose else None,
            )
            print(f"완료: 파일 {count}개 저장")
        else:
            target_dir = client.resolve(destination)
            uploaded = client.upload(
                source, target_dir, overwrite=not args.no_overwrite
            )
            print(f"완료: {uploaded} ({_human(source.stat().st_size)})")
    return 0


def cmd_extract(args):
    destination = Path(args.to or ".")
    with _client(args) as client:
        remote = client.resolve(args.path)
        entries = None
        try:
            entries = client.list_dir(remote)
            is_dir = True
        except NasError:
            is_dir = False

        if is_dir:
            target = destination / Path(remote).name if destination.is_dir() else destination
            print(f"폴더 다운로드: {remote} -> {target}")
            count = client.download_tree(
                remote, target,
                on_file=lambda p: print(f"  - {p.name}") if args.verbose else None,
            )
            print(f"완료: 파일 {count}개 추출 ({len(entries)}개 최상위 항목)")
        else:
            name = Path(remote).name
            target = destination / name if destination.is_dir() else destination
            client.download(remote, target)
            print(f"완료: {target} ({_human(target.stat().st_size)})")
            if args.unpack and name.endswith(archive.SNAPSHOT_SUFFIX):
                unpack_to = target.parent / name[: -len(archive.SNAPSHOT_SUFFIX)]
                count = archive.extract(target, unpack_to)
                print(f"압축 해제: {unpack_to} (파일 {count}개)")
    return 0


def cmd_snapshot(args):
    source = Path(args.source or ".").resolve()
    project = args.name or _project_name(source)
    patterns = archive.load_excludes(source) + list(args.exclude or [])
    remote_dir = f"{SNAPSHOT_DIR}/{project}"

    with tempfile.TemporaryDirectory() as tmp:
        name = archive.snapshot_name(project)
        local_archive = Path(tmp) / name
        print(f"스냅샷 생성: {source}")
        count = archive.create(
            source, local_archive, patterns=patterns,
            on_add=lambda rel: print(f"  + {rel}") if args.verbose else None,
        )
        size = local_archive.stat().st_size
        print(f"  파일 {count}개, {_human(size)}")
        with _client(args) as client:
            uploaded = client.upload(local_archive, remote_dir)
        print(f"완료: {uploaded}")
        if args.keep:
            kept = Path(args.keep) / name
            kept.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(local_archive, kept)
            print(f"로컬 사본: {kept}")
    return 0


def _snapshots(client, project):
    try:
        entries = client.list_dir(f"{SNAPSHOT_DIR}/{project}")
    except NasError:
        return []  # 스냅샷 폴더 자체가 없으면 '없음'과 같은 뜻이다.
    snaps = [e for e in entries
             if not e["is_dir"] and e["name"].endswith(archive.SNAPSHOT_SUFFIX)]
    snaps.sort(key=lambda e: archive.parse_stamp(e["name"]), reverse=True)
    return snaps


def cmd_snapshots(args):
    project = args.name or _project_name(args.source or ".")
    with _client(args) as client:
        snaps = _snapshots(client, project)
    if not snaps:
        print(f"'{project}' 의 스냅샷이 없습니다.")
        return 0
    print(f"'{project}' 스냅샷 {len(snaps)}개 (최신순):")
    for entry in snaps:
        print(f"  {entry['name']:<44} {_human(entry['size']):>9}")
    return 0


def cmd_restore(args):
    project = args.name or _project_name(args.to or ".")
    destination = Path(args.to or ".").resolve()

    with _client(args) as client:
        snaps = _snapshots(client, project)
        if not snaps:
            raise NasError(
                f"'{project}' 의 스냅샷을 NAS 에서 찾을 수 없습니다.\n"
                f"  'nas snapshots --name {project}' 로 목록을 확인하세요."
            )
        if args.snapshot:
            chosen = next((e for e in snaps if e["name"] == args.snapshot), None)
            if chosen is None:
                raise NasError(f"그런 스냅샷이 없습니다: {args.snapshot}")
        else:
            chosen = snaps[0]

        print(f"복원할 스냅샷: {chosen['name']} ({_human(chosen['size'])})")
        if destination.exists() and any(destination.iterdir()) and not args.force:
            raise NasError(
                f"{destination} 가 비어 있지 않습니다. 덮어쓰려면 --force 를 붙이세요."
            )
        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / chosen["name"]
            client.download(chosen["path"], local)
            count = archive.extract(
                local, destination,
                on_extract=lambda n: print(f"  - {n}") if args.verbose else None,
            )
    print(f"완료: {destination} 에 파일 {count}개 복원")
    return 0


# -------------------------------------------------------------- 인자 파서

def build_parser():
    parser = argparse.ArgumentParser(
        prog="nas",
        description="시놀로지 NAS 를 저장소로 쓰는 작업 저장/추출 도구",
    )
    parser.add_argument("--env-file", help=".env 파일 경로 (기본: 저장소 루트의 .env)")
    parser.add_argument("-v", "--verbose", action="store_true", help="파일 단위로 진행 상황 출력")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("check", help="NAS 연결과 로그인을 확인한다")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("ls", help="NAS 폴더 내용을 본다")
    p.add_argument("path", nargs="?", default="", help="NAS 경로 (기본: NAS_BASE_PATH)")
    p.set_defaults(func=cmd_ls)

    p = sub.add_parser("save", help="파일 또는 폴더를 NAS 에 저장한다")
    p.add_argument("source", help="올릴 로컬 파일/폴더")
    p.add_argument("--to", help="NAS 안의 대상 경로 (기본: 기준 경로 바로 아래)")
    p.add_argument("--no-overwrite", action="store_true", help="같은 이름이 있으면 실패시킨다")
    p.set_defaults(func=cmd_save)

    p = sub.add_parser("extract", help="NAS 에서 파일 또는 폴더를 꺼내온다")
    p.add_argument("path", help="가져올 NAS 경로")
    p.add_argument("--to", help="저장할 로컬 경로 (기본: 현재 폴더)")
    p.add_argument("--no-unpack", dest="unpack", action="store_false",
                   help="받은 tar.gz 를 자동으로 풀지 않는다")
    p.set_defaults(func=cmd_extract, unpack=True)

    p = sub.add_parser("snapshot", help="작업 폴더 전체를 묶어 NAS 에 저장한다")
    p.add_argument("source", nargs="?", default=".", help="묶을 폴더 (기본: 현재 폴더)")
    p.add_argument("--name", help="프로젝트 이름 (기본: 폴더 이름)")
    p.add_argument("--exclude", action="append", help="추가로 제외할 패턴 (여러 번 지정 가능)")
    p.add_argument("--keep", help="이 폴더에 로컬 사본도 남긴다")
    p.set_defaults(func=cmd_snapshot)

    p = sub.add_parser("snapshots", help="NAS 에 저장된 스냅샷 목록을 본다")
    p.add_argument("source", nargs="?", default=".", help="이름 추론에 쓸 폴더")
    p.add_argument("--name", help="프로젝트 이름")
    p.set_defaults(func=cmd_snapshots)

    p = sub.add_parser("restore", help="NAS 의 스냅샷을 되돌린다 (기본: 가장 최신)")
    p.add_argument("--name", help="프로젝트 이름 (기본: 대상 폴더 이름)")
    p.add_argument("--to", help="복원할 로컬 폴더 (기본: 현재 폴더)")
    p.add_argument("--snapshot", help="특정 스냅샷 파일 이름")
    p.add_argument("--force", action="store_true", help="폴더가 비어 있지 않아도 덮어쓴다")
    p.set_defaults(func=cmd_restore)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except NasError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n중단했습니다.", file=sys.stderr)
        return 130
