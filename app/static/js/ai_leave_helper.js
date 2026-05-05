// AI 휴무 도우미 — Phase 8 ai_leave (정규식 기반, 외부 LLM 미사용).
// commands router 의 parse / approve / reject endpoint 사용 (예약 도우미와 동일).
// intent="create_leave" 는 백엔드 router 가 자연어에 휴무 키워드 (휴무/반차/연차/오프) 보고 자동 분기.

function _aiLeaveHelperData() {
  return {
    open: true,
    busy: false,
    raw_text: "",
    error: "",
    command_id: null,
    result: null,
    approve_memo: "",
    approved_payload: null,

    init() {},

    _token() {
      return (
        localStorage.getItem("dosu_admin_token") ||
        window.adminToken ||
        ""
      );
    },

    _headers() {
      const t = this._token();
      const h = { "Content-Type": "application/json" };
      if (t) h["X-Admin-Token"] = t;
      return h;
    },

    statusBadgeClass() {
      if (!this.result) return "ai-helper-badge--info";
      const s = this.result.status;
      if (s === "executed" || s === "needs_approval") return "ai-helper-badge--success";
      if (s === "validation_failed" || s === "rejected" || s === "failed") return "ai-helper-badge--danger";
      return "ai-helper-badge--warning";
    },

    statusBadgeText() {
      const s = this.result ? this.result.status : "";
      const map = {
        needs_approval: "승인 대기",
        validation_failed: "검증 실패",
        executed: "등록됨",
        rejected: "거부됨",
        failed: "실패",
        needs_clarification: "정보 부족",
        patient_selection_required: "치료사 선택 필요",
      };
      return map[s] || s || "대기";
    },

    async onParse() {
      this.error = "";
      this.approved_payload = null;
      const txt = (this.raw_text || "").trim();
      if (!txt) return;
      const today = new Date();
      this.busy = true;
      try {
        const r = await fetch("/api/ai/commands/parse", {
          method: "POST",
          headers: this._headers(),
          body: JSON.stringify({
            raw_text: txt,
            current_calendar_year: today.getFullYear(),
            current_calendar_month: today.getMonth() + 1,
            today_iso: today.toISOString().slice(0, 10),
          }),
        });
        if (r.status === 401) {
          this.error = "관리자 인증이 필요합니다. 우측 상단 🔒 버튼으로 로그인 후 다시 시도해주세요.";
          return;
        }
        const body = await r.json();
        if (!r.ok || !body.ok) {
          this.error = body.message || "분석 실패";
          return;
        }
        // 백엔드가 자연어에 휴무 키워드 없는 경우 create_appointment 흐름으로 응답할 수도 있음
        if (body.result && body.result.intent !== "create_leave") {
          this.error = "휴무 명령으로 인식되지 않았습니다. '휴무' / '반차' / '연차' / '오프' 키워드를 포함해주세요.";
          return;
        }
        this.command_id = body.command_id;
        this.result = body.result;
      } catch (e) {
        this.error = "네트워크 오류: " + e.message;
      } finally {
        this.busy = false;
      }
    },

    async onSelectTherapist(therapist_id) {
      // 동명 치료사 선택 — 현재는 raw_text 에 치료사 이름 + 추가 식별자 명시 안내 (re-parse)
      // 향후 commands router 에 select-therapist endpoint 추가 가능
      this.error = "동명 치료사가 있어 자동 선택 ⊥. 명령에 치료사 식별자를 추가해주세요. (예: 'X치료사 (사번)')";
      // 선택된 id 만 표시 (사용자 안내용)
      void therapist_id;
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
            (body.error === "missing_fields" ? "치료사/날짜/휴무유형 모두 필요합니다." : "승인 실패");
          return;
        }
        this.approved_payload = body.result_payload || {};
        if (this.result) this.result.status = body.execution_status || "executed";
        // 부모 화면에 갱신 hint
        if (typeof window.refreshLeaveCalendar === "function") {
          try { window.refreshLeaveCalendar(); } catch (e) {}
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
      this.approve_memo = "";
      this.approved_payload = null;
    },
  };
}

window.aiLeaveHelper = _aiLeaveHelperData;

function _aiLeaveHelperRegister() {
  if (window.Alpine && typeof window.Alpine.data === "function") {
    window.Alpine.data("aiLeaveHelper", _aiLeaveHelperData);
    return true;
  }
  return false;
}
if (!_aiLeaveHelperRegister()) {
  document.addEventListener("alpine:init", _aiLeaveHelperRegister);
}

