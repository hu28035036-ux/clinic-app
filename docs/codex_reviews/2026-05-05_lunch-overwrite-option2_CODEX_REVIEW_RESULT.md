**검토 결과**

Finding: [app/routers/api.py](<C:/Users/user/Desktop/새 폴더/병원예약관리/병원예약관리/app/routers/api.py:4449>) / [app/routers/api.py](<C:/Users/user/Desktop/새 폴더/병원예약관리/병원예약관리/app/routers/api.py:4524>)  
`_hm_to_min()`이 `HH:MM`의 분 단위 범위를 검증하지 않습니다. 그래서 `lunch_enabled=True`, `lunch_start="12:75"`, `lunch_end="13:30"` 같은 설정이 invalid로 graceful 처리되지 않고 `13:15~13:30`처럼 해석되어 점심 셀/라벨이 출력될 수 있습니다. 현재 invalid 테스트는 [tests/test_export_lunch_window.py](<C:/Users/user/Desktop/새 폴더/병원예약관리/병원예약관리/tests/test_export_lunch_window.py:147>)에서 `"abc"`만 커버해서 이 케이스를 놓칩니다.

권장 수정:
`_hm_to_min()` 또는 점심 파싱부에서 `0 <= hour <= 23`, `0 <= minute <= 59`를 명시 검증하고, 실패 시 현재처럼 `lunch_slots=set()` / `lunch_label_text=""`로 내려가게 하세요. `24:00`을 end 전용으로 허용하려면 별도 처리해야 합니다.

그 외 요청 체크:
- 점심 시작 예약 skip: 의도대로 보입니다.
- 일반 예약 span이 점심 슬롯을 침범할 때 자르기: 의도대로 보입니다.
- 점심 row 우선 표시 및 `is_lunch` entry 무시: 의도대로 보입니다.
- 라벨 1회 출력: 현재 구조상 정상으로 보입니다.
- DB/예약 DB/AI/UI 영향: 이번 diff는 export API 렌더링 로직 한정으로 보이며 직접 영향은 없어 보입니다.

검증:
`venv\Scripts\python.exe -m pytest ...` 실행은 현재 shell policy에 의해 차단됐습니다. `python -m ruff ...`는 시스템 Python에 `ruff`가 없어 실행하지 못했습니다. 따라서 보고된 `2154 passed` / ruff 통과 결과는 독립 재현하지 못했습니다.