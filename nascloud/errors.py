"""Synology DSM API 오류 코드를 사람이 읽을 수 있는 메시지로 변환한다."""


class NasError(Exception):
    """NAS 통신 중 발생한 모든 오류의 기반 클래스."""


class NasAuthError(NasError):
    """로그인/세션 관련 오류."""


class NasApiError(NasError):
    """DSM API 가 error 코드를 돌려준 경우."""

    def __init__(self, code, api=None, hint=None):
        self.code = code
        self.api = api
        message = describe(code, api)
        if hint:
            message = f"{message} ({hint})"
        super().__init__(f"[{code}] {message}")


# 모든 API 가 공유하는 코드
_COMMON = {
    100: "알 수 없는 오류",
    101: "잘못된 파라미터",
    102: "요청한 API 가 NAS 에 존재하지 않음",
    103: "요청한 method 가 존재하지 않음",
    104: "NAS 가 이 API 버전을 지원하지 않음",
    105: "권한 없음 - 이 계정으로는 허용되지 않는 작업",
    106: "세션 만료",
    107: "다른 곳에서 로그인하여 세션이 끊김",
    119: "SID 가 유효하지 않음 - 다시 로그인 필요",
}

_AUTH = {
    400: "계정이 없거나 비밀번호가 틀림",
    401: "비활성화된 계정",
    402: "권한이 거부됨",
    403: "2단계 인증 코드가 필요함 - SYNOLOGY_OTP 를 설정하세요",
    404: "2단계 인증 코드가 틀림",
    406: "이 계정은 2단계 인증이 필수로 설정되어 있음",
    407: "IP 가 차단됨 (DSM 자동 차단 목록 확인)",
    408: "비밀번호가 만료됨",
    409: "비밀번호가 만료되어 변경이 필요함",
    410: "비밀번호 변경이 강제됨",
}

_FILESTATION = {
    400: "파일 작업 파라미터가 잘못됨",
    401: "알 수 없는 파일 작업 오류",
    402: "NAS 가 너무 바쁨",
    403: "이 사용자는 해당 파일 작업을 수행할 수 없음",
    404: "잘못된 그룹으로 파일 작업 시도",
    405: "사용자/그룹 권한이 파일 작업을 허용하지 않음",
    406: "cannot get user/group info (DSM 내부 오류)",
    407: "허용되지 않은 작업",
    408: "해당 경로의 파일 또는 폴더가 없음",
    409: "지원하지 않는 파일 시스템",
    410: "실패 - 더 자세한 정보 없음",
    411: "읽기 전용 파일 시스템",
    412: "파일 이름이 너무 김",
    413: "대상 폴더로 복사/이동할 수 없음",
    414: "대상 경로에 같은 이름이 이미 존재함",
    415: "권한 거부됨",
    416: "디스크 공간 부족",
    417: "입출력 오류",
    418: "잘못된 파일 이름",
    419: "이름이 예약어라 사용할 수 없음",
    1100: "폴더 생성 실패",
    1101: "대상 폴더의 상위 경로가 존재하지 않음",
    1800: "업로드할 파일이 이미 존재함 (overwrite 옵션 확인)",
    1801: "업로드 대상 폴더에 쓸 수 없음",
    1802: "업로드 대상 경로가 존재하지 않음",
    1803: "디스크 공간 부족으로 업로드 실패",
    1804: "업로드 대상에 대한 권한이 없음",
    1805: "업로드가 허용되지 않음",
}

_BY_API = {
    "SYNO.API.Auth": _AUTH,
    "SYNO.FileStation": _FILESTATION,
}


def describe(code, api=None):
    """오류 코드 하나를 한국어 설명으로 바꾼다."""
    if code in _COMMON:
        return _COMMON[code]
    if api:
        for prefix, table in _BY_API.items():
            if api.startswith(prefix) and code in table:
                return table[code]
    # API 를 모르면 두 테이블을 모두 뒤져 본다.
    for table in (_AUTH, _FILESTATION):
        if code in table:
            return table[code]
    return "문서에 없는 오류 코드"
