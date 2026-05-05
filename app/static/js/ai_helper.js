// AI 예약 도우미 — Alpine.js 컴포넌트.
// 단계: parse → (select-patient | select-treatment) → approve / reject.
// SSOT § 11 endpoint 호출. 모든 호출은 X-Admin-Token 헤더 (관리자 인증).
//
// 본 파일은 자체적으로 토큰을 가져오지 않음 — 기존 admin 화면의 sessionStorage 또는
// window.adminToken 등을 참조 (프로젝트 컨벤션 준수).

function _aiHelperData() {
  return {
    open: true,
    busy: false,
    raw_text: "",
    error: "",
    command_id: null,
    result: null,
    diagnostics: null,
    approve_memo: "",
    approved_payload: null,

    init() {
      // 후처리 hook 자리. 현재 없음.
    },

    _token() {
      // 기존 admin 화면 컨벤션 (main.html § getToken) 정합 — localStorage 'dosu_admin_token'.
      return (
        localStorage.getItem("dosu_admin_token") ||
        window.adminToken ||
        ""
      );
    },

    _headers() {
      const token = this._token();
      const h = { "Content-Type": "application/json" };
      if (token) h["X-Admin-Token"] = token;
      return h;
    },

    statusBadgeClass() {
      if (!this.result) return "ai-helper-badge--info";
      const s = this.result.status;
      if (s === "executed" || s === "needs_approval") return "ai-helper-badge--success";
      if (
        s === "patient_selection_required" ||
        s === "treatment_selection_required" ||
        s === "treatment_alias_conflict" ||
        s === "patient_not_found"
      )
        return "ai-helper-badge--warning";
      if (s === "validation_failed" || s === "patient_mismatch" || s === "rejected" || s === "failed")
        return "ai-helper-badge--danger";
      return "ai-helper-badge--info";
    },

    statusBadgeText() {
      const s = this.result ? this.result.status : "";
      const map = {
        needs_approval: "승인 대기",
        patient_selection_required: "환자 선택 필요",
        patient_mismatch: "환자 불일치",
        patient_not_found: "환자 없음 (신환)",
        treatment_selection_required: "치료항목 선택 필요",
        treatment_alias_conflict: "치료항목 충돌",
        treatment_not_found: "치료항목 없음",
        validation_failed: "검증 실패",
        executed: "등록됨",
        rejected: "거부됨",
        failed: "실패",
      };
      return map[s] || s || "대기";
    },

    async onParse() {
      this.error = "";
      this.approved_payload = null;
      const txt = (this.raw_text || "").trim();
      if (!txt) return;
      const today = new Date();
      const today_iso = today.toISOString().slice(0, 10);
      this.busy = true;
      try {
        const r = await fetch("/api/ai/commands/parse", {
          method: "POST",
          headers: this._headers(),
          body: JSON.stringify({
            raw_text: txt,
            current_calendar_year: today.getFullYear(),
            current_calendar_month: today.getMonth() + 1,
            today_iso: today_iso,
          }),
        });
        if (r.status === 401) {
          this.error = "관리자 인증이 필요합니다. 관리자 탭에서 로그인 후 다시 시도해주세요.";
          return;
        }
        const body = await r.json();
        if (!r.ok || !body.ok) {
          this.error = body.message || "분석 실패";
          return;
        }
        this.command_id = body.command_id;
        this.result = body.result;
        this.diagnostics = body.diagnostics;
      } catch (e) {
        this.error = "네트워크 오류: " + e.message;
      } finally {
        this.busy = false;
      }
    },

    async onSelectPatient(patient_id) {
      if (!this.command_id || !patient_id) return;
      this.error = "";
      this.busy = true;
      try {
        const r = await fetch(
          `/api/ai/commands/${this.command_id}/select-patient`,
          {
            method: "POST",
            headers: this._headers(),
            body: JSON.stringify({ patient_id: patient_id }),
          }
        );
        const body = await r.json();
        if (!r.ok || !body.ok) {
          this.error = body.message || "환자 선택 실패";
          return;
        }
        this.result = body.result;
        this.diagnostics = body.diagnostics;
      } catch (e) {
        this.error = "네트워크 오류: " + e.message;
      } finally {
        this.busy = false;
      }
    },

    async onApprove() {
      if (!this.command_id) return;
      this.error = "";
      this.busy = true;
      try {
        const r = await fetch(
          `/api/ai/commands/${this.command_id}/approve`,
          {
            method: "POST",
            headers: this._headers(),
            body: JSON.stringify({ memo: this.approve_memo || null }),
          }
        );
        const body = await r.json();
        if (!r.ok) {
          this.error = body.detail || body.message || "승인 실패";
          return;
        }
        if (!body.ok) {
          this.error =
            body.error_message ||
            (body.error === "approval_blocked" ? "승인 불가 상태입니다." : "승인 실패");
          // result 도 갱신해서 사용자가 다음 단계 알 수 있게
          if (body.result) this.result = body.result;
          return;
        }
        this.approved_payload = body.result_payload || {};
        // status badge 도 executed 로 갱신
        if (this.result) this.result.status = body.execution_status || "executed";
        // 부모 화면에 새로고침 hint (기존 캘린더 / 표 / 통계)
        if (typeof window.refreshDayBoard === "function") {
          try { window.refreshDayBoard(); } catch (e) {}
        }
      } catch (e) {
        this.error = "네트워크 오류: " + e.message;
      } finally {
        this.busy = false;
      }
    },

    async onReject() {
      if (!this.command_id) return;
      this.error = "";
      this.busy = true;
      try {
        const r = await fetch(
          `/api/ai/commands/${this.command_id}/reject`,
          {
            method: "POST",
            headers: this._headers(),
            body: JSON.stringify({ reason: "사용자 취소" }),
          }
        );
        const body = await r.json();
        if (!r.ok || !body.ok) {
          this.error = body.message || "거부 실패";
          return;
        }
        if (this.result) this.result.status = "rejected";
      } catch (e) {
        this.error = "네트워크 오류: " + e.message;
      } finally {
        this.busy = false;
      }
    },

    onReset() {
      this.raw_text = "";
      this.error = "";
      this.command_id = null;
      this.result = null;
      this.diagnostics = null;
      this.approve_memo = "";
      this.approved_payload = null;
    },
  };
}

// Alpine.data 등록 (alpine:init 표준) + Alpine 이 이미 로드되어 있으면 즉시 등록.
// 또한 window.aiHelper 호환 유지 (다른 코드가 함수 호출형 사용 시).
window.aiHelper = _aiHelperData;

function _aiHelperRegister() {
  if (window.Alpine && typeof window.Alpine.data === "function") {
    window.Alpine.data("aiHelper", _aiHelperData);
    return true;
  }
  return false;
}
if (!_aiHelperRegister()) {
  document.addEventListener("alpine:init", _aiHelperRegister);
}

