# AI_DESIGN_TOKENS.md

> 디자인 토큰 (색·간격·크기·라운드·그림자·타이포그래피) 정의.
> 본 문서는 **명세** 입니다. 실제 CSS 변수 / Tailwind config / SCSS 등으로의 코드 적용은 AI 기능 구현 / 검증 완료 후 진행합니다.
> 토큰 값은 권장값이며, 실제 적용 단계에서 미세 조정 가능합니다. 변경 시 [AI_REQUIREMENTS_OVERRIDES.md](AI_REQUIREMENTS_OVERRIDES.md) 에 기록합니다.

---

## 0. 운용 원칙

- 본 문서가 단일 소스입니다. 다른 디자인 문서(`AI_UI_UX_DESIGN_PLAN.md`, `AI_UI_STYLE_GUIDE.md`)는 **이 토큰 이름을 인용**해 사용합니다.
- 토큰 이름은 코드 적용 시 그대로 CSS 변수 / Tailwind 키로 매핑할 수 있도록 일관된 네이밍을 사용합니다.
- HEX 값은 권장값이며 실 적용 시 화면 보정 가능. 단, **분위기·대비**는 본 문서를 따릅니다.
- **치료사별 색상**은 기존 기능을 유지하므로 본 토큰과는 별도로 운용합니다 (충돌만 회피).

---

## 1. 색상 토큰

### 1.1 표면 / 배경

| 이름 | 권장 HEX | 용도 |
|---|---|---|
| `background` | `#F6F7F4` | 페이지 전체 배경 (밝은 따뜻한 회색) |
| `surface`    | `#F1F2EE` | 헤더 / 사이드바 / 표 헤더 등 보조 표면 |
| `card`       | `#FFFFFF` | 흰색 카드 배경 |

### 1.2 포인트 (그린 / 차콜 그린)

| 이름 | 권장 HEX | 용도 |
|---|---|---|
| `primary`       | `#1F3D2B` | 주요 포인트 (Primary 버튼, 선택 탭, 강조 텍스트). 진한 그린 / 차콜 그린. |
| `primary-hover` | `#16301F` | Primary hover / pressed |
| `primary-soft`  | `#E2EBE0` | 선택된 탭 배경, 선택된 후보 카드 배경, 정보 강조 배경 |

### 1.3 텍스트

| 이름 | 권장 HEX | 용도 |
|---|---|---|
| `text-primary`   | `#1A1F1B` | 본문 / 제목 |
| `text-secondary` | `#5C6660` | 보조 텍스트 |
| `text-muted`     | `#8C938E` | placeholder / caption |

### 1.4 보더

| 이름 | 권장 HEX | 용도 |
|---|---|---|
| `border` | `#E5E7E2` | 카드 / 표 / 입력창 보더 (얇고 연하게) |

### 1.5 상태

| 이름 | 권장 HEX | 용도 |
|---|---|---|
| `success`      | `#3F8E5C` | 완료 / 등록 완료 / 성공 텍스트 |
| `success-soft` | `#E0F0E5` | 성공 메시지·badge 배경 |
| `warning`      | `#A86A1B` | 선택 필요 / 주의 텍스트 |
| `warning-soft` | `#F7ECCC` | 선택 필요·경고 배경 (연 옐로우 / 베이지) |
| `danger`       | `#A8392B` | 오류 / 취소 텍스트 |
| `danger-soft`  | `#F4DDD8` | 오류·취소 배경 |
| `info`         | `#3A6F75` | 정보 / 진행 텍스트 |
| `info-soft`    | `#DBE9EB` | 정보 / 진행 배경 |
| `disabled`     | `#C8CCC6` | 비활성 배경 / 텍스트 |

### 1.6 사용 규칙

- 원색 과다 금지. 상태는 명확하되 톤에서 튀지 않게.
- 색만으로 의미 전달 금지 (텍스트 / 아이콘과 함께 사용).
- 같은 의미 상태는 **모든 화면에서 동일 토큰** 사용.
- 다크 모드는 본 토큰 범위 밖 (현 단계 미적용, 추후 별도 정의).

---

## 2. 간격 토큰

| 이름 | 권장 값 | 용도 |
|---|---|---|
| `page-padding`        | 24px | 페이지 좌우 / 상하 외곽 패딩 |
| `section-gap`         | 24px | 섹션 / 큰 컨테이너 간 세로 간격 |
| `card-padding`        | 20px | 카드 내부 패딩 |
| `card-gap`            | 16px | 카드 간 세로 / 가로 간격 |
| `table-cell-padding`  | 12px | 표 셀 좌우 패딩 (상하는 절반) |
| `form-gap`            | 16px | 폼 필드 간 세로 간격 |

> 모든 간격은 4의 배수로 통일.

---

## 3. 크기 토큰

| 이름 | 권장 값 | 용도 |
|---|---|---|
| `input-height`      | 40px | 입력창 / 검색창 높이 |
| `button-height`     | 40px | 버튼 높이 (입력창과 동일하게 정렬) |
| `table-row-height`  | 48px | 표 행 높이 (좁지 않게) |
| `badge-height`      | 22px | 상태 badge 높이 |
| `sidebar-width`     | 224px | 사이드바 폭 (현재 구조에 맞게 조정 가능) |
| `header-height`     | 56px | 상단 헤더 높이 (있을 경우) |

> 작은 보조 버튼은 32px 높이 별도 (가이드의 `button-sm` 규칙 시 추가 정의).

---

## 4. 라운드 토큰

| 이름 | 권장 값 | 용도 |
|---|---|---|
| `radius-sm`     | 4px  | 작은 요소, 사이드바 강조 라인 |
| `radius-md`     | 8px  | 메시지 박스 / 일반 박스 |
| `radius-lg`     | 12px | 큰 컨테이너 |
| `radius-xl`     | 16px | 대형 모달 |
| `radius-card`   | 12px | 카드 (== `radius-lg` 동일 권장) |
| `radius-button` | 8px  | 버튼 (== `radius-md` 동일 권장) |
| `radius-input`  | 8px  | 입력창 (== `radius-md` 동일 권장) |
| `radius-badge`  | 999px | pill 형태 (캡슐) |

> 라운드는 카드·버튼·입력창 사이에서 **시각적 일관성**을 우선합니다.

---

## 5. 테두리 / 그림자

| 이름 | 권장 값 | 용도 |
|---|---|---|
| `border-width` | 1px | 모든 보더 기본 굵기 |
| `card-border`  | `border-width` solid `border` | 카드 보더 |
| `card-shadow`  | `0 1px 2px rgba(20, 30, 24, 0.04), 0 4px 8px rgba(20, 30, 24, 0.04)` | 카드 기본 그림자 (매우 약함) |
| `hover-shadow` | `0 2px 6px rgba(20, 30, 24, 0.06), 0 8px 16px rgba(20, 30, 24, 0.06)` | 클릭 가능한 카드 hover |
| `focus-ring`   | `0 0 0 3px rgba(31, 61, 43, 0.18)` | 입력·버튼 포커스 외곽선 (포인트 컬러 18% 투명) |

> 그림자는 의도적으로 약하게. "떠 있는 카드"보다 "정돈된 흰 종이" 느낌.

---

## 6. 타이포그래피

### 6.1 폰트 패밀리

- 한국어: `Pretendard`, `system-ui`, `-apple-system`, `Segoe UI`, `Roboto`, sans-serif (실제 적용 시 결정).
- 모노스페이스 (시간 / 숫자 정렬용 옵션): `JetBrains Mono`, `Consolas`, monospace.

### 6.2 텍스트 토큰

| 이름 | 크기 / 행간 / 굵기 | 용도 |
|---|---|---|
| `page-title`   | 22px / 1.4 / 600 | 페이지 상단 제목 |
| `section-title`| 18px / 1.4 / 600 | 큰 섹션 제목 |
| `card-title`   | 16px / 1.5 / 600 | 카드 헤더 제목 |
| `body`         | 14px / 1.5 / 400 | 본문 / 폼 / 표 본문 |
| `small`        | 13px / 1.4 / 400 | 보조 본문 |
| `caption`      | 12px / 1.4 / 400 | 도움말 / 예시 / placeholder 부가 |
| `badge-text`   | 12px / 1.2 / 600 | badge / pill 텍스트 (소형 굵게) |
| `table-header` | 13px / 1.4 / 600 | 표 헤더 |
| `table-body`   | 14px / 1.5 / 400 | 표 본문 |

### 6.3 규칙

- 본문 글자가 너무 작아지지 않도록 14px 하한 권장.
- 굵기는 400 / 500 / 600 만 사용 (700 은 강조 한정).
- 한국어 환경에서 letter-spacing 은 0 또는 -0.01em 권장.

---

## 7. 토큰 사용 예시 (코드는 미적용)

> 실제 적용 단계에서 아래와 같은 매핑이 가능하도록 토큰을 정리했습니다.
> 현재 단계에서는 **참고용 의사코드**일 뿐 실제 CSS 파일에 반영하지 않습니다.

```css
:root {
  --background: #F6F7F4;
  --surface: #F1F2EE;
  --card: #FFFFFF;

  --primary: #1F3D2B;
  --primary-hover: #16301F;
  --primary-soft: #E2EBE0;

  --text-primary: #1A1F1B;
  --text-secondary: #5C6660;
  --text-muted: #8C938E;
  --border: #E5E7E2;

  --success: #3F8E5C;       --success-soft: #E0F0E5;
  --warning: #A86A1B;       --warning-soft: #F7ECCC;
  --danger:  #A8392B;       --danger-soft:  #F4DDD8;
  --info:    #3A6F75;       --info-soft:    #DBE9EB;
  --disabled:#C8CCC6;

  --page-padding: 24px;
  --section-gap: 24px;
  --card-padding: 20px;
  --card-gap: 16px;
  --table-cell-padding: 12px;
  --form-gap: 16px;

  --input-height: 40px;
  --button-height: 40px;
  --table-row-height: 48px;
  --badge-height: 22px;
  --sidebar-width: 224px;
  --header-height: 56px;

  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-card: var(--radius-lg);
  --radius-button: var(--radius-md);
  --radius-input: var(--radius-md);
  --radius-badge: 999px;

  --border-width: 1px;
  --card-shadow: 0 1px 2px rgba(20,30,24,0.04), 0 4px 8px rgba(20,30,24,0.04);
  --hover-shadow: 0 2px 6px rgba(20,30,24,0.06), 0 8px 16px rgba(20,30,24,0.06);
  --focus-ring: 0 0 0 3px rgba(31, 61, 43, 0.18);
}
```

> 위 블록은 **참고용 의사코드**이며 현재 단계에서는 어떤 CSS 파일에도 작성하지 않습니다.

---

## 8. 변경 / 우선순위

- 본 토큰 값은 디자인 적용 단계에서 미세 조정 가능.
- 큰 변경 (포인트 컬러 변경, 라운드 / 폰트 패밀리 변경 등)이 발생하면 [AI_REQUIREMENTS_OVERRIDES.md](AI_REQUIREMENTS_OVERRIDES.md) 에 이력으로 남기고, 본 문서를 갱신.
- 다른 디자인 문서와 충돌하면 [AI_CURRENT_DECISIONS.md](AI_CURRENT_DECISIONS.md) 의 결정과 본 토큰을 우선합니다.

---

## 9. 적용 시점 (재확인)

본 토큰의 실제 코드 적용은 AI 기능 구현·검증·회귀 검증이 모두 끝난 후, [AI_UI_UX_DESIGN_PLAN.md § 11](AI_UI_UX_DESIGN_PLAN.md) 체크리스트가 모두 충족된 뒤에 진행합니다.

이번 단계에서는 **CSS 변수, Tailwind config, SCSS, 인라인 스타일을 모두 수정하지 않습니다.**
