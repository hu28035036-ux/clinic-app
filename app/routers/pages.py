"""HTML 페이지"""
import socket
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ..config import resource_path, load_config, APP_VERSION

router = APIRouter()
templates = Jinja2Templates(directory=str(resource_path("app/templates")))


def _app_title() -> str:
    """헤더·브라우저 탭에 표시할 앱(홈페이지) 이름.
    config.json 의 app_title 을 매 렌더 시 라이브 조회 → 관리자 탭 수정이 즉시 반영.
    base.html 을 상속하는 모든 페이지(main/setup/server_info)가 이 전역을 사용.
    """
    return (load_config().get("app_title") or "병원 예약 관리").strip() or "병원 예약 관리"


templates.env.globals["app_title"] = _app_title

def _local_ips():
    """이 PC 의 로컬 IP 목록.
    첫 번째 항목은 '실제 외부 연결에 사용되는 IP' (가장 정확 — 환자/직원 다른 PC 에서 접속용).
    이어서 getaddrinfo 로 얻은 부가 IP (CGNAT·WSL·VPN 가상 어댑터 등) 가 뒤따름.
    """
    ips = []
    # 1순위: UDP 소켓을 '외부 IP 로 연결하는 척' 하고 getsockname → 실제 라우팅되는 인터페이스 IP
    #         (병원 공유기 LAN IP 예: 192.168.0.x, 10.0.0.x — 다른 PC 접속 가능)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        primary = s.getsockname()[0]
        s.close()
        if primary and not primary.startswith("127."):
            ips.append(primary)
    except Exception:
        pass

    # 2순위: hostname 기반 부가 IP (CGNAT·WSL·VPN 등 포함 — 참고용)
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None):
            ip = info[4][0]
            if ":" not in ip and not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except Exception:
        pass

    if not ips:
        ips.append("127.0.0.1")
    return ips

# HTML 문서는 항상 서버에 재검증(no-cache) → 매번 최신 ?v=<버전> 을 받아
# 업데이트가 새로고침 한 번에 반영되게 한다. (정적 자산은 main.py 에서 버전별
# immutable 캐시 — 문서만 no-cache 면 새 버전 URL 을 항상 집어온다.)
_NO_CACHE_HEADERS = {"Cache-Control": "no-cache"}


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    cfg = load_config()
    if not cfg.get("mode"): return RedirectResponse("/setup", 302)
    return templates.TemplateResponse(
        request, "main.html",
        {"config": cfg, "local_ips": _local_ips(), "app_version": APP_VERSION},
        headers=_NO_CACHE_HEADERS,
    )

@router.get("/setup", response_class=HTMLResponse)
def setup(request: Request):
    return templates.TemplateResponse(
        request, "setup.html",
        {"config": load_config(), "local_ips": _local_ips(), "app_version": APP_VERSION},
        headers=_NO_CACHE_HEADERS,
    )
