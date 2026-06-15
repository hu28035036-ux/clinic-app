let THERAPISTS = [], PATIENTS = [], LAST_APPTS = {}, THERAPIST_LEAVES = [];
const BOARD_EMPLOYEE_FILTER_KEY = 'dosu_board_selected_employee_ids';
// AI 보조: /api/ai/health 캐시
let AI_HEALTH = null;
// 대량 데이터 대응: id → 환자 객체 Map (O(1) 조회). loadMasters() 에서 채워짐.
let PATIENTS_BY_ID = new Map();
let EMPLOYEES_ALL = [];   // 전체 직원 (예약 모달 등에서 사용)
let DOCTORS = [];         // 진료항목 처리 가능 직원
let CURRENT_CATEGORY = 'manual';  // 레거시 호환용. 4단계에서 제거 예정.
let MINI_APPT_COUNTS = {};
let MINI_LEAVE_MAP = {};
let MINI_RENDER_KEY = 0;

function getBoardSelectableEmployees(){
  return THERAPISTS
    .filter(t => t.active !== false)
    .filter(t => t.can_manual !== false);
}

function readBoardSelectedEmployeeIds(){
  try {
    const raw = localStorage.getItem(BOARD_EMPLOYEE_FILTER_KEY);
    if(raw === null) return null;
    const parsed = JSON.parse(raw);
    if(!Array.isArray(parsed)) return null;
    return parsed.map(String);
  } catch(e){
    return null;
  }
}

function getBoardVisibleTherapists(){
  const candidates = getBoardSelectableEmployees();
  const selected = readBoardSelectedEmployeeIds();
  if(selected === null) return candidates;
  const selectedSet = new Set(selected);
  return candidates.filter(t => selectedSet.has(t.id));
}

function getBoardVisibleTherapistsIncludingCurrent(currentId){
  const visible = getBoardVisibleTherapists();
  if(!currentId || visible.some(t => t.id === currentId)) return visible;
  const current = THERAPISTS.find(t => t.id === currentId);
  return current ? [...visible, current] : visible;
}

function boardEmployeeFilterLabel(){
  const total = getBoardSelectableEmployees().length;
  const selected = readBoardSelectedEmployeeIds();
  if(selected === null) return `전체 ${total}`;
  return `${getBoardVisibleTherapists().length}/${total}`;
}

function renderBoardEmployeePicker(){
  const employees = getBoardSelectableEmployees();
  const selected = readBoardSelectedEmployeeIds();
  const selectedSet = selected === null ? null : new Set(selected);
  const rows = employees.map(t => {
    const checked = selectedSet === null || selectedSet.has(t.id);
    return `<label class="board-employee-option">
      <input type="checkbox" class="board-employee-chk" value="${t.id}" ${checked?'checked':''}>
      <span class="color-dot" style="background:${t.color||'#9CA3AF'}"></span>
      <span>${t.name}</span>
    </label>`;
  }).join('');
  return `<div class="board-employee-picker" id="board-employee-picker" style="display:none" onclick="event.stopPropagation()">
    <div class="board-employee-picker-head">
      <b>예약표 표시 직원</b>
      <span class="muted">${employees.length}명</span>
    </div>
    <div class="board-employee-picker-list">
      ${rows || '<div class="muted" style="padding:8px">표시 가능한 직원 없음</div>'}
    </div>
    <div class="board-employee-picker-actions">
      <button class="mini" onclick="setBoardEmployeeSelection('all')">전체</button>
      <button class="mini" onclick="setBoardEmployeeSelection('none')">해제</button>
      <button class="primary mini" onclick="applyBoardEmployeeSelection()">적용</button>
    </div>
  </div>`;
}

function toggleBoardEmployeePicker(event){
  event.stopPropagation();
  const picker = document.getElementById('board-employee-picker');
  if(!picker) return;
  picker.style.display = picker.style.display === 'none' ? 'block' : 'none';
}

function closeBoardEmployeePicker(){
  const picker = document.getElementById('board-employee-picker');
  if(picker) picker.style.display = 'none';
}

function setBoardEmployeeSelection(mode){
  if(mode === 'all'){
    localStorage.removeItem(BOARD_EMPLOYEE_FILTER_KEY);
  } else if(mode === 'none'){
    localStorage.setItem(BOARD_EMPLOYEE_FILTER_KEY, JSON.stringify([]));
  }
  renderDayBoard();
}

function applyBoardEmployeeSelection(){
  const ids = Array.from(document.querySelectorAll('.board-employee-chk:checked')).map(x => x.value);
  localStorage.setItem(BOARD_EMPLOYEE_FILTER_KEY, JSON.stringify(ids));
  renderDayBoard();
}

document.addEventListener('click', closeBoardEmployeePicker);

// 치료항목 메타 — 서버 /api/treatment-meta 에서 로드 (프론트 하드코딩 폴백 없음)
let TX_META = {
  treatment_codes: [],
  treatment_names: {},
  treatment_category: {},
  treatment_category_name: {},
  treatment_short: {},
  treatment_minutes: {},
  treatment_role: {},
  treatment_show: {},
  doctor_treatments: [],
  therapist_treatments: [],
  manual_treatments: [],
  count_increment: {},
  eswt_code: '',
  all_treatments: [],
  employee_categories: [],
};

// 호환용 (이전 코드가 TX_MINUTES 참조 시)
let TX_MINUTES = TX_META.treatment_minutes;
let MANUAL_SLOT_LIMIT = null;

async function loadTreatmentMeta(){
  try {
    const m = await (await fetch('/api/treatment-meta')).json();
    if(m && m.treatment_codes) {
      TX_META = m;
      TX_MINUTES = m.treatment_minutes || TX_MINUTES;
      if(Array.isArray(m.employee_categories)) EMPLOYEE_CATEGORIES = m.employee_categories;
    }
  } catch(e){}
  try {
    const s = await (await fetch('/api/system-settings')).json();
    if(s){
      MANUAL_SLOT_LIMIT = s.manual_slot_limit;
    }
  } catch(e){}
}

// 호환: 기존 코드가 참조할 수 있는 옛 상수들. 실제 값은 TX_META(DB) 기준.
const TREATMENTS = { manual: [], treatment: [] };

function treatmentNameToCode(name){
  const target = (name || '').trim();
  if(!target) return '';
  for(const [code, txName] of Object.entries(TX_META.treatment_names || {})){
    if(txName === target) return code;
  }
  return '';
}

function treatmentShortByName(name){
  const code = treatmentNameToCode(name);
  if(!code) return (name || '').trim();
  return TX_META.treatment_short[code] || TX_META.treatment_names[code] || code;
}

function shortTreatments(memo){
  if(!memo) return '';
  const m = memo.match(/^\[([^\]]+)\]/);
  if(!m) return '';
  return m[1].split(',').map(s => treatmentShortByName(s)).join('·');
}

// 예약 객체 → 치료항목 코드 배열 (새 스키마 또는 레거시 메모 양쪽 지원)
function apptTreatmentCodes(ep){
  if(ep && Array.isArray(ep.treatment_codes) && ep.treatment_codes.length){
    return ep.treatment_codes;
  }
  const m = (ep && ep.memo || '').match(/^\[([^\]]+)\]/);
  if(!m) return [];
  return m[1].split(',').map(s => treatmentNameToCode(s)).filter(Boolean);
}

function txShort(code){ return TX_META.treatment_short[code] || code; }
function txName(code){ return TX_META.treatment_names[code] || code; }
function txByCode(code){ return (TX_META.all_treatments || []).find(t => t.code === code) || null; }
function txCategoryId(code){ return (TX_META.treatment_category || {})[code] || ''; }
function txCategoryName(code){ return (TX_META.treatment_category_name || {})[code] || ''; }
function activeTreatmentCategories(){
  const cats = (TX_META.employee_categories || EMPLOYEE_CATEGORIES || []).filter(c => c.active !== false);
  const used = new Set((TX_META.treatment_codes || []).map(code => txCategoryId(code)).filter(Boolean));
  if(!used.size) return cats;
  return cats.filter(c => used.has(c.id));
}
function treatmentCodesForCategory(categoryId){
  const codes = TX_META.treatment_codes || [];
  const assigned = codes.filter(code => txCategoryId(code));
  if(!categoryId || assigned.length) return codes.filter(code => !categoryId || txCategoryId(code) === categoryId);
  const cats = TX_META.employee_categories || EMPLOYEE_CATEGORIES || [];
  const cat = cats.find(c => c.id === categoryId) || {};
  if(cat.default_can_doctor_treatment && !cat.default_can_manual){
    return codes.filter(isDoctorCode);
  }
  const therapistCodes = codes.filter(isTherapistCode);
  return therapistCodes.length ? therapistCodes : codes;
}
function employeeCanSelectedTreatments(employee, codes){
  if(!employee || !codes || !codes.length) return true;
  const selectedIds = employee.treatment_ids || [];
  if(employee.treatment_override_enabled === true){
    return codes.every(code => {
      const tx = txByCode(code);
      return tx && selectedIds.includes(tx.id);
    });
  }
  if(employee.category_id){
    return codes.every(code => {
      const categoryId = txCategoryId(code);
      return !categoryId || categoryId === employee.category_id;
    });
  }
  return true;
}
function isManualCode(code){
  // 도수치료 = 치료사 역할 + 체외충격파 제외
  return TX_META.treatment_role[code] === 'therapist' && !isEswtCode(code);
}
function isDoctorCode(code){ return TX_META.treatment_role[code] === 'doctor'; }
function isTherapistCode(code){ return TX_META.treatment_role[code] === 'therapist'; }
function isEswtCode(code){ return !!TX_META.eswt_code && code === TX_META.eswt_code; }

// 예약탭이 현재 화면에 보이는지 판정 — 백그라운드 polling 가드용
// (다른 탭 보고 있을 땐 예약 fetch 를 쉬어서 서버 부담·네트워크 낭비 줄임)
function _isReserveTabActive(){
  const pane = document.getElementById('tab-reserve');
  return !!(pane && pane.classList.contains('active'));
}

function switchTab(id, btn){
  document.querySelectorAll('.tab-pane').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
  document.getElementById(id).classList.add('active'); btn.classList.add('active');
  if(id==='tab-patients'){ LAST_APPTS={}; pmSearch(); }
  else if(id==='tab-therapists'){
    // ⚠ 서브탭 상태 강제 리셋 — 이전에 '휴무일 관리' 서브탭에 있다가 다른 탭 다녀오면
    //   서브탭 active 가 휴무일에 남아 있어서 직원탭 첫 클릭 시 직원관리 화면이 안 보이는 현상 방지.
    //   switchTherapistTab('manage', ...) 를 명시 호출해 active 클래스와 로딩을 일관되게 처리.
    const manageBtn = document.getElementById('therapist-subtab-manage');
    if(manageBtn){
      switchTherapistTab('manage', manageBtn);
    } else {
      loadTherapistsSheet();
    }
  }
  else if(id==='tab-inventory'){
    loadInventorySheet();
  }
  else if(id==='tab-records'){
    loadRecordsSheet();
  }
  else if(id==='tab-reserve'){
    // 복귀 시 즉시 최신화 — 다른 탭 보는 동안 polling 이 쉬었으므로 stale 데이터 방지.
    // fire-and-forget: 사용자 체감 속도 우선 (await 쓰면 탭 전환이 멈춘 듯 보임).
    try { renderDayBoard(); } catch(e) {}
    try { loadTodayList();  } catch(e) {}
    try { if (window._miniCal) reloadMiniCalendar(window._miniCal.getDate()); } catch(e) {}
  }
  else if(id==='tab-admin') loadTreatmentsCard();
}

let RECORDS_DATA = null;
let RECORDS_ACTIVE_TAB = 'manual';
let RECORDS_SELECTED_DATE = '';
const RECORD_WEEKDAY_LABELS = ['월', '화', '수', '목', '금', '토', '일'];

function recordDateStr(d){
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function recordDateFromStr(value){
  const parts = (value || recordDateStr(new Date())).split('-').map(Number);
  return new Date(parts[0], (parts[1] || 1) - 1, parts[2] || 1);
}

function recordAddDays(d, amount){
  const next = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  next.setDate(next.getDate() + amount);
  return next;
}

function recordWeekDates(selectedDate){
  const apiDates = RECORDS_DATA?.week_dates || [];
  if(apiDates.length === 7) return apiDates;
  const selected = recordDateFromStr(selectedDate);
  const mondayOffset = (selected.getDay() + 6) % 7;
  const monday = recordAddDays(selected, -mondayOffset);
  return Array.from({length: 7}, (_, idx) => recordDateStr(recordAddDays(monday, idx)));
}

function recordShortDateLabel(dateStr){
  const parts = (dateStr || '').split('-');
  if(parts.length !== 3) return dateStr || '';
  return `${Number(parts[1])}/${Number(parts[2])}`;
}

function recordWeekRangeLabel(dates){
  if(!dates.length) return '';
  const first = dates[0].replace(/-/g, '.');
  const last = dates[dates.length - 1].slice(5).replace(/-/g, '.');
  return `${first} - ${last}`;
}

function recordSelectedDate(){
  const el = document.getElementById('record-date');
  const current = (el?.value || RECORDS_SELECTED_DATE || '').trim();
  RECORDS_SELECTED_DATE = current || recordDateStr(new Date());
  if(el && !el.value) el.value = RECORDS_SELECTED_DATE;
  return RECORDS_SELECTED_DATE;
}

function recordActiveSetting(){
  return (RECORDS_DATA?.tabs || []).find(t => t.tab_key === RECORDS_ACTIVE_TAB)
    || (RECORDS_DATA?.tabs || [])[0]
    || {tab_key:'manual', label:'메뉴얼', category_id:''};
}

function recordEmployeesForCategory(categoryId){
  return (RECORDS_DATA?.employees || [])
    .filter(e => e.active !== false)
    .filter(e => categoryId && e.category_id === categoryId)
    .sort((a,b) => (a.sort_order||0) - (b.sort_order||0) || (a.name||'').localeCompare(b.name||'', 'ko'));
}

function recordCategoryOptions(selectedId){
  const cats = RECORDS_DATA?.categories || [];
  return '<option value="">과 선택</option>' + cats.map(c =>
    `<option value="${escapeAttr(c.id)}" ${c.id===selectedId?'selected':''}>${escapeHtml(c.name || '')}</option>`
  ).join('');
}

function recordEmployeeOptions(categoryId, selectedId){
  const employees = recordEmployeesForCategory(categoryId);
  if(!categoryId) return '<option value="">과를 먼저 선택</option>';
  if(!employees.length) return '<option value="">해당 과 직원 없음</option>';
  return '<option value="">직원 선택</option>' + employees.map(e =>
    `<option value="${escapeAttr(e.id)}" ${e.id===selectedId?'selected':''}>${escapeHtml(e.name || '')}</option>`
  ).join('');
}

async function loadRecordsSheet(){
  const subtabs = document.getElementById('record-subtabs');
  const list = document.getElementById('record-list');
  if(subtabs) subtabs.innerHTML = '<span class="muted">불러오는 중...</span>';
  if(list) list.innerHTML = '';
  try {
    const recordDate = recordSelectedDate();
    const params = new URLSearchParams({record_date: recordDate});
    const r = await fetch(`/api/records?${params.toString()}`);
    const data = await r.json().catch(() => ({}));
    if(!r.ok) throw new Error(data.detail || r.statusText);
    RECORDS_DATA = data;
    RECORDS_SELECTED_DATE = data.record_date || recordDate;
    if(!(data.tabs || []).some(t => t.tab_key === RECORDS_ACTIVE_TAB)){
      RECORDS_ACTIVE_TAB = (data.tabs || [])[0]?.tab_key || 'manual';
    }
    renderRecordsSheet();
  } catch(e) {
    if(subtabs) subtabs.innerHTML = '';
    if(list) list.innerHTML = `<p class="muted" style="padding:12px;color:#DC2626;">기록 조회 실패: ${escapeHtml(e.message || e)}</p>`;
  }
}

function renderRecordsSheet(){
  const data = RECORDS_DATA || {tabs:[], categories:[], employees:[], entries:[], counts:{}};
  const setting = recordActiveSetting();
  const categoryId = setting.category_id || '';
  const selectedDate = data.record_date || recordSelectedDate();
  const tabEntries = (data.entries || []).filter(e => e.tab_key === setting.tab_key);
  const employees = recordEmployeesForCategory(categoryId);
  const countMap = (data.counts || {})[setting.tab_key] || {};

  const title = document.getElementById('record-title');
  if(title) title.textContent = `▥ ${setting.label || '기록'}`;

  const dateEl = document.getElementById('record-date');
  if(dateEl) dateEl.value = selectedDate;

  renderRecordsWeekdays(selectedDate, setting);

  const subtabs = document.getElementById('record-subtabs');
  if(subtabs){
    subtabs.innerHTML = (data.tabs || []).map(t => `
      <div class="record-subtab-wrap ${t.tab_key===setting.tab_key?'active':''}">
        <button type="button" class="record-subtab" onclick="selectRecordTab('${t.tab_key}')">${escapeHtml(t.label || '')}</button>
        <button type="button" class="record-tab-edit-btn" onclick="editRecordTabName('${t.tab_key}')" title="이름 수정" aria-label="이름 수정">✎</button>
      </div>
    `).join('');
  }

  const catEl = document.getElementById('record-category');
  if(catEl) catEl.innerHTML = recordCategoryOptions(categoryId);
  const empEl = document.getElementById('record-employee');
  if(empEl) empEl.innerHTML = recordEmployeeOptions(categoryId, empEl.value || '');

  const list = document.getElementById('record-list');
  if(list){
    const rows = tabEntries.map(entry => `
      <tr>
        <td>${escapeHtml(entry.chart_no || '-')}</td>
        <td><b>${escapeHtml(entry.patient_name || '-')}</b></td>
        <td>${escapeHtml(entry.employee_name || '-')}</td>
        <td class="record-actions">
          <button class="mini" onclick="editRecordEntry('${entry.id}')">수정</button>
          <button class="mini danger" onclick="deleteRecordEntry('${entry.id}')">삭제</button>
        </td>
      </tr>
    `).join('');
    list.innerHTML = rows ? `
      <table class="data-table record-table">
        <thead><tr><th>차트번호</th><th>성함</th><th>직원</th><th>관리</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    ` : '<div class="muted" style="padding:12px">선택한 날짜의 기록 없음</div>';
  }

  const counts = document.getElementById('record-counts');
  if(counts){
    const chips = employees.map(e => `
      <div class="record-count-chip">
        <span><span class="color-dot" style="background:${escapeAttr(e.color || '#9CA3AF')}"></span>${escapeHtml(e.name || '')}</span>
        <b>${Number(countMap[e.id] || 0).toLocaleString()}</b>
      </div>
    `).join('');
    counts.innerHTML = `
      <div class="record-count-title">직원별 개수 <span class="muted">(${escapeHtml(selectedDate)})</span></div>
      <div class="record-count-grid">${chips || '<span class="muted">표시할 직원 없음</span>'}</div>
    `;
  }
}

function renderRecordsWeekdays(selectedDate, setting){
  const box = document.getElementById('record-weekdays');
  if(!box) return;
  const dates = recordWeekDates(selectedDate);
  const weekCounts = (RECORDS_DATA?.week_counts || {})[setting.tab_key] || {};
  const dayButtons = dates.map((dateStr, idx) => {
    const active = dateStr === selectedDate ? 'active' : '';
    const count = Number(weekCounts[dateStr] || 0);
    return `<button type="button" class="record-weekday ${active}" onclick="selectRecordsDate('${dateStr}')">
      <span>${RECORD_WEEKDAY_LABELS[idx]}</span>
      <strong>${recordShortDateLabel(dateStr)}</strong>
      ${count ? `<em>${count}</em>` : '<em></em>'}
    </button>`;
  }).join('');
  box.innerHTML = `
    <div class="record-week-nav">
      <button type="button" class="mini" onclick="moveRecordsWeek(-1)" title="지난 주">‹</button>
      <b>${escapeHtml(recordWeekRangeLabel(dates))}</b>
      <button type="button" class="mini" onclick="moveRecordsWeek(1)" title="다음 주">›</button>
    </div>
    <div class="record-weekday-grid">${dayButtons}</div>
  `;
}

function changeRecordsDate(){
  RECORDS_SELECTED_DATE = _v('record-date') || recordDateStr(new Date());
  loadRecordsSheet();
}

function setRecordsToday(){
  RECORDS_SELECTED_DATE = recordDateStr(new Date());
  const el = document.getElementById('record-date');
  if(el) el.value = RECORDS_SELECTED_DATE;
  loadRecordsSheet();
}

function selectRecordsDate(dateStr){
  RECORDS_SELECTED_DATE = dateStr || recordDateStr(new Date());
  const el = document.getElementById('record-date');
  if(el) el.value = RECORDS_SELECTED_DATE;
  loadRecordsSheet();
}

function moveRecordsWeek(delta){
  const next = recordAddDays(recordDateFromStr(recordSelectedDate()), Number(delta || 0) * 7);
  selectRecordsDate(recordDateStr(next));
}

function selectRecordTab(tabKey){
  RECORDS_ACTIVE_TAB = tabKey || 'manual';
  renderRecordsSheet();
}

function editRecordTabName(tabKey){
  const tab = (RECORDS_DATA?.tabs || []).find(t => t.tab_key === tabKey);
  if(!tab) return;
  showModal(`<h3>기록 탭 이름 수정</h3>
    <label>이름 <input id="record-tab-name-input" value="${escapeAttr(tab.label || '')}" maxlength="30" autofocus></label>
    <div class="modal-actions"><button onclick="closeModal()">취소</button>
      <button class="primary" onclick="saveRecordTabName('${tabKey}')">저장</button></div>`);
}

async function saveRecordTabName(tabKey){
  const tab = (RECORDS_DATA?.tabs || []).find(t => t.tab_key === tabKey);
  if(!tab) return;
  await saveRecordTabSetting(tabKey, {
    label: _v('record-tab-name-input') || tab.label,
    category_id: tab.category_id || '',
  }, true);
}

async function saveRecordTabCategory(){
  const tab = recordActiveSetting();
  await saveRecordTabSetting(tab.tab_key, {
    label: tab.label || '',
    category_id: _v('record-category') || '',
  }, false);
}

async function saveRecordTabSetting(tabKey, body, closeAfter){
  const r = await fetch(`/api/records/tabs/${tabKey}`, {
    method:'PUT',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body),
  });
  if(!r.ok){ alert('저장 실패\n' + await _apiErrorText(r)); return; }
  if(closeAfter) closeModal();
  await loadRecordsSheet();
}

function recordEntryKeydown(event){
  if(event.key === 'Enter'){
    event.preventDefault();
    saveRecordEntry();
  }
}

async function saveRecordEntry(){
  const tab = recordActiveSetting();
  const body = {
    tab_key: tab.tab_key,
    record_date: recordSelectedDate(),
    chart_no: _v('record-chart-no'),
    patient_name: _v('record-patient-name'),
    employee_id: _v('record-employee'),
  };
  if(!body.chart_no && !body.patient_name){ alert('차트번호 또는 성함을 입력하세요'); return; }
  if(!body.employee_id){ alert('직원을 선택하세요'); return; }
  const r = await fetch('/api/records/entries', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body),
  });
  if(!r.ok){ alert('저장 실패\n' + await _apiErrorText(r)); return; }
  const chart = document.getElementById('record-chart-no');
  const name = document.getElementById('record-patient-name');
  if(chart) chart.value = '';
  if(name) name.value = '';
  await loadRecordsSheet();
  document.getElementById('record-chart-no')?.focus();
}

function editRecordEntry(entryId){
  const entry = (RECORDS_DATA?.entries || []).find(row => row.id === entryId);
  if(!entry) return;
  const tab = (RECORDS_DATA?.tabs || []).find(t => t.tab_key === entry.tab_key) || recordActiveSetting();
  const categoryId = tab.category_id || '';
  showModal(`<h3>기록 수정</h3>
    <label>날짜 <input id="record-edit-date" type="date" value="${escapeAttr(entry.record_date || recordSelectedDate())}"></label>
    <label>차트번호 <input id="record-edit-chart-no" type="text" maxlength="30" value="${escapeAttr(entry.chart_no || '')}"></label>
    <label>성함 <input id="record-edit-patient-name" type="text" maxlength="50" value="${escapeAttr(entry.patient_name || '')}"></label>
    <label>직원
      <select id="record-edit-employee">${recordEmployeeOptions(categoryId, entry.employee_id || '')}</select>
    </label>
    <div class="modal-actions"><button onclick="closeModal()">취소</button>
      <button class="primary" onclick="updateRecordEntry('${entry.id}')">저장</button></div>`);
}

async function updateRecordEntry(entryId){
  const body = {
    record_date: _v('record-edit-date') || recordSelectedDate(),
    chart_no: _v('record-edit-chart-no'),
    patient_name: _v('record-edit-patient-name'),
    employee_id: _v('record-edit-employee'),
  };
  if(!body.chart_no && !body.patient_name){ alert('차트번호 또는 성함을 입력하세요'); return; }
  if(!body.employee_id){ alert('직원을 선택하세요'); return; }
  const r = await fetch(`/api/records/entries/${entryId}`, {
    method:'PUT',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body),
  });
  if(!r.ok){ alert('수정 실패\n' + await _apiErrorText(r)); return; }
  const saved = await r.json().catch(() => ({}));
  RECORDS_SELECTED_DATE = saved.record_date || body.record_date || RECORDS_SELECTED_DATE;
  closeModal();
  await loadRecordsSheet();
}

async function deleteRecordEntry(entryId){
  if(!confirm('삭제하시겠습니까?')) return;
  const r = await fetch(`/api/records/entries/${entryId}`, {method:'DELETE'});
  if(!r.ok){ alert('삭제 실패\n' + await _apiErrorText(r)); return; }
  await loadRecordsSheet();
}

async function switchCategory(cat, btn){
  // 4단계: 도수/치료 분리 제거됨. 호환용 스텁.
  CURRENT_CATEGORY = cat || 'manual';
  await reloadMiniCalendar(window._miniCal ? window._miniCal.getDate() : new Date());
  await renderDayBoard();
  await loadTodayList();
}

async function switchAdminTab(name, btn){
  // 통계·시스템·데이터변환은 관리자 비밀번호 인증 필요
  if(name==='stats' || name==='system' || name==='convert' || name==='settlement'){
    if(!await ensureAdmin()) return;  // 취소 시 전환하지 않음
  }
  document.querySelectorAll('#tab-admin .sub-tab').forEach(b=>b.classList.remove('active'));
  document.querySelectorAll('.admin-pane').forEach(p=>p.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('admin-'+name).classList.add('active');
  if(name==='system'){ loadSystemForm(); loadAboutBox(); }
  if(name==='treatments') loadTreatmentsCard();
  if(name==='aggregate') initAggregate();
  if(name==='settlement') initSettlement();
  if(name==='stats') initStats();
  if(name==='convert') dcReset();
  if(name==='ai') loadAiSettingForm();
}
function switchTherapistTab(name, btn){
  document.querySelectorAll('#tab-therapists .sub-tab').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('#tab-therapists .admin-pane').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('therapist-' + name).classList.add('active');

  if(name === 'manage') loadTherapistsSheet();
  if(name === 'leave') loadLeaveCalendar();
}

async function openLeaveModal(dateStr){
  await loadMasters();
  const leaves = await loadTherapistLeaves(dateStr);
  const memo = leaves[0]?.memo || '';

  const selectedTypeMap = {};
  const selectedKindMap = {};
  leaves.forEach(x => {
    selectedTypeMap[x.therapist_id] = x.leave_type || 'full';
    selectedKindMap[x.therapist_id] = x.leave_kind || 'annual';
  });

  const rows = EMPLOYEES_ALL
  .filter(t => t.active !== false)
  .map(t => `
    <div class="leave-row">
      <label class="chk-item">
        <input type="checkbox" class="leave-ther-chk" value="${t.id}" ${selectedTypeMap[t.id] ? 'checked' : ''}>
        <span>
          <span class="color-dot" style="background:${t.color}"></span>
          <span class="leave-name-text">${t.name}</span>
        </span>
      </label>
      <select class="leave-type-sel" data-tid="${t.id}">
        <option value="full" ${selectedTypeMap[t.id] === 'full' ? 'selected' : ''}>종일</option>
        <option value="am" ${selectedTypeMap[t.id] === 'am' ? 'selected' : ''}>오전반차</option>
        <option value="pm" ${selectedTypeMap[t.id] === 'pm' ? 'selected' : ''}>오후반차</option>
      </select>
      <select class="leave-kind-sel" data-tid="${t.id}">
        <option value="annual"  ${selectedKindMap[t.id] === 'monthly' ? '' : 'selected'}>연차</option>
        <option value="monthly" ${selectedKindMap[t.id] === 'monthly' ? 'selected' : ''}>월차</option>
      </select>
    </div>
  `).join('');

  showModal(`
    <h3>🗓️ ${dateStr} 휴무자 설정</h3>
    <div style="max-height:320px;overflow-y:auto;border:1px solid var(--sky-100);padding:10px;border-radius:8px;background:#fff">
      ${rows || '<p class="muted">치료사 없음</p>'}
    </div>
    <label>메모
      <input id="leave-memo" value="${memo.replace(/"/g, '&quot;')}">
    </label>
    <div class="modal-actions">
      <button onclick="closeModal()">닫기</button>
      <button class="primary" onclick="saveLeaveDay('${dateStr}')">저장</button>
    </div>
  `);
}

async function saveLeaveDay(dateStr){
  const checkedIds = new Set(
    Array.from(document.querySelectorAll('.leave-ther-chk:checked')).map(x => x.value)
  );

  const items = Array.from(document.querySelectorAll('.leave-type-sel'))
    .filter(sel => checkedIds.has(sel.dataset.tid))
    .map(sel => {
      const tid = sel.dataset.tid;
      const kindSel = document.querySelector(`.leave-kind-sel[data-tid="${tid}"]`);
      return {
        therapist_id: tid,
        leave_type: sel.value,
        leave_kind: kindSel ? kindSel.value : 'annual',
      };
    });

  const body = {
    leave_date: dateStr,
    items: items,
    memo: _v('leave-memo') || ''
  };

  const r = await fetch('/api/therapist-leaves/bulk-set', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body)
  });

  if(!r.ok){
    const text = await r.text();
    alert('휴무 저장 실패\n' + text);
    return;
  }

  closeModal();
  await loadLeaveCalendar();
  await reloadMiniCalendar(window._miniCal ? window._miniCal.getDate() : new Date());
  await renderDayBoard();
  await loadTodayList();
}

// ──────────────── 휴무일 추가 (직원 1명 · 여러 날짜 동시 등록) ────────────────
// 직원은 /api/employees(EMPLOYEES_ALL), 날짜는 미니달력 다중선택 — 모두 동적 데이터.
// 선택한 날짜별로 종일/오전·오후반차 + 연차/월차 를 각각 지정 후 한 번에 등록.
let _leaveBulkSel = new Map();   // dateStr → { type, kind }

function _leaveBulkDateLabel(d){
  const dt = new Date(d + 'T00:00:00');
  return `${dt.getMonth()+1}월 ${dt.getDate()}일 (${'일월화수목금토'[dt.getDay()]})`;
}

async function openLeaveBulkAddModal(){
  await loadMasters();                 // EMPLOYEES_ALL 최신화 (신규 직원 반영)
  _leaveBulkSel = new Map();
  if(window._leaveBulkCal){ try { window._leaveBulkCal.destroy(); } catch(e){} window._leaveBulkCal = null; }

  const empOpts = EMPLOYEES_ALL
    .filter(e => e.active !== false)
    .map(e => `<option value="${e.id}">${e.name}${e.category_name ? ' (' + e.category_name + ')' : ''}</option>`)
    .join('');

  showModal(`
    <h3>➕ 휴무일 추가</h3>
    <label>직원
      <select id="leave-bulk-emp">
        <option value="">직원 선택…</option>
        ${empOpts}
      </select>
    </label>
    <p class="muted" style="margin:10px 0 4px">달력에서 휴무 날짜를 클릭해 여러 날짜를 선택하세요.</p>
    <div id="leave-bulk-cal" style="margin-bottom:12px"></div>
    <div id="leave-bulk-list" class="leave-bulk-list"></div>
    <label>메모
      <input id="leave-bulk-memo" placeholder="(선택) 전체 날짜 공통 메모">
    </label>
    <div class="modal-actions">
      <button onclick="closeModal()">닫기</button>
      <button class="primary" onclick="saveLeaveBulkAdd()">등록</button>
    </div>
  `);

  const el = document.getElementById('leave-bulk-cal');
  window._leaveBulkCal = new FullCalendar.Calendar(el, {
    initialView: 'dayGridMonth',
    locale: 'ko',
    height: 340,
    headerToolbar: { left: 'prev', center: 'title', right: 'next' },
    fixedWeekCount: false,
    selectable: false,
    dateClick: (info) => _leaveBulkToggleDate(info.dateStr),
  });
  window._leaveBulkCal.render();
  _leaveBulkRenderList();
}

function _leaveBulkToggleDate(d){
  if(_leaveBulkSel.has(d)) _leaveBulkSel.delete(d);
  else _leaveBulkSel.set(d, { type: 'full', kind: 'annual' });
  _leaveBulkRefreshCal();
  _leaveBulkRenderList();
}

function _leaveBulkRefreshCal(){
  const cal = window._leaveBulkCal;
  if(!cal) return;
  cal.removeAllEvents();
  for(const d of _leaveBulkSel.keys()){
    cal.addEvent({ start: d, allDay: true, display: 'background', backgroundColor: '#38bdf8' });
  }
}

function _leaveBulkSetType(d, v){ const o = _leaveBulkSel.get(d); if(o){ o.type = v; } }
function _leaveBulkSetKind(d, v){ const o = _leaveBulkSel.get(d); if(o){ o.kind = v; } }

function _leaveBulkRenderList(){
  const box = document.getElementById('leave-bulk-list');
  if(!box) return;
  const dates = Array.from(_leaveBulkSel.keys()).sort();
  if(dates.length === 0){
    box.innerHTML = '<p class="muted">선택된 날짜가 없습니다.</p>';
    return;
  }
  box.innerHTML = dates.map(d => {
    const v = _leaveBulkSel.get(d);
    return `
      <div class="leave-bulk-row" data-date="${d}">
        <span class="leave-bulk-date">${_leaveBulkDateLabel(d)}</span>
        <select class="leave-type-sel" onchange="_leaveBulkSetType('${d}', this.value)">
          <option value="full" ${v.type === 'full' ? 'selected' : ''}>종일</option>
          <option value="am" ${v.type === 'am' ? 'selected' : ''}>오전반차</option>
          <option value="pm" ${v.type === 'pm' ? 'selected' : ''}>오후반차</option>
        </select>
        <select class="leave-kind-sel" onchange="_leaveBulkSetKind('${d}', this.value)">
          <option value="annual" ${v.kind === 'monthly' ? '' : 'selected'}>연차</option>
          <option value="monthly" ${v.kind === 'monthly' ? 'selected' : ''}>월차</option>
        </select>
        <button class="mini" title="제외" onclick="_leaveBulkToggleDate('${d}')">✕</button>
      </div>`;
  }).join('');
}

async function saveLeaveBulkAdd(){
  const empSel = document.getElementById('leave-bulk-emp');
  const empId = empSel ? empSel.value : '';
  if(!empId){ alert('직원을 선택하세요.'); return; }
  if(_leaveBulkSel.size === 0){ alert('휴무 날짜를 1개 이상 선택하세요.'); return; }

  const items = Array.from(_leaveBulkSel.entries()).map(([d, v]) => ({
    employee_id: empId,
    leave_date: d,
    leave_type: v.type || 'full',
    leave_kind: v.kind || 'annual',
  }));

  const r = await fetch('/api/employee-leaves/bulk-add', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items, memo: _v('leave-bulk-memo') || '' }),
  });

  if(!r.ok){
    const text = await r.text();
    alert('휴무 등록 실패\n' + text);
    return;
  }
  const res = await r.json().catch(() => ({}));

  closeModal();
  await loadLeaveCalendar();
  if(window._miniCal){ await reloadMiniCalendar(window._miniCal.getDate()); }
  alert(`✓ 휴무 ${res.count || items.length}건이 등록되었습니다.`);
}

// 서버 에러 응답에서 사용자에게 보여줄 짧은 텍스트 추출.
//   FastAPI HTTPException 은 {"detail":"메시지"} 형식 → detail 만 꺼냄.
//   JSON 이 아니면 raw text. 실패하면 status 라인.
async function _apiErrorText(r){
  try {
    const ct = r.headers.get('content-type') || '';
    if (ct.includes('application/json')) {
      const j = await r.json();
      if (j && typeof j.detail === 'string') return j.detail;
      return JSON.stringify(j);
    }
  } catch(e) {}
  try { return await r.text(); } catch(e) { return r.statusText || ('HTTP ' + r.status); }
}

const ADMIN_KEY='dosu_admin_token';
function getToken(){return localStorage.getItem(ADMIN_KEY)||'';}
function setToken(t){if(t)localStorage.setItem(ADMIN_KEY,t);else localStorage.removeItem(ADMIN_KEY);}
async function adminFetch(url,opts={}){
  opts.headers=Object.assign({'X-Admin-Token':getToken()},opts.headers||{});
  let r=await fetch(url,opts);
  if(r.status===401){setToken(''); applyAdminUiState(false); if(!(await promptAdminLogin()))throw new Error('취소'); opts.headers['X-Admin-Token']=getToken(); r=await fetch(url,opts);}
  return r;
}
async function ensureAdmin(){
  // v1.3.5+: 비밀번호 변경 권장 알림은 *관리자 로그인 시점* (doAdminLogin) 에만 1회 — 탭 변경 시마다 ❌
  if(getToken()){const r=await fetch('/api/admin/status',{headers:{'X-Admin-Token':getToken()}});const d=await r.json();if(d.authenticated){applyAdminUiState(true);return true;}setToken('');applyAdminUiState(false);}
  return await promptAdminLogin();
}
function promptAdminLogin(){return new Promise(resolve=>{
  showModal(`<h3>🔒 관리자 로그인</h3><p class="muted">비밀번호를 입력하세요</p>
    <label>비밀번호 <input id="adm-pw" type="password" autofocus onkeydown="if(event.key==='Enter')document.getElementById('adm-go').click()"></label>
    <p id="adm-err" class="muted" style="color:#dc2626"></p>
    <div class="modal-actions"><button onclick="closeModal();window._admResolve&&window._admResolve(false)">취소</button>
    <button class="primary" id="adm-go" onclick="doAdminLogin()">로그인</button></div>
    <p class="muted" style="font-size:11px">초기: <code>admin1234</code></p>`);
  window._admResolve=resolve;});}
async function doAdminLogin(){
  const pw=document.getElementById('adm-pw').value;
  const r=await fetch('/api/admin/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:pw})});
  if(!r.ok){
    // 서버가 주는 실제 사유를 그대로 노출.
    //   특히 429(5회 실패 후 5분 잠금)를 "비밀번호 오류" 로 뭉뚱그리면,
    //   올바른 비밀번호인데도 "틀렸다" 고 오인하게 됨 (잠금은 전 PC 공용).
    let msg = '비밀번호가 올바르지 않습니다.';
    try { const e = await r.json(); if(e && e.detail) msg = e.detail; } catch(_){}
    if(r.status === 429 && !/잠[겼금]/.test(msg)){
      msg = '로그인이 일시적으로 잠겼습니다. 잠시 후 다시 시도하세요.';
    }
    const el = document.getElementById('adm-err');
    if(el) el.textContent = msg;
    return;
  }
  const d=await r.json(); setToken(d.token); closeModal();
  applyAdminUiState(true);
  if(d.is_default_password) alert('⚠️ 기본 비밀번호 사용 중');
  window._admResolve&&window._admResolve(true); window._admResolve=null;
}
function adminLogout(){
  if(getToken())fetch('/api/admin/logout',{method:'POST',headers:{'X-Admin-Token':getToken()}});
  setToken('');
  applyAdminUiState(false);
}

// 관리자 로그인 여부에 따라 UI 노출 토글
function applyAdminUiState(isLoggedIn){
  const btn = document.getElementById('admin-lock-btn');
  const tab = document.getElementById('admin-tab-btn');
  if(btn){
    btn.textContent = isLoggedIn ? '🔓' : '🔒';
    btn.title = isLoggedIn ? '관리자 로그아웃' : '관리자 로그인';
  }
  if(tab){
    tab.style.display = isLoggedIn ? '' : 'none';
  }
  // 로그아웃 상태에서 관리자 탭이 활성이면 예약 탭으로 복귀
  if(!isLoggedIn){
    const adminPane = document.getElementById('tab-admin');
    if(adminPane && adminPane.classList.contains('active')){
      const reserveBtn = document.querySelector('.tab-btn[onclick*="tab-reserve"]');
      if(reserveBtn) switchTab('tab-reserve', reserveBtn);
    }
  }
}

// 🔒/🔓 버튼 클릭: 로그아웃 상태면 로그인 모달, 로그인 상태면 로그아웃 확인
async function adminLockClick(){
  if(getToken()){
    // 현재 세션이 유효한지 서버 확인
    try {
      const r = await fetch('/api/admin/status',{headers:{'X-Admin-Token':getToken()}});
      const d = await r.json();
      if(d.authenticated){
        if(confirm('로그아웃하시겠습니까?')){
          adminLogout();
          alert('로그아웃되었습니다.');
        }
        return;
      }
    } catch(e){}
    // 토큰은 있으나 서버에서 무효 → 초기화 후 로그인 유도
    setToken('');
    applyAdminUiState(false);
  }
  await promptAdminLogin();
}

// 페이지 로드 시 토큰 유효성 확인 → 관리자 탭 초기 노출 결정
async function initAdminUi(){
  if(!getToken()){ applyAdminUiState(false); return; }
  try {
    const r = await fetch('/api/admin/status',{headers:{'X-Admin-Token':getToken()}});
    const d = await r.json();
    applyAdminUiState(!!d.authenticated);
    if(!d.authenticated) setToken('');
  } catch(e){ applyAdminUiState(false); }
}

async function loadMasters(){
  // ── 필수 마스터(직원)만 await. PATIENTS 는 비동기 백그라운드 로드 ──
  try {
    EMPLOYEES_ALL = await (await fetch('/api/employees')).json();
  } catch(e){ EMPLOYEES_ALL = []; }
  THERAPISTS = EMPLOYEES_ALL.filter(e => e.can_manual !== false || e.can_eswt !== false);
  DOCTORS = EMPLOYEES_ALL.filter(e => e.can_doctor_treatment === true);

  // ─── 대량(수만 건) 대응 ───
  //   예전: PATIENTS 80K light 로드(2초+11MB)를 기다려서 첫 렌더가 지연
  //   현재: 백그라운드로 던지고 즉시 return → 첫 화면 즉시 표시
  //   예약표 렌더는 서버가 appointments 응답에 embed 한 patient_name/chart 사용
  //   검색 패널들은 /api/patients/search 서버 검색으로 전환
  _loadPatientsBackground();
}

// PATIENTS 캐시 백그라운드 로드 (fire-and-forget). 끝나도 UI 는 안 기다림.
//   - 일부 모달/과거 코드에서 PATIENTS_BY_ID.get(id) 를 사용할 때 있어서 캐시는 유지
//   - 로드되는 동안 get() 이 undefined 면 appointments embed 값을 대체로 사용
let _PATIENTS_LOADED = false;
async function _loadPatientsBackground(){
  if(_PATIENTS_LOADED) return;
  try {
    const data = await (await fetch('/api/patients?light=1')).json();
    PATIENTS = data || [];
    PATIENTS_BY_ID = new Map(PATIENTS.map(p => [p.id, p]));
    _PATIENTS_LOADED = true;
    _updatePatientCountBadge();
  } catch(e){ /* 무시 — appointments embed 로 커버 */ }
}

// 환자 탭 버튼의 (환자 수) 배지 갱신 — PATIENTS 배열 길이 기반
function _updatePatientCountBadge(){
  const el = document.getElementById('pm-count-badge');
  if (!el) return;
  if (!_PATIENTS_LOADED) { el.textContent = '(…)'; return; }
  el.textContent = `(${(PATIENTS || []).length.toLocaleString()}명)`;
}

// 환자 CRUD 후 캐시 강제 재로드 → 배지도 자동 갱신
async function _reloadPatientsCache(){
  _PATIENTS_LOADED = false;
  await _loadPatientsBackground();
}

// 단건 환자 캐시 (검색 결과·예약 embed 에서 받은 환자를 Map 에 upsert)
function _upsertPatientCache(p){
  if(!p || !p.id) return;
  const idx = (PATIENTS || []).findIndex(x => x.id === p.id);
  let merged = p;
  if(idx >= 0){
    merged = Object.assign({}, PATIENTS[idx], p);
    PATIENTS[idx] = merged;
  } else {
    PATIENTS.push(p);
  }
  PATIENTS_BY_ID.set(p.id, merged);
  _updatePatientCountBadge();
}

const PM_RECENT_KEY = 'dosu_recent_patient_searches';

function _pmRememberRecentPatient(p){
  if(!p || !p.id) return;
  const existing = _pmLoadRecentPatients().filter(x => x.id !== p.id);
  const compact = {
    id: p.id,
    chart_no: p.chart_no || '',
    name: p.name || '',
    gender: p.gender || '',
    phone: p.phone || '',
    birth_date: p.birth_date || '',
    memo: p.memo || '',
    counts_show: p.counts_show || [],
  };
  localStorage.setItem(PM_RECENT_KEY, JSON.stringify([compact, ...existing].slice(0, 10)));
}

function _pmLoadRecentPatients(){
  try {
    const raw = JSON.parse(localStorage.getItem(PM_RECENT_KEY) || '[]');
    if(!Array.isArray(raw)) return [];
    return raw
      .filter(p => p && p.id)
      .map(p => Object.assign({}, p, PATIENTS_BY_ID.get(p.id) || {}))
      .slice(0, 10);
  } catch(e){ return []; }
}

function _pmForgetRecentPatient(pid){
  if(!pid) return;
  try {
    const raw = JSON.parse(localStorage.getItem(PM_RECENT_KEY) || '[]');
    if(!Array.isArray(raw)) return;
    localStorage.setItem(PM_RECENT_KEY, JSON.stringify(raw.filter(p => p && p.id !== pid)));
  } catch(e){}
}

function _removePatientFromSearchState(state, pid){
  if(!state || !pid || !Array.isArray(state.hits)) return;
  const before = state.hits.length;
  state.hits = state.hits.filter(p => p && p.id !== pid);
  const removed = before - state.hits.length;
  if(removed > 0){
    state.total = Math.max(0, (state.total || 0) - removed);
    state.offset = Math.min(state.offset || state.hits.length, state.hits.length);
  }
}

function _removePatientFromClientState(pid){
  if(!pid) return;
  PATIENTS = (PATIENTS || []).filter(p => p && p.id !== pid);
  PATIENTS_BY_ID.delete(pid);
  delete LAST_APPTS[pid];
  delete PM_HISTORY_CACHE[pid];
  _pmForgetRecentPatient(pid);
  _removePatientFromSearchState(_pmState, pid);
  _removePatientFromSearchState(_pqsState, pid);
  _updatePatientCountBadge();
}

async function loadTherapistLeaves(date=''){
  const url = date ? `/api/therapist-leaves?date=${date}` : '/api/therapist-leaves';
  THERAPIST_LEAVES = await (await fetch(url)).json();
  return THERAPIST_LEAVES;
}

// ──────────────── AI 휴무 등록 (세션 14) ────────────────
//   백엔드 3 엔드포인트는 세션 13 에서 완성됨 (POST /api/ai/action/{parse,preview,execute}).
//   본 UI 는 preview → execute 두 단계만 호출. parse 는 디버깅용 (호출 안 함).
//   안전 원칙: 사용자가 "휴무 등록하기" 클릭 전에는 execute 호출 절대 금지.
let _aiLeaveLastPreview = null;

function _aiLeaveTypeLabel(t){
  // 백엔드는 spec § 4.1 의 "full"/"morning"/"afternoon" 값을 반환.
  // 기존 캘린더는 'am'/'pm'/'full' 사용 — UI 표시는 양쪽 모두 처리.
  if(t === 'full') return '종일';
  if(t === 'morning' || t === 'am') return '오전 반차';
  if(t === 'afternoon' || t === 'pm') return '오후 반차';
  return t || '-';
}
function _aiLeaveKindLabel(k){
  if(k === 'monthly') return '월차';
  if(k === 'annual') return '연차';
  return k || '-';
}

function aiLeaveOnInput(){
  const el = document.getElementById('ai-leave-input');
  const btn = document.getElementById('ai-leave-analyze-btn');
  if(!el || !btn) return;
  const len = (el.value || '').trim().length;
  btn.disabled = !(len >= 1 && len <= 200);
}

function aiLeaveReset(){
  _aiLeaveLastPreview = null;
  const inp = document.getElementById('ai-leave-input');
  if(inp) inp.value = '';
  const memo = document.getElementById('ai-leave-memo');
  if(memo) memo.value = '';
  const ack = document.getElementById('ai-leave-overwrite-ack');
  if(ack) ack.checked = false;
  const ow = document.getElementById('ai-leave-overwrite-row');
  if(ow) ow.style.display = 'none';
  const pv = document.getElementById('ai-leave-preview');
  if(pv) pv.style.display = 'none';
  const status = document.getElementById('ai-leave-status');
  if(status){ status.textContent = ''; status.className = 'muted'; }
  aiLeaveOnInput();
}

function aiLeaveSyncSubmitButton(){
  const btn = document.getElementById('ai-leave-submit-btn');
  if(!btn) return;
  const data = _aiLeaveLastPreview;
  if(!data || !data.safe_to_execute){
    btn.disabled = true;
    return;
  }
  if(data.mode === 'overwrite'){
    const ack = document.getElementById('ai-leave-overwrite-ack');
    btn.disabled = !(ack && ack.checked);
  } else {
    btn.disabled = false;
  }
}

function aiLeaveRenderPreview(data){
  _aiLeaveLastPreview = data;
  const pv = document.getElementById('ai-leave-preview');
  const status = document.getElementById('ai-leave-status');

  // candidate 가 없을 때 (safe_to_execute=false) — 카드 자체는 숨기고 status 에 사유 표시
  if(!data.candidate){
    if(pv) pv.style.display = 'none';
    if(status){
      const msg = data.message || data.outcome || '분석 실패';
      // warnings 가 있고 message 와 다르면 추가 표시 (중복 회피)
      const ws = Array.isArray(data.warnings) ? data.warnings.filter(w => w && w !== msg) : [];
      status.textContent = '⚠ ' + msg + (ws.length ? ' — ' + ws.join(' / ') : '');
      status.className = 'ai-leave-status-error';
    }
    return;
  }

  // candidate 있음 → 미리보기 카드 표시
  const c = data.candidate;
  document.getElementById('ai-leave-emp').textContent = c.employee_name || c.employee_name_raw || '-';
  document.getElementById('ai-leave-date').textContent =
    (c.resolved_date || '-') + (c.original_date_text ? ` (원문: "${c.original_date_text}")` : '');
  document.getElementById('ai-leave-type').textContent = _aiLeaveTypeLabel(c.leave_type);
  document.getElementById('ai-leave-kind').textContent = _aiLeaveKindLabel(c.leave_kind);

  // assumption (날짜 해석 근거) — 노란 박스로 강조
  const aBox = document.getElementById('ai-leave-assumption');
  if(c.assumption){
    aBox.textContent = '🗓 ' + c.assumption;
    aBox.style.display = '';
  } else {
    aBox.textContent = '';
    aBox.style.display = 'none';
  }

  // warnings (mode/예약/이미 휴무 있음 등)
  const wBox = document.getElementById('ai-leave-warnings');
  wBox.innerHTML = '';
  const items = Array.isArray(data.warnings) ? data.warnings.slice() : [];
  if(typeof data.appointments_count === 'number' && data.appointments_count > 0){
    // 백엔드 warnings 에 이미 포함되어 있으면 중복 방지를 위해 추가 안 함.
    const has = items.some(w => /예약/.test(w));
    if(!has) items.push(`해당 날짜에 예약 ${data.appointments_count} 건이 있습니다`);
  }
  items.forEach(w => {
    const div = document.createElement('div');
    div.className = 'ai-leave-warn';
    div.textContent = '⚠ ' + w;
    wBox.appendChild(div);
  });

  // overwrite 체크박스 (mode === 'overwrite' 만 노출)
  const owRow = document.getElementById('ai-leave-overwrite-row');
  const ack = document.getElementById('ai-leave-overwrite-ack');
  if(data.mode === 'overwrite'){
    owRow.style.display = '';
    if(ack) ack.checked = false;
  } else {
    owRow.style.display = 'none';
    if(ack) ack.checked = false;
  }

  pv.style.display = '';
  if(status){
    if(data.mode === 'noop'){
      status.textContent = 'ℹ 이미 같은 내용으로 등록되어 있습니다';
      status.className = 'ai-leave-status-info';
    } else if(data.mode === 'overwrite'){
      status.textContent = '⚠ 기존 휴무를 덮어씁니다 — 체크박스 확인 필요';
      status.className = 'ai-leave-status-warn';
    } else {
      status.textContent = '✓ 분석 완료 — 미리보기 확인 후 등록하세요';
      status.className = 'ai-leave-status-ok';
    }
  }
  aiLeaveSyncSubmitButton();
}

async function aiLeaveAnalyze(){
  const inp = document.getElementById('ai-leave-input');
  const status = document.getElementById('ai-leave-status');
  const btn = document.getElementById('ai-leave-analyze-btn');
  if(!inp) return;
  const text = (inp.value || '').trim();
  if(!text || text.length > 200) return;
  btn.disabled = true;
  if(status){ status.textContent = '분석 중...'; status.className = 'muted'; }
  try {
    const r = await adminFetch('/api/ai/action/preview', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({text: text})
    });
    if(r.status === 503){
      const msg = await r.text();
      if(status){ status.textContent = '⚠ AI 서비스를 사용할 수 없습니다 (관리자 설정 확인)'; status.className = 'ai-leave-status-error'; }
      // eslint-disable-next-line no-console
      console.warn('AI provider unavailable:', msg);
      return;
    }
    if(!r.ok){
      const msg = await r.text();
      if(status){ status.textContent = '⚠ 분석 실패: ' + msg; status.className = 'ai-leave-status-error'; }
      return;
    }
    const data = await r.json();
    aiLeaveRenderPreview(data);
  } catch(e){
    if(status){ status.textContent = '⚠ 네트워크 오류: ' + (e && e.message ? e.message : e); status.className = 'ai-leave-status-error'; }
  } finally {
    aiLeaveOnInput();  // 분석 버튼 다시 활성화 (입력값 그대로 있으므로)
  }
}

async function aiLeaveSubmit(){
  const data = _aiLeaveLastPreview;
  const status = document.getElementById('ai-leave-status');
  const btn = document.getElementById('ai-leave-submit-btn');
  if(!data || !data.safe_to_execute || !data.preview_token){
    if(status){ status.textContent = '⚠ 등록할 수 있는 분석 결과가 없습니다'; status.className = 'ai-leave-status-error'; }
    return;
  }
  if(data.mode === 'overwrite'){
    const ack = document.getElementById('ai-leave-overwrite-ack');
    if(!(ack && ack.checked)){
      if(status){ status.textContent = '⚠ 덮어쓰기 확인 체크가 필요합니다'; status.className = 'ai-leave-status-warn'; }
      return;
    }
  }
  const memo = (document.getElementById('ai-leave-memo').value || '').trim();
  btn.disabled = true;
  if(status){ status.textContent = '등록 중...'; status.className = 'muted'; }
  try {
    const r = await adminFetch('/api/ai/action/execute', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        preview_token: data.preview_token,
        confirm: true,
        overwrite_acknowledged: data.mode === 'overwrite',
        memo: memo
      })
    });
    let body = null;
    try { body = await r.json(); } catch(_) { body = null; }
    if(r.ok && body && body.ok){
      // 성공 — 캘린더 갱신 + 카드 리셋
      alert('✓ 휴무가 등록되었습니다.');
      try { await loadLeaveCalendar(); } catch(_){}
      aiLeaveReset();
      return;
    }
    // 실패 outcome 매핑 (spec § 12 표 — 백엔드의 message 필드를 그대로 사용)
    const outcome = (body && body.outcome) || ('http_' + r.status);
    const msg = (body && body.message) || ('등록 실패: ' + outcome);
    if(r.status === 409){
      // 동시 변경 — 다시 분석 유도
      alert('⚠ ' + msg + '\n\n다시 분석해주세요.');
      aiLeaveReset();
    } else {
      alert('⚠ ' + msg);
      if(status){ status.textContent = '⚠ ' + msg; status.className = 'ai-leave-status-error'; }
    }
    aiLeaveSyncSubmitButton();
  } catch(e){
    if(status){ status.textContent = '⚠ 네트워크 오류: ' + (e && e.message ? e.message : e); status.className = 'ai-leave-status-error'; }
    aiLeaveSyncSubmitButton();
  }
}

async function loadLeaveCalendar(){
  await loadMasters();
  const allLeaves = await loadTherapistLeaves();

  const el = document.getElementById('leave-calendar');
  if(!window._leaveCal){
    window._leaveCal = new FullCalendar.Calendar(el, {
      initialView:'dayGridMonth',
      locale:'ko',
      height:650,
      headerToolbar:{left:'prev,next today', center:'title', right:''},
      dateClick: async (info) => {
        await openLeaveModal(info.dateStr);
      },
      eventClick: async (info) => {
        // [패치] 등록된 휴무 블록을 클릭해도 같은 수정 모달 열기
        const d = info.event.start;
        const dateStr = d.getFullYear() + '-' +
          String(d.getMonth()+1).padStart(2,'0') + '-' +
          String(d.getDate()).padStart(2,'0');
        await openLeaveModal(dateStr);
      }
    });
    window._leaveCal.render();
  }

  const grouped = {};
  allLeaves.forEach(x => {
    if(!grouped[x.leave_date]) grouped[x.leave_date] = [];
    // 휴무 등록은 전 직원(EMPLOYEES_ALL) 대상이므로 표시도 전 직원에서 찾는다.
    // (치료사만 담는 THERAPISTS 로 찾으면 간호과/원무과 등 비치료사 휴무가 누락됨)
    const t = EMPLOYEES_ALL.find(tt => tt.id === x.therapist_id);
    if(t){
      const typeLabel =
        x.leave_type === 'am' ? '오전' :
        x.leave_type === 'pm' ? '오후' : '종일';
      const kindLabel = x.leave_kind === 'monthly' ? '월차' : '연차';
      grouped[x.leave_date].push({
        therapist_id: t.id,
        name: t.name,
        color: t.color || '#9CA3AF',
        typeLabel: typeLabel,
        kindLabel: kindLabel,
      });
    }
  });

  window._leaveCal.removeAllEvents();

  Object.entries(grouped).forEach(([date, items]) => {
    // 치료사 ID 기준 중복 제거 (같은 치료사가 같은 날 중복 등록되어 있을 경우)
    const seen = new Set();
    items.forEach(it => {
      if(seen.has(it.therapist_id)) return;
      seen.add(it.therapist_id);
      window._leaveCal.addEvent({
        start: date,
        allDay: true,
        title: `${it.name}(${it.typeLabel},${it.kindLabel})`,
        backgroundColor: it.color,
        borderColor: it.color,
        textColor: '#fff'
      });
    });
  });

  document.getElementById('leave-summary').innerHTML =
    '<p class="muted">등록된 휴무: ' + allLeaves.length + '건</p>';
}

async function loadMiniCalendarData(baseDate = null){
  const d = baseDate || (window._miniCal ? window._miniCal.getDate() : new Date());

  const y = d.getFullYear();
  const m = d.getMonth();
  const first = new Date(y, m, 1);
  const last = new Date(y, m + 1, 0);

  const startStr = `${first.getFullYear()}-${String(first.getMonth()+1).padStart(2,'0')}-${String(first.getDate()).padStart(2,'0')}`;
  const endStr = `${last.getFullYear()}-${String(last.getMonth()+1).padStart(2,'0')}-${String(last.getDate()).padStart(2,'0')}`;

  const apptRes = await fetch(`/api/appointments?start=${startStr}T00:00:00&end=${endStr}T23:59:59`);
  const apptData = await apptRes.json();

  MINI_APPT_COUNTS = {};
  apptData
    .filter(a => a.extendedProps.status !== 'canceled')
    .forEach(a => {
      const ds = a.start.slice(0, 10);
      MINI_APPT_COUNTS[ds] = (MINI_APPT_COUNTS[ds] || 0) + 1;
    });

  const leaveData = await loadTherapistLeaves();

  MINI_LEAVE_MAP = {};
  leaveData.forEach(x => {
    if (!MINI_LEAVE_MAP[x.leave_date]) MINI_LEAVE_MAP[x.leave_date] = [];

    // 비치료사(간호과/원무과 등) 휴무도 미니달력에 표시되도록 전 직원에서 찾는다.
    const t = EMPLOYEES_ALL.find(tt => tt.id === x.therapist_id);
    if (!t) return;

    const typeLabel =
      x.leave_type === 'am' ? '오전' :
      x.leave_type === 'pm' ? '오후' : '종일';

    MINI_LEAVE_MAP[x.leave_date].push({
      label: `${t.name}(${typeLabel})`,
      color: t.color || '#9CA3AF'
    });
  });
}

function paintMiniCalendarCells(){
  const root = document.getElementById('month-cal');
  if (!root) return;

  root.querySelectorAll('.fc-daygrid-day').forEach(dayEl => {
    const dateStr = dayEl.getAttribute('data-date');
    if (!dateStr) return;

    const frame = dayEl.querySelector('.fc-daygrid-day-frame');
    if (!frame) return;

    frame.querySelectorAll('.center-badge, .leave-name-list').forEach(el => el.remove());

    const active = MINI_APPT_COUNTS[dateStr] || 0;
    const leaveNames = MINI_LEAVE_MAP[dateStr] || [];

    if (active > 0) {
      const b = document.createElement('div');
      b.className = 'day-count-badge center-badge';
      b.textContent = `${active}명`;
      frame.appendChild(b);
    }

    if (leaveNames.length > 0) {
      const wrap = document.createElement('div');
      wrap.className = 'leave-name-list';
      wrap.title = leaveNames.map(n => n.label).join('\n');

      // 좁은 미니캘린더 셀에 휴무명이 많으면 셀이 과도하게 길어져 깨져 보임.
      //   최대 MAX_MINI_LEAVE 개만 칩으로 노출, 나머지는 "+N" 으로 축약 (전체는 title 툴팁).
      const MAX_MINI_LEAVE = 3;
      const shown = leaveNames.slice(0, MAX_MINI_LEAVE);
      shown.forEach(n => {
        const row = document.createElement('div');
        row.className = 'leave-name-item';
        row.textContent = n.label;
        // 치료사 본인 색상 적용 (가독성을 위해 배경은 옅게, 글자는 진하게)
        row.style.backgroundColor = hexWithAlpha(n.color, 0.22);
        row.style.color = n.color;
        row.style.borderLeft = `3px solid ${n.color}`;
        wrap.appendChild(row);
      });
      if (leaveNames.length > MAX_MINI_LEAVE) {
        const more = document.createElement('div');
        more.className = 'leave-name-item leave-name-more';
        more.textContent = `+${leaveNames.length - MAX_MINI_LEAVE}`;
        wrap.appendChild(more);
      }

      frame.appendChild(wrap);
    }
  });
  syncMiniCalendarSelection();
}

// HEX 색상에 알파값 적용해서 rgba 문자열 반환 (#RRGGBB 또는 #RGB 모두 지원)
function hexWithAlpha(hex, alpha){
  if(!hex) return `rgba(156,163,175,${alpha})`;
  let h = hex.replace('#','').trim();
  if(h.length === 3) h = h.split('').map(c => c+c).join('');
  if(h.length !== 6) return hex;
  const r = parseInt(h.substring(0,2),16);
  const g = parseInt(h.substring(2,4),16);
  const b = parseInt(h.substring(4,6),16);
  return `rgba(${r},${g},${b},${alpha})`;
}

async function reloadMiniCalendar(baseDate = null){
  await loadMiniCalendarData(baseDate);
  paintMiniCalendarCells();
}

function dateKey(value){
  if(typeof value === 'string') return value.slice(0, 10);
  const d = value ? new Date(value) : new Date();
  const p = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())}`;
}

function syncMiniCalendarSelection(date = window._currentDate){
  const root = document.getElementById('month-cal');
  if(!root) return;
  const key = dateKey(date || new Date());
  root.querySelectorAll('.fc-daygrid-day').forEach(dayEl => {
    dayEl.classList.toggle('mini-selected-day', dayEl.getAttribute('data-date') === key);
  });
}

document.addEventListener('DOMContentLoaded', async () => {
  await loadTreatmentMeta();
  await loadMasters();

  // 관리자 로그인 상태에 따라 🔒 버튼 / 관리자 탭 초기화
  await initAdminUi();

  // 단계 C #9: 생년월일/연락처 자동 포맷 (전역 위임)
  installInputFormatters();

  window._miniCal = new FullCalendar.Calendar(document.getElementById('month-cal'), {
    initialView: 'dayGridMonth',
    locale: 'ko',
    // height: 'auto' → 달력이 내용(주 수·휴무명 배지)에 맞춰 늘어남.
    //   고정 320px 이면 휴무명/환자수 배지가 많은 달에 내부 스크롤바가 생기며
    //   셀이 잘려 "깨진" 것처럼 보였다 (셀 콘텐츠 301px > 가시영역 262px).
    height: 'auto',
    headerToolbar: { left: 'prev', center: 'title', right: 'next' },
    fixedWeekCount: false,
    dayMaxEvents: 0,
    displayEventTime: false,
    events: [],
    datesSet: async (info) => {
      await reloadMiniCalendar(info.start);
    },
    dayCellDidMount: () => {
      paintMiniCalendarCells();
      syncMiniCalendarSelection();
    },
    dateClick: (info) => {
      window._currentDate = new Date(info.dateStr);
      syncMiniCalendarSelection(window._currentDate);
      renderDayBoard();
    },
  });

  window._miniCal.render();

  await reloadMiniCalendar(new Date());

  window._currentDate = new Date();
  syncMiniCalendarSelection(window._currentDate);
  await renderDayBoard();
  await loadTodayList();

  // ─────────────────────────────────────────────────────────────
  // 백그라운드 polling — 3가지 조건에서만 실제 fetch 수행:
  //   (1) 브라우저 탭이 화면에 보임 (document.hidden === false)
  //   (2) 예약탭이 현재 활성 탭 (_isReserveTabActive())
  // 둘 중 하나라도 거짓이면 그 tick 은 건너뜀 → 요청량 대폭 감소.
  // 다른 탭(환자/직원/관리자) 보는 동안엔 예약 fetch 0. 최소화 상태에서도 0.
  // 예약탭 복귀·창 복원 시에는 switchTab / visibilitychange 에서 즉시 fetch 수행.
  // ─────────────────────────────────────────────────────────────
  setInterval(async () => {
    if (document.hidden) return;
    if (!_isReserveTabActive()) return;
    await loadTodayList();
  }, 5000);

  setInterval(async () => {
    if (document.hidden) return;
    if (!_isReserveTabActive()) return;
    await renderDayBoard();
  }, 5000);

  setInterval(async () => {
    if (document.hidden) return;
    if (!_isReserveTabActive()) return;
    await reloadMiniCalendar(window._miniCal ? window._miniCal.getDate() : new Date());
  }, 15000);

  // 창 최소화/다른 브라우저 탭 →  원복 시 즉시 최신 상태로 동기화
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) return;
    if (!_isReserveTabActive()) return;
    try { renderDayBoard(); } catch(e) {}
    try { loadTodayList();  } catch(e) {}
    try { if (window._miniCal) reloadMiniCalendar(window._miniCal.getDate()); } catch(e) {}
  });
});

function timeSlots(){
  // 운영 시작 ~ 운영 종료 시각까지 slot_minutes 간격.
  // m <= e 로 마지막 운영 종료 시각(예: 18:30) 도 행으로 표시.
  // 단 그 마지막 행은 "운영 종료 라인" 으로만 쓰이고 실제 예약 시작은
  // _saveAppt 검증에서 _endMin > _closeMin 으로 여전히 차단됨 (변경 없음).
  const [oh,om] = CFG.openTime.split(':').map(Number);
  const [ch,cm] = CFG.closeTime.split(':').map(Number);
  const s = oh*60 + om, e = ch*60 + cm;
  const r = [];
  for (let m = s; m <= e; m += CFG.slotMinutes) r.push(m);
  return r;
}
function fmtTime(m){return `${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}`;}
function fmtDateKr(d){return `${d.getFullYear()}년 ${d.getMonth()+1}월 ${d.getDate()}일 (${'일월화수목금토'[d.getDay()]})`;}
// 24시간제 날짜+시간 표시 (예: 2026-04-16 14:30)
function fmtDateTime24(d){
  const p = n => String(n).padStart(2,'0');
  return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}
// 24시간제 날짜만 (예: 2026-04-16)
function fmtDate24(d){
  const p = n => String(n).padStart(2,'0');
  return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())}`;
}
function timeToMinutes(hhmm){
  const [h, m] = (hhmm || '00:00').split(':').map(Number);
  return h * 60 + m;
}
// 예약 시간창 [startMin, endMin) 가 점심창과 겹치는지 검사 (예약 차단용).
function _isLunchOverlap(startMin, endMin){
  if(!CFG.lunchEnabled) return false;
  const ls = timeToMinutes(CFG.lunchStart);
  const le = timeToMinutes(CFG.lunchEnd);
  return le > ls && endMin > ls && startMin < le;
}

async function renderDayBoard(){
  const date = window._currentDate || new Date();
  window._currentDate = date;

  const y = date.getFullYear();
  const mo = String(date.getMonth()+1).padStart(2,'0');
  const dd = String(date.getDate()).padStart(2,'0');
  const dateStr = `${y}-${mo}-${dd}`;
  if(window._miniCal){
    const calDate = window._miniCal.getDate();
    if(calDate.getFullYear() !== y || calDate.getMonth() !== date.getMonth()){
      window._miniCal.gotoDate(date);
      setTimeout(() => syncMiniCalendarSelection(date), 0);
    } else {
      syncMiniCalendarSelection(date);
    }
  } else {
    syncMiniCalendarSelection(date);
  }

  const r = await fetch(`/api/appointments?start=${dateStr}T00:00:00&end=${dateStr}T23:59:59`);
  const appts = await r.json();
  const leaves = await (await fetch(`/api/therapist-leaves?date=${dateStr}`)).json();
  const slots = timeSlots();
  const activeAppts = appts.filter(a => a.extendedProps.status !== 'canceled');

  let html = `<div class="board-header">
    <button class="mini" onclick="moveDay(-1)">◀ 이전</button>
    <button class="mini" onclick="goToday()">오늘</button>
    <button class="mini" onclick="moveDay(1)">다음 ▶</button>
    <h3 class="board-date">${fmtDateKr(date)}</h3>
    <div class="board-employee-filter">
      <button class="mini" onclick="toggleBoardEmployeePicker(event)">표시 직원 <span class="badge gray">${boardEmployeeFilterLabel()}</span></button>
      ${renderBoardEmployeePicker()}
    </div>
    <button class="mini" onclick="downloadManualScheduleXlsx()" title="현재 날짜의 도수치료 예약을 A4 가로 엑셀로 다운로드">📊 도수치료 엑셀</button>
  </div>`;

  // ─────── 열 구성 ───────
  // 고정 공용 3열 + 치료사 동적 열
  const COL_DOC = '__doctor__';
  const COL_ESWT = '__eswt__';
  const COL_MANUAL = '__manual__';
  const fixedCols = [
    { id: COL_DOC,    name: '🩺 의사(공용)',       color: '#3B82F6', isFixed: true },
    { id: COL_ESWT,   name: '⚡ 체외충격파(공용)', color: '#F97316', isFixed: true },
    { id: COL_MANUAL, name: '💆 치료사 미배정',  color: '#8B5CF6', isFixed: true },
  ];
  const activeThers = getBoardVisibleTherapists();
  const therCols = activeThers.map(t => ({
    id: t.id, name: t.name, color: t.color || '#9CA3AF', isFixed: false,
    can_eswt: t.can_eswt !== false, can_manual: t.can_manual !== false,
  }));
  const cols = [...fixedCols, ...therCols];

  // ─────── 휴무 판정 (시간대별) ───────
  const amUntil = timeToMinutes(CFG.leaveAmUntil || '14:00');
  const pmFrom  = timeToMinutes(CFG.leavePmFrom  || '13:00');
  function isLeaveAt(tid, m){
    const info = leaves.find(x => (x.therapist_id||x.employee_id) === tid);
    if(!info) return { leave:false, full:false, type:null };
    const t = info.leave_type || 'full';
    if(t === 'full')                return { leave:true, full:true, type:'full' };
    if(t === 'am' && m < amUntil)   return { leave:true, full:false, type:'am' };
    if(t === 'pm' && m >= pmFrom)   return { leave:true, full:false, type:'pm' };
    return { leave:false, full:false, type:null };
  }
  // 치료사별 전일 휴무 여부 (헤더/rowspan 용)
  const fullLeaveSet = new Set();
  therCols.forEach(c => {
    const info = leaves.find(x => (x.therapist_id||x.employee_id) === c.id);
    if(info && (info.leave_type||'full') === 'full') fullLeaveSet.add(c.id);
  });

  // ─────── 예약 → 셀 분산 배치 ───────
  // cellsByCol[colId][slotMinute] = [ {item} ... ]
  const cellsByCol = {};
  cols.forEach(c => { cellsByCol[c.id] = {}; });

  // 드래그 시 "한 예약에 다른 치료코드도 있는지" 조회용 맵 (분리 필요 여부 판정)
  window._BOARD_APPT_CODES = {};

  activeAppts.forEach(ap => {
    const ep = ap.extendedProps;
    const startDate = new Date(ap.start);
    const slot = startDate.getHours()*60 + startDate.getMinutes();
    const codes = apptTreatmentCodes(ep);
    window._BOARD_APPT_CODES[ap.id] = codes.slice();
    const assignMap = {};
    (ep.assignments || []).forEach(a => { assignMap[a.treatment_code] = a.handler_id; });
    // 환자 정보: 서버가 embed 한 ep.patient_name/chart 를 1순위, PATIENTS_BY_ID (백그라운드 로드됨) 를 2순위
    const patient = PATIENTS_BY_ID.get(ep.patient_id) || {
      id: ep.patient_id,
      name: ep.patient_name || '?',
      chart_no: ep.patient_chart_no || '-',
      phone: ep.patient_phone || '',
      birth_date: ep.patient_birth_date || '',
      memo: ep.patient_memo || '',
    };

    codes.forEach(code => {
      let targetCol = null;
      let extraNote = '';  // 공용 열 추가 표시용 (신환/휴무)

      if(isDoctorCode(code)){
        // 의사 역할 치료항목 전체 → 의사 공용 열에 표시
        //   (주사/연골주사 + 앞으로 추가되는 모든 의사 역할 항목 자동 포함)
        //   의사 개인 열로 분기 없음, 모두 의사 공용 풀
        targetCol = COL_DOC;
      } else if(isEswtCode(code)){
        const hid = assignMap[TX_META.eswt_code];
        if(hid){
          // 그 치료사가 헤더에 있고, 그 시간 휴무 아닐 때만 치료사 열
          const exists = therCols.find(c => c.id === hid);
          const leaveState = exists ? isLeaveAt(hid, slot) : null;
          if(exists && !(leaveState && leaveState.leave)){
            targetCol = hid;
          } else {
            // 담당자가 사라졌거나 휴무면 공용 열
            targetCol = COL_ESWT;
            if(exists && leaveState && leaveState.leave){
              extraNote = `${exists.name} 휴무`;
            }
          }
        } else {
          targetCol = COL_ESWT;
        }
      } else if(isManualCode(code)){
        // 도수치료 전체 (manual30/60/80/90 등 모든 시간항목 자동 포함)
        const tid = ep.therapist_id;
        if(tid){
          const exists = therCols.find(c => c.id === tid);
          const leaveState = exists ? isLeaveAt(tid, slot) : null;
          if(exists && !(leaveState && leaveState.leave)){
            targetCol = tid;
          } else {
            // 담당 치료사 휴무 → 치료사 미배정 공용 열로
            targetCol = COL_MANUAL;
            if(exists && leaveState && leaveState.leave){
              extraNote = `${exists.name} 휴무`;
            }
          }
        } else {
          // 담당 없음 → 미배정
          targetCol = COL_MANUAL;
        }
      }
      if(!targetCol) return;

      // 예약 시간(시작~끝)은 "도수치료" 항목에만 표시
      //   충격파/주사/연골주사는 별도 시간 표기 생략
      let timeStr = '';
      if(isManualCode(code)){
        const durMin = (TX_META.treatment_minutes && TX_META.treatment_minutes[code])
                      || ep.duration_min || CFG.slotMinutes;
        const endDate = new Date(startDate.getTime() + durMin * 60000);
        const _hm = d => `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
        timeStr = `${_hm(startDate)} ~ ${_hm(endDate)}`;
      }

      const item = {
        apptId: ap.id,
        status: ep.status,
        chart: patient?.chart_no || '-',
        name: patient?.name || '?',
        code: code,
        short: txShort(code),
        extraNote,
        // 셀 두 번째 줄: 도수치료만 "09:30 ~ 10:00" 형식으로 표시
        timeStr,
        // 도수치료(미배정) 공용 열 내부에서 드래그 대상으로 표시
        isManualUnassigned: (targetCol === COL_MANUAL),
        // 체외충격파 셀 이동 대상
        isEswt: isEswtCode(code),
      };
      cellsByCol[targetCol][slot] = (cellsByCol[targetCol][slot] || []);
      cellsByCol[targetCol][slot].push(item);
    });
  });

  // ─────── 테이블 렌더 ───────
  html += `<div class="board-wrap"><table class="board-table"><thead><tr><th class="time-col">시간</th>`;
  cols.forEach(c => {
    const isFull = fullLeaveSet.has(c.id);
    const suffix = isFull ? ' · 휴무' : '';
    html += `<th class="ther-col ${isFull?'ther-leave-head':''} ${c.isFixed?'fixed-col':''}"
              style="border-top:4px solid ${c.color}">${c.name}${suffix}</th>`;
  });
  html += `</tr></thead><tbody>`;

  // ─────── 사전 계산: 반일 휴무 rowspan 세그먼트 (#4) ───────
  // colLeavePlan[colId] = { skipMap: {slotIdx: true} (rowspan에 흡수된 행),
  //                          spanMap: {slotIdx: {span:N, label:'오전휴무'}} (이 위치에 td span 출력) }
  const colLeavePlan = {};
  cols.forEach(c => {
    const plan = { skipMap: {}, spanMap: {} };
    if(c.isFixed || fullLeaveSet.has(c.id)) {
      colLeavePlan[c.id] = plan;
      return;
    }
    // 슬롯별 휴무 상태 + 예약 유무 배열
    const slotStates = slots.map((m, idx) => {
      const st = isLeaveAt(c.id, m);
      const hasAppt = (cellsByCol[c.id][m] || []).length > 0;
      return { idx, m, isLeave: st.leave && !st.full, type: st.type, hasAppt };
    });
    // 반일 휴무 연속 구간 찾기 — 예약 있는 슬롯에서 끊고, 예약 없는 슬롯만 묶음
    let i = 0;
    while(i < slotStates.length){
      const s = slotStates[i];
      if(s.isLeave && !s.hasAppt){
        // 같은 type 으로 예약 없는 연속 구간 찾기
        let j = i;
        while(j+1 < slotStates.length){
          const next = slotStates[j+1];
          if(next.isLeave && !next.hasAppt && next.type === s.type) j++;
          else break;
        }
        const span = j - i + 1;
        const label = s.type === 'am' ? '오전휴무' : '오후휴무';
        plan.spanMap[i] = { span, label };
        for(let k = i+1; k <= j; k++) plan.skipMap[k] = true;
        i = j + 1;
      } else {
        i++;
      }
    }
    colLeavePlan[c.id] = plan;
  });

  // ─────── 사전 계산: 예약 rowspan (#8 — 1시간 예약이 연속 셀 채우기) ───────
  // apptSpanPlan[colId] = { skipMap: {slotIdx: true}, spanMap: {slotIdx: span} }
  const apptSpanPlan = {};
  const slotByMin = {};
  slots.forEach((m, idx) => { slotByMin[m] = idx; });
  cols.forEach(c => {
    const plan = { skipMap: {}, spanMap: {} };
    slots.forEach((m, idx) => {
      if(plan.skipMap[idx]) return;
      const items = cellsByCol[c.id][m] || [];
      if(!items.length) return;
      // 각 item 의 치료 소요시간 → 슬롯 수. 여러 item 이 쌓이면 최대값.
      let maxSpan = 1;
      items.forEach(it => {
        const dur = (TX_META.treatment_minutes && TX_META.treatment_minutes[it.code]) || CFG.slotMinutes;
        const s = Math.max(1, Math.round(dur / CFG.slotMinutes));
        if(s > maxSpan) maxSpan = s;
      });
      // 뒤 슬롯에 예약/휴무 rowspan이 있으면 그 앞까지로 span 축소
      let actualSpan = 1;
      for(let k = 1; k < maxSpan; k++){
        const ni = idx + k;
        if(ni >= slots.length) break;
        const nm = slots[ni];
        const nextItems = cellsByCol[c.id][nm] || [];
        if(nextItems.length) break;
        if(!c.isFixed){
          const lp = colLeavePlan[c.id];
          if(lp && (lp.spanMap[ni] || lp.skipMap[ni])) break;
        }
        actualSpan = k + 1;
      }
      if(actualSpan > 1){
        plan.spanMap[idx] = actualSpan;
        for(let k = 1; k < actualSpan; k++) plan.skipMap[idx + k] = true;
      }
    });
    apptSpanPlan[c.id] = plan;
  });

  // ─────── 점심시간 슬롯 인덱스 계산 ───────
  // 슬롯창 [m, m+slot) 가 점심창 [ls, le) 와 겹치면 점심 슬롯.
  // lunchBlocked: 그 날의 활성 예약 중 [start, start+duration) 이 점심창과
  //   조금이라도 겹치면 병합 포기 (rowspan 충돌 + 기존 예약 보호).
  //   슬롯 시작 시각만 보면 12:00 시작 60분 예약이 12:30 점심창과 겹쳐도
  //   누락되므로, 예약 실제 시간창 기준으로 검사해야 함.
  let lunchSlotIdxs = [];
  let lunchBlocked = false;
  if (CFG.lunchEnabled) {
    const ls = timeToMinutes(CFG.lunchStart);
    const le = timeToMinutes(CFG.lunchEnd);
    if (le > ls) {
      slots.forEach((m, idx) => {
        const slotEnd = m + CFG.slotMinutes;
        if (slotEnd > ls && m < le) lunchSlotIdxs.push(idx);
      });
      lunchBlocked = activeAppts.some(ap => {
        const sd = new Date(ap.start);
        const sMin = sd.getHours() * 60 + sd.getMinutes();
        const dur = (ap.extendedProps && ap.extendedProps.duration_min)
                    || CFG.slotMinutes;
        const eMin = sMin + dur;
        return eMin > ls && sMin < le;
      });
    }
  }
  const isLunchRow = (rowIdx) =>
    CFG.lunchEnabled && !lunchBlocked && lunchSlotIdxs.includes(rowIdx);

  slots.forEach((m, rowIdx) => {
    // 마지막 행 = 운영 종료 시각 → 드롭 불가 · 시각적으로 옅게 처리
    const isClosing = (rowIdx === slots.length - 1);
    const trCls = isClosing ? ' class="closing-row"'
                            : (isLunchRow(rowIdx) ? ' class="lunch-row"' : '');
    html += `<tr${trCls}><td class="time-cell">${fmtTime(m)}</td>`;

    // 점심시간 가로 병합: 첫 점심 슬롯에서 colspan+rowspan 셀 1개만 출력,
    // 이후 점심 슬롯 행은 데이터 셀 모두 생략 (rowspan 에 흡수)
    if (isLunchRow(rowIdx)) {
      if (rowIdx === lunchSlotIdxs[0]) {
        const span = lunchSlotIdxs.length;
        html += `<td class="lunch-cell" colspan="${cols.length}" rowspan="${span}">
          <div class="lunch-cell-center">🍱 점심시간 ${CFG.lunchStart}~${CFG.lunchEnd}</div></td>`;
      }
      html += `</tr>`;
      return;
    }
    cols.forEach(c => {
      // 치료사 전일 휴무: 첫 행에서 rowspan 처리
      if(!c.isFixed && fullLeaveSet.has(c.id)){
        if(rowIdx === 0){
          html += `<td class="leave-cell leave-cell-large" rowspan="${slots.length}">
            <div class="leave-cell-center">휴무</div></td>`;
        }
        return;
      }

      // 반일 휴무 rowspan 처리 (#4)
      if(!c.isFixed){
        const plan = colLeavePlan[c.id];
        if(plan && plan.skipMap[rowIdx]){
          // 위 행의 rowspan에 흡수됨 → 출력 안 함
          return;
        }
        if(plan && plan.spanMap[rowIdx]){
          const { span, label } = plan.spanMap[rowIdx];
          html += `<td class="leave-cell leave-cell-merged" rowspan="${span}">
            <div class="leave-cell-center">${label}</div></td>`;
          return;
        }
      }

      // 예약 rowspan 에 흡수된 셀은 출력 안 함 (#8)
      const aPlan = apptSpanPlan[c.id];
      if(aPlan && aPlan.skipMap[rowIdx]) return;

      const items = cellsByCol[c.id][m] || [];
      if(items.length){
        const cellInner = items.map(it => renderApptCellItem(it, c)).join('');
        const extraCls = c.isFixed ? 'fixed-col-cell' : '';
        const span = (aPlan && aPlan.spanMap[rowIdx]) || 1;
        const rsAttr = span > 1 ? ` rowspan="${span}"` : '';
        const multiCls = span > 1 ? ' appt-cell-multi' : '';
        html += `<td class="appt-cell-stack ${extraCls}${multiCls}"${rsAttr} data-col="${c.id}" data-slot="${m}">${cellInner}</td>`;
      } else {
        // 빈 셀: 공용 열도 이제 클릭 가능 (#6은 단계 D에서 별도 처리, 여기선 클릭 핸들러만 추가)
        if(c.isFixed){
          html += `<td class="empty-cell empty-fixed appt-cell-stack" data-col="${c.id}" data-slot="${m}" onclick="emptyCellClick(event, ${m}, '${c.id}')"></td>`;
        } else {
          html += `<td class="empty-cell appt-cell-stack" data-col="${c.id}" data-slot="${m}" onclick="emptyCellClick(event, ${m}, '${c.id}')"></td>`;
        }
      }
    });
    html += `</tr>`;
  });
  html += `</tbody></table></div>`;

  document.getElementById('day-board').innerHTML = html;
  attachBoardDnD();
}

// ─────── 드래그앤드롭 (체외충격파 + 도수치료 미배정) ───────

function attachBoardDnD(){
  if(typeof Sortable === 'undefined') return;

  const stacks = document.querySelectorAll('.appt-cell-stack');
  stacks.forEach(el => {
    // 중복 생성 방지
    if(el._sortable){ el._sortable.destroy(); }
    el._sortable = Sortable.create(el, {
      group: 'board-dnd',
      animation: 150,
      delay: 120,                  // 모바일 긴 누름 후 드래그
      delayOnTouchOnly: true,
      touchStartThreshold: 4,
      // 드래그 대상: 체외충격파 + 도수치료 (치료사 열/공용 열 모두 이동 가능)
      filter: (evt, target) => {
        if(!(target instanceof HTMLElement)) return false;
        const line = target.closest('.appt-line');
        if(!line) return true;  // 라인 밖은 필터
        const code = line.dataset.code;
        // 체외충격파/도수치료 모두 어떤 열에서든 드래그 가능 (반복 이동 허용)
        if(isEswtCode(code)) return false;
        if(isManualCode(code)) return false;  // 모든 도수치료 시간항목 드래그 허용
        return true;  // 주사/연골 드래그 불가
      },
      onEnd: async (evt) => {
        const el = evt.item;
        const fromCell = evt.from;
        const toCell   = evt.to;
        const apptId = el.dataset.apptId;
        const code   = el.dataset.code;
        const toColId = toCell?.dataset?.col;
        const fromSlot = fromCell?.dataset?.slot;
        const toSlot   = toCell?.dataset?.slot;
        if(!apptId || !code) return;
        if(fromCell === toCell) return;

        // 시간 변경 여부 계산 (분 단위) — 같은 셀(time+col) 아니면 시간 또는 열이 바뀜
        const slotChanged = (toSlot !== undefined && fromSlot !== undefined && toSlot !== fromSlot);
        const newSlotMin = slotChanged ? parseInt(toSlot, 10) : null;

        // 점심시간 차단 — 드롭 슬롯이 점심창과 겹치면 거부 + 원위치 복귀
        if(newSlotMin != null){
          const dur = (TX_META.treatment_minutes && TX_META.treatment_minutes[code]) || CFG.slotMinutes;
          if(_isLunchOverlap(newSlotMin, newSlotMin + dur)){
            alert(`점심시간(${CFG.lunchStart}~${CFG.lunchEnd})으로는 이동할 수 없습니다.`);
            renderDayBoard();
            return;
          }
        }

        // 체외충격파: 같은 group 안에서 치료사 열 ↔ 공용 열 이동
        if(isEswtCode(code)){
          await handleEswtDrop(apptId, toColId, newSlotMin);
        } else if(isManualCode(code)){
          // 도수치료 미배정 → 치료사 열로만 이동 허용 (모든 시간항목)
          await handleManualDrop(apptId, toColId, newSlotMin, code);
        }
      }
    });
  });
}

// 통계탭 조회 기간의 도수치료 통계를 엑셀(.xlsx)로 다운로드 (보고서용)
async function downloadStatsXlsx(){
  const dFrom = document.getElementById('stat-from')?.value;
  const dTo   = document.getElementById('stat-to')?.value;
  if(!dFrom || !dTo){ alert('조회 기간을 먼저 선택하세요.'); return; }
  if(dTo < dFrom){ alert('종료일이 시작일보다 이전입니다.'); return; }
  try {
    const r = await fetch(`/api/export/stats.xlsx?date_from=${dFrom}&date_to=${dTo}`);
    if(!r.ok){
      const msg = await _apiErrorText(r);
      alert(r.status === 400 ? msg : ('엑셀 생성 실패\n' + msg));
      return;
    }
    const blob = await r.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `도수치료_통계_${dFrom}_${dTo}.xlsx`;
    document.body.appendChild(a); a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 100);
  } catch(e) {
    alert('엑셀 다운로드 오류: ' + (e?.message || e));
  }
}

// 현재 날짜 도수치료 예약을 A4 가로 엑셀로 다운로드 (인쇄용)
async function downloadManualScheduleXlsx(){
  const d = window._currentDate || new Date();
  const dateStr = fmtDate24(d);
  try {
    const r = await fetch(`/api/export/manual-schedule.xlsx?date=${dateStr}`);
    if(!r.ok){ alert('엑셀 생성 실패\n' + await r.text()); return; }
    const blob = await r.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `도수치료_예약현황_${dateStr}.xlsx`;
    document.body.appendChild(a); a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 100);
  } catch(e) {
    alert('엑셀 다운로드 오류: ' + (e?.message || e));
  }
}

// 현재 보드 날짜(Y-M-D) + 슬롯(분) → 서버 저장용 ISO 문자열
function _slotToStartAtISO(slotMin){
  const d = window._currentDate || new Date();
  const y = d.getFullYear();
  const mo = String(d.getMonth()+1).padStart(2,'0');
  const dd = String(d.getDate()).padStart(2,'0');
  const hh = String(Math.floor(slotMin/60)).padStart(2,'0');
  const mm = String(slotMin%60).padStart(2,'0');
  return `${y}-${mo}-${dd}T${hh}:${mm}:00`;
}

// 예약에 드래그 대상 코드 외에 다른 코드가 더 있으면 "분리 이동"이 필요함
//   - 같은 예약의 충격파/도수치료가 한 시간에 묶여 있다가
//     한쪽만 다른 시간으로 옮기면 다른 쪽도 같이 끌려가는 문제 방지
function _apptHasOtherCodes(apptId, draggedCode){
  const codes = (window._BOARD_APPT_CODES||{})[apptId] || [];
  return codes.some(c => c !== draggedCode);
}

async function handleEswtDrop(apptId, toColId, newSlotMin){
  const eswtCode = TX_META.eswt_code;
  if(!eswtCode){ alert('체외충격파 항목이 설정되어 있지 않습니다.'); refresh(); return; }
  let handlerId = null;
  if(toColId === '__eswt__'){
    handlerId = null;  // 공용
  } else if(toColId === '__doctor__' || toColId === '__manual__'){
    alert('체외충격파는 치료사 열 또는 체외충격파 공용 열로만 이동할 수 있습니다.');
    refresh(); return;
  } else {
    const t = THERAPISTS.find(x => x.id === toColId);
    if(!t){ alert('치료사 정보를 찾을 수 없습니다.'); refresh(); return; }
    if(t.can_eswt === false || !employeeCanSelectedTreatments(t, [eswtCode])){
      alert(`${t.name} 선생님은 이 체외충격파 항목을 담당할 수 없습니다.`);
      refresh(); return;
    }
    handlerId = toColId;  // 치료사 id
  }

  const timeChanged = (newSlotMin !== null && newSlotMin !== undefined && !Number.isNaN(newSlotMin));
  const hasOther = _apptHasOtherCodes(apptId, eswtCode);

  // 시간이 바뀌었고 예약에 다른 치료가 더 있으면 → 분리 이동 (원본의 다른 치료는 자리 유지)
  if(timeChanged && hasOther){
    const r = await fetch(`/api/appointments/${apptId}/split-code`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        treatment_code: eswtCode,
        start_at: _slotToStartAtISO(newSlotMin),
        handler_id: handlerId,
      }),
    });
    if(!r.ok){ alert('분리 이동 실패\n' + await r.text()); }
    refresh(); return;
  }

  // 단독 코드이거나 시간 변경 없음 → 기존 경로
  if(timeChanged){
    const r1 = await fetch(`/api/appointments/${apptId}`, {
      method:'PUT',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ start_at: _slotToStartAtISO(newSlotMin) }),
    });
    if(!r1.ok){ alert('시간 변경 실패\n' + await r1.text()); refresh(); return; }
  }
  const r = await fetch(`/api/appointments/${apptId}/assign`, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ treatment_code: eswtCode, handler_id: handlerId }),
  });
  if(!r.ok){ alert(await r.text()); }
  refresh();
}

async function handleManualDrop(apptId, toColId, newSlotMin, draggedCodeArg){
  // 도수치료는 appointments.therapist_id 로 관리 → PUT
  const draggedCode = draggedCodeArg || (TX_META.manual_treatments || [])[0];
  if(!draggedCode){ alert('도수치료 항목이 설정되어 있지 않습니다.'); refresh(); return; }
  let newTid = null;
  if(toColId === '__manual__'){
    newTid = null;  // 공용 미배정
  } else if(toColId === '__doctor__' || toColId === '__eswt__'){
    alert('도수치료는 치료사 열 또는 치료사 미배정 공용 열로만 이동할 수 있습니다.');
    refresh(); return;
  } else {
    // 대상 치료사가 can_manual=true 인지 확인
    const t = THERAPISTS.find(x => x.id === toColId);
    if(!t){ alert('치료사 정보를 찾을 수 없습니다.'); refresh(); return; }
    if(t.can_manual === false){
      alert(`${t.name} 선생님은 도수치료 담당이 아닙니다.`);
      refresh(); return;
    }
    if(!employeeCanSelectedTreatments(t, [draggedCode])){
      alert(`${t.name} 선생님은 이 치료항목을 담당할 수 없습니다.`);
      refresh(); return;
    }
    newTid = toColId;
  }

  const timeChanged = (newSlotMin !== null && newSlotMin !== undefined && !Number.isNaN(newSlotMin));
  const hasOther = _apptHasOtherCodes(apptId, draggedCode);

  // 시간이 바뀌었고 예약에 다른 치료가 더 있으면 → 분리 이동
  //   (원본 예약은 도수 제거, 새 예약에 도수만 포함)
  if(timeChanged && hasOther){
    const r = await fetch(`/api/appointments/${apptId}/split-code`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        treatment_code: draggedCode,
        start_at: _slotToStartAtISO(newSlotMin),
        therapist_id: newTid,
      }),
    });
    if(!r.ok){ alert('분리 이동 실패\n' + await r.text()); }
    refresh(); return;
  }

  // 단독 코드이거나 시간 변경 없음 → 기존 경로 (한 번의 PUT 으로 therapist + time)
  const body = { therapist_id: newTid };
  if(timeChanged) body.start_at = _slotToStartAtISO(newSlotMin);
  const r = await fetch(`/api/appointments/${apptId}`, {
    method:'PUT',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body),
  });
  if(!r.ok){ alert(await r.text()); }
  refresh();
}

// 색상 → 파스텔 변환 (헤더는 진한 색, 셀 배경은 파스텔)
function pastelize(hex){
  // "#3B82F6" → "rgba(59,130,246,0.18)"
  const m = (hex||'').match(/^#?([0-9a-f]{6})$/i);
  if(!m) return 'rgba(229,231,235,0.5)';
  const h = m[1];
  const r = parseInt(h.slice(0,2),16), g = parseInt(h.slice(2,4),16), b = parseInt(h.slice(4,6),16);
  return `rgba(${r},${g},${b},0.18)`;
}

// 셀 한 줄 렌더 (1줄: 차트 성함 (약자)  /  2줄: 예약 시간)
function renderApptCellItem(it, col){
  const stMark = {reserved:'📅', approved:'✅'}[it.status] || '';
  const bg = pastelize(col.color);
  let label = `${it.chart} ${it.name} (${it.short}${it.extraNote?`·${it.extraNote}`:''})`;
  const timeHtml = it.timeStr
    ? `<span class="appt-line-time" style="font-size:11px;color:#475569;line-height:1.2;">${it.timeStr}</span>`
    : '';
  // data-is-manual: 도수치료 시간항목(30/60/80/90 등)을 일반화 — CSS 커서 스타일이
  //   하드코딩된 manual30/60 이 아닌 role 기반으로 자동 반영되도록.
  const isManualAttr = isManualCode(it.code) ? ' data-is-manual="1"' : '';
  return `<div class="appt-line"
      style="background:${bg}; color:#111827; border-left:3px solid ${col.color};"
      data-appt-id="${it.apptId}"
      data-code="${it.code}"${isManualAttr}
      onclick="openAppt('${it.apptId}')">
      <span class="appt-line-mark">${stMark}</span>
      <span class="appt-line-text">${label}</span>
      ${timeHtml}
    </div>`;
}

function moveDay(d){const x=new Date(window._currentDate);x.setDate(x.getDate()+d);window._currentDate=x;renderDayBoard();}
function goToday(){window._currentDate=new Date();renderDayBoard();}
function quickCreateAt(min, tid){
  const d = new Date(window._currentDate);
  d.setHours(Math.floor(min/60), min%60, 0, 0);
  const end = new Date(d.getTime() + CFG.slotMinutes * 60000);
  openCreate(toLocal(d), toLocal(end));

  setTimeout(() => {
    const s = document.getElementById('f-tid');
    if (!s) return;

    if (CURRENT_CATEGORY === 'treatment') {
      s.value = '';
      return;
    }

    if (tid && tid !== '__none__') {
      s.value = tid;
    }
  }, 50);
}
function toLocal(d){const p=n=>String(n).padStart(2,'0');return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;}
function quickCreate(){const n=new Date();n.setMinutes(0,0,0);if(n.getHours()<9)n.setHours(9);const e=new Date(n.getTime()+CFG.slotMinutes*60000);openCreate(toLocal(n),toLocal(e));}
async function fetchPatientForReservation(pid){
  const cached = PATIENTS_BY_ID.get(pid);
  if(cached) return cached;
  try {
    const r = await fetch(`/api/patients/${encodeURIComponent(pid)}?_=${Date.now()}`);
    if(!r.ok) return null;
    const p = await r.json();
    _upsertPatientCache(p);
    return p;
  } catch(e){
    return null;
  }
}

async function quickCreateFor(pid){
  // 예약 탭으로 전환 + 신규 예약 모달 열고 환자 자동 선택
  const reserveBtn = document.querySelector('.tab-btn[onclick*="tab-reserve"]');
  if(reserveBtn && !document.getElementById('tab-reserve').classList.contains('active')){
    switchTab('tab-reserve', reserveBtn);
  }
  const n=new Date(); n.setMinutes(0,0,0);
  if(n.getHours()<9) n.setHours(9);
  const e=new Date(n.getTime()+CFG.slotMinutes*60000);
  openCreate(toLocal(n),toLocal(e));
  setTimeout(async ()=>{
    const p = await fetchPatientForReservation(pid);
    if(!p){ const s=document.getElementById('f-pid'); if(s) s.value=pid; return; }
    _pmRememberRecentPatient(p);
    pidPick(p.id, p.chart_no||'-', p.name||'?', p.birth_date||'-', p.phone||'-');
  }, 60);
}
// 모달 닫기: 배경(modal-bg)에서 mousedown→mouseup 모두 일어났을 때만 닫음.
// 내부에서 드래그 후 배경 위에서 놓는 경우는 닫지 않음.
let _modalBgDownTarget = null;
function modalBgDown(e){ _modalBgDownTarget = e.target; }
function modalBgUp(e){
  const bg = document.getElementById('modal-bg');
  if(_modalBgDownTarget === bg && e.target === bg){
    bg.style.display = 'none';
  }
  _modalBgDownTarget = null;
}
function closeModal(e){
  // 프로그래매틱 호출(취소/닫기 버튼)은 무조건 닫음
  // 이벤트 인자가 들어온 경우(구 호출부 호환) 에도 닫기
  document.getElementById('modal-bg').style.display='none';
}
async function savePatientMemo(pid){
  const el = document.getElementById('a-patient-memo');
  if(!el) return;
  const r = await fetch(`/api/patients/${pid}/memo`, {
    method: 'PATCH',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ memo: el.value }),
  });
  if(r.ok){
    alert('메모가 저장되었습니다.');
    await refresh();
  } else {
    alert('메모 저장 실패');
  }
}
function showModal(h){document.getElementById('modal-body').innerHTML=h;document.getElementById('modal-bg').style.display='flex';}
function _v(id){return document.getElementById(id).value;}

async function loadTodayList(){
  const today = new Date();
  const y = today.getFullYear(), m = String(today.getMonth()+1).padStart(2,'0'), d = String(today.getDate()).padStart(2,'0');
  document.getElementById('today-date').textContent = `${y}.${m}.${d}`;
  try{
    const r = await fetch(`/api/appointments?start=${y}-${m}-${d}T00:00:00&end=${y}-${m}-${d}T23:59:59`);
    const data = await r.json();
    const active = data.filter(a => a.extendedProps.status !== 'canceled');
    const canceled = data.filter(a => a.extendedProps.status === 'canceled');

    document.getElementById('today-items').innerHTML =
      active.length ? buildGroupedHtml(active, false)
                    : '<p class="muted" style="font-size:13px">금일 예약 없음</p>';
    document.getElementById('canceled-items').innerHTML =
      canceled.length ? buildGroupedHtml(canceled, true)
                      : '<p class="muted" style="font-size:12px">취소 없음</p>';
  } catch(e) {
    document.getElementById('today-items').innerHTML = '<p class="muted">조회 실패</p>';
  }
}

// 예약 응답(extendedProps)에서 환자 표시정보 추출.
//   PATIENTS_BY_ID 캐시를 1순위로, 서버가 응답에 embed 한 patient_name/chart 를 2순위로 사용.
//   예약에서 신규 환자를 막 등록해 마스터 캐시 동기화 전이어도 '?' 대신 실제 이름이 나오도록.
//   (예약표 day-board 는 이미 같은 폴백을 사용 — 금일목록/상세모달도 동일하게 맞춤)
function apptPatientInfo(ep){
  return PATIENTS_BY_ID.get(ep.patient_id) || {
    id: ep.patient_id,
    name: ep.patient_name || '',
    chart_no: ep.patient_chart_no || '',
    phone: ep.patient_phone || '',
    birth_date: ep.patient_birth_date || '',
    memo: ep.patient_memo || '',
  };
}

function buildSimpleTodayHtml(items, isC){
  return items
    .sort((a,b) => new Date(a.start) - new Date(b.start))
    .map(a => {
      const ep = a.extendedProps;
      const patient = apptPatientInfo(ep);
      const t = new Date(a.start);
      const time = `${String(t.getHours()).padStart(2,'0')}:${String(t.getMinutes()).padStart(2,'0')}`;
      const stMark = {reserved:'📅', treated:'✓', approved:'✅', canceled:'❌'}[ep.status];

      return `
        <div class="today-row ${isC ? 'canceled' : ''}" onclick="openAppt('${a.id}')">
          <span class="t-time">${stMark} ${time}</span>
          <span class="t-name">${patient?.chart_no || '-'} / ${patient?.name || '?'}</span>
        </div>
      `;
    })
    .join('');
}

function buildGroupedHtml(items, isC){
  // #8 그룹화 규칙:
  //  - 한 예약을 1번만 표시 (중복 제거)
  //  - 그룹 결정 우선순위:
  //    1) 도수치료(치료사 항목 - eswt 제외) 포함 → 그 예약의 therapist_id 그룹 (없으면 '__manual__' = 치료사 미배정)
  //    2) 체외충격파 포함 → assignments['eswt'].handler_id 그룹 (없으면 '__eswt__' = 체외충격파 공용)
  //    3) 의사 항목만 → '__doctor__' = 의사 그룹
  // 약자 라벨은 모든 코드 표시: "도수6·충·주"

  const gr = {};   // groupKey → [appt items]
  items.forEach(a => {
    const ep = a.extendedProps;
    const codes = apptTreatmentCodes(ep);
    if(!codes.length) return;
    const assignMap = {};
    (ep.assignments||[]).forEach(x => { assignMap[x.treatment_code] = x.handler_id; });

    let groupKey = null;
    if(codes.some(isManualCode)){
      // 도수치료 등 치료사(non-eswt) 항목 → therapist_id 기준
      groupKey = ep.therapist_id || '__manual__';
    } else if(codes.includes(TX_META.eswt_code)){
      groupKey = assignMap[TX_META.eswt_code] || '__eswt__';
    } else if(codes.some(isDoctorCode)){
      groupKey = '__doctor__';
    } else {
      groupKey = '__doctor__';   // 안전망
    }
    (gr[groupKey] = gr[groupKey] || []).push(a);
  });

  // 출력 순서: 치료사들 → 치료사 미배정 → 체외충격파 공용 → 의사 그룹
  const order = [
    ...THERAPISTS.filter(t => t.active !== false).map(t => t.id),
    '__manual__', '__eswt__', '__doctor__',
  ];
  return order
    .filter(k => gr[k] && gr[k].length)
    .map(key => {
      let name, color;
      if(key === '__doctor__'){ name = '🩺 의사'; color = '#3B82F6'; }
      else if(key === '__eswt__'){ name = '⚡ 체외충격파(공용)'; color = '#F97316'; }
      else if(key === '__manual__'){ name = '💆 치료사 미배정'; color = '#8B5CF6'; }
      else {
        const t = THERAPISTS.find(x => x.id === key);
        name = t ? t.name : '미배정';
        color = t ? t.color : '#9CA3AF';
      }
      const rows = gr[key]
        .sort((a,b) => new Date(a.start) - new Date(b.start))
        .map(a => rowHtmlV2(a, isC))
        .join('');
      return `<div class="ther-group">
        <div class="ther-group-head" style="background:${color}">${name} <span>(${gr[key].length})</span></div>
        <div class="ther-group-body">${rows}</div>
      </div>`;
    })
    .join('');
}

// 한 줄 형식: 09:00 박환자 1234 (도수6·충)
function rowHtmlV2(a, isC){
  const ep = a.extendedProps;
  const patient = apptPatientInfo(ep);
  const t = new Date(a.start);
  const time = `${String(t.getHours()).padStart(2,'0')}:${String(t.getMinutes()).padStart(2,'0')}`;
  const stMark = {reserved:'📅', approved:'✅', canceled:'❌'}[ep.status] || '';
  const codes = apptTreatmentCodes(ep);
  const shorts = codes.map(c => txShort(c)).join('·');
  return `<div class="today-row ${isC?'canceled':''}" onclick="openAppt('${a.id}')">
    <span class="t-time">${stMark} ${time}</span>
    <span class="t-name">${patient?.name||'?'} ${patient?.chart_no||''}</span>
    <span class="t-tx">(${shorts})</span>
  </div>`;
}

// 레거시 rowHtml (다른 곳에서 호출 시)
function rowHtml(a,isC){
  return rowHtmlV2(a, isC);
}

// ─────── 새 예약 모달 (3단계 재작성) ───────

// 환자의 최근 도수치료 담당 (approved 중 가장 최근) — 이어받기 로직
async function fetchLastManualTherapist(patientId){
  if(!patientId) return null;
  try {
    const r = await fetch(`/api/patients/${patientId}/history?limit=30&offset=0`);
    if(!r.ok) return null;
    const data = await r.json();
    for(const item of (data.items||[])){
      if((item.treatment_codes||[]).some(c => isManualCode(c))){
        // 도수치료 담당 = appointment.therapist_id 자체 (assignments에는 없음)
        if(item.therapist_id) return item.therapist_id;
      }
    }
  } catch(e){}
  return null;
}

// 환자의 도수치료 이력 요약 (신환 체크박스 자동 토글용)
// canceled 제외 reserved/approved 전체에서 도수치료 포함 예약 있는지 확인
async function fetchManualHistorySummary(patientId){
  if(!patientId) return { has_manual_history: false, has_new_patient_flag: false };
  try {
    const r = await fetch(`/api/patients/${patientId}/manual-history-summary`);
    if(!r.ok) return { has_manual_history: false, has_new_patient_flag: false };
    return await r.json();
  } catch(e){ return { has_manual_history: false, has_new_patient_flag: false }; }
}

// 새 예약 모달의 🆕 신환 체크박스 자동 상태 결정
//  - 환자 선택 + 도수치료 항목 체크됨
//    → 과거 도수치료 이력 있으면 자동 해제
//    → 없으면 자동 체크 (첫 도수치료 = 신환)
//  - 도수치료 체크 안 됐거나 환자 미선택 → 해제
//
// ⚠ 사용자 우선 원칙:
//   사용자가 체크박스를 한 번이라도 직접 토글했으면 (_newPatientUserTouched=true)
//   이후 자동 판단은 체크박스 값을 **덮어쓰지 않고** 힌트 텍스트만 갱신한다.
//   openCreate 에서 _modalState 리셋 시 이 플래그도 false 로 초기화.
async function _updateNewPatientCheckbox(){
  const cb = document.getElementById('f-is-new');
  const hintId = 'f-is-new-hint';
  let hint = document.getElementById(hintId);
  if(!cb) return;
  if(!hint){
    hint = document.createElement('div');
    hint.id = hintId;
    hint.className = 'muted';
    hint.style.cssText = 'font-size:12px;margin-top:2px;margin-left:24px;';
    cb.parentElement.parentElement.insertBefore(hint, cb.parentElement.nextSibling);
  }
  // 최초 1회만 onchange 리스너 부착 — 사용자가 만지면 이후 자동 덮어쓰기 금지
  if(!cb._userTouchListenerAttached){
    cb.addEventListener('change', () => {
      _modalState.newPatientUserTouched = true;
      // 사용자가 수동 토글한 순간 힌트도 사용자 우선 모드 표기로
      const h = document.getElementById('f-is-new-hint');
      if(h) h.textContent = '(사용자가 직접 설정함 — 자동 판단 중단)';
    });
    cb._userTouchListenerAttached = true;
  }

  const pid = _v('f-pid');
  const codes = [...document.querySelectorAll('.f-tx-chk:checked')].map(c => c.value);
  const hasManual = codes.some(isManualCode);
  const userTouched = !!_modalState.newPatientUserTouched;

  // 사용자 우선: 이미 만졌으면 cb.checked 건드리지 않음
  if(!pid || !hasManual){
    if(!userTouched) cb.checked = false;
    if(hint) hint.textContent = userTouched ? '(사용자가 직접 설정함)' : '';
    return;
  }
  const sum = await fetchManualHistorySummary(pid);
  if(sum.has_manual_history){
    if(!userTouched) cb.checked = false;
    hint.textContent = userTouched
      ? `이전 도수치료 이력 ${sum.manual_count}건 있음 — 기본 해제 권장 (사용자 설정 유지)`
      : `이전 도수치료 이력 ${sum.manual_count}건 있음 → 신환 아님 (자동 해제)`;
  } else {
    if(!userTouched) cb.checked = true;
    hint.textContent = userTouched
      ? '이전 도수치료 이력 없음 — 기본 체크 권장 (사용자 설정 유지)'
      : '이전 도수치료 이력 없음 → 신환 (자동 체크)';
  }
}

// 특정 날짜에 휴무인 employee_id 집합 (해당 시간대 포함)
async function fetchLeavesOn(dateStr, startMin){
  try {
    const leaves = await (await fetch(`/api/therapist-leaves?date=${dateStr}`)).json();
    const amUntil = _tm(CFG.leaveAmUntil || '14:00');
    const pmFrom  = _tm(CFG.leavePmFrom  || '13:00');
    const off = new Set();
    leaves.forEach(x => {
      const t = x.leave_type || 'full';
      if(t === 'full') off.add(x.therapist_id || x.employee_id);
      else if(t === 'am' && startMin < amUntil) off.add(x.therapist_id || x.employee_id);
      else if(t === 'pm' && startMin >= pmFrom) off.add(x.therapist_id || x.employee_id);
    });
    return off;
  } catch(e){ return new Set(); }
}
function _tm(hhmm){ const [h,m]=hhmm.split(':').map(Number); return h*60+m; }

// 해당 날짜·30분 슬롯의 기존 도수치료 건수 (자기 자신 제외)
async function countManualOnSlot(dateStr, startMin, excludeApptId){
  try {
    const end = dateStr + 'T23:59:59';
    const r = await fetch(`/api/appointments?start=${dateStr}T00:00:00&end=${end}`);
    const arr = await r.json();
    let n = 0;
    arr.forEach(a => {
      if(excludeApptId && a.id === excludeApptId) return;
      const ep = a.extendedProps || {};
      if(ep.status === 'canceled') return;
      const codes = apptTreatmentCodes(ep);
      if(!codes.some(isManualCode)) return;
      const d = new Date(a.start);
      const m = d.getHours()*60 + d.getMinutes();
      // 같은 30분 슬롯에 시작?
      if(Math.floor(m/30) === Math.floor(startMin/30)
         && d.toISOString().slice(0,10) === dateStr){
        n++;
      }
    });
    return n;
  } catch(e){ return 0; }
}

// 현재 예약 모달 상태 (치료사 선택 자동화용)
let _modalState = { manualTherapistAuto: null, patientId: null, newPatientUserTouched: false };
let _pendingCreateReservationState = null;

function renderCreateTreatmentChecks(checkedCodes = []){
  const checkedSet = new Set(checkedCodes || []);
  const codes = (TX_META.treatment_codes || [])
    .filter(code => {
      const tx = txByCode(code);
      return !tx || tx.active !== false;
    });
  if(!codes.length){
    return '<div class="muted" style="padding:8px 4px;font-size:12px;">활성 치료항목이 없습니다.</div>';
  }
  return codes.map(code => {
    const name = TX_META.treatment_names[code] || code;
    const dur = TX_MINUTES[code] || 30;
    return `<label class="chk-item">
      <input type="checkbox" class="f-tx-chk" value="${code}"
             data-name="${escapeAttr(name)}" data-dur="${dur}"
             ${checkedSet.has(code)?'checked':''}
             onchange="onTxCheckChange()">
      <span>${escapeHtml(name)} <em>(${dur}분)</em></span>
    </label>`;
  }).join('');
}

function openCreate(startStr, endStr){
  const sd = new Date(startStr);
  const dateVal = toLocal(sd).slice(0,10);
  const timeVal = toLocal(sd).slice(11,16);
  const defaultDur = Math.max(10, Math.round((new Date(endStr)-sd)/60000));

  _modalState = { manualTherapistAuto: null, patientId: null, newPatientUserTouched: false };

  const trChecks = renderCreateTreatmentChecks();

  showModal(`<div class="modal-title-row">
      <h3>새 예약</h3>
      <button class="mini" type="button" onclick="openNewPatientFromCreateModal()">+ 신규 환자 등록</button>
    </div>
    <div class="patient-picker">
      <label>환자 <small class="muted">(이름/차트/연락처 검색)</small></label>
      <input id="f-pid-search" type="text" placeholder="검색어 입력"
             oninput="pidSearch()" autocomplete="off">
      <div id="f-pid-results" class="pid-results"></div>
      <div id="f-pid-selected" class="pid-selected"><span class="muted">환자를 선택하세요</span></div>
      <input type="hidden" id="f-pid" value="">
    </div>

    <div class="chk-group">
      <div class="chk-label">치료항목 <small class="muted">(전체 항목에서 선택)</small></div>
      <div id="f-tx-list" class="tx-check-list">${trChecks}</div>
    </div>

    <div class="row-3">
      <label>날짜 <input id="f-date" type="date" value="${dateVal}" onchange="onTxCheckChange()"></label>
      <label>시간 <input id="f-time" type="time" step="600" min="${CFG.openTime}" max="${CFG.closeTime}" value="${timeVal}" onchange="onTxCheckChange()"></label>
      <label>총 시간(분) <input id="f-dur" type="number" value="${defaultDur}" min="5" max="480"></label>
    </div>

    <div id="f-therapist-box" class="chk-group" style="display:none">
      <div class="chk-label">담당 치료사
        <small class="muted">(도수치료/체외충격파 담당)</small>
      </div>
      <select id="f-tid" onchange="onTherapistChange()"></select>
      <div id="f-tid-hint" class="muted" style="font-size:12px; margin-top:4px"></div>
    </div>

    <div id="f-eswt-box" class="chk-group" style="display:none">
      <div class="chk-label">체외충격파 담당 <small class="muted">(빈 값 = 공용 미배정)</small></div>
      <select id="f-eswt-tid"></select>
    </div>

    <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
      <input type="checkbox" id="f-is-new" style="width:16px;height:16px;">
      <span>■ 신환 (처음 방문 환자)</span>
    </label>
    <label>📅 당일메모 <small class="muted" style="font-weight:normal;">(오늘 예약에만 기록, 환자기록에 남음)</small>
      <textarea id="f-memo" rows="2" placeholder="오늘 진료/운영 관련 메모"></textarea>
    </label>
    <label id="f-patient-memo-label">📌 메모 <small class="muted" style="font-weight:normal;">(환자 누적 메모 — 다음 예약 때도 계속 표시)</small>
      <textarea id="f-patient-memo" rows="2" placeholder="환자 특이사항/주의사항 등 지속 메모"></textarea>
    </label>

    <div class="modal-actions">
      <button onclick="closeModal()">취소</button>
      <button class="primary" onclick="createAppt()">예약 등록</button>
    </div>`);
}

function captureCreateReservationState(){
  const date = _v('f-date') || '';
  const time = _v('f-time') || '';
  const duration = parseInt(_v('f-dur') || '0') || CFG.slotMinutes || 30;
  return {
    date,
    time,
    duration,
    codes: [...document.querySelectorAll('.f-tx-chk:checked')].map(x => x.value),
    therapistId: _v('f-tid') || '',
    eswtHandlerId: _v('f-eswt-tid') || '',
    patientId: _v('f-pid') || '',
    patientSelectedHtml: document.getElementById('f-pid-selected')?.innerHTML || '',
    memo: _v('f-memo') || '',
    patientMemo: _v('f-patient-memo') || '',
    isNewPatient: document.getElementById('f-is-new')?.checked || false,
  };
}

function _reservationStateRange(state){
  const fallback = new Date();
  fallback.setMinutes(0, 0, 0);
  if(fallback.getHours() < 9) fallback.setHours(9);
  const start = state && state.date && state.time
    ? new Date(`${state.date}T${state.time}:00`)
    : fallback;
  const dur = Math.max(5, parseInt(state?.duration || CFG.slotMinutes || 30));
  const end = new Date(start.getTime() + dur * 60000);
  return [toLocal(start), toLocal(end)];
}

function openNewPatientFromCreateModal(){
  _pendingCreateReservationState = captureCreateReservationState();
  openNewPatientForReservation(true);
}

async function restoreCreateReservationAfterPatient(newP){
  const state = _pendingCreateReservationState;
  _pendingCreateReservationState = null;
  if(!state){
    quickCreateFor(newP.id);
    return;
  }
  const [startStr, endStr] = _reservationStateRange(state);
  openCreate(startStr, endStr);
  setTimeout(async () => {
    const box = document.getElementById('f-tx-list');
    if(box) box.innerHTML = renderCreateTreatmentChecks(state.codes || []);
    if(document.getElementById('f-date')) document.getElementById('f-date').value = state.date || document.getElementById('f-date').value;
    if(document.getElementById('f-time')) document.getElementById('f-time').value = state.time || document.getElementById('f-time').value;
    if(document.getElementById('f-dur')) document.getElementById('f-dur').value = state.duration || document.getElementById('f-dur').value;
    if(document.getElementById('f-memo')) document.getElementById('f-memo').value = state.memo || '';
    if(document.getElementById('f-patient-memo')) document.getElementById('f-patient-memo').value = state.patientMemo || '';
    const newFlag = document.getElementById('f-is-new');
    if(newFlag){
      newFlag.checked = true;
      newFlag.dataset.auto = '1';
    }

    _pmRememberRecentPatient(newP);
    await pidPick(
      newP.id,
      newP.chart_no || '-',
      newP.name || '?',
      newP.birth_date || '-',
      newP.phone || '-'
    );

    const tidSel = document.getElementById('f-tid');
    if(tidSel && state.therapistId) tidSel.value = state.therapistId;
    await onTherapistChange();
    const eswtSel = document.getElementById('f-eswt-tid');
    if(eswtSel && state.eswtHandlerId) eswtSel.value = state.eswtHandlerId;
  }, 80);
}

// 치료항목 체크 변화 → 시간 합산·치료사 드롭다운 가시화·자동 선택 트리거
async function onTxCheckChange(){
  const checks = [...document.querySelectorAll('.f-tx-chk:checked')];
  const codes = checks.map(c => c.value);
  // 시간 합산 (체크박스가 하나라도 변하면 자동 합산, 사용자가 수동 입력한 값은 덮어쓰기)
  let total = 0;
  checks.forEach(c => { total += parseInt(c.getAttribute('data-dur'))||0; });
  if(total) document.getElementById('f-dur').value = total;

  const hasManual = codes.some(isManualCode);
  const hasEswt = codes.some(isEswtCode);
  const box = document.getElementById('f-therapist-box');
  const eswtBox = document.getElementById('f-eswt-box');

  // 치료사 드롭다운: 도수치료 or 체외충격파 중 하나라도 체크되면 표시
  if(hasManual || hasEswt){
    box.style.display = '';
    await rebuildTherapistSelect(codes);
  } else {
    box.style.display = 'none';
  }

  // 체외충격파 별도 셀렉트: 체외충격파만 단독, 또는 도수치료+체외충격파 조합
  if(hasEswt){
    eswtBox.style.display = '';
    await rebuildEswtSelect(codes);
  } else {
    eswtBox.style.display = 'none';
  }
  // 치료항목이 바뀌면 신환 체크박스 재판정 (도수치료 체크/해제 시)
  await _updateNewPatientCheckbox();
}

// 메인 치료사 드롭다운 재구성 — 전체 치료사 표시, 부적격자는 회색·선택불가 (해석 B)
async function rebuildTherapistSelect(codes){
  const sel = document.getElementById('f-tid');
  const hint = document.getElementById('f-tid-hint');
  if(!sel) return;

  const date = _v('f-date');
  const time = _v('f-time');
  const startMin = time ? _tm(time) : 0;
  const offSet = date ? await fetchLeavesOn(date, startMin) : new Set();

  const hasManual = codes.some(isManualCode);
  const hasEswt   = codes.some(isEswtCode);
  const mainTreatmentCodes = hasManual ? codes.filter(isManualCode) : codes.filter(isEswtCode);

  const visibleTherapists = getBoardVisibleTherapists();
  const opts = ['<option value="">(미배정)</option>'];
  visibleTherapists.forEach(t => {
    let disabled = false;
    const reasons = [];
    if(t.active === false){ disabled = true; reasons.push('비활성'); }
    if(hasManual && t.can_manual === false){ disabled = true; reasons.push('도수치료 불가'); }
    // 체외충격파만 있을 땐 체외충격파 가능 여부로 판정
    if(!hasManual && hasEswt && t.can_eswt === false){ disabled = true; reasons.push('체외충격파 불가'); }
    if(!employeeCanSelectedTreatments(t, mainTreatmentCodes)){ disabled = true; reasons.push('치료항목 미선택'); }
    if(offSet.has(t.id)){ disabled = true; reasons.push('휴무'); }

    const label = `${t.name}${reasons.length?` (${reasons.join(', ')})`:''}`;
    opts.push(`<option value="${t.id}" ${disabled?'disabled':''}>${label}</option>`);
  });
  sel.innerHTML = opts.join('');

  // 자동 선택: 도수치료 포함일 때 환자의 이전 도수치료 담당 이어받기
  if(hasManual && _modalState.patientId){
    const last = await fetchLastManualTherapist(_modalState.patientId);
    _modalState.manualTherapistAuto = last;
    if(last){
      const cand = visibleTherapists.find(t => t.id === last);
      if(cand && cand.active !== false && cand.can_manual !== false
         && employeeCanSelectedTreatments(cand, mainTreatmentCodes) && !offSet.has(last)){
        sel.value = last;
        hint.textContent = `이전 담당자(${cand.name}) 자동 선택됨`;
      } else {
        sel.value = '';
        hint.textContent = '이전 담당자가 있으나 현재 선택 불가 — 수동 선택 필요';
      }
    } else {
      sel.value = '';
      hint.textContent = '이전 도수치료 기록 없음 (신규) — 미배정으로 진행 또는 선택';
    }
  } else {
    hint.textContent = '';
  }

  await onTherapistChange();
}

// 메인 치료사가 바뀌면 체외충격파 담당 동기화
async function onTherapistChange(){
  const codes = [...document.querySelectorAll('.f-tx-chk:checked')].map(c=>c.value);
  const hasManual = codes.some(isManualCode);
  const hasEswt   = codes.some(isEswtCode);
  if(!hasEswt) return;

  // 체외충격파+도수치료 동시: 체외충격파 담당 = 도수치료 담당 (단, 그 사람이 체외충격파 가능할 때)
  if(hasManual){
    const tid = _v('f-tid');
    const eswtSel = document.getElementById('f-eswt-tid');
    if(tid){
      const t = THERAPISTS.find(x => x.id === tid);
      const eswtCodes = codes.filter(isEswtCode);
      if(t && t.can_eswt !== false && employeeCanSelectedTreatments(t, eswtCodes)) eswtSel.value = tid;
      else eswtSel.value = '';  // 불가능하면 공용
    } else {
      eswtSel.value = '';
    }
  }
}

// 체외충격파 드롭다운: 체외충격파 가능 + 비휴무 치료사만 선택 가능, 나머지 회색
async function rebuildEswtSelect(codes){
  const sel = document.getElementById('f-eswt-tid');
  if(!sel) return;
  const date = _v('f-date');
  const time = _v('f-time');
  const startMin = time ? _tm(time) : 0;
  const offSet = date ? await fetchLeavesOn(date, startMin) : new Set();
  const eswtCodes = codes.filter(isEswtCode);

  const opts = ['<option value="">(공용 미배정)</option>'];
  getBoardVisibleTherapists().forEach(t => {
    let disabled = false;
    const reasons = [];
    if(t.active === false){ disabled = true; reasons.push('비활성'); }
    if(t.can_eswt === false){ disabled = true; reasons.push('체외충격파 불가'); }
    if(!employeeCanSelectedTreatments(t, eswtCodes)){ disabled = true; reasons.push('치료항목 미선택'); }
    if(offSet.has(t.id)){ disabled = true; reasons.push('휴무'); }
    const label = `${t.name}${reasons.length?` (${reasons.join(', ')})`:''}`;
    opts.push(`<option value="${t.id}" ${disabled?'disabled':''}>${label}</option>`);
  });
  sel.innerHTML = opts.join('');

  // 체외충격파만 단독이면 미배정 기본
  const hasManual = codes.some(isManualCode);
  if(!hasManual){
    sel.value = '';
  } else {
    // 도수치료 담당 따라감
    await onTherapistChange();
  }
}

// 환자 검색 — 서버 검색 기반. 전체 환자 캐시가 아직 로딩 중이어도 바로 찾는다.
let _pidSearchTimer = null;
let _pidSearchSeq = 0;

function _renderPidSearchRows(box, hits){
  box.innerHTML = hits.length
    ? hits.map(p => `<div class="pid-row" onclick='pidPick(${JSON.stringify(p.id)}, ${JSON.stringify(p.chart_no||"-")}, ${JSON.stringify(p.name||"?")}, ${JSON.stringify(p.birth_date||"-")}, ${JSON.stringify(p.phone||"-")})'><b>${p.chart_no||'-'}</b> / ${p.name} <span class="muted">/ ${p.birth_date||'-'} / ${p.phone||'-'}</span></div>`).join('')
    : '<div class="pid-row muted">일치 환자 없음</div>';
  box.style.display = 'block';
}

function pidSearch(){
  const input = document.getElementById('f-pid-search');
  const box = document.getElementById('f-pid-results');
  const q = (input?.value || '').trim();
  clearTimeout(_pidSearchTimer);
  if(!q){ box.innerHTML=''; box.style.display='none'; return; }

  const qLower = q.toLowerCase();
  const localHits = (PATIENTS || []).filter(p =>
    (p.name||'').toLowerCase().includes(qLower) ||
    (p.chart_no||'').toLowerCase().includes(qLower) ||
    (p.phone||'').toLowerCase().includes(qLower) ||
    (p.birth_date||'').toLowerCase().includes(qLower)
  ).slice(0,10);
  if(localHits.length) _renderPidSearchRows(box, localHits);
  else {
    box.innerHTML = '<div class="pid-row muted">검색 중...</div>';
    box.style.display = 'block';
  }

  const seq = ++_pidSearchSeq;
  _pidSearchTimer = setTimeout(async () => {
    try {
      const r = await fetch(`/api/patients/search?q=${encodeURIComponent(q)}&limit=10&offset=0&_=${Date.now()}`);
      if(!r.ok) throw new Error(r.statusText);
      const data = await r.json();
      if(seq !== _pidSearchSeq) return;
      const hits = data.items || [];
      hits.forEach(_upsertPatientCache);
      _renderPidSearchRows(box, hits);
    } catch(e){
      if(seq !== _pidSearchSeq) return;
      box.innerHTML = `<div class="pid-row muted">검색 실패: ${escapeHtml(e.message || e)}</div>`;
      box.style.display = 'block';
    }
  }, 120);
}

async function pidPick(id, chart, name, birth, phone){
  document.getElementById('f-pid').value = id;
  document.getElementById('f-pid-selected').innerHTML =
    `<b>${chart}</b> / ${name} <span class="muted">/ ${birth} / ${phone}</span>`;
  document.getElementById('f-pid-search').value = '';
  document.getElementById('f-pid-results').style.display = 'none';
  _modalState.patientId = id;
  _pmRememberRecentPatient({id, chart_no: chart, name, birth_date: birth, phone});
// 환자 누적 메모 불러오기
  const _foundPt = PATIENTS_BY_ID.get(id);
  const _pmEl = document.getElementById('f-patient-memo');
  if(_pmEl && _foundPt) _pmEl.value = _foundPt.memo || '';
  // 환자 선택되면 치료항목 체크박스 재평가(이어받기 적용)
  await onTxCheckChange();
  // 신환 체크박스 자동 토글 (이전 도수치료 이력 있으면 해제)
  await _updateNewPatientCheckbox();
}

// 2버튼 경고 모달 (예약 위 오버레이)
function confirmBlock(msg){
  return new Promise(resolve => {
    const el = document.createElement('div');
    el.className = 'warn-overlay';
    el.innerHTML = `<div class="warn-box">
      <div class="warn-icon">⚠️</div>
      <div class="warn-msg">${msg}</div>
      <div class="warn-actions">
        <button class="mini" data-v="0">취소</button>
        <button class="mini primary" data-v="1">확인</button>
      </div>
    </div>`;
    document.body.appendChild(el);
    el.addEventListener('click', e => {
      const v = e.target.dataset.v;
      if(v === '0' || v === '1'){
        el.remove();
        resolve(v === '1');
      }
    });
  });
}

async function createAppt(){
  const pid = _v('f-pid');
  if(!pid){ alert('환자를 선택하세요'); return; }
  const date = _v('f-date'), time = _v('f-time');
  if(!date || !time){ alert('날짜/시간을 선택하세요'); return; }
  const checks = [...document.querySelectorAll('.f-tx-chk:checked')];
  if(!checks.length){ alert('치료항목을 하나 이상 선택하세요'); return; }

  const codes = checks.map(c => c.value);
  const duration = parseInt(_v('f-dur')) || 30;

  // 운영시간 체크 (#7)
  const _openMin = _tm(CFG.openTime), _closeMin = _tm(CFG.closeTime);
  const _startMin = _tm(time);
  const _endMin = _startMin + duration;
  if(_startMin < _openMin || _endMin > _closeMin){
    alert(`예약 가능 시간은 운영시간(${CFG.openTime}~${CFG.closeTime}) 내여야 합니다.`);
    return;
  }
  if(_isLunchOverlap(_startMin, _endMin)){
    alert(`점심시간(${CFG.lunchStart}~${CFG.lunchEnd})에는 예약을 잡을 수 없습니다.`);
    return;
  }
  const therapistId = _v('f-tid') || null;     // 도수치료 담당
  const eswtHandlerId = _v('f-eswt-tid') || null;
  const isNewPatient = document.getElementById('f-is-new')?.checked || false;

  const startMin = _tm(time);

  // ─ 도수치료 한도 경고 (설정값 or 자동값 중 작은 쪽)
  const hasManual = codes.some(isManualCode);
  if(hasManual){
    // 가능 치료사 수 - 휴무자 수
    const offSet = await fetchLeavesOn(date, startMin);
    const manualCodes = codes.filter(isManualCode);
    const capableOnShift = getBoardVisibleTherapists().filter(t =>
      t.active !== false && t.can_manual !== false
      && employeeCanSelectedTreatments(t, manualCodes)
      && !offSet.has(t.id)
    ).length;
    const limit = MANUAL_SLOT_LIMIT != null
      ? Math.min(MANUAL_SLOT_LIMIT, capableOnShift)
      : capableOnShift;
    const current = await countManualOnSlot(date, startMin, null);
    if(limit > 0 && current >= limit){
      const ok = await confirmBlock(
        `해당 시간(${time}) 도수치료 인원이 한도(${limit}명)를 초과합니다.<br>그래도 예약하시겠습니까?`
      );
      if(!ok) return;
    } else if(limit === 0 && capableOnShift === 0){
      const ok = await confirmBlock(
        `해당 시간에 도수치료 가능한 치료사가 없습니다.<br>그래도 예약하시겠습니까?`
      );
      if(!ok) return;
    }
  }

  // ─ 의사 전원 휴무 시 주사/연골주사 경고
  const hasDoctorTx = codes.some(isDoctorCode);
  if(hasDoctorTx){
    const offSet = await fetchLeavesOn(date, startMin);
    const availDoctors = DOCTORS.filter(d => d.active !== false && !offSet.has(d.id));
    if(DOCTORS.length > 0 && availDoctors.length === 0){
      const ok = await confirmBlock(
        `해당 시간에 근무 중인 의사가 없습니다.<br>주사/연골주사는 의사 공용 풀로 등록됩니다. 진행하시겠습니까?`
      );
      if(!ok) return;
    }
  }

  // ─ assignments 구성 (주사/연골주사/체외충격파)
  const assignments = [];
  for(const code of codes){
    if(isManualCode(code)) continue;
    if(isEswtCode(code)){
      assignments.push({treatment_code: code, handler_id: eswtHandlerId || null});
    } else {
      // injection / cartilage: 미배정으로 시작 (의사가 나중에 배정)
      assignments.push({treatment_code: code, handler_id: null});
    }
  }

  const trNames = codes.map(c => txName(c)).join(', ');
  const body = {
    patient_id: pid,
    therapist_id: therapistId,
    treatment_codes: codes,
    start_at: `${date}T${time}:00`,
    duration_min: duration,
    memo: (`[${trNames}] ${_v('f-memo')||''}`).trim(),
    assignments: assignments,
    is_new_patient: isNewPatient,
  };

  const r = await fetch('/api/appointments', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(body),
  });
  if(!r.ok){
    const t = await r.text(); alert('예약 저장 실패\n' + t); return;
  }

  // 환자 누적 메모 저장 (변경된 경우)
  const _newPatientMemo = _v('f-patient-memo');
  if(_newPatientMemo !== undefined && pid){
    await fetch(`/api/patients/${pid}/memo`, {
      method: 'PATCH',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ memo: _newPatientMemo }),
    });
  }

  closeModal();
  refresh();
}

// onTreatmentChange 레거시 이름 (다른 곳에서 참조될 수 있음)
function onTreatmentChange(){ return onTxCheckChange(); }
async function refresh(){
  await loadMasters();
  await reloadMiniCalendar(window._miniCal ? window._miniCal.getDate() : new Date());
  await renderDayBoard();
  await loadTodayList();
}

async function openAppt(aid){
  // 단건 조회: 이 날짜만 조회하는 게 가벼움. 연간은 비효율.
  const d = window._currentDate || new Date();
  const y = d.getFullYear();
  const r = await fetch(`/api/appointments?start=${y}-01-01T00:00:00&end=${y+1}-01-01T00:00:00`);
  const ap = (await r.json()).find(a => a.id === aid);
  if(!ap){ alert('예약 없음'); return; }

  const ev = { start: new Date(ap.start), end: new Date(ap.end), extendedProps: ap.extendedProps };
  const ep = ev.extendedProps;
  // 낙관적 락용 버전 — 모달에서 저장 시 함께 전송
  window._currentApptVersion = (typeof ep.version === 'number') ? ep.version : null;
  window._currentApptId = aid;
  const status = ep.status;
  const patient = apptPatientInfo(ep);

  const codes = apptTreatmentCodes(ep);
  const assignMap = {};
  (ep.assignments || []).forEach(a => { assignMap[a.treatment_code] = a.handler_id; });

  const hasManual = codes.some(isManualCode);
  const hasEswt = codes.some(isEswtCode);
  const hasDoctor = codes.some(isDoctorCode);

  // 20-3-1-UI (post-19-P / F-10): canceled + no_show=true 면 "노쇼" 배지로 대체
  const badge = (status === 'canceled' && ep.no_show)
    ? '<span class="badge red">⚠ 노쇼</span>'
    : ({
        reserved: '<span class="badge gray">▦ 예약됨</span>',
        approved: '<span class="badge green">✓ 치료완료</span>',
        canceled: '<span class="badge red">× 취소됨</span>',
      }[status] || '');

  const therapistName = (() => {
    if(!ep.therapist_id) return hasManual ? '미배정(도수치료)' : '-';
    const t = THERAPISTS.find(x => x.id === ep.therapist_id);
    return t ? t.name : '미배정';
  })();

  // 치료항목 뱃지 표시
  const codeBadges = codes.map(c => `<span class="tx-badge">${txName(c)}</span>`).join(' ');

  // 담당 배정 섹션 (수정 가능)
  let assignSection = '';
  if(status === 'reserved'){
    assignSection += `<div class="approval-section active">
      <h4>담당 배정 <small class="muted">(언제든 수정 가능)</small></h4>
      ${hasManual ? renderManualAssignRow(ep, codes.filter(isManualCode)) : ''}
      ${hasEswt ? renderEswtAssignRow(assignMap[TX_META.eswt_code], codes.filter(isEswtCode)) : ''}
      ${hasDoctor ? renderDoctorAssignRows(codes, assignMap) : ''}
      <div class="section-actions"><button class="primary" onclick="saveAssignments('${aid}')">💾 담당 배정 저장</button></div>
    </div>`;
  } else if(status === 'approved'){
    // 승인된 건은 담당자 이름만 표시
    const lines = [];
    if(ep.therapist_id){
      const t = THERAPISTS.find(x => x.id === ep.therapist_id);
      if(codes.some(isManualCode)) lines.push(`도수치료 → ${t?t.name:'-'}`);
    } else if(hasManual){
      lines.push('도수치료 → 미배정');
    }
    if(hasEswt){
      const hid = assignMap[TX_META.eswt_code];
      if(hid){
        const h = THERAPISTS.find(x => x.id === hid);
        lines.push(`체외충격파 → ${h ? h.name : '미배정'}`);
      } else lines.push('체외충격파 → 공용(미배정)');
    }
    codes.filter(isDoctorCode).forEach(c => {
      const hid = assignMap[c];
      if(hid){
        const d = DOCTORS.find(x => x.id === hid) || EMPLOYEES_ALL.find(x => x.id === hid);
        lines.push(`${txName(c)} → ${d ? d.name : '미배정'}`);
      } else lines.push(`${txName(c)} → 의사 공용(미배정)`);
    });
    assignSection = `<div class="approval-section done">
      <h4>담당 배정</h4>
      ${lines.map(l => `<div>${l}</div>`).join('')}
    </div>`;
  }

  // 예약 시간 수정 섹션
  let editSection = '';
  if(status === 'reserved'){
    const startLocal = toLocal(ev.start);
    editSection = `<div class="approval-section active">
      <h4>예약 시간 수정</h4>
      <div class="row-3 compact-edit-row">
        <label>날짜 <input id="a-date" type="date" value="${startLocal.slice(0,10)}"></label>
        <label>시간 <input id="a-time" type="time" step="600" min="${CFG.openTime}" max="${CFG.closeTime}" value="${startLocal.slice(11,16)}"></label>
        <label>시간(분) <input id="a-dur" type="number" value="${ep.duration_min || 30}"></label>
      </div>
      <div class="compact-edit-actions">
        <button class="primary" onclick="saveApptTime('${aid}')">💾 시간 저장</button>
      </div>
    </div>`;
  }

  // 치료완료 섹션
  let approveSection = '';
  if(status === 'reserved'){
    approveSection = `<div class="approval-section active">
      <h4>치료완료 <small class="muted">(치료 후 클릭)</small></h4>
      <button class="primary green" onclick="approveAppt('${aid}')">✓ 치료완료</button>
    </div>`;
  } else if(status === 'approved'){
    approveSection = `<div class="approval-section done">
      <h4>치료완료 ✓</h4>
      <p class="muted">${ep.approved_at || '-'} · 치료완료 처리됨</p>
      <button onclick="revertApprove('${aid}')">↩ 치료완료 취소</button>
    </div>`;
  }

  // 취소/삭제
  let cancelBlock = '';
  if(status === 'reserved'){
    cancelBlock = `<hr><h4>취소 / 삭제</h4>
      <input id="c-memo" placeholder="취소 사유 (선택)">
      <div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap">
        <button class="danger" onclick="cancelAppt('${aid}')">예약 취소</button>
        <button class="danger" onclick="deleteAppt('${aid}')" style="background:#991b1b;color:#fff;border-color:#991b1b">🗑️ 완전 삭제</button>
      </div>`;
  } else if(status === 'canceled'){
    cancelBlock = `<hr><button class="danger" onclick="deleteAppt('${aid}')" style="background:#991b1b;color:#fff">🗑️ 완전 삭제</button>`;
  }

  // 신환 표시 / 수정 (예약됨 상태에서만 체크박스, 완료/취소는 표시만)
  const isNewNow = ep.is_new_patient || false;
  let newPatientSection = '';
  if(status === 'reserved'){
    newPatientSection = `<div class="approval-section active" style="padding:10px 14px;">
      <label style="display:flex;align-items:center;gap:8px;cursor:pointer;font-size:14px;">
        <input type="checkbox" id="a-is-new" ${isNewNow ? 'checked' : ''} style="width:16px;height:16px;">
        <span>■ 신환 (처음 방문 환자)</span>
      </label>
      <button class="primary" style="margin-top:8px;" onclick="saveNewPatient('${aid}')">💾 신환 여부 저장</button>
    </div>`;
  } else if(isNewNow){
    newPatientSection = `<p style="color:#059669;font-weight:600;">■ 신환</p>`;
  }

  showModal(`<div class="appointment-detail-modal"><h3>예약 상세 ${badge}</h3>
    <p><b>${patient?.name||'?'}</b> · 차트 ${patient?.chart_no||'-'} · 담당: ${therapistName}</p>
    <p>${fmtDateTime24(ev.start)} · ${ep.duration_min||30}분</p>
    <p class="tx-badges">${codeBadges}</p>
    ${ep.memo ? `<p style="color:#555;font-size:13px;margin:4px 0;">📅 <b>당일메모:</b> ${ep.memo}</p>` : ''}
    ${patient?.memo ? `<p style="color:#1d4ed8;font-size:13px;margin:4px 0;">📌 <b>메모:</b> ${patient.memo}</p>` : ''}
    ${status === 'reserved' ? `
      <div class="approval-section active" style="margin-top:8px;">
        <h4 style="margin-bottom:6px;">📌 메모 수정 <small class="muted">(저장 시 다음 예약에도 유지)</small></h4>
        <textarea id="a-patient-memo" rows="2" style="width:100%;box-sizing:border-box;">${patient?.memo||''}</textarea>
        <button class="primary" style="margin-top:6px;" onclick="savePatientMemo('${ep.patient_id}')">💾 메모 저장</button>
      </div>` : ''}
    ${newPatientSection}
    ${editSection}
    ${assignSection}
    ${approveSection}
    ${cancelBlock}
    <div class="modal-actions"><button onclick="closeModal()">닫기</button></div></div>`);
}

// 도수치료 담당 드롭다운
function renderManualAssignRow(ep, manualCodes){
  const opts = ['<option value="">(미배정)</option>'];
  getBoardVisibleTherapistsIncludingCurrent(ep.therapist_id).forEach(t => {
    const reasons = [];
    if(t.active === false) reasons.push('비활성');
    if(t.can_manual === false) reasons.push('도수치료 불가');
    if(!employeeCanSelectedTreatments(t, manualCodes)) reasons.push('치료항목 미선택');
    const disabled = reasons.length > 0;
    const reason = reasons.join(', ');
    opts.push(`<option value="${t.id}" ${t.id===ep.therapist_id?'selected':''} ${disabled?'disabled':''}>${t.name}${reason?` (${reason})`:''}</option>`);
  });
  return `<label>도수치료 담당
    <select id="a-manual-tid">${opts.join('')}</select>
  </label>`;
}

// 체외충격파 담당 드롭다운
function renderEswtAssignRow(currentHid, eswtCodes){
  const opts = ['<option value="">(공용 미배정)</option>'];
  getBoardVisibleTherapistsIncludingCurrent(currentHid).forEach(t => {
    const reasons = [];
    if(t.active === false) reasons.push('비활성');
    if(t.can_eswt === false) reasons.push('체외충격파 불가');
    if(!employeeCanSelectedTreatments(t, eswtCodes)) reasons.push('치료항목 미선택');
    const disabled = reasons.length > 0;
    const reason = reasons.join(', ');
    opts.push(`<option value="${t.id}" ${t.id===currentHid?'selected':''} ${disabled?'disabled':''}>${t.name}${reason?` (${reason})`:''}</option>`);
  });
  return `<label>체외충격파 담당
    <select id="a-eswt-tid">${opts.join('')}</select>
  </label>`;
}

// 주사/연골주사 담당 의사 드롭다운
function renderDoctorAssignRows(codes, assignMap){
  let html = '';
  codes.filter(isDoctorCode).forEach(code => {
    const cur = assignMap[code];
    const opts = ['<option value="">(공용 미배정)</option>'];
    DOCTORS.forEach(d => {
      const reasons = [];
      if(d.active === false) reasons.push('비활성');
      if(!employeeCanSelectedTreatments(d, [code])) reasons.push('치료항목 미선택');
      const disabled = reasons.length > 0;
      opts.push(`<option value="${d.id}" ${d.id===cur?'selected':''} ${disabled?'disabled':''}>${d.name}${reasons.length?` (${reasons.join(', ')})`:''}</option>`);
    });
    html += `<label>${txName(code)} 담당
      <select id="a-doc-${code}">${opts.join('')}</select>
    </label>`;
  });
  return html;
}

// 낙관적 락 409 응답 처리 — 다른 PC에서 먼저 수정됐음을 알리고 새로고침
async function handleConflict(resp, aid){
  let msg = '다른 PC에서 먼저 수정되었습니다.';
  try {
    const j = await resp.json();
    if(j?.detail?.message) msg = j.detail.message;
  } catch(e){}
  // 모달 닫고 전체 새로고침 후, 동일 예약 모달 재오픈
  closeModal();
  await refresh();
  alert(msg + '\n최신 정보를 불러옵니다.');
  if(aid){
    try { await openAppt(aid); } catch(e){}
  }
}

// 담당 배정 저장 (도수 담당 변경 = appointments PUT, 나머지는 assign API)
async function saveAssignments(aid){
  // 낙관적 락용 version — 동일 모달 내 연속 저장 대비 매번 갱신
  let ver = window._currentApptVersion;
  // 1) 도수치료 담당 (therapist_id 변경) — appointments PUT
  const manualSel = document.getElementById('a-manual-tid');
  if(manualSel){
    const newTid = manualSel.value || null;
    const r = await fetch(`/api/appointments/${aid}`, {
      method:'PUT',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ therapist_id: newTid, version: ver }),
    });
    if(r.status === 409){ await handleConflict(r, aid); return; }
    if(!r.ok){ alert('도수치료 담당 변경 실패\n' + await r.text()); return; }
    try { const j = await r.json(); if(typeof j.version === 'number') ver = j.version; } catch(e){}
  }
  // 2) 체외충격파 담당 — assign API
  const eswtSel = document.getElementById('a-eswt-tid');
  if(eswtSel){
    const hid = eswtSel.value || null;
    const eswtCode = TX_META.eswt_code;
    if(!eswtCode){ alert('체외충격파 항목이 설정되어 있지 않습니다.'); return; }
    const r = await fetch(`/api/appointments/${aid}/assign`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ treatment_code: eswtCode, handler_id: hid, version: ver }),
    });
    if(r.status === 409){ await handleConflict(r, aid); return; }
    if(!r.ok){ alert('체외충격파 담당 변경 실패\n' + await r.text()); return; }
    try { const j = await r.json(); if(typeof j.version === 'number') ver = j.version; } catch(e){}
  }
  // 3) 의사 역할 치료 담당 (주사/연골주사/추가된 의사 역할 항목 전체) — assign API
  //    모달 HTML 에 렌더된 'a-doc-*' select 를 DOM 에서 직접 찾아 저장.
  //    renderDoctorAssignRows() 가 isDoctorCode 로 select 를 동적 생성하므로,
  //    새 의사 항목이 추가돼도 자동으로 여기 포함됨.
  const docSelects = document.querySelectorAll('[id^="a-doc-"]');
  for(const sel of docSelects){
    const code = sel.id.substring('a-doc-'.length);
    const hid = sel.value || null;
    const r = await fetch(`/api/appointments/${aid}/assign`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ treatment_code: code, handler_id: hid, version: ver }),
    });
    if(r.status === 409){ await handleConflict(r, aid); return; }
    if(!r.ok){ alert(`${txName(code)} 담당 변경 실패\n` + await r.text()); return; }
    try { const j = await r.json(); if(typeof j.version === 'number') ver = j.version; } catch(e){}
  }
  window._currentApptVersion = ver;
  closeModal(); refresh();
}

async function saveNewPatient(aid){
  const checked = document.getElementById('a-is-new')?.checked || false;
  const r = await fetch(`/api/appointments/${aid}`, {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ is_new_patient: checked, version: window._currentApptVersion }),
  });
  if(r.status === 409){ await handleConflict(r, aid); return; }
  if(!r.ok){ alert('저장 실패\n' + await r.text()); return; }
  closeModal(); refresh();
}

async function saveApptTime(aid){
  const date = _v('a-date'), time = _v('a-time');
  const dur = parseInt(_v('a-dur')) || 30;
  if(!date || !time){ alert('날짜/시간을 입력하세요'); return; }
  // 운영시간 체크 (#7)
  const _openMin = _tm(CFG.openTime), _closeMin = _tm(CFG.closeTime);
  const _startMin = _tm(time);
  const _endMin = _startMin + dur;
  if(_startMin < _openMin || _endMin > _closeMin){
    alert(`예약 가능 시간은 운영시간(${CFG.openTime}~${CFG.closeTime}) 내여야 합니다.`);
    return;
  }
  if(_isLunchOverlap(_startMin, _endMin)){
    alert(`점심시간(${CFG.lunchStart}~${CFG.lunchEnd})에는 예약을 잡을 수 없습니다.`);
    return;
  }
  const r = await fetch(`/api/appointments/${aid}`, {
    method:'PUT',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ start_at: `${date}T${time}:00`, duration_min: dur, version: window._currentApptVersion }),
  });
  if(r.status === 409){ await handleConflict(r, aid); return; }
  if(!r.ok){ alert('시간 저장 실패\n' + await r.text()); return; }
  closeModal(); refresh();
}

async function approveAppt(aid){
  const ok = await confirmBlock('치료완료 처리하시겠습니까?<br><small>완료 카운트가 자동으로 증가합니다.</small>');
  if(!ok) return;
  const r = await fetch(`/api/appointments/${aid}/approve`, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ approved_by:'치료완료', version: window._currentApptVersion }),
  });
  if(r.status === 409){ await handleConflict(r, aid); return; }
  if(!r.ok){ alert('치료완료 처리 실패\n' + await r.text()); return; }
  closeModal(); refresh();
}

async function revertApprove(aid){
  const ok = await confirmBlock('치료완료를 취소하시겠습니까?<br><small>완료 카운트가 자동으로 감소합니다.</small>');
  if(!ok) return;
  const r = await fetch(`/api/appointments/${aid}/revert-approve`, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ version: window._currentApptVersion }),
  });
  if(r.status === 409){ await handleConflict(r, aid); return; }
  if(!r.ok){ alert('치료완료 취소 실패\n' + await r.text()); return; }
  closeModal(); refresh();
}

async function cancelAppt(aid){
  const memoEl = document.getElementById('c-memo');
  const body = {
    memo: memoEl ? memoEl.value : '',
    version: window._currentApptVersion,
  };
  const r = await fetch(`/api/appointments/${aid}/cancel`, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body),
  });
  if(r.status === 409){ await handleConflict(r, aid); return; }
  if(!r.ok){ alert('취소 실패\n' + await r.text()); return; }
  closeModal(); refresh();
}

async function deleteAppt(aid){
  if(!confirm('⚠️ 완전 삭제하시겠습니까? 되돌릴 수 없습니다.')) return;
  if(!await ensureAdmin()) return;
  const r = await adminFetch(`/api/appointments/${aid}`, {method:'DELETE'});
  if(!r.ok){ alert('삭제 실패\n' + await r.text()); return; }
  closeModal(); refresh();
}

// ─────── 단계 C #9: 입력 자동 포맷 ───────
// 생년월일: 19900101 → 1990-01-01, 8자리 초과 차단
// 연락처: 01012345678 → 010-1234-5678, 11자리 초과 차단
// data-fmt 속성으로 분류: birth | phone (모달이 동적이라 위임 방식)

function _formatBirthDate(digits){
  // YYYYMMDD → YYYY-MM-DD (부분도 진행)
  digits = digits.slice(0, 8);
  if(digits.length <= 4) return digits;
  if(digits.length <= 6) return digits.slice(0,4) + '-' + digits.slice(4);
  return digits.slice(0,4) + '-' + digits.slice(4,6) + '-' + digits.slice(6);
}

function _formatPhone(digits){
  // 01012345678 → 010-1234-5678
  // 02xxxxxxx (서울) → 02-xxxx-xxxx
  digits = digits.slice(0, 11);
  if(digits.startsWith('02')){
    if(digits.length <= 2) return digits;
    if(digits.length <= 5) return digits.slice(0,2) + '-' + digits.slice(2);
    if(digits.length <= 9) return digits.slice(0,2) + '-' + digits.slice(2,6) + '-' + digits.slice(6);
    return digits.slice(0,2) + '-' + digits.slice(2,6) + '-' + digits.slice(6,10);
  }
  // 모바일/지방국번 (3자리)
  if(digits.length <= 3) return digits;
  if(digits.length <= 7) return digits.slice(0,3) + '-' + digits.slice(3);
  if(digits.length <= 10) return digits.slice(0,3) + '-' + digits.slice(3,6) + '-' + digits.slice(6);
  return digits.slice(0,3) + '-' + digits.slice(3,7) + '-' + digits.slice(7);
}

function _autoFormatInput(el){
  // [패치] 검색용 input 은 자동 포맷 대상에서 제외 (한글 입력 보장)
  const elId = el.id || '';
  if(elId === 'pqs-input' || elId === 'pm-search' || elId === 'f-pid-search') return;

  // 자동 분류: id 또는 placeholder 또는 data-fmt 로 판단
  const id = elId.toLowerCase();
  const ph = (el.placeholder || '').toLowerCase();
  const fmt = el.dataset.fmt;

  let kind = fmt;
  if(!kind){
    if(id.includes('birth') || id.includes('-birth') || ph.includes('생년월일')) kind = 'birth';
    else if(id.includes('phone') || id.includes('-phone') || ph.includes('010-') || ph.includes('02-')) kind = 'phone';
  }
  if(!kind) return;

  const v = el.value || '';
  const digits = v.replace(/\D/g, '');
  const formatted = kind === 'birth' ? _formatBirthDate(digits) : _formatPhone(digits);
  if(formatted !== v){
    // 커서 위치 보존 (간단히 끝으로)
    el.value = formatted;
  }
}

function installInputFormatters(){
  // 위임: document 전체에 input 이벤트 1개만 — 동적 모달도 자동 처리
  document.addEventListener('input', (e) => {
    const el = e.target;
    if(!(el instanceof HTMLInputElement)) return;
    // [패치] 한글 IME 조합 중에는 포맷 적용 스킵 (한글 입력 깨짐 방지)
    if(e.isComposing) return;
    // type=date 는 브라우저 네이티브 처리에 맡김 (자동 포맷 안 함)
    if(el.type === 'date' || el.type === 'time' || el.type === 'number'
       || el.type === 'password' || el.type === 'email' || el.type === 'checkbox'
       || el.type === 'radio') return;
    _autoFormatInput(el);
  }, true);

  // type=date 에 사용자가 19900101 형태 직접 입력은 브라우저가 막아주지 않음.
  // 환자 편집/직원 편집 모달에 type=date 가 있다면 그대로 두고,
  // 단계 D 신규 환자 등록 모달에서는 type=text + data-fmt=birth 로 사용 권장.
}

// ─────── 단계 D #1: 예약탭 환자 검색 패널 ───────

// ── 예약탭 환자 검색: 서버 검색 기반, 20명씩 누적 (더보기 방식) ──
const PQS_PAGE = 20;
let _pqsState = { q: '', hits: [], total: 0, offset: 0 };
let _pqsTimer = null;

function pqsSearch(){
  // 검색어 변경 시 state 리셋 후 첫 페이지 fetch (debounce 180ms)
  clearTimeout(_pqsTimer);
  _pqsTimer = setTimeout(() => {
    const q = (document.getElementById('pqs-input').value || '').trim();
    _pqsState = { q, hits: [], total: 0, offset: 0 };
    if(!q){
      const box = document.getElementById('pqs-results');
      box.style.display = 'none'; box.innerHTML = '';
      return;
    }
    _pqsFetchPage();
  }, 180);
}

async function _pqsFetchPage(){
  const st = _pqsState;
  const url = `/api/patients/search?q=${encodeURIComponent(st.q)}&limit=${PQS_PAGE}&offset=${st.offset}&_=${Date.now()}`;
  try {
    const r = await fetch(url);
    if(!r.ok) throw new Error(r.statusText);
    const d = await r.json();
    st.hits = st.hits.concat(d.items || []);
    st.total = d.total || 0;
    st.offset = st.hits.length;
    // 캐시 upsert (환자 선택 시 즉시 조회 가능하도록)
    (d.items || []).forEach(_upsertPatientCache);
    _renderPqs();
  } catch(e){
    document.getElementById('pqs-results').innerHTML =
      `<div class="pqs-empty">검색 실패: ${e.message}</div>`;
  }
}

function pqsLoadMore(){ _pqsFetchPage(); }

async function pqsRefreshNow(){
  const input = document.getElementById('pqs-input');
  const q = (input && input.value || '').trim();
  _pqsState = { q, hits: [], total: 0, offset: 0 };
  if(!q){
    const box = document.getElementById('pqs-results');
    if(box){ box.style.display = 'none'; box.innerHTML = ''; }
    return;
  }
  await _pqsFetchPage();
}

function _renderPqs(){
  const st = _pqsState;
  const box = document.getElementById('pqs-results');
  if(!st.q){ box.style.display = 'none'; box.innerHTML = ''; return; }
  if(!st.hits.length){
    box.innerHTML = `<div class="pqs-empty">일치하는 환자 없음.
      <a href="#" onclick="event.preventDefault();openNewPatientForReservation()">+ 신규 환자 등록</a></div>`;
    box.style.display = 'block';
    return;
  }
  const rows = st.hits.map(p => `
    <div class="pqs-row-item">
      <div class="pqs-info">
        <b>${p.chart_no||'-'}</b> · <b>${p.name||'?'}</b>
        <span class="muted">/ ${p.birth_date||'-'} / ${p.phone||'-'}</span>
      </div>
      <button class="mini primary" onclick="pqsReserveFor('${p.id}')">＋ 예약</button>
    </div>
  `).join('');
  const remain = Math.max(0, st.total - st.hits.length);
  const more = remain > 0
    ? `<div class="pqs-row-item" style="justify-content:center;padding:8px;">
         <button class="mini" onclick="pqsLoadMore()">+ ${Math.min(PQS_PAGE, remain)}명 더 보기 (${remain.toLocaleString()}명 남음)</button>
       </div>`
    : `<div class="pqs-row-item muted" style="justify-content:center;padding:6px;font-size:12px;">
         전체 ${st.total.toLocaleString()}명 · 모두 표시
       </div>`;
  box.innerHTML = rows + more;
  box.style.display = 'block';
}

function pqsReserveFor(pid){
  // 결과 패널 닫고 새 예약 모달에 환자 자동 선택
  document.getElementById('pqs-input').value = '';
  document.getElementById('pqs-results').style.display = 'none';
  quickCreateFor(pid);
}

// ─────── 단계 D #2: 신규 환자 등록 → 자동으로 예약 모달 열기 ───────

function openNewPatientForReservation(fromCreateModal=false){
  // 환자 편집 모달과 동일하지만 처방/완료 카운트는 숨기고 (counts 비움), 저장 후 자동 예약 진입
  showModal(`<h3>＋ 신규 환자 등록 <small class="muted">(등록 후 곧바로 예약)</small></h3>
    <label>이름 * <input id="np-name" placeholder="환자 이름"></label>
    <div class="row-3">
      <label>연락처
        <input id="np-phone" type="tel" data-fmt="phone" maxlength="13" inputmode="tel"
               placeholder="01012345678 → 010-1234-5678">
      </label>
      <label>차트번호 <input id="np-chart" placeholder="선택사항"></label>
    </div>
    <div class="row-birth-sex">
      <label style="flex:1 1 auto;min-width:0;">생년월일
        <input id="np-birth" type="text" data-fmt="birth" maxlength="10" inputmode="numeric"
               placeholder="19900101 → 1990-01-01">
      </label>
      <div class="sex-group">
        <span class="sex-group-label">성별</span>
        <label class="sex-radio"><input type="radio" name="np-sex" value="M"> M</label>
        <label class="sex-radio"><input type="radio" name="np-sex" value="F"> F</label>
      </div>
    </div>
    <label>환자 기록 <textarea id="np-memo" rows="2" placeholder="진료 메모 (선택)"></textarea></label>
    <div class="modal-actions">
      <button onclick="${fromCreateModal ? 'cancelNewPatientFromCreateModal()' : 'closeModal()'}">취소</button>
      <button class="primary" onclick="saveNewPatientAndReserve()">💾 등록 후 예약</button>
    </div>
  `);
  setTimeout(() => document.getElementById('np-name').focus(), 80);
}

function cancelNewPatientFromCreateModal(){
  const state = _pendingCreateReservationState;
  _pendingCreateReservationState = null;
  if(!state){
    closeModal();
    return;
  }
  const [startStr, endStr] = _reservationStateRange(state);
  openCreate(startStr, endStr);
  setTimeout(async () => {
    const box = document.getElementById('f-tx-list');
    if(box) box.innerHTML = renderCreateTreatmentChecks(state.codes || []);
    if(document.getElementById('f-dur')) document.getElementById('f-dur').value = state.duration || '';
    if(document.getElementById('f-memo')) document.getElementById('f-memo').value = state.memo || '';
    if(document.getElementById('f-is-new')) document.getElementById('f-is-new').checked = state.isNewPatient || false;
    if(state.patientId){
      const pidInput = document.getElementById('f-pid');
      const pidSelected = document.getElementById('f-pid-selected');
      if(pidInput) pidInput.value = state.patientId;
      if(pidSelected && state.patientSelectedHtml) pidSelected.innerHTML = state.patientSelectedHtml;
      _modalState.patientId = state.patientId;
    }
    await onTxCheckChange();
    const tidSel = document.getElementById('f-tid');
    if(tidSel && state.therapistId) tidSel.value = state.therapistId;
    await onTherapistChange();
    const eswtSel = document.getElementById('f-eswt-tid');
    if(eswtSel && state.eswtHandlerId) eswtSel.value = state.eswtHandlerId;
  }, 80);
}

async function saveNewPatientAndReserve(){
  const name = document.getElementById('np-name').value.trim();
  if(!name){ alert('이름을 입력하세요'); return; }
  const sexEl = document.querySelector('input[name="np-sex"]:checked');
  const body = {
    name,
    birth_date: document.getElementById('np-birth').value || null,
    phone: document.getElementById('np-phone').value || null,
    chart_no: document.getElementById('np-chart').value || null,
    gender: sexEl ? sexEl.value : "",
    memo: document.getElementById('np-memo').value || '',
    counts: [],
  };
  const r = await fetch('/api/patients', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body),
  });
  if(!r.ok){
    const msg = await _apiErrorText(r);
    alert(r.status === 409 ? msg : ('환자 등록 실패\n' + msg));
    return;
  }
  const newP = await r.json();
  _upsertPatientCache(newP);
  _pmRememberRecentPatient(newP);
  // 전체 환자 캐시 재로딩은 대량 데이터에서 느릴 수 있으므로 백그라운드로만 갱신한다.
  _loadPatientsBackground();
  closeModal();
  // 새 예약 모달을 그 환자로 자동 진입
  await restoreCreateReservationAfterPatient(newP);
}

// 빈 셀 클릭 → 신규 예약 (#6: 공용 열도 클릭 가능)
function emptyCellClick(e, min, tid){
  if(e.target !== e.currentTarget) return;  // 드래그 placeholder 무시
  // 공용 열 클릭 시: 새 예약 모달을 담당 미배정 상태로 열기
  if(tid === '__doctor__' || tid === '__eswt__' || tid === '__manual__'){
    quickCreateAt(min, '');   // 담당자 빈 값
  } else {
    quickCreateAt(min, tid);
  }
}

// 레거시 호환 함수
async function markTreated(aid){ return approveAppt(aid); }
async function approve(aid){ return approveAppt(aid); }
async function revertTreat(aid){ return revertApprove(aid); }

// ─────── 환자 관리 (6단계: 아코디언 치료이력 + 항목별 완료 카운트) ───────

let PM_OPEN_PID = null;       // 현재 펼쳐진 환자 id
let PM_HISTORY_CACHE = {};    // { pid: {items, total, offset} }
const HISTORY_PAGE = 30;

// ── 환자탭: 서버 검색 + 20명씩 더보기 ──
const PM_PAGE = 20;
let _pmState = { q: '', type: 'name', hits: [], total: 0, offset: 0 };
let _pmTimer = null;

function _pmDoneCompact(p){
  const items = (p.counts_show || []);
  if(!items.length) return '-';
  return items.map(c => `${c.short} ${c.done_count||0}`).join(' · ');
}

function pmSearchDebounced(){
  clearTimeout(_pmTimer);
  _pmTimer = setTimeout(() => pmSearch(), 180);
}

async function pmSearch(force=false){
  // 검색어·필드 변경 시 state 리셋
  const type = document.getElementById('pm-type').value;
  const q = document.getElementById('pm-search').value.trim();
  const stale = force || (_pmState.q !== q) || (_pmState.type !== type);
  if(stale){
    _pmState = { q, type, hits: [], total: 0, offset: 0 };
  }
  if(!Object.keys(LAST_APPTS).length){
    try { LAST_APPTS = await (await fetch('/api/patients/last-appointments')).json(); } catch(e){}
  }
  if(!q){
    // 검색 전: 비어있는 안내 화면 (목록을 미리 그리지 않음)
    _pmRenderEmpty();
    return;
  }
  if(stale){
    await _pmFetchPage();
  } else {
    _pmRender();
  }
}

async function pmLoadMore(){ await _pmFetchPage(); }

async function _pmFetchPage(){
  const st = _pmState;
  const url = `/api/patients/search?q=${encodeURIComponent(st.q)}&field=${encodeURIComponent(st.type)}&limit=${PM_PAGE}&offset=${st.offset}&_=${Date.now()}`;
  try {
    const r = await fetch(url);
    if(!r.ok) throw new Error(r.statusText);
    const d = await r.json();
    st.hits = st.hits.concat(d.items || []);
    st.total = d.total || 0;
    st.offset = st.hits.length;
    (d.items || []).forEach(p => {
      _upsertPatientCache(p);
      _pmRememberRecentPatient(p);
    });
    _pmRender();
  } catch(e){
    document.getElementById('pm-results').innerHTML =
      `<div class="muted" style="padding:16px;color:#B74841;">검색 실패: ${e.message}</div>`;
  }
}

function _pmRenderEmpty(){
  const recent = _pmLoadRecentPatients();
  if(recent.length){
    const rowsHtml = recent.map(p => {
      const last = LAST_APPTS[p.id];
      const lastStr = last ? fmtDate24(new Date(last)) : '-';
      const isOpen = (PM_OPEN_PID === p.id);
      const gtag = (p.gender === 'M') ? '<span class="gender-tag m">M</span>'
                : (p.gender === 'F') ? '<span class="gender-tag f">F</span>'
                : '<span class="muted">-</span>';
      const mainRow = `<tr class="pm-row ${isOpen?'open':''}" onclick="togglePatientHistory('${p.id}', event)">
        <td>${escapeHtml(p.chart_no||'-')}</td>
        <td><b>${escapeHtml(p.name||'')}</b></td>
        <td style="text-align:center;">${gtag}</td>
        <td>${escapeHtml(p.phone||'-')}</td>
        <td>${escapeHtml(p.birth_date||'-')}</td>
        <td class="muted" style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml(p.memo||'-')}</td>
        <td class="tx-done-compact">${escapeHtml(_pmDoneCompact(p))}</td>
        <td>${lastStr}</td>
        <td onclick="event.stopPropagation()">
          <button class="mini" onclick="editPatientById('${p.id}')">수정</button>
          <button class="mini" onclick="quickCreateFor('${p.id}')">예약</button>
          <button class="mini danger" onclick="delPatient('${p.id}')">삭제</button>
        </td></tr>`;
      const historyRow = isOpen ? `<tr class="pm-history-row"><td colspan="9">
        <div id="pm-history-${p.id}" class="pm-history-box">
          <div class="muted">치료이력 불러오는 중...</div>
        </div>
      </td></tr>` : '';
      return mainRow + historyRow;
    }).join('');
    document.getElementById('pm-results').innerHTML = `
      <div class="muted" style="padding:8px 12px;font-size:12px;background:#EEF6FC;border:1px solid #BBD7EE;border-radius:8px;margin-bottom:8px;">
        최근 검색/선택 환자 <b>${recent.length}명</b>
      </div>
      <table class="data-table">
        <thead><tr>
          <th>차트번호</th><th>이름</th><th style="text-align:center;width:48px;">성별</th>
          <th>연락처</th><th>생년월일</th>
          <th>환자 기록</th><th>완료 횟수</th><th>마지막 예약</th><th>관리</th>
        </tr></thead>
        <tbody>${rowsHtml}</tbody>
      </table>`;
    if(PM_OPEN_PID) renderHistoryBox(PM_OPEN_PID);
    return;
  }
  document.getElementById('pm-results').innerHTML = `
    <div class="muted" style="padding:16px 12px;font-size:13px;background:#EEF6FC;border:1px solid #BBD7EE;border-radius:8px;">
      위 검색창에 <b>이름 / 차트번호 / 연락처 / 생년월일</b> 중 하나를 입력하세요.
      <br><span style="font-size:12px;">검색 결과는 20명씩 표시되며, 더보기 버튼으로 추가 조회됩니다.</span>
    </div>`;
}

function _pmRender(){
  const st = _pmState;
  if(!st.q){ _pmRenderEmpty(); return; }
  const list = st.hits;
  const totalHits = st.total;

  const rowsHtml = list.map(p => {
    const last = LAST_APPTS[p.id];
    const lastStr = last ? fmtDate24(new Date(last)) : '-';
    const isOpen = (PM_OPEN_PID === p.id);
    const gtag = (p.gender === 'M') ? '<span class="gender-tag m">M</span>'
              : (p.gender === 'F') ? '<span class="gender-tag f">F</span>'
              : '<span class="muted">-</span>';
    const mainRow = `<tr class="pm-row ${isOpen?'open':''}" onclick="togglePatientHistory('${p.id}', event)">
      <td>${p.chart_no||'-'}</td>
      <td><b>${p.name}</b></td>
      <td style="text-align:center;">${gtag}</td>
      <td>${p.phone||'-'}</td>
      <td>${p.birth_date||'-'}</td>
      <td class="muted" style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${p.memo||'-'}</td>
      <td class="tx-done-compact">${_pmDoneCompact(p)}</td>
      <td>${lastStr}</td>
      <td onclick="event.stopPropagation()">
        <button class="mini" onclick="editPatientById('${p.id}')">수정</button>
        <button class="mini" onclick="quickCreateFor('${p.id}')">예약</button>
        <button class="mini danger" onclick="delPatient('${p.id}')">삭제</button>
      </td></tr>`;
    const historyRow = isOpen ? `<tr class="pm-history-row"><td colspan="9">
      <div id="pm-history-${p.id}" class="pm-history-box">
        <div class="muted">치료이력 불러오는 중...</div>
      </div>
    </td></tr>` : '';
    return mainRow + historyRow;
  }).join('');

  // 상단 요약 + 하단 더보기 버튼
  const remain = Math.max(0, totalHits - list.length);
  const capNote = `<div class="muted" style="padding:8px 12px;font-size:12px;background:#EEF6FC;border:1px solid #BBD7EE;border-radius:8px;margin-bottom:8px;">
      "${st.q}" 검색 결과 <b>${totalHits.toLocaleString()}명</b> · 현재 <b>${list.length}명</b> 표시
    </div>`;
  const moreBtnHtml = remain > 0
    ? `<div style="text-align:center;padding:10px;">
         <button class="mini" onclick="pmLoadMore()">+ ${Math.min(PM_PAGE, remain)}명 더 보기 (${remain.toLocaleString()}명 남음)</button>
       </div>`
    : (list.length > 0
        ? `<div class="muted" style="text-align:center;font-size:12px;padding:6px;">모두 표시됨</div>`
        : '');

  document.getElementById('pm-results').innerHTML = `${capNote}
    <table class="data-table">
    <thead><tr>
      <th>차트번호</th><th>이름</th><th style="text-align:center;width:48px;">성별</th>
      <th>연락처</th><th>생년월일</th>
      <th>환자 기록</th><th>완료 횟수</th><th>마지막 예약</th><th>관리</th>
    </tr></thead>
    <tbody>${rowsHtml || '<tr><td colspan=9>환자 없음</td></tr>'}</tbody>
  </table>${moreBtnHtml}`;

  // 이미 열려있는 환자 있으면 그 내용 재렌더
  if(PM_OPEN_PID){
    renderHistoryBox(PM_OPEN_PID);
  }
}

async function togglePatientHistory(pid, evt){
  // 버튼 영역 클릭은 행 토글 막기 (이미 stopPropagation 걸었지만 보강)
  if(evt && evt.target && evt.target.closest('button')) return;

  if(PM_OPEN_PID === pid){
    // 이미 열린 행 → 닫기
    PM_OPEN_PID = null;
    pmSearch();
    return;
  }
  // 다른 행이 열려있으면 닫고 이 행 열기
  PM_OPEN_PID = pid;
  const recentPatient = PATIENTS_BY_ID.get(pid) || _pmLoadRecentPatients().find(p => p.id === pid);
  if(recentPatient) _pmRememberRecentPatient(recentPatient);
  PM_HISTORY_CACHE[pid] = null;
  pmSearch();
  // 데이터 로드 후 렌더
  await loadHistoryPage(pid, 0, true);
  renderHistoryBox(pid);
}

async function loadHistoryPage(pid, offset, reset){
  const cache = PM_HISTORY_CACHE[pid] || { days: [], items: [], total: 0, offset: 0 };
  if(reset){ cache.days = []; cache.items = []; cache.offset = 0; }
  try {
    const r = await fetch(`/api/patients/${pid}/history?offset=${offset}&limit=${HISTORY_PAGE}`);
    if(!r.ok) throw new Error(r.statusText);
    const data = await r.json();
    // total = 방문일 수 기준, offset/limit 도 방문일 단위
    cache.total = data.total;
    cache.offset = offset + ((data.days || []).length);
    cache.days = cache.days.concat(data.days || []);
    // 하위호환(legacy): fetchLastManualTherapist 가 data.items 를 사용
    cache.items = cache.items.concat(data.items || []);
  } catch(e){
    cache.error = String(e);
  }
  PM_HISTORY_CACHE[pid] = cache;
}

function renderHistoryBox(pid){
  const box = document.getElementById('pm-history-' + pid);
  if(!box) return;
  const cache = PM_HISTORY_CACHE[pid];
  if(!cache){ box.innerHTML = '<div class="muted">치료이력 불러오는 중...</div>'; return; }
  if(cache.error){
    box.innerHTML = `<div class="muted">치료이력 조회 실패: ${cache.error}</div>`;
    return;
  }
  if(cache.total === 0){
    box.innerHTML = '<div class="muted">승인된 치료이력이 없습니다.</div>';
    return;
  }
  const days = cache.days || [];
  const rows = days.map(formatHistoryDay).join('');
  const hasMore = cache.offset < cache.total;
  const moreBtn = hasMore
    ? `<button class="mini" onclick="loadMoreHistory('${pid}')">+ 30일 더 보기 (${cache.total - cache.offset}일 남음)</button>`
    : '';
  box.innerHTML = `<div class="pm-history-list">${rows}</div>
    <div class="pm-history-foot">
      <span class="muted">총 ${cache.total}일 방문 · 현재 ${days.length}일 표시</span>
      ${moreBtn}
    </div>`;
}

async function loadMoreHistory(pid){
  const cache = PM_HISTORY_CACHE[pid];
  if(!cache) return;
  await loadHistoryPage(pid, cache.offset, false);
  renderHistoryBox(pid);
}

// 단일 예약 → "HH:MM 치료1(담당)·치료2(담당)" 조각
function _formatApptInline(ap){
  const dt = new Date(ap.start_at);
  const hh = String(dt.getHours()).padStart(2,'0');
  const mm = String(dt.getMinutes()).padStart(2,'0');
  const codes = ap.treatment_codes || [];
  const assignments = ap.assignments || {};
  const therapistName = ap.therapist_name || null;
  const codeParts = codes.map(code => {
    const name = txName(code);
    if(isDoctorCode(code) || code === TX_META.eswt_code){
      // 의사 역할 (주사/연골주사/새 의사 항목 전체) + 체외충격파 →
      //   assignments[code].handler_name 으로 담당자 표시
      const a = assignments[code];
      const handler = a && a.handler_name;
      return handler ? `${name}(${handler})` : `${name}(미배정)`;
    }
    if(isManualCode(code)){
      // 도수치료(30/60/80/90분 등 모든 시간항목)
      return therapistName ? `${name}(${therapistName})` : `${name}(미배정)`;
    }
    return name;
  }).join('·');
  return `${hh}:${mm} ${codeParts}`;
}

// 방문일 1줄 포맷 — 하루 안 여러 예약은 " / " 로 합쳐 한 줄에 표시
// 예: 2026-04-16  09:30 체외충격파(박치료사) / 10:30 도수치료60분(이치료사)
function formatHistoryDay(day){
  const appts = day.appointments || [];
  const inline = appts.map(_formatApptInline).join(' / ');
  return `<div class="pm-history-line"><b>${day.date}</b> &nbsp; ${inline}</div>`;
}

// 하위호환 — 기존 이름으로 호출하는 코드가 남아있어도 동작하도록 alias
function formatHistoryLine(item){
  // 평면 item → 단일 예약 한 줄로 fallback
  const dt = new Date(item.start_at);
  const y = dt.getFullYear();
  const mo = String(dt.getMonth()+1).padStart(2,'0');
  const d = String(dt.getDate()).padStart(2,'0');
  return `<div class="pm-history-line"><b>${y}-${mo}-${d}</b> &nbsp; ${_formatApptInline(item)}</div>`;
}

// 대량 데이터 대응: id 만 받아 단건 fetch 후 편집 모달 오픈
//   (pmSearch 의 <tr> 에 전체 환자 JSON 을 inline 삽입하면 80K×수KB → HTML 폭증)
async function editPatientById(pid){
  try {
    const r = await fetch(`/api/patients/${pid}`);
    if(!r.ok){ alert('환자 정보를 불러오지 못했습니다: ' + r.status); return; }
    const p = await r.json();
    _upsertPatientCache(p);
    _pmRememberRecentPatient(p);
    return editPatient(p);
  } catch(e){ alert('오류: ' + e.message); }
}

function editPatient(p){
  // 표시 ON + 활성 항목만 처방/완료 입력 노출
  const counts = p.counts || {};
  const visibleItems = Object.values(counts)
    .filter(c => c.show && c.active)
    .sort((a,b) => (a.code||'').localeCompare(b.code||''));

  const rxRow = visibleItems.map(c => `
    <label>${c.name}
      <input id="p-rx-${c.treatment_id}" type="number" min="0" value="${c.rx_count||0}">
    </label>`).join('');
  const doneRow = visibleItems.map(c => `
    <label>${c.name}
      <input id="p-done-${c.treatment_id}" type="number" min="0" value="${c.done_count||0}">
    </label>`).join('');

  const rxBlock = visibleItems.length ? `
    <div class="rx-grid-head">처방 횟수 <small class="muted">(표 표시 항목만)</small></div>
    <div class="rx-grid">${rxRow}</div>
    <div class="rx-grid-head">완료 횟수 <small class="muted">(치료완료 시 자동 증가)</small></div>
    <div class="rx-grid">${doneRow}</div>
  ` : '<p class="muted" style="margin:10px 0">표시 ON 인 치료항목이 없습니다. 관리자 탭 → 치료항목에서 설정하세요.</p>';

  // visible 항목 id 들을 hidden 으로 보존 → savePatient 에서 사용
  const visibleIds = visibleItems.map(c => c.treatment_id).join(',');

  const curGender = (p.gender || '').toUpperCase();
  showModal(`<h3>${p.id?'환자 수정':'신규 환자'}</h3>
    <label>이름 * <input id="p-name" value="${p.name||''}"></label>
    <div class="row-3">
      <label>연락처 <input id="p-phone" type="tel" data-fmt="phone" maxlength="13" inputmode="tel" placeholder="01012345678 → 010-1234-5678" value="${p.phone||''}"></label>
      <label>차트번호 <input id="p-chart" value="${p.chart_no||''}"></label>
    </div>
    <div class="row-birth-sex">
      <label style="flex:1 1 auto;min-width:0;">생년월일
        <input id="p-birth" type="text" data-fmt="birth" maxlength="10" inputmode="numeric" placeholder="19900101 → 1990-01-01" value="${p.birth_date||''}">
      </label>
      <div class="sex-group">
        <span class="sex-group-label">성별</span>
        <label class="sex-radio"><input type="radio" name="p-sex" value="M" ${curGender==='M'?'checked':''}> M</label>
        <label class="sex-radio"><input type="radio" name="p-sex" value="F" ${curGender==='F'?'checked':''}> F</label>
      </div>
    </div>
    ${rxBlock}
    <input type="hidden" id="p-visible-ids" value="${visibleIds}">
    <label>환자 기록 <textarea id="p-memo" rows="3">${p.memo||''}</textarea></label>
    <div class="modal-actions">
      <button onclick="closeModal()">취소</button>
      <button class="primary" onclick="savePatient('${p.id||''}')">저장</button>
    </div>`);
}

async function savePatient(pid){
  const name = _v('p-name').trim();
  if(!name){ alert('이름을 입력하세요'); return; }

  // 동적 카운트 수집
  const visibleIds = (_v('p-visible-ids') || '').split(',').filter(Boolean);
  const counts = visibleIds.map(tid => ({
    treatment_id: tid,
    rx_count:   parseInt(document.getElementById('p-rx-' + tid)?.value || '0') || 0,
    done_count: parseInt(document.getElementById('p-done-' + tid)?.value || '0') || 0,
  }));

  const sexEl = document.querySelector('input[name="p-sex"]:checked');
  const body = {
    name,
    birth_date: _v('p-birth') || null,
    phone: _v('p-phone') || null,
    chart_no: _v('p-chart') || null,
    gender: sexEl ? sexEl.value : "",
    memo: _v('p-memo'),
    counts,
  };
  const url = pid ? `/api/patients/${pid}` : '/api/patients';
  const r = await fetch(url, {
    method: pid ? 'PUT' : 'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body),
  });
  if(!r.ok){
    const msg = await _apiErrorText(r);
    alert(r.status === 409 ? msg : ('저장 실패\n' + msg));
    return;
  }
  const savedP = await r.json();
  _upsertPatientCache(savedP);
  _pmRememberRecentPatient(savedP);
  closeModal();
  LAST_APPTS = {};
  PM_HISTORY_CACHE = {};
  await _reloadPatientsCache();
  await pmSearch(true);
}

async function delPatient(pid){
  if(!await ensureAdmin()) return;
  if(!confirm('환자를 완전히 삭제하시겠습니까?')) return;
  const r = await adminFetch(`/api/patients/${pid}`, {method:'DELETE'});
  if(!r.ok){ alert('삭제 실패\n' + await r.text()); return; }
  if(PM_OPEN_PID === pid) PM_OPEN_PID = null;
  _removePatientFromClientState(pid);
  LAST_APPTS = {};
  PM_HISTORY_CACHE = {};
  await _reloadPatientsCache();
  await pmSearch(true);
  await pqsRefreshNow();
}

// ─────── 직원 관리 (과별 카드 + 권한 override) ───────

let EMPLOYEES = [];  // 전체 직원 캐시
let EMPLOYEE_CATEGORIES = [];

async function loadEmployeesSheet(){
  await loadMasters();
  try {
    [EMPLOYEES, EMPLOYEE_CATEGORIES] = await Promise.all([
      (await fetch('/api/employees')).json(),
      (await fetch('/api/employee-categories')).json(),
    ]);
  } catch(e){
    EMPLOYEES = [];
    EMPLOYEE_CATEGORIES = [];
  }

  const sortKey = (document.getElementById('tm-sort')||{}).value || 'sort_order';

  // API 반환 순서(sort_order)를 기본으로 사용. 다른 키 선택 시 JS 정렬
  if(sortKey !== 'sort_order'){
    const sorter = (a,b) => {
      const av = (a[sortKey]||'').toString();
      const bv = (b[sortKey]||'').toString();
      if(!av && bv) return 1;
      if(av && !bv) return -1;
      return av.localeCompare(bv,'ko',{numeric:true});
    };
    EMPLOYEES.sort(sorter);
  }

  const sortedCats = [...EMPLOYEE_CATEGORIES]
    .sort((a,b) =>
    (a.sort_order||0) - (b.sort_order||0) || (a.name||'').localeCompare(b.name||'', 'ko')
  );
  const known = new Set(sortedCats.map(c => c.id));
  const uncategorized = EMPLOYEES.filter(e => !known.has(e.category_id));
  let html = sortedCats.map(c => {
    const rows = EMPLOYEES.filter(e => e.category_id === c.id);
    return renderEmployeeCategoryCard(c, rows);
  }).join('');
  if(uncategorized.length){
    html += renderEmployeeCategoryCard({
      id: '', name: '미분류', color: '#9CA3AF', active: true,
      default_can_doctor_treatment: false, default_can_manual: true, default_can_eswt: true,
    }, uncategorized);
  }
  document.getElementById('employee-category-list').innerHTML =
    html || '<div class="muted" style="padding:12px">등록된 과가 없습니다.</div>';

  // 직접지정 모드일 때만 드래그 정렬 활성화
  if(sortKey === 'sort_order') initEmpSortable();
}

function capChip(label, on, inherited){
  const cls = on ? 'on' : 'off';
  const suffix = inherited ? ' 기본' : '';
  return `<span class="emp-cap-chip ${cls}">${escapeHtml(label)}${suffix}</span>`;
}

function empCapEmptyText(text){
  return `<span class="emp-cap-empty">${escapeHtml(text)}</span>`;
}

function treatmentChipLabel(t){
  return t.short || t.name || t.code || '치료항목';
}

function treatmentChipList(items, inherited){
  return items.map(t => capChip(treatmentChipLabel(t), true, inherited)).join(' ');
}

function categoryTreatmentChips(category){
  if(!category.id) return empCapEmptyText('과 미지정');
  const items = categoryTreatments(category.id);
  return items.length ? treatmentChipList(items, true) : empCapEmptyText('과 활성 치료항목 없음');
}

function employeeTreatmentItems(e){
  const categoryItems = e.category_id ? categoryTreatments(e.category_id) : [];
  if(e.treatment_override_enabled === true){
    const byId = new Map(categoryItems.map(t => [t.id, t]));
    return (e.treatment_ids || []).map(id => byId.get(id)).filter(Boolean);
  }
  return categoryItems;
}

function employeeTreatmentChips(e){
  const items = employeeTreatmentItems(e);
  const inherited = e.treatment_override_enabled !== true;
  if(!items.length){
    return empCapEmptyText(e.treatment_override_enabled ? '선택 항목 없음' : '과 활성 치료항목 없음');
  }
  return treatmentChipList(items, inherited);
}

function employeeTreatmentSummary(e){
  const items = employeeTreatmentItems(e);
  if(!items.length) return '';
  return e.treatment_override_enabled ? `직접 지정 ${items.length}개` : `과 기본 ${items.length}개`;
}

function renderEmployeeCategoryCard(category, list){
  const defaults = categoryTreatmentChips(category);
  const categoryStatus = category.id && category.active === false
    ? '<span class="badge gray">○ 비활성 과</span>'
    : '';
  const editButtons = category.id ? `
    <button class="mini" onclick='editEmployeeCategory(${JSON.stringify(category).replace(/'/g,"&#39;")})'>과 수정</button>
    <button class="mini" onclick="toggleEmployeeCategory('${category.id}', ${category.active===false?'true':'false'})">${category.active===false?'활성화':'비활성화'}</button>
    <button class="mini danger" onclick="deleteEmployeeCategory('${category.id}')">과 삭제</button>
    <button class="primary" onclick="editEmployee({category_id:'${category.id}', color:'${category.color||'#9CA3AF'}', active:true})">+ 직원 추가</button>
  ` : '';
  const rows = list.map(e => {
    const caps = employeeTreatmentChips(e);
    const txNames = employeeTreatmentSummary(e);
    const txSummary = txNames
      ? `<div class="muted" style="font-size:11px;margin-top:3px">${escapeHtml(txNames)}</div>`
      : '';
    const statusBadge = e.active
      ? '<span class="badge green">● 활성</span>'
      : '<span class="badge gray">○ 비활성</span>';
    return `<tr data-id="${e.id}">
      <td class="drag-handle" title="드래그하여 순서 변경">⠿</td>
      <td><span class="color-dot" style="background:${e.color}"></span> <b>${e.name}</b></td>
      <td>${e.birth_date||'-'}</td>
      <td>${e.phone||'-'}</td>
      <td>${e.hire_date||'-'}</td>
      <td>${caps}${txSummary}</td>
      <td>${statusBadge}</td>
      <td>
        <button class="mini" onclick='editEmployee(${JSON.stringify(e).replace(/'/g,"&#39;")})'>수정</button>
        <button class="mini danger" onclick="delEmployee('${e.id}')">삭제</button>
      </td>
    </tr>`;
  }).join('');
  return `<div class="emp-box">
    <div class="emp-box-head">
      <div>
        <h3><span class="color-dot" style="background:${category.color||'#9CA3AF'}"></span> ${category.name} ${categoryStatus}</h3>
        <div>${defaults}</div>
      </div>
      <div class="sheet-toolbar">${editButtons}</div>
    </div>
    ${rows ? `<table class="data-table emp-table">
      <thead><tr>
        <th style="width:32px"></th>
        <th>이름</th><th>생년월일</th><th>연락처</th><th>입사일</th>
        <th>권한</th><th>상태</th><th>관리</th>
      </tr></thead>
      <tbody class="emp-sortable-body" data-category="${category.id||''}">${rows}</tbody>
    </table>` : '<div class="muted" style="padding:12px">등록된 직원 없음</div>'}
  </div>`;
}

async function _saveEmployeeOrder(tbody){
  const ids = [...tbody.querySelectorAll('tr[data-id]')].map((tr, idx) => ({
    id: tr.dataset.id, sort_order: idx + 1,
  }));
  await fetch('/api/employees/reorder', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(ids),
  });
  // 보드 갱신 (예약현황 열 순서 반영)
  await loadMasters();
  await renderDayBoard();
}

function initEmpSortable(){
  document.querySelectorAll('.emp-sortable-body').forEach(tbody => {
    if(tbody._sortable){ tbody._sortable.destroy(); }
    tbody._sortable = Sortable.create(tbody, {
      handle: '.drag-handle',
      animation: 150,
      ghostClass: 'sortable-ghost',
      onEnd: () => _saveEmployeeOrder(tbody),
    });
  });
}

function boolSelectValue(v){
  if(v === true) return 'true';
  if(v === false) return 'false';
  return '';
}

function readBoolSelect(id){
  const v = document.getElementById(id)?.value;
  if(v === 'true') return true;
  if(v === 'false') return false;
  return null;
}

function employeeCategoryOptions(selectedId){
  const cats = (EMPLOYEE_CATEGORIES || []).filter(c => c.active !== false);
  return cats.map(c => `<option value="${c.id}" ${c.id===selectedId?'selected':''}>${c.name}</option>`).join('');
}

const REPRESENTATIVE_COLORS = [
  ['빨강','#EF4444'], ['주황','#F97316'], ['노랑','#EAB308'], ['연두','#84CC16'], ['초록','#22C55E'],
  ['민트','#14B8A6'], ['하늘','#38BDF8'], ['파랑','#3B82F6'], ['남색','#6366F1'], ['보라','#A855F7'],
];

function renderColorSwatches(prefix, currentColor){
  return REPRESENTATIVE_COLORS.map(([label, color]) =>
    `<span class="color-swatch ${color.toUpperCase()===(currentColor||'').toUpperCase()?'selected':''}" title="${label}" style="background:${color}" data-color="${color}" onclick="selectNamedSwatch('${prefix}', this)"></span>`
  ).join('');
}

function selectNamedSwatch(prefix, el){
  document.querySelectorAll(`[data-color-prefix="${prefix}"] .color-swatch`).forEach(s => s.classList.remove('selected'));
  el.classList.add('selected');
  const input = document.getElementById(`${prefix}-color`);
  if(input) input.value = el.dataset.color;
  updateNamedColorPreview(prefix, el.dataset.color);
}

function openNamedDetailColor(prefix, event){
  event.preventDefault();
  document.getElementById(`${prefix}-color`)?.click();
}

function onNamedDetailColorChange(prefix, color){
  document.querySelectorAll(`[data-color-prefix="${prefix}"] .color-swatch`).forEach(s => s.classList.remove('selected'));
  updateNamedColorPreview(prefix, color);
}

function updateNamedColorPreview(prefix, color){
  const dot = document.getElementById(`${prefix}-color-preview-dot`);
  const txt = document.getElementById(`${prefix}-color-preview-text`);
  if(dot) dot.style.background = color;
  if(txt) txt.textContent = color;
}

function editEmployeeCategory(c){
  c = c || {color:'#3B82F6', active:true, default_can_manual:true, default_can_eswt:true, default_can_doctor_treatment:false};
  const color = c.color || '#3B82F6';
  showModal(`<h3>${c.id?'과 수정':'새 과 추가'}</h3>
    <label>과 이름 * <input id="ec-name" value="${c.name||''}"></label>
    <div class="emp-color-section">
      <div class="emp-color-label">• 과 색상</div>
      <div class="color-swatches" data-color-prefix="ec">
        ${renderColorSwatches('ec', color)}
        <div class="color-detail-container">
          <button class="color-detail-btn" title="세부 색상 선택" onclick="openNamedDetailColor('ec', event)">🎨</button>
          <input class="color-hidden-input" id="ec-color" type="color" value="${color}" oninput="onNamedDetailColorChange('ec', this.value)">
        </div>
      </div>
      <div class="color-preview-row">
        <span class="color-preview-dot" id="ec-color-preview-dot" style="background:${color}"></span>
        <span id="ec-color-preview-text" style="font-size:12px;color:#4B5563;">${color}</span>
      </div>
    </div>
    <div class="caps-section">
      <div class="caps-section-label">과 기본 권한</div>
      <div class="caps-row">
        <label class="chk-item"><input id="ec-manual" type="checkbox" ${c.default_can_manual!==false?'checked':''}> <span>도수치료</span></label>
        <label class="chk-item"><input id="ec-eswt" type="checkbox" ${c.default_can_eswt!==false?'checked':''}> <span>체외충격파</span></label>
      </div>
    </div>
    <label class="chk-item" style="margin-top:6px"><input id="ec-active" type="checkbox" ${c.active!==false?'checked':''}> <span>활성</span></label>
    <div class="modal-actions"><button onclick="closeModal()">취소</button>
      <button class="primary" onclick="saveEmployeeCategory('${c.id||''}')">저장</button></div>`);
}

async function saveEmployeeCategory(cid){
  const body = {
    name: _v('ec-name'),
    color: _v('ec-color') || '#9CA3AF',
    active: document.getElementById('ec-active').checked,
    sort_order: (EMPLOYEE_CATEGORIES.find(c => c.id === cid)||{}).sort_order || 0,
    default_can_doctor_treatment: false,
    default_can_manual: document.getElementById('ec-manual').checked,
    default_can_eswt: document.getElementById('ec-eswt').checked,
  };
  if(!body.name){ alert('과 이름을 입력하세요'); return; }
  const r = await fetch(cid ? `/api/employee-categories/${cid}` : '/api/employee-categories', {
    method: cid ? 'PUT' : 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(body),
  });
  if(!r.ok){ alert('저장 실패\n' + await r.text()); return; }
  closeModal();
  await loadEmployeesSheet();
}

async function toggleEmployeeCategory(cid, active){
  const c = EMPLOYEE_CATEGORIES.find(x => x.id === cid);
  if(!c) return;
  const body = Object.assign({}, c, {active});
  const r = await fetch(`/api/employee-categories/${cid}`, {
    method:'PUT',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body),
  });
  if(!r.ok){ alert('변경 실패\n' + await r.text()); return; }
  await loadEmployeesSheet();
}

async function deleteEmployeeCategory(cid){
  const c = EMPLOYEE_CATEGORIES.find(x => x.id === cid);
  if(!c) return;
  if(!confirm(`과 "${c.name}" 을(를) 삭제하시겠습니까?\n직원/치료항목이 연결되어 있으면 안전하게 비활성화됩니다.`)) return;
  if(!await ensureAdmin()) return;
  const r = await adminFetch(`/api/employee-categories/${cid}`, {method:'DELETE'});
  const data = await r.json().catch(() => ({}));
  if(!r.ok){ alert('삭제 실패\n' + (data.detail || data.error || r.status)); return; }
  if(data.deactivated){
    alert('연결된 직원 또는 치료항목이 있어 과를 비활성화했습니다.');
  }
  await loadEmployeesSheet();
  await loadTreatmentMeta();
}

// ─────── 재고 관리 (과별 품목 + 동적 관리 열) ───────

let INVENTORY_DATA = null;
const INVENTORY_COLLAPSED_KEY = 'inventory_collapsed_categories';
let INVENTORY_COLLAPSED = {};

try {
  INVENTORY_COLLAPSED = JSON.parse(localStorage.getItem(INVENTORY_COLLAPSED_KEY) || '{}') || {};
} catch(e) {
  INVENTORY_COLLAPSED = {};
}

function inventoryIsCollapsed(categoryId){
  return !!INVENTORY_COLLAPSED[categoryId];
}

function saveInventoryCollapsed(){
  try { localStorage.setItem(INVENTORY_COLLAPSED_KEY, JSON.stringify(INVENTORY_COLLAPSED)); } catch(e) {}
}

function toggleInventoryCategory(categoryId){
  INVENTORY_COLLAPSED[categoryId] = !inventoryIsCollapsed(categoryId);
  saveInventoryCollapsed();
  const card = document.getElementById(`inv-card-${categoryId}`);
  const collapsed = inventoryIsCollapsed(categoryId);
  if(card) card.classList.toggle('collapsed', collapsed);
  const btn = document.getElementById(`inv-collapse-${categoryId}`);
  if(btn){
    btn.textContent = collapsed ? '▸' : '▾';
    btn.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
  }
}

function inventoryAuthor(categoryId){
  return (document.getElementById(`inv-author-${categoryId}`)?.value || '').trim();
}

function inventoryDateLabel(value){
  if(!value) return '';
  try {
    const d = new Date(value);
    if(!isNaN(d.getTime())){
      const y = d.getFullYear();
      const m = String(d.getMonth()+1).padStart(2,'0');
      const day = String(d.getDate()).padStart(2,'0');
      const hh = String(d.getHours()).padStart(2,'0');
      const mm = String(d.getMinutes()).padStart(2,'0');
      return `${y}-${m}-${day} ${hh}:${mm}`;
    }
  } catch(e) {}
  return value;
}

function inventoryInputType(field){
  if((field.field_type || 'text') === 'number') return 'number';
  if((field.field_type || 'text') === 'date') return 'date';
  return 'text';
}

async function loadInventorySheet(){
  const box = document.getElementById('inventory-list');
  if(!box) return;
  box.innerHTML = '<p class="muted" style="padding:12px">불러오는 중...</p>';
  try {
    const r = await fetch('/api/inventory');
    const data = await r.json().catch(() => ({}));
    if(!r.ok) throw new Error(data.detail || r.statusText);
    INVENTORY_DATA = data;
    renderInventorySheet(data);
  } catch(e){
    box.innerHTML = '<p class="muted" style="padding:12px;color:#DC2626;">재고 조회 실패: '
      + escapeHtml(e && e.message ? e.message : e)
      + '</p>';
  }
}

function renderInventorySheet(data){
  const box = document.getElementById('inventory-list');
  if(!box) return;
  const sections = data.categories || [];
  if(!sections.length){
    box.innerHTML = '<p class="muted" style="padding:12px">직원 탭에서 과를 먼저 추가하세요.</p>';
    return;
  }
  box.innerHTML = `<div class="inventory-stack">${sections.map(renderInventoryCategory).join('')}</div>`;
}

function renderInventoryCategory(section){
  const c = section.category || {};
  const state = section.state || {};
  const fields = section.fields || [];
  const items = section.items || [];
  const colCount = 3 + fields.length;
  const fieldHeads = fields.map(field => `
    <th class="inventory-field-head">
      <span>${escapeHtml(field.name || '')}</span>
      <span class="inventory-field-actions">
        <button type="button" class="inventory-icon-btn" onclick='editInventoryField("${c.id}", ${JSON.stringify(field).replace(/'/g,"&#39;")})' title="관리 열 수정" aria-label="관리 열 수정">✎</button>
        <button type="button" class="inventory-icon-btn inventory-icon-btn-danger" onclick="deleteInventoryField('${field.id}', '${c.id}')" title="관리 열 삭제" aria-label="관리 열 삭제">×</button>
      </span>
    </th>`).join('');
  const rows = items.map(item => {
    const valueCells = fields.map(field => {
      const v = (item.values || {})[field.id] || '';
      return `<td>
        <input class="inventory-cell-input" type="${inventoryInputType(field)}"
               value="${escapeAttr(v)}"
               data-item-id="${item.id}"
               data-field-id="${field.id}"
               data-category-id="${c.id}"
               data-saved-value="${escapeAttr(v)}"
               onkeydown="if(event.key==='Enter'){event.preventDefault();this.blur();}"
               onblur="saveInventoryValue(this)">
      </td>`;
    }).join('');
    const inactive = item.active === false ? '<span class="badge gray">비활성</span>' : '';
    return `<tr>
      <td><b>${escapeHtml(item.name || '')}</b> ${inactive}</td>
      <td>${escapeHtml(item.unit || '')}</td>
      ${valueCells}
      <td class="inventory-row-actions">
        <button type="button" class="inventory-icon-btn" onclick='editInventoryItem("${c.id}", ${JSON.stringify(item).replace(/'/g,"&#39;")})' title="품목 수정" aria-label="품목 수정">✎</button>
        <button type="button" class="inventory-icon-btn inventory-icon-btn-danger" onclick="deleteInventoryItem('${item.id}', '${c.id}')" title="품목 삭제" aria-label="품목 삭제">×</button>
      </td>
    </tr>`;
  }).join('');
  const emptyRow = `<tr><td colspan="${colCount}" class="muted" style="text-align:left;padding:14px">등록된 품목 없음</td></tr>`;
  const collapsed = inventoryIsCollapsed(c.id);
  return `<div id="inv-card-${escapeAttr(c.id)}" class="inventory-category-card ${collapsed ? 'collapsed' : ''}">
    <div class="inventory-category-head">
      <div>
        <div class="inventory-category-title">
          <button class="inventory-collapse-btn" id="inv-collapse-${escapeAttr(c.id)}"
                  onclick="toggleInventoryCategory('${c.id}')"
                  aria-expanded="${collapsed ? 'false' : 'true'}"
                  title="과 접기/펼치기">${collapsed ? '▸' : '▾'}</button>
          <h3><span class="color-dot" style="background:${c.color || '#9CA3AF'}"></span> ${escapeHtml(c.name || '')}</h3>
        </div>
        <div class="inventory-author-row">
          <label>마지막 작성자
            <input id="inv-author-${c.id}" value="${escapeAttr(state.last_author || '')}" placeholder="작성자 이름">
          </label>
          <button class="mini" onclick="saveInventoryAuthor('${c.id}')">작성자 저장</button>
          <span class="muted">${state.last_author ? '최근 기록 ' + escapeHtml(inventoryDateLabel(state.last_written_at)) : '작성자 기록 없음'}</span>
        </div>
      </div>
      <div class="sheet-toolbar inventory-category-actions">
        <button class="small inventory-action-btn" onclick="editInventoryItem('${c.id}', null)">+ 품목 추가</button>
        <button class="small inventory-action-btn" onclick="editInventoryField('${c.id}', null)">+ 관리 열 추가</button>
      </div>
    </div>
    <div class="inventory-category-body" style="overflow-x:auto;">
      <table class="data-table inventory-table">
        <thead><tr>
          <th class="inventory-item-col">품목</th>
          <th class="inventory-unit-col">단위</th>
          ${fieldHeads}
          <th class="inventory-actions-col">관리</th>
        </tr></thead>
        <tbody>${rows || emptyRow}</tbody>
      </table>
    </div>
  </div>`;
}

function editInventoryItem(categoryId, item){
  item = item || {name:'', unit:'', active:true, sort_order:0};
  showModal(`<h3>${item.id?'재고 품목 수정':'재고 품목 추가'}</h3>
    <label>품목명 * <input id="inv-item-name" value="${escapeAttr(item.name || '')}" autofocus></label>
    <label>단위 <input id="inv-item-unit" value="${escapeAttr(item.unit || '')}" placeholder="예: 개, 박스, 병"></label>
    <label class="chk-item" style="margin-top:8px"><input id="inv-item-active" type="checkbox" ${item.active!==false?'checked':''}> <span>활성</span></label>
    <div class="modal-actions"><button onclick="closeModal()">취소</button>
      <button class="primary" onclick="saveInventoryItem('${categoryId}', '${item.id || ''}', ${Number(item.sort_order || 0)})">저장</button></div>`);
}

async function saveInventoryItem(categoryId, itemId, sortOrder){
  const body = {
    category_id: categoryId,
    name: _v('inv-item-name'),
    unit: _v('inv-item-unit'),
    active: document.getElementById('inv-item-active').checked,
    sort_order: sortOrder || 0,
    author: inventoryAuthor(categoryId),
  };
  if(!body.name.trim()){ alert('품목명을 입력하세요.'); return; }
  const r = await adminFetch(itemId ? `/api/inventory/items/${itemId}` : '/api/inventory/items', {
    method: itemId ? 'PUT' : 'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body),
  });
  if(!r.ok){ alert('저장 실패\n' + await _apiErrorText(r)); return; }
  closeModal();
  await loadInventorySheet();
}

async function deleteInventoryItem(itemId, categoryId){
  if(!confirm('이 품목을 삭제하시겠습니까? 입력된 셀 값도 함께 삭제됩니다.')) return;
  const r = await adminFetch(`/api/inventory/items/${itemId}?author=${encodeURIComponent(inventoryAuthor(categoryId))}`, {method:'DELETE'});
  if(!r.ok){ alert('삭제 실패\n' + await _apiErrorText(r)); return; }
  await loadInventorySheet();
}

function editInventoryField(categoryId, field){
  field = field || {name:'', field_type:'text', active:true, sort_order:0};
  showModal(`<h3>${field.id?'관리 열 수정':'관리 열 추가'}</h3>
    <label>열 이름 * <input id="inv-field-name" value="${escapeAttr(field.name || '')}" placeholder="예: 현재수량, 위치, 유통기한" autofocus></label>
    <label>입력 형태
      <select id="inv-field-type">
        <option value="text" ${(field.field_type||'text')==='text'?'selected':''}>문자</option>
        <option value="number" ${field.field_type==='number'?'selected':''}>숫자</option>
        <option value="date" ${field.field_type==='date'?'selected':''}>날짜</option>
      </select>
    </label>
    <div class="modal-actions"><button onclick="closeModal()">취소</button>
      <button class="primary" onclick="saveInventoryField('${categoryId}', '${field.id || ''}', ${Number(field.sort_order || 0)})">저장</button></div>`);
}

async function saveInventoryField(categoryId, fieldId, sortOrder){
  const body = {
    category_id: categoryId,
    name: _v('inv-field-name'),
    field_type: _v('inv-field-type') || 'text',
    active: true,
    sort_order: sortOrder || 0,
    author: inventoryAuthor(categoryId),
  };
  if(!body.name.trim()){ alert('관리 열 이름을 입력하세요.'); return; }
  const r = await adminFetch(fieldId ? `/api/inventory/fields/${fieldId}` : '/api/inventory/fields', {
    method: fieldId ? 'PUT' : 'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body),
  });
  if(!r.ok){ alert('저장 실패\n' + await _apiErrorText(r)); return; }
  closeModal();
  await loadInventorySheet();
}

async function deleteInventoryField(fieldId, categoryId){
  if(!confirm('이 관리 열을 삭제하시겠습니까? 해당 열에 입력된 값도 함께 삭제됩니다.')) return;
  const r = await adminFetch(`/api/inventory/fields/${fieldId}?author=${encodeURIComponent(inventoryAuthor(categoryId))}`, {method:'DELETE'});
  if(!r.ok){ alert('삭제 실패\n' + await _apiErrorText(r)); return; }
  await loadInventorySheet();
}

async function saveInventoryValue(input){
  const value = input.value || '';
  if(input.dataset.savedValue === value) return;
  input.classList.add('saving');
  try {
    const r = await adminFetch('/api/inventory/values', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        item_id: input.dataset.itemId,
        field_id: input.dataset.fieldId,
        value,
        author: inventoryAuthor(input.dataset.categoryId),
      }),
    });
    if(!r.ok){ throw new Error(await _apiErrorText(r)); }
    input.dataset.savedValue = value;
  } catch(e){
    alert('셀 저장 실패: ' + (e && e.message ? e.message : e));
  } finally {
    input.classList.remove('saving');
  }
}

async function saveInventoryAuthor(categoryId){
  const r = await adminFetch('/api/inventory/category-state', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({
      category_id: categoryId,
      last_author: inventoryAuthor(categoryId),
    }),
  });
  if(!r.ok){ alert('작성자 저장 실패\n' + await _apiErrorText(r)); return; }
  await loadInventorySheet();
}

// ===== 색상 선택기 공통 함수 =====
function selectSwatch(el){
  document.querySelectorAll('.color-swatch').forEach(s => s.classList.remove('selected'));
  el.classList.add('selected');
  const color = el.dataset.color;
  document.getElementById('e-color').value = color;
  updateColorPreview(color);
}

function openDetailColor(event){
  event.preventDefault();
  const input = document.getElementById('e-color');
  input.click();
}

function onDetailColorChange(color){
  document.querySelectorAll('.color-swatch').forEach(s => s.classList.remove('selected'));
  updateColorPreview(color);
}

function updateColorPreview(color){
  const dot = document.getElementById('color-preview-dot');
  const txt = document.getElementById('color-preview-text');
  if(dot) dot.style.background = color;
  if(txt) txt.textContent = color;
}

function initColorPicker(currentColor){
  // 현재 색상과 일치하는 스와치 선택 표시
  let matched = false;
  document.querySelectorAll('.color-swatch').forEach(s => {
    if(s.dataset.color && s.dataset.color.toUpperCase() === currentColor.toUpperCase()){
      s.classList.add('selected');
      matched = true;
    }
  });
  updateColorPreview(currentColor);
}
// ===== 색상 선택기 공통 함수 끝 =====

function categoryTreatments(categoryId){
  return (TX_META.all_treatments || [])
    .filter(t => t.active !== false && (!categoryId || t.category_id === categoryId))
    .sort((a,b) => (a.sort_order||0) - (b.sort_order||0) || (a.name||'').localeCompare(b.name||'', 'ko'));
}

function renderEmployeeTreatmentChecks(categoryId, selectedIds, overrideEnabled){
  const items = categoryTreatments(categoryId);
  if(!items.length){
    return '<div class="muted" style="padding:8px">선택한 과에 활성 치료항목이 없습니다.</div>';
  }
  const selected = new Set(selectedIds || []);
  return items.map(t => {
    const checked = overrideEnabled ? selected.has(t.id) : true;
    return `<label class="chk-item emp-treatment-check">
      <input type="checkbox" class="e-treatment-id" value="${t.id}" ${checked?'checked':''} ${overrideEnabled?'':'disabled'}>
      <span><b>${t.name}</b> <small class="muted">${t.short||t.code}</small></span>
    </label>`;
  }).join('');
}

function refreshEmployeeTreatmentChecks(){
  const catId = _v('e-category');
  const override = document.getElementById('e-treatment-override')?.checked || false;
  const current = [...document.querySelectorAll('.e-treatment-id:checked')].map(x => x.value);
  const box = document.getElementById('e-treatment-list');
  if(box) box.innerHTML = renderEmployeeTreatmentChecks(catId, current, override);
}

function editEmployee(e){
  e = e || {};
  const firstCat = (EMPLOYEE_CATEGORIES || []).find(c => c.active !== false) || {};
  const categoryId = e.category_id || firstCat.id || '';
  const txOverride = e.treatment_override_enabled === true;
  showModal(`<h3>${e.id?'직원 수정':'신규 직원'}</h3>
    <label>이름 * <input id="e-name" value="${e.name||''}"></label>
    <label>과
      <select id="e-category" onchange="refreshEmployeeTreatmentChecks()">${employeeCategoryOptions(categoryId)}</select>
    </label>
    <div class="emp-row2">
      <label>생년월일 <input id="e-birth" type="text" data-fmt="birth" maxlength="10" inputmode="numeric" placeholder="19900101 → 1990-01-01" value="${e.birth_date||''}"></label>
      <label>연락처 <input id="e-phone" type="tel" data-fmt="phone" maxlength="13" inputmode="tel" placeholder="01012345678 → 010-1234-5678" value="${e.phone||''}"></label>
    </div>
    <label>입사일 <input id="e-hire" type="text" data-fmt="birth" maxlength="10" inputmode="numeric" placeholder="20200101 → 2020-01-01" value="${e.hire_date||''}"></label>
    <div class="caps-section">
      <div class="caps-section-label">직원별 권한 override</div>
        <label>도수치료
          <select id="e-manual-cap">
            <option value="" ${boolSelectValue(e.can_manual_override)===''?'selected':''}>과 기본값</option>
            <option value="true" ${boolSelectValue(e.can_manual_override)==='true'?'selected':''}>가능</option>
            <option value="false" ${boolSelectValue(e.can_manual_override)==='false'?'selected':''}>불가</option>
          </select>
        </label>
      <label>체외충격파
        <select id="e-eswt-cap">
          <option value="" ${boolSelectValue(e.can_eswt_override)===''?'selected':''}>과 기본값</option>
          <option value="true" ${boolSelectValue(e.can_eswt_override)==='true'?'selected':''}>가능</option>
          <option value="false" ${boolSelectValue(e.can_eswt_override)==='false'?'selected':''}>불가</option>
        </select>
      </label>
    </div>
    <div class="caps-section">
      <div class="caps-section-label">담당 가능 치료항목</div>
      <label class="chk-item">
        <input id="e-treatment-override" type="checkbox" ${txOverride?'checked':''} onchange="refreshEmployeeTreatmentChecks()">
        <span>직원별로 직접 선택</span>
      </label>
      <div id="e-treatment-list" class="emp-treatment-list">
        ${renderEmployeeTreatmentChecks(categoryId, e.treatment_ids || [], txOverride)}
      </div>
    </div>
    <label class="chk-item" style="margin-top:6px"><input id="e-active" type="checkbox" ${e.active!==false?'checked':''}> <span>활성</span></label>
    <div class="emp-color-section">
      <div class="emp-color-label">• 색상 선택</div>
      <div class="color-swatches" id="color-swatches">
        <span class="color-swatch" title="빨강"    style="background:#EF4444" data-color="#EF4444" onclick="selectSwatch(this)"></span>
        <span class="color-swatch" title="주황"    style="background:#F97316" data-color="#F97316" onclick="selectSwatch(this)"></span>
        <span class="color-swatch" title="노랑"    style="background:#EAB308" data-color="#EAB308" onclick="selectSwatch(this)"></span>
        <span class="color-swatch" title="연두"    style="background:#84CC16" data-color="#84CC16" onclick="selectSwatch(this)"></span>
        <span class="color-swatch" title="초록"    style="background:#22C55E" data-color="#22C55E" onclick="selectSwatch(this)"></span>
        <span class="color-swatch" title="민트"    style="background:#14B8A6" data-color="#14B8A6" onclick="selectSwatch(this)"></span>
        <span class="color-swatch" title="하늘"    style="background:#38BDF8" data-color="#38BDF8" onclick="selectSwatch(this)"></span>
        <span class="color-swatch" title="파랑"    style="background:#3B82F6" data-color="#3B82F6" onclick="selectSwatch(this)"></span>
        <span class="color-swatch" title="남색"    style="background:#6366F1" data-color="#6366F1" onclick="selectSwatch(this)"></span>
        <span class="color-swatch" title="보라"    style="background:#A855F7" data-color="#A855F7" onclick="selectSwatch(this)"></span>
        <div class="color-detail-container">
          <button class="color-detail-btn" title="세부 색상 선택" onclick="openDetailColor(event)">🎨</button>
          <input class="color-hidden-input" id="e-color" type="color" value="${e.color||firstCat.color||'#3B82F6'}" oninput="onDetailColorChange(this.value)">
        </div>
      </div>
      <div class="color-preview-row">
        <span class="color-preview-dot" id="color-preview-dot"></span>
        <span id="color-preview-text" style="font-size:12px;color:#4B5563;">선택된 색상</span>
      </div>
    </div>
    <div class="modal-actions"><button onclick="closeModal()">취소</button>
      <button class="primary" onclick="saveEmployee('${e.id||''}')">저장</button></div>`);

  // 색상 선택기 초기화
  setTimeout(() => initColorPicker(e.color||firstCat.color||'#3B82F6'), 50);
}

async function saveEmployee(eid){
  const categoryId = _v('e-category') || null;
  const validTreatmentIds = new Set(categoryTreatments(categoryId).map(t => t.id));
  const body = {
    name: _v('e-name'),
    category_id: categoryId,
    birth_date: _v('e-birth') || null,
    phone: _v('e-phone') || null,
    hire_date: document.getElementById('e-hire')?.value || null,
    color: _v('e-color'),
    active: document.getElementById('e-active').checked,
    can_doctor_treatment_override: readBoolSelect('e-doc-cap'),
    can_manual_override: readBoolSelect('e-manual-cap'),
    can_eswt_override: readBoolSelect('e-eswt-cap'),
    treatment_override_enabled: document.getElementById('e-treatment-override')?.checked || false,
    treatment_ids: [...document.querySelectorAll('.e-treatment-id:checked')]
      .map(x => x.value)
      .filter(id => validTreatmentIds.has(id)),
  };
  if(!body.name){ alert('이름을 입력하세요'); return; }
  if(!body.category_id){ alert('과를 먼저 추가하고 선택하세요'); return; }
  const url = eid ? `/api/employees/${eid}` : '/api/employees';
  const r = await fetch(url, {
    method: eid ? 'PUT' : 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(body),
  });
  if(!r.ok){
    const t = await r.text(); alert('저장 실패\n' + t); return;
  }
  closeModal();
  await loadMasters();
  loadEmployeesSheet();
}

async function delEmployee(eid){
  if(!await ensureAdmin()) return;
  if(!confirm('삭제하시겠습니까?')) return;
  const r = await adminFetch(`/api/employees/${eid}`, {method:'DELETE'});
  if(!r.ok){ const t = await r.text(); alert('삭제 실패\n' + t); return; }
  await loadMasters();
  loadEmployeesSheet();
}

// ─────── 호환 alias (기존 코드가 부르는 이름들) ───────
// 다른 곳에서 loadTherapistsSheet/editTherapist를 호출할 수 있으니 유지
async function loadTherapistsSheet(){ return loadEmployeesSheet(); }
function editTherapist(t){
  return editEmployee(t || {});
}
async function saveTherapist(tid){ return saveEmployee(tid); }
async function delTherapist(tid){ return delEmployee(tid); }

let REVENUE_RECORDS = null;
let REVENUE_STATS = null;
let DAILY_REPORT = null;
let DAILY_CASH_LEDGER = null;
let _revenueInitialized = false;

function revenueDateStr(d){
  const y = d.getFullYear();
  const m = String(d.getMonth()+1).padStart(2,'0');
  const day = String(d.getDate()).padStart(2,'0');
  return `${y}-${m}-${day}`;
}

function revenueDefaultRange(){
  const now = new Date();
  return [
    revenueDateStr(new Date(now.getFullYear(), now.getMonth(), 1)),
    revenueDateStr(new Date(now.getFullYear(), now.getMonth()+1, 0)),
  ];
}

function revenueSetRange(prefix, fromStr, toStr){
  if(prefix === 'rev-record'){
    const dateEl = document.getElementById('rev-record-date');
    if(dateEl) dateEl.value = toStr || fromStr;
    return;
  }
  const fromEl = document.getElementById(prefix + '-from');
  const toEl = document.getElementById(prefix + '-to');
  if(fromEl) fromEl.value = fromStr;
  if(toEl) toEl.value = toStr;
}

function applyRevenuePreset(target, preset){
  const now = new Date();
  now.setHours(0,0,0,0);
  let start = new Date(now);
  let end = new Date(now);
  if(preset === 'week'){
    start.setDate(end.getDate() - 6);
  } else if(preset === 'month_now'){
    start = new Date(now.getFullYear(), now.getMonth(), 1);
    end = new Date(now.getFullYear(), now.getMonth()+1, 0);
  } else if(preset === 'month_prev'){
    start = new Date(now.getFullYear(), now.getMonth()-1, 1);
    end = new Date(now.getFullYear(), now.getMonth(), 0);
  } else if(preset === '30d'){
    start.setDate(end.getDate() - 29);
  }
  const prefix = target === 'record' ? 'rev-record' : 'rev-stat';
  revenueSetRange(prefix, revenueDateStr(target === 'record' ? end : start), revenueDateStr(end));
  if(target === 'record') loadRevenueRecords();
  else loadRevenueStats();
}

async function initStats(){
  const [fromStr, toStr] = revenueDefaultRange();
  if(!_revenueInitialized){
    revenueSetRange('rev-record', revenueDateStr(new Date()), revenueDateStr(new Date()));
    revenueSetRange('rev-stat', fromStr, toStr);
    const reportDateEl = document.getElementById('daily-report-date');
    if(reportDateEl) reportDateEl.value = revenueDateStr(new Date());
    const cashLedgerDateEl = document.getElementById('daily-cash-ledger-date');
    if(cashLedgerDateEl) cashLedgerDateEl.value = revenueDateStr(new Date());
    _revenueInitialized = true;
  }
  await loadRevenueUiSettings();
  loadRevenueRecords();
}

async function switchRevenueTab(name, btn){
  document.querySelectorAll('#admin-stats .revenue-sub-tab').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('#admin-stats .revenue-pane').forEach(p => p.classList.remove('active'));
  if(btn) btn.classList.add('active');
  const pane = document.getElementById('revenue-pane-' + name);
  if(pane) pane.classList.add('active');
  await loadRevenueUiSettings();
  if(name === 'records') loadRevenueRecords();
  if(name === 'cash-ledger') loadDailyCashLedger();
  if(name === 'stats') loadRevenueStats();
  if(name === 'daily-report') loadDailyReport();
}

function applyDailyCashLedgerPreset(preset){
  if(preset === 'today'){
    const el = document.getElementById('daily-cash-ledger-date');
    if(el) el.value = revenueDateStr(new Date());
  }
  loadDailyCashLedger();
}

function applyDailyReportPreset(preset){
  if(preset === 'today'){
    const el = document.getElementById('daily-report-date');
    if(el) el.value = revenueDateStr(new Date());
  }
  loadDailyReport();
}

function dailyReportSelectedCodes(){
  return [...document.querySelectorAll('.daily-report-treatment-check:checked')]
    .map(x => x.value)
    .filter(Boolean);
}

function dailyReportCurrentFields(){
  return [...document.querySelectorAll('.daily-report-field')].map((box, idx) => {
    const type = box.dataset.type || 'long_text';
    const label = box.querySelector('.daily-report-field-label')?.value || '';
    let value = '';
    if(type === 'checkbox'){
      value = !!box.querySelector('.daily-report-field-value')?.checked;
    } else {
      value = box.querySelector('.daily-report-field-value')?.value || '';
    }
    return {
      id: box.dataset.id || '',
      label,
      type,
      value,
      sort_order: idx,
    };
  });
}

function dailyReportTreatmentBase(code){
  const t = (DAILY_REPORT?.treatments || []).find(x => x.code === code) || {};
  return {
    code,
    treatment_id: t.id || '',
    treatment_name: t.name || code,
    treatment_short: t.short || t.name || code,
    category_id: t.category_id || '',
    category_name: t.category_name || '',
    quantity_total: 0,
    price_total: 0,
    incentive_total: 0,
    net_total: 0,
    record_count: 0,
  };
}

function dailyReportBuildAuto(selectedCodes){
  const byCode = {};
  (DAILY_REPORT?.settlement_items || []).forEach(row => {
    if(row && row.code) byCode[row.code] = row;
  });
  const items = (selectedCodes || []).map(code => Object.assign(
    dailyReportTreatmentBase(code),
    byCode[code] || {}
  ));
  const totals = items.reduce((acc, row) => {
    acc.quantity_total += Number(row.quantity_total || 0);
    acc.price_total += Number(row.price_total || 0);
    acc.incentive_total += Number(row.incentive_total || 0);
    acc.net_total += Number(row.net_total || 0);
    acc.record_count += Number(row.record_count || 0);
    return acc;
  }, {quantity_total:0, price_total:0, incentive_total:0, net_total:0, record_count:0});
  return {items, totals};
}

function renderDailyReportJournal(){
  const journal = DAILY_REPORT?.journal || {};
  const revenueRecord = DAILY_REPORT?.revenue_record || {};
  const revenueLines = journal.revenue_lines || [];
  const revenueSummaryKeys = new Set(['collected_amount', 'total_expense', 'cash_total']);
  const revenueSummary = revenueLines.filter(row => revenueSummaryKeys.has(row.key));
  const revenueDetail = revenueLines.filter(row => !revenueSummaryKeys.has(row.key) && Number(row.amount || 0) !== 0);
  const revenueRows = revenueDetail.map(row => `
    <tr>
      <td>${escapeHtml(revenueFieldLabel(row.key) || row.label || row.key || '')}</td>
      <td>${revenueMoney(row.amount)}</td>
    </tr>`).join('');
  const treatmentLines = journal.treatment_lines || [];
  const totals = journal.totals || {};
  const treatmentRows = treatmentLines.map(row => `
    <tr>
      <td>${escapeHtml(row.label || row.code || '')}</td>
      <td>${revenueQuantity(row.quantity_total)}</td>
      <td>${revenueMoney(row.price_total)}</td>
      <td>${revenueMoney(row.incentive_total)}</td>
    </tr>`).join('');
  return `
    <div class="stats-section daily-report-journal-section">
      <h3 class="stats-section-title">업무일지 반영</h3>
      <div class="daily-report-journal-grid">
        <div class="daily-report-journal-panel">
          <h4>매출 기록</h4>
          <div class="daily-report-journal-total">
            ${revenueSummary.map(row => `<span>${escapeHtml(revenueFieldLabel(row.key) || row.label || row.key || '')} ${revenueMoney(row.amount)}</span>`).join('') || '<span>매출 기록 없음</span>'}
          </div>
          <div style="overflow-x:auto;">
            <table class="data-table daily-report-journal-table daily-report-journal-money-table">
              <thead><tr><th>항목</th><th>금액</th></tr></thead>
              <tbody>${revenueRows || `<tr><td colspan="2">${revenueRecord.exists ? '추가 금액 없음' : '매출 기록 없음'}</td></tr>`}</tbody>
            </table>
          </div>
          ${revenueRecord.memo ? `<div class="daily-report-journal-memo"><b>메모</b><span>${escapeHtml(revenueRecord.memo)}</span></div>` : ''}
        </div>
        <div class="daily-report-journal-panel">
          <h4>정산 입력</h4>
          <div class="daily-report-journal-total">
            <span>수량 ${revenueQuantity(totals.quantity_total)}</span>
            <span>수가 ${revenueMoney(totals.price_total)}</span>
            <span>인센티브 ${revenueMoney(totals.incentive_total)}</span>
          </div>
          <div style="overflow-x:auto;">
            <table class="data-table daily-report-journal-table">
              <thead><tr><th>항목</th><th>수량</th><th>정산 수가</th><th>인센티브</th></tr></thead>
              <tbody>${treatmentRows || '<tr><td colspan="4">정산 기록 없음</td></tr>'}</tbody>
            </table>
          </div>
        </div>
      </div>
    </div>`;
}

function renderDailyReportAuto(){
  const el = document.getElementById('daily-report-auto');
  if(!el || !DAILY_REPORT) return;
  const selected = dailyReportSelectedCodes();
  DAILY_REPORT.selected_treatment_codes = selected;
  const auto = dailyReportBuildAuto(selected);
  DAILY_REPORT.auto = auto;
  const rows = (auto.items || []).map(row => `
    <tr>
      <td>${escapeHtml(row.treatment_short || row.treatment_name || row.code)}</td>
      <td>${revenueQuantity(row.quantity_total)}</td>
      <td>${revenueMoney(row.price_total)}</td>
      <td>${revenueMoney(row.incentive_total)}</td>
      <td>${revenueMoney(row.net_total)}</td>
    </tr>`).join('');
  el.innerHTML = `
    <div class="stats-summary-grid daily-report-summary-grid">
      <div class="stat-card"><div class="stat-label">선택 항목</div><div class="stat-value">${revenueQuantity(selected.length)}</div></div>
      <div class="stat-card"><div class="stat-label">정산 수량</div><div class="stat-value">${revenueQuantity(auto.totals.quantity_total)}</div></div>
      <div class="stat-card"><div class="stat-label">정산 수가</div><div class="stat-value">${revenueMoney(auto.totals.price_total)}</div></div>
      <div class="stat-card"><div class="stat-label">차감 후</div><div class="stat-value">${revenueMoney(auto.totals.net_total)}</div></div>
    </div>
    <div class="stats-section">
      <h3 class="stats-section-title">정산 참고</h3>
      ${rows
        ? `<div style="overflow-x:auto;"><table class="data-table daily-report-auto-table"><thead><tr><th>치료항목</th><th>수량</th><th>정산 수가</th><th>인센티브</th><th>차감 후</th></tr></thead><tbody>${rows}</tbody></table></div>`
        : '<p class="muted" style="margin:0;">선택한 치료항목이 없습니다.</p>'}
    </div>`;
}

function dailyReportSelectionChanged(){
  document.querySelectorAll('.daily-report-treatment-chip').forEach(label => {
    const input = label.querySelector('.daily-report-treatment-check');
    label.classList.toggle('active', !!input?.checked);
  });
  renderDailyReportAuto();
}

function renderDailyReportField(field){
  const type = field.type || 'long_text';
  const id = field.id || ('field_' + Math.random().toString(16).slice(2));
  let control = '';
  if(type === 'short_text'){
    control = `<input class="daily-report-field-value" type="text" maxlength="200" value="${escapeAttr(field.value || '')}" placeholder="내용">`;
  } else if(type === 'number'){
    control = `<input class="daily-report-field-value" type="number" min="0" step="1" value="${escapeAttr(field.value ?? 0)}">`;
  } else if(type === 'checkbox'){
    control = `<label class="daily-report-check-row"><input class="daily-report-field-value" type="checkbox" ${field.value ? 'checked' : ''}> <span>체크됨</span></label>`;
  } else {
    control = `<textarea class="daily-report-field-value" maxlength="2000" rows="4" placeholder="내용">${escapeHtml(field.value || '')}</textarea>`;
  }
  return `<div class="daily-report-field" data-id="${escapeAttr(id)}" data-type="${escapeAttr(type)}">
    <div class="daily-report-field-head">
      <input class="daily-report-field-label" type="text" maxlength="50" value="${escapeAttr(field.label || '')}" placeholder="칸 제목">
      <span class="daily-report-field-type">${escapeHtml(field.type_label || type)}</span>
      <button class="small danger" onclick="removeDailyReportField(this)">삭제</button>
    </div>
    ${control}
  </div>`;
}

function renderDailyReport(data){
  DAILY_REPORT = data || {};
  const body = document.getElementById('daily-report-body');
  if(!body) return;
  body.innerHTML = `
    ${renderDailyReportJournal()}`;
}

async function loadDailyReport(){
  const dateEl = document.getElementById('daily-report-date');
  if(dateEl && !dateEl.value) dateEl.value = revenueDateStr(new Date());
  const reportDate = dateEl?.value || '';
  if(!reportDate) return;
  const loading = document.getElementById('daily-report-loading');
  const body = document.getElementById('daily-report-body');
  try {
    if(loading) loading.style.display = 'block';
    const r = await adminFetch(`/api/revenue/daily-report?date=${encodeURIComponent(reportDate)}&_=${Date.now()}`);
    const data = await r.json().catch(() => ({}));
    if(!r.ok) throw new Error(data.detail || r.statusText);
    renderDailyReport(data);
  } catch(e){
    if(body) body.innerHTML = `<p class="muted" style="color:#DC2626;padding:12px;">일일 업무 보고 조회 실패: ${escapeHtml(e && e.message ? e.message : e)}</p>`;
  } finally {
    if(loading) loading.style.display = 'none';
  }
}

function addDailyReportField(){
  showModal(`<h3>보고 칸 추가</h3>
    <label>칸 제목 <input id="daily-report-new-label" type="text" maxlength="50" placeholder="예: 특이사항"></label>
    <label>입력 타입
      <select id="daily-report-new-type">
        <option value="long_text">긴글</option>
        <option value="short_text">짧은글</option>
        <option value="number">숫자</option>
        <option value="checkbox">체크</option>
      </select>
    </label>
    <div class="modal-actions">
      <button onclick="closeModal()">취소</button>
      <button class="primary" onclick="confirmAddDailyReportField()">추가</button>
    </div>`);
}

function confirmAddDailyReportField(){
  const label = (document.getElementById('daily-report-new-label')?.value || '').trim();
  const type = document.getElementById('daily-report-new-type')?.value || 'long_text';
  if(!label){ alert('칸 제목을 입력하세요.'); return; }
  const box = document.getElementById('daily-report-fields');
  if(!box) return;
  const empty = box.querySelector('.daily-report-empty');
  if(empty) empty.remove();
  const typeLabel = {short_text:'짧은글', long_text:'긴글', number:'숫자', checkbox:'체크'}[type] || '긴글';
  const field = {id:'field_' + Date.now().toString(36), label, type, type_label:typeLabel, value: type === 'checkbox' ? false : (type === 'number' ? 0 : '')};
  box.insertAdjacentHTML('beforeend', renderDailyReportField(field));
  closeModal();
}

function removeDailyReportField(btn){
  const field = btn.closest('.daily-report-field');
  if(field) field.remove();
  const box = document.getElementById('daily-report-fields');
  if(box && !box.querySelector('.daily-report-field')){
    box.innerHTML = '<p class="muted daily-report-empty">추가된 보고 칸이 없습니다.</p>';
  }
}

async function saveDailyReport(){
  const reportDate = document.getElementById('daily-report-date')?.value || '';
  if(!reportDate){ alert('날짜를 선택하세요.'); return; }
  const customFields = dailyReportCurrentFields();
  const blank = customFields.find(f => !(f.label || '').trim());
  if(blank){ alert('보고 칸 제목을 입력하세요.'); return; }
  try {
    const r = await adminFetch('/api/revenue/daily-report', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        report_date: reportDate,
        selected_treatment_codes: dailyReportSelectedCodes(),
        custom_fields: customFields,
      }),
    });
    const data = await r.json().catch(() => ({}));
    if(!r.ok || data.ok === false) throw new Error(data.detail || data.error || r.statusText);
    renderDailyReport(data);
    alert('일일 업무 보고를 저장했습니다.');
  } catch(e){
    alert('일일 업무 보고 저장 실패: ' + (e && e.message ? e.message : e));
  }
}

function populateRevenueCategorySelect(id, categories, selectedId){
  const sel = document.getElementById(id);
  if(!sel) return;
  const prev = selectedId !== undefined ? selectedId : sel.value;
  const rows = categories || [];
  sel.innerHTML = '<option value="">전체</option>' + rows
    .map(c => `<option value="${c.id}">${escapeHtml(c.name || '')}</option>`)
    .join('');
  sel.value = rows.some(c => c.id === prev) ? prev : '';
}

function syncRevenueCategorySelects(categories, selectedId){
  populateRevenueCategorySelect('rev-stat-category', categories, selectedId);
}

const REVENUE_CASH_DENOMS = [50000, 10000, 5000, 1000, 500, 100, 10];
const REVENUE_PAYMENT_FIELDS = [
  {key:'total_medical_fee', label:'총진료비'},
  {key:'nhis_burden_total', label:'공단부담총액'},
  {key:'cash_amount', label:'현금수납액'},
  {key:'card_amount', label:'카드수납액'},
  {key:'receivable_income', label:'미수입금'},
  {key:'unpaid_amount', label:'미수발생'},
  {key:'health_living_fee', label:'건강생활유지비'},
  {key:'certificate_amount', label:'입,통원확인서'},
  {key:'disability_fund', label:'장애인기금'},
  {key:'uninsured_amount', label:'비급여'},
  {key:'meal_amount', label:'식대'},
  {key:'other_amount', label:'기타'},
  {key:'discount_amount', label:'할인'},
  {key:'free_amount', label:'FREE'},
  {key:'cash_expense_amount', label:'현금지출'},
  {key:'transfer_amount', label:'계좌입금'},
];
const REVENUE_TOTAL_FIELDS = [
  {key:'collected_amount', label:'수납액', formula:[
    {type:'field', key:'total_medical_fee', sign:1},
    {type:'field', key:'nhis_burden_total', sign:-1},
    {type:'field', key:'unpaid_amount', sign:-1},
    {type:'field', key:'health_living_fee', sign:-1},
    {type:'field', key:'disability_fund', sign:-1},
  ]},
  {key:'total_expense', label:'총지출', formula:[
    {type:'total', key:'collected_amount', sign:1},
    {type:'field', key:'card_amount', sign:-1},
    {type:'field', key:'discount_amount', sign:-1},
    {type:'field', key:'free_amount', sign:-1},
    {type:'field', key:'cash_expense_amount', sign:-1},
    {type:'field', key:'transfer_amount', sign:-1},
  ]},
  {key:'cash_total', label:'현금', formula:[
    {type:'total', key:'collected_amount', sign:1},
    {type:'total', key:'total_expense', sign:-1},
  ]},
];
const REVENUE_FIELD_LABEL_STORAGE_KEY = 'dosu.revenue.fieldLabels.v1';
const REVENUE_FIELD_ORDER_STORAGE_KEY = 'dosu.revenue.fieldOrder.v1';
const REVENUE_TOTAL_FORMULA_STORAGE_KEY = 'dosu.revenue.totalFormulas.v1';
const REVENUE_DAILY_FIELDS_STORAGE_KEY = 'dosu.revenue.dailyFields.v1';
const REVENUE_FIELD_DEFAULT_LABELS = Object.fromEntries(
  [...REVENUE_PAYMENT_FIELDS, ...REVENUE_TOTAL_FIELDS].map(f => [f.key, f.label])
);
let REVENUE_FIELD_LABELS = loadRevenueFieldLabels();
let REVENUE_FIELD_ORDER = loadRevenueFieldOrder();
let REVENUE_TOTAL_FORMULAS_CUSTOM = loadRevenueTotalFormulas();
let REVENUE_DRAG_FIELD = '';
let REVENUE_DAILY_FIELD_KEYS = loadRevenueDailyFieldKeys();
let REVENUE_UI_SETTINGS_LOADED = false;
let REVENUE_UI_SETTINGS_LOADING = null;
let REVENUE_UI_SETTINGS_SAVE_TIMER = null;

function revenueUiSettingsPayload(){
  return {
    field_labels: REVENUE_FIELD_LABELS,
    field_order: revenueNormalizeFieldOrder(REVENUE_FIELD_ORDER),
    total_formulas: REVENUE_TOTAL_FORMULAS_CUSTOM,
    daily_fields: revenueNormalizeDailyFieldKeys(REVENUE_DAILY_FIELD_KEYS, true),
  };
}

function saveRevenueUiSettingsLocal(){
  try {
    localStorage.setItem(REVENUE_FIELD_LABEL_STORAGE_KEY, JSON.stringify(REVENUE_FIELD_LABELS));
    localStorage.setItem(REVENUE_FIELD_ORDER_STORAGE_KEY, JSON.stringify(REVENUE_FIELD_ORDER));
    localStorage.setItem(REVENUE_TOTAL_FORMULA_STORAGE_KEY, JSON.stringify(REVENUE_TOTAL_FORMULAS_CUSTOM));
    localStorage.setItem(REVENUE_DAILY_FIELDS_STORAGE_KEY, JSON.stringify(REVENUE_DAILY_FIELD_KEYS));
  } catch(e){}
}

function applyRevenueUiSettings(settings){
  if(!settings || typeof settings !== 'object') return;
  if(settings.field_labels && typeof settings.field_labels === 'object'){
    REVENUE_FIELD_LABELS = {...REVENUE_FIELD_DEFAULT_LABELS};
    Object.entries(settings.field_labels).forEach(([key, label]) => {
      if(REVENUE_FIELD_DEFAULT_LABELS[key] && String(label || '').trim()){
        REVENUE_FIELD_LABELS[key] = String(label || '').trim().slice(0, 30);
      }
    });
  }
  if(Array.isArray(settings.field_order) && settings.field_order.length){
    REVENUE_FIELD_ORDER = revenueNormalizeFieldOrder(settings.field_order);
  }
  if(settings.total_formulas && typeof settings.total_formulas === 'object'){
    const next = {};
    Object.entries(settings.total_formulas).forEach(([key, terms]) => {
      if(REVENUE_TOTAL_FIELDS.some(field => field.key === key)){
        const normalized = revenueNormalizeFormulaTerms(key, terms);
        if(normalized.length) next[key] = normalized;
      }
    });
    REVENUE_TOTAL_FORMULAS_CUSTOM = next;
  }
  if(Array.isArray(settings.daily_fields) && settings.daily_fields.length){
    REVENUE_DAILY_FIELD_KEYS = revenueNormalizeDailyFieldKeys(settings.daily_fields, true);
  }
  saveRevenueUiSettingsLocal();
}

async function loadRevenueUiSettings(){
  if(REVENUE_UI_SETTINGS_LOADED) return;
  if(REVENUE_UI_SETTINGS_LOADING) return REVENUE_UI_SETTINGS_LOADING;
  REVENUE_UI_SETTINGS_LOADING = (async () => {
    try {
      const r = await adminFetch('/api/revenue/ui-settings?_=' + Date.now());
      const data = await r.json().catch(() => ({}));
      if(r.ok) applyRevenueUiSettings(data.settings || {});
    } catch(e){
      // 서버 설정을 못 읽으면 기존 PC별 localStorage fallback 을 그대로 사용한다.
    } finally {
      REVENUE_UI_SETTINGS_LOADED = true;
      REVENUE_UI_SETTINGS_LOADING = null;
    }
  })();
  return REVENUE_UI_SETTINGS_LOADING;
}

function persistRevenueUiSettings(){
  saveRevenueUiSettingsLocal();
  clearTimeout(REVENUE_UI_SETTINGS_SAVE_TIMER);
  REVENUE_UI_SETTINGS_SAVE_TIMER = setTimeout(async () => {
    try {
      await adminFetch('/api/revenue/ui-settings', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({settings: revenueUiSettingsPayload()}),
      });
    } catch(e){}
  }, 250);
}

function revenueMoney(v){
  const n = Math.round(Number(v || 0));
  return n.toLocaleString() + '원';
}

function loadRevenueFieldLabels(){
  let saved = {};
  try {
    saved = JSON.parse(localStorage.getItem(REVENUE_FIELD_LABEL_STORAGE_KEY) || '{}') || {};
  } catch(e){
    saved = {};
  }
  const out = {...REVENUE_FIELD_DEFAULT_LABELS};
  Object.keys(out).forEach(key => {
    const label = String(saved[key] || '').trim();
    if(label) out[key] = label.slice(0, 30);
  });
  return out;
}

function saveRevenueFieldLabels(){
  persistRevenueUiSettings();
}

function revenueFieldLabel(field){
  return REVENUE_FIELD_LABELS[field] || REVENUE_FIELD_DEFAULT_LABELS[field] || field;
}

function revenueNormalizeFieldLabel(label){
  return String(label || '').replace(/\s+/g, '').toLowerCase();
}

function revenueFieldKeyForCurrentLabel(label){
  const normalized = revenueNormalizeFieldLabel(label);
  if(!normalized) return '';
  const matches = Object.keys(REVENUE_FIELD_DEFAULT_LABELS)
    .filter(key => revenueNormalizeFieldLabel(revenueFieldLabel(key)) === normalized);
  return matches.length === 1 ? matches[0] : '';
}

function revenueSetFieldLabel(field, rawLabel){
  if(!REVENUE_FIELD_DEFAULT_LABELS[field]) return {ok:false, message:'헤더를 찾을 수 없습니다.'};
  const label = String(rawLabel || '').trim();
  if(!label){
    REVENUE_FIELD_LABELS[field] = REVENUE_FIELD_DEFAULT_LABELS[field];
    return {ok:true};
  }
  const duplicate = Object.keys(REVENUE_FIELD_DEFAULT_LABELS).find(key => (
    key !== field && revenueNormalizeFieldLabel(revenueFieldLabel(key)) === revenueNormalizeFieldLabel(label)
  ));
  if(duplicate){
    return {ok:false, message:`이미 사용 중인 헤더 이름입니다: ${revenueFieldLabel(duplicate)}`};
  }
  REVENUE_FIELD_LABELS[field] = label.slice(0, 30);
  return {ok:true};
}

function revenueRefreshAfterFormulaChange(){
  saveRevenueFieldLabels();
  refreshRevenueFieldLabels();
  recalcRevenueRecordTotals();
  if(REVENUE_RECORDS) renderRevenueRecords(REVENUE_RECORDS);
  if(REVENUE_STATS) renderRevenueStats(REVENUE_STATS);
  if(DAILY_REPORT) renderDailyReport(DAILY_REPORT);
}

function revenueCurrentFieldLabels(){
  return Object.fromEntries(Object.keys(REVENUE_FIELD_DEFAULT_LABELS).map(key => [key, revenueFieldLabel(key)]));
}

function revenueNormalizeFieldOrder(order){
  const allKeys = revenueAllRecordFields().map(field => field.key);
  const allowed = new Set(allKeys);
  const normalized = [];
  (Array.isArray(order) ? order : []).forEach(key => {
    key = String(key || '').trim();
    if(allowed.has(key) && !normalized.includes(key)) normalized.push(key);
  });
  allKeys.forEach(key => {
    if(!normalized.includes(key)) normalized.push(key);
  });
  return normalized;
}

function loadRevenueFieldOrder(){
  try {
    return revenueNormalizeFieldOrder(JSON.parse(localStorage.getItem(REVENUE_FIELD_ORDER_STORAGE_KEY) || '[]'));
  } catch(e){
    return revenueNormalizeFieldOrder([]);
  }
}

function saveRevenueFieldOrder(){
  persistRevenueUiSettings();
}

function revenueOrderedRecordFields(){
  const byKey = Object.fromEntries(revenueAllRecordFields().map(field => [field.key, field]));
  return revenueNormalizeFieldOrder(REVENUE_FIELD_ORDER).map(key => byKey[key]).filter(Boolean);
}

function revenueNormalizeDailyFieldKeys(keys, defaultAll=false){
  const allKeys = revenueAllRecordFields().map(field => field.key);
  const allowed = new Set(allKeys);
  const source = Array.isArray(keys) ? keys : [];
  const normalized = source
    .map(key => String(key || '').trim())
    .filter((key, idx, arr) => allowed.has(key) && arr.indexOf(key) === idx);
  return normalized.length || !defaultAll ? normalized : allKeys;
}

function loadRevenueDailyFieldKeys(){
  try {
    const raw = localStorage.getItem(REVENUE_DAILY_FIELDS_STORAGE_KEY);
    return raw
      ? revenueNormalizeDailyFieldKeys(JSON.parse(raw), true)
      : revenueNormalizeDailyFieldKeys([], true);
  } catch(e){
    return revenueNormalizeDailyFieldKeys([], true);
  }
}

function saveRevenueDailyFieldKeys(){
  persistRevenueUiSettings();
}

function revenueDailyFieldsForStats(){
  const selected = new Set(revenueNormalizeDailyFieldKeys(REVENUE_DAILY_FIELD_KEYS, true));
  const fields = revenueOrderedRecordFields().filter(field => selected.has(field.key));
  return fields.length ? fields : revenueOrderedRecordFields();
}

function openRevenueDailyFieldEditor(){
  const selected = new Set(revenueNormalizeDailyFieldKeys(REVENUE_DAILY_FIELD_KEYS, true));
  const rows = revenueOrderedRecordFields().map(field => `
    <label class="revenue-daily-field-option">
      <input class="revenue-daily-field-check" type="checkbox" value="${escapeAttr(field.key)}" ${selected.has(field.key) ? 'checked' : ''}>
      <span>${escapeHtml(revenueFieldLabel(field.key))}</span>
    </label>`).join('');
  showModal(`<div class="revenue-formula-modal revenue-daily-field-modal">
    <h3>일별 매출 항목</h3>
    <div class="revenue-daily-field-actions">
      <button type="button" class="small" onclick="setRevenueDailyFieldChecks(true)">전체 선택</button>
      <button type="button" class="small" onclick="setRevenueDailyFieldChecks(false)">전체 해제</button>
    </div>
    <div class="revenue-daily-field-list">${rows}</div>
    <p id="revenue-daily-field-error" class="revenue-formula-error"></p>
    <div class="modal-actions">
      <button onclick="closeModal()">취소</button>
      <button class="primary" onclick="saveRevenueDailyFieldEditor()">적용</button>
    </div>
  </div>`);
}

function setRevenueDailyFieldChecks(checked){
  document.querySelectorAll('.revenue-daily-field-check').forEach(input => {
    input.checked = !!checked;
  });
}

function saveRevenueDailyFieldEditor(){
  const keys = [...document.querySelectorAll('.revenue-daily-field-check:checked')]
    .map(input => input.value)
    .filter(Boolean);
  const normalized = revenueNormalizeDailyFieldKeys(keys);
  if(!normalized.length){
    const el = document.getElementById('revenue-daily-field-error');
    if(el) el.textContent = '하나 이상 선택하세요.';
    return;
  }
  REVENUE_DAILY_FIELD_KEYS = normalized;
  saveRevenueDailyFieldKeys();
  closeModal();
  if(REVENUE_STATS) renderRevenueStats(REVENUE_STATS);
}

function revenueFieldKind(fieldKey){
  return REVENUE_TOTAL_FIELDS.some(field => field.key === fieldKey) ? 'total' : 'payment';
}

function revenueDefaultTotalFormula(totalKey){
  const field = REVENUE_TOTAL_FIELDS.find(item => item.key === totalKey);
  return (field?.formula || []).map(term => ({
    type: term.type === 'total' ? 'total' : 'field',
    key: term.key,
    sign: Number(term.sign || 1) < 0 ? -1 : 1,
  }));
}

function revenueFormulaAllowedSourceKeys(totalKey){
  const totalIndex = REVENUE_TOTAL_FIELDS.findIndex(field => field.key === totalKey);
  return [
    ...REVENUE_PAYMENT_FIELDS.map(field => field.key),
    ...REVENUE_TOTAL_FIELDS
      .slice(0, Math.max(0, totalIndex))
      .map(field => field.key),
  ];
}

function revenueNormalizeFormulaTerms(totalKey, terms, fallbackToDefault=false){
  const allowed = new Set(revenueFormulaAllowedSourceKeys(totalKey));
  const source = Array.isArray(terms) ? terms : [];
  const normalized = source
    .map(term => {
      const key = revenueFieldKeyForCurrentLabel(term?.label) || String(term?.key || '').trim();
      if(!allowed.has(key)) return null;
      return {
        type: revenueFieldKind(key) === 'total' ? 'total' : 'field',
        key,
        sign: Number(term?.sign || 1) < 0 ? -1 : 1,
      };
    })
    .filter(Boolean);
  return normalized.length || !fallbackToDefault
    ? normalized
    : revenueDefaultTotalFormula(totalKey);
}

function loadRevenueTotalFormulas(){
  let saved = {};
  try {
    saved = JSON.parse(localStorage.getItem(REVENUE_TOTAL_FORMULA_STORAGE_KEY) || '{}') || {};
  } catch(e){
    saved = {};
  }
  const out = {};
  REVENUE_TOTAL_FIELDS.forEach(field => {
    if(Object.prototype.hasOwnProperty.call(saved, field.key)){
      out[field.key] = revenueNormalizeFormulaTerms(field.key, saved[field.key]);
    }
  });
  return out;
}

function saveRevenueTotalFormulas(){
  persistRevenueUiSettings();
}

function revenueFormulaForTotal(totalKey){
  if(Object.prototype.hasOwnProperty.call(REVENUE_TOTAL_FORMULAS_CUSTOM, totalKey)){
    return revenueNormalizeFormulaTerms(totalKey, REVENUE_TOTAL_FORMULAS_CUSTOM[totalKey]);
  }
  return revenueDefaultTotalFormula(totalKey);
}

function revenueRecordDate(){
  const el = document.getElementById('rev-record-date');
  if(el && !el.value) el.value = revenueDateStr(new Date());
  return el?.value || revenueDateStr(new Date());
}

function revenueAllRecordFields(){
  return [...REVENUE_PAYMENT_FIELDS, ...REVENUE_TOTAL_FIELDS];
}

function revenueRecordFieldMemos(rec){
  return (rec && typeof rec.field_memos === 'object' && rec.field_memos) ? rec.field_memos : {};
}

function renderRevenueEditableHeader(field){
  return `<div class="revenue-field-header">
    <span class="revenue-field-drag-handle" draggable="true" data-revenue-drag-field="${escapeAttr(field)}" ondragstart="startRevenueFieldDrag(event)" ondragend="endRevenueFieldDrag(event)" title="드래그로 순서 변경" aria-hidden="true">↕</span>
    <span data-revenue-header-label="${escapeAttr(field)}">${escapeHtml(revenueFieldLabel(field))}</span>
    <button type="button" class="revenue-header-edit-btn" onclick="editRevenueFieldLabel('${escapeAttr(field)}')" title="수정" aria-label="수정">✎</button>
  </div>`;
}

function refreshRevenueFieldLabels(){
  document.querySelectorAll('[data-revenue-header-label]').forEach(el => {
    const field = el.dataset.revenueHeaderLabel || '';
    el.textContent = revenueFieldLabel(field);
  });
}

function editRevenueFieldLabel(field){
  if(!REVENUE_FIELD_DEFAULT_LABELS[field]) return;
  if(revenueFieldKind(field) === 'total'){
    openRevenueFormulaEditor(field);
    return;
  }
  openRevenueHeaderEditor(field);
}

function revenueEditorError(message){
  const el = document.getElementById('revenue-formula-editor-error');
  if(el) el.textContent = message || '';
}

function openRevenueHeaderEditor(field){
  showModal(`<div class="revenue-formula-modal">
    <h3>항목 수정</h3>
    <label>이름
      <input id="revenue-field-label-input" type="text" maxlength="30" value="${escapeAttr(revenueFieldLabel(field))}">
    </label>
    <p id="revenue-formula-editor-error" class="revenue-formula-error"></p>
    <div class="modal-actions">
      <button onclick="closeModal()">취소</button>
      <button class="primary" onclick="saveRevenueHeaderEditor('${escapeAttr(field)}')">저장</button>
    </div>
  </div>`);
  setTimeout(() => document.getElementById('revenue-field-label-input')?.focus(), 0);
}

function saveRevenueHeaderEditor(field){
  const result = revenueSetFieldLabel(field, document.getElementById('revenue-field-label-input')?.value || '');
  if(!result.ok){
    revenueEditorError(result.message || '저장할 수 없습니다.');
    return;
  }
  closeModal();
  revenueRefreshAfterFormulaChange();
}

function revenueFormulaSourceOptionsHtml(totalKey, selectedKey){
  const allowed = revenueFormulaAllowedSourceKeys(totalKey);
  return allowed.map(key => {
    const kind = revenueFieldKind(key) === 'total' ? '계산' : '입력';
    return `<option value="${escapeAttr(key)}" ${key === selectedKey ? 'selected' : ''}>${escapeHtml(kind)} · ${escapeHtml(revenueFieldLabel(key))}</option>`;
  }).join('');
}

function revenueFormulaTermsHtml(totalKey, terms){
  const normalized = revenueNormalizeFormulaTerms(totalKey, terms);
  if(!normalized.length){
    return '<p class="muted revenue-formula-empty">공식 항목 없음</p>';
  }
  return normalized.map(term => `
    <div class="revenue-formula-term">
      <select class="revenue-formula-sign">
        <option value="1" ${term.sign > 0 ? 'selected' : ''}>더하기</option>
        <option value="-1" ${term.sign < 0 ? 'selected' : ''}>빼기</option>
      </select>
      <select class="revenue-formula-source">
        ${revenueFormulaSourceOptionsHtml(totalKey, term.key)}
      </select>
      <button type="button" class="mini danger" onclick="removeRevenueFormulaTerm(this)">삭제</button>
    </div>
  `).join('');
}

function openRevenueFormulaEditor(totalKey){
  const terms = revenueFormulaForTotal(totalKey);
  showModal(`<div class="revenue-formula-modal">
    <h3>${escapeHtml(revenueFieldLabel(totalKey))} 수정</h3>
    <label>이름
      <input id="revenue-field-label-input" type="text" maxlength="30" value="${escapeAttr(revenueFieldLabel(totalKey))}">
    </label>
    <div class="revenue-formula-head">
      <b>공식</b>
      <button type="button" class="small" onclick="addRevenueFormulaTerm('${escapeAttr(totalKey)}')">항목 추가</button>
    </div>
    <div id="revenue-formula-terms" class="revenue-formula-terms" data-total-field="${escapeAttr(totalKey)}">
      ${revenueFormulaTermsHtml(totalKey, terms)}
    </div>
    <p id="revenue-formula-editor-error" class="revenue-formula-error"></p>
    <div class="modal-actions">
      <button onclick="closeModal()">취소</button>
      <button onclick="resetRevenueFormulaEditor('${escapeAttr(totalKey)}')">기본값</button>
      <button class="primary" onclick="saveRevenueFormulaEditor('${escapeAttr(totalKey)}')">저장</button>
    </div>
  </div>`);
}

function addRevenueFormulaTerm(totalKey){
  const box = document.getElementById('revenue-formula-terms');
  if(!box) return;
  const firstKey = revenueFormulaAllowedSourceKeys(totalKey)[0] || '';
  if(!firstKey) return;
  const existing = [...box.querySelectorAll('.revenue-formula-term')].map(row => ({
    key: row.querySelector('.revenue-formula-source')?.value || '',
    sign: Number(row.querySelector('.revenue-formula-sign')?.value || 1),
  }));
  existing.push({key:firstKey, sign:1});
  box.innerHTML = revenueFormulaTermsHtml(totalKey, existing);
}

function removeRevenueFormulaTerm(btn){
  const row = btn.closest('.revenue-formula-term');
  const box = document.getElementById('revenue-formula-terms');
  if(row) row.remove();
  if(box && !box.querySelector('.revenue-formula-term')){
    box.innerHTML = '<p class="muted revenue-formula-empty">공식 항목 없음</p>';
  }
}

function resetRevenueFormulaEditor(totalKey){
  const box = document.getElementById('revenue-formula-terms');
  if(box) box.innerHTML = revenueFormulaTermsHtml(totalKey, revenueDefaultTotalFormula(totalKey));
}

function saveRevenueFormulaEditor(totalKey){
  const labelResult = revenueSetFieldLabel(totalKey, document.getElementById('revenue-field-label-input')?.value || '');
  if(!labelResult.ok){
    revenueEditorError(labelResult.message || '저장할 수 없습니다.');
    return;
  }
  const terms = [...document.querySelectorAll('#revenue-formula-terms .revenue-formula-term')].map(row => ({
    key: row.querySelector('.revenue-formula-source')?.value || '',
    sign: Number(row.querySelector('.revenue-formula-sign')?.value || 1),
  }));
  REVENUE_TOTAL_FORMULAS_CUSTOM[totalKey] = revenueNormalizeFormulaTerms(totalKey, terms);
  saveRevenueTotalFormulas();
  closeModal();
  revenueRefreshAfterFormulaChange();
}

function revenueRowAmounts(tr){
  const amounts = {};
  REVENUE_PAYMENT_FIELDS.forEach(field => { amounts[field.key] = 0; });
  if(tr){
    tr.querySelectorAll('.revenue-amount-input').forEach(inp => {
      amounts[inp.dataset.field] = revenueAmountValue(inp.value);
    });
  } else {
    REVENUE_PAYMENT_FIELDS.forEach(field => {
      amounts[field.key] = 0;
    });
  }
  return amounts;
}

function revenueCalculatedTotals(amounts){
  const totals = {};
  REVENUE_TOTAL_FIELDS.forEach(totalField => {
    totals[totalField.key] = revenueFormulaForTotal(totalField.key).reduce((sum, term) => {
      const source = term.type === 'total' ? totals : amounts;
      const currentLabelKey = revenueFieldKeyForCurrentLabel(revenueFieldLabel(term.key));
      const sourceKey = currentLabelKey || term.key;
      return sum + Number(source?.[sourceKey] ?? source?.[term.key] ?? 0) * Number(term.sign || 1);
    }, 0);
  });
  return totals;
}

function startRevenueFieldDrag(event){
  const field = event.currentTarget?.dataset?.revenueDragField || '';
  if(!field) return;
  REVENUE_DRAG_FIELD = field;
  event.dataTransfer.effectAllowed = 'move';
  event.dataTransfer.setData('text/plain', field);
  const row = event.currentTarget.closest('tr');
  if(row) row.classList.add('revenue-row-dragging');
}

function overRevenueFieldDrag(event){
  const target = event.currentTarget?.dataset?.revenueFieldRow || '';
  const source = REVENUE_DRAG_FIELD || event.dataTransfer.getData('text/plain');
  if(!source || !target || source === target) return;
  event.preventDefault();
  event.dataTransfer.dropEffect = 'move';
  const rect = event.currentTarget.getBoundingClientRect();
  const after = event.clientY > rect.top + rect.height / 2;
  event.currentTarget.classList.toggle('revenue-row-drop-before', !after);
  event.currentTarget.classList.toggle('revenue-row-drop-after', after);
}

function leaveRevenueFieldDrag(event){
  event.currentTarget.classList.remove('revenue-row-drop-before', 'revenue-row-drop-after');
}

function dropRevenueField(event){
  const target = event.currentTarget?.dataset?.revenueFieldRow || '';
  const source = REVENUE_DRAG_FIELD || event.dataTransfer.getData('text/plain');
  const insertAfter = event.currentTarget.classList.contains('revenue-row-drop-after');
  document.querySelectorAll('.revenue-row-drop-before, .revenue-row-drop-after').forEach(row => {
    row.classList.remove('revenue-row-drop-before', 'revenue-row-drop-after');
  });
  if(!source || !target || source === target) return;
  event.preventDefault();
  const order = revenueNormalizeFieldOrder(REVENUE_FIELD_ORDER);
  const from = order.indexOf(source);
  let to = order.indexOf(target);
  if(from < 0 || to < 0 || from === to) return;
  order.splice(from, 1);
  to = order.indexOf(target);
  if(insertAfter) to += 1;
  order.splice(to, 0, source);
  REVENUE_FIELD_ORDER = revenueNormalizeFieldOrder(order);
  saveRevenueFieldOrder();
  if(REVENUE_RECORDS) renderRevenueRecords(REVENUE_RECORDS);
  if(REVENUE_STATS) renderRevenueStats(REVENUE_STATS);
}

function endRevenueFieldDrag(){
  REVENUE_DRAG_FIELD = '';
  document.querySelectorAll('.revenue-row-dragging, .revenue-row-drop-before, .revenue-row-drop-after').forEach(row => {
    row.classList.remove('revenue-row-dragging', 'revenue-row-drop-before', 'revenue-row-drop-after');
  });
}

function revenueVisibleDates(){
  return [...document.querySelectorAll('[data-revenue-date-col]')]
    .map(el => el.dataset.revenueDateCol || '')
    .filter(Boolean);
}

function revenueAmountsForDate(dateStr){
  const amounts = {};
  REVENUE_PAYMENT_FIELDS.forEach(field => { amounts[field.key] = 0; });
  document.querySelectorAll('.revenue-amount-input').forEach(inp => {
    if(inp.dataset.date === dateStr){
      amounts[inp.dataset.field] = revenueAmountValue(inp.value);
    }
  });
  return amounts;
}

function revenueAmountValue(v){
  const raw = String(v || '').trim();
  const negative = raw.startsWith('-') || raw.startsWith('−');
  const cleaned = raw.replace(/[^\d]/g, '');
  const n = parseInt(cleaned || '0', 10) || 0;
  return negative ? -n : n;
}

function revenueAmountDisplay(v){
  const n = revenueAmountValue(v);
  if(!n) return '';
  return n < 0 ? '-' + Math.abs(n).toLocaleString() : n.toLocaleString();
}

function revenueQuantity(v){
  const n = Math.max(0, parseInt(v || '0') || 0);
  return n.toLocaleString();
}

function revenueCashCounts(rec){
  const raw = rec?.cash_counts || {};
  const counts = {};
  REVENUE_CASH_DENOMS.forEach(denom => {
    counts[String(denom)] = Math.max(0, parseInt(raw[String(denom)] || raw[denom] || 0, 10) || 0);
  });
  return counts;
}

function revenueCashCountsFromRow(tr){
  const counts = {};
  REVENUE_CASH_DENOMS.forEach(denom => {
    const input = tr.querySelector(`.revenue-cash-count-input[data-denom="${denom}"]`);
    counts[String(denom)] = Math.max(0, parseInt(input?.value || '0', 10) || 0);
  });
  return counts;
}

function revenueCashCountsFromDataset(el){
  let raw = {};
  try {
    raw = JSON.parse(el?.dataset?.cashCounts || '{}');
  } catch(e){
    raw = {};
  }
  return revenueCashCounts({cash_counts: raw});
}

function revenueCashCountsTotal(counts){
  return REVENUE_CASH_DENOMS.reduce((sum, denom) => {
    return sum + denom * (Math.max(0, parseInt(counts[String(denom)] || 0, 10) || 0));
  }, 0);
}

function revenueCashCountsHasValue(counts){
  return Object.values(counts || {}).some(v => (parseInt(v || 0, 10) || 0) > 0);
}

function renderRevenueCashLedger(rec){
  const counts = revenueCashCounts(rec);
  const hasCounts = revenueCashCountsHasValue(counts);
  const total = revenueCashCountsTotal(counts);
  const rows = REVENUE_CASH_DENOMS.map(denom => {
    const count = counts[String(denom)] || 0;
    return `<label class="cash-ledger-item">
      <span>${denom.toLocaleString()}원</span>
      <input class="revenue-cash-count-input" type="number" min="0" step="1"
             data-denom="${denom}" value="${count || ''}" inputmode="numeric"
             oninput="updateRevenueCashLedger(this)">
      <b data-cash-subtotal="${denom}">${revenueMoney(denom * count)}</b>
    </label>`;
  }).join('');
  return `<details class="cash-ledger" ${hasCounts ? 'open' : ''}>
    <summary>현금 기입장</summary>
    <div class="cash-ledger-grid">${rows}</div>
    <div class="cash-ledger-total"><span>총합</span><b data-cash-ledger-total>${revenueMoney(total)}</b></div>
  </details>`;
}

function updateRevenueCashLedger(input){
  const tr = input.closest('.revenue-record-row');
  if(!tr) return;
  const counts = revenueCashCountsFromRow(tr);
  REVENUE_CASH_DENOMS.forEach(denom => {
    const sub = tr.querySelector(`[data-cash-subtotal="${denom}"]`);
    if(sub) sub.textContent = revenueMoney(denom * (counts[String(denom)] || 0));
  });
  const total = revenueCashCountsTotal(counts);
  const totalEl = tr.querySelector('[data-cash-ledger-total]');
  if(totalEl) totalEl.textContent = revenueMoney(total);
  const cashInput = tr.querySelector('.revenue-amount-input[data-field="cash_amount"]');
  if(cashInput){
    cashInput.value = revenueAmountDisplay(total);
    cashInput.dataset.cashLedger = revenueCashCountsHasValue(counts) ? '1' : '';
  }
  recalcRevenueRecordTotals();
}

function normalizeRevenueCashAmount(input){
  input.dataset.cashLedger = '';
  normalizeRevenueAmount(input);
  const tr = input.closest('.revenue-record-row');
  if(!tr) return;
  tr.querySelectorAll('.revenue-cash-count-input').forEach(el => { el.value = ''; });
  tr.querySelectorAll('[data-cash-subtotal]').forEach(el => { el.textContent = revenueMoney(0); });
  const totalEl = tr.querySelector('[data-cash-ledger-total]');
  if(totalEl) totalEl.textContent = revenueMoney(0);
}

function dailyCashLedgerDate(){
  const el = document.getElementById('daily-cash-ledger-date');
  if(el && !el.value) el.value = revenueDateStr(new Date());
  return el?.value || revenueDateStr(new Date());
}

function dailyCashLedgerRecord(){
  const dateStr = dailyCashLedgerDate();
  return (DAILY_CASH_LEDGER?.records || [])[0] || {
    record_date: dateStr,
    total_medical_fee: 0,
    nhis_burden_total: 0,
    cash_amount: 0,
    cash_counts: {},
    card_amount: 0,
    receivable_income: 0,
    transfer_amount: 0,
    unpaid_amount: 0,
    health_living_fee: 0,
    certificate_amount: 0,
    disability_fund: 0,
    uninsured_amount: 0,
    meal_amount: 0,
    other_amount: 0,
    discount_amount: 0,
    free_amount: 0,
    cash_expense_amount: 0,
    field_memos: {},
    memo: '',
  };
}

function revenueAppliedAmount(field, value){
  return revenueAmountValue(value);
}

function revenueUnpaidApplied(rec){
  if(rec && rec.unpaid_applied_amount !== undefined && rec.unpaid_applied_amount !== null){
    return Number(rec.unpaid_applied_amount || 0);
  }
  return Number(rec?.unpaid_amount || 0);
}

function dailyCashLedgerCounts(){
  const counts = {};
  REVENUE_CASH_DENOMS.forEach(denom => {
    const input = document.querySelector(`.daily-cash-count-input[data-denom="${denom}"]`);
    counts[String(denom)] = Math.max(0, parseInt(input?.value || '0', 10) || 0);
  });
  return counts;
}

function updateDailyCashLedger(input){
  if(input){
    const n = Math.max(0, parseInt(input.value || '0', 10) || 0);
    input.value = n ? String(n) : '';
  }
  const counts = dailyCashLedgerCounts();
  REVENUE_CASH_DENOMS.forEach(denom => {
    const sub = document.querySelector(`[data-daily-cash-subtotal="${denom}"]`);
    if(sub) sub.textContent = revenueMoney(denom * (counts[String(denom)] || 0));
  });
  const totalEl = document.querySelector('[data-daily-cash-total]');
  if(totalEl) totalEl.textContent = revenueMoney(revenueCashCountsTotal(counts));
}

async function loadDailyCashLedger(){
  const dateStr = dailyCashLedgerDate();
  if(!dateStr) return;
  const loading = document.getElementById('daily-cash-ledger-loading');
  const body = document.getElementById('daily-cash-ledger-body');
  try {
    if(loading) loading.style.display = 'block';
    const params = new URLSearchParams({date_from: dateStr, date_to: dateStr});
    const r = await adminFetch(`/api/revenue/records?${params.toString()}`);
    const data = await r.json().catch(() => ({}));
    if(!r.ok) throw new Error(data.detail || r.statusText);
    DAILY_CASH_LEDGER = data;
    renderDailyCashLedger(data);
  } catch(e){
    if(body) body.innerHTML = `<p class="muted" style="color:#DC2626;padding:12px;">현금기입장 조회 실패: ${escapeHtml(e && e.message ? e.message : e)}</p>`;
  } finally {
    if(loading) loading.style.display = 'none';
  }
}

function renderDailyCashLedger(data){
  const body = document.getElementById('daily-cash-ledger-body');
  if(!body) return;
  const dateStr = data?.date_from || dailyCashLedgerDate();
  const rec = (data?.records || [])[0] || {record_date: dateStr, cash_counts: {}};
  const counts = revenueCashCounts(rec);
  const rows = REVENUE_CASH_DENOMS.map(denom => {
    const count = counts[String(denom)] || 0;
    return `<tr>
      <td>${denom.toLocaleString()}원</td>
      <td><input class="daily-cash-count-input" type="number" min="0" step="1" inputmode="numeric" data-denom="${denom}" value="${count || ''}" oninput="updateDailyCashLedger(this)"></td>
      <td data-daily-cash-subtotal="${denom}">${revenueMoney(denom * count)}</td>
    </tr>`;
  }).join('');
  body.innerHTML = `<div class="daily-cash-ledger-wrap">
    <table class="data-table daily-cash-ledger-table">
      <thead><tr><th>단위</th><th>수량</th><th>금액</th></tr></thead>
      <tbody>${rows}</tbody>
      <tfoot><tr><td colspan="2">${escapeHtml(revenueDateLabel(rec.record_date || dateStr))} 총합</td><td data-daily-cash-total>${revenueMoney(revenueCashCountsTotal(counts))}</td></tr></tfoot>
    </table>
  </div>`;
}

async function saveDailyCashLedger(){
  const dateStr = dailyCashLedgerDate();
  if(!dateStr) return;
  if(!document.querySelector('.daily-cash-count-input')){
    await loadDailyCashLedger();
  }
  const counts = dailyCashLedgerCounts();
  const rec = dailyCashLedgerRecord();
  const entry = {
    record_date: dateStr,
    category_id: '',
    total_medical_fee: revenueAmountValue(rec.total_medical_fee),
    nhis_burden_total: revenueAmountValue(rec.nhis_burden_total),
    cash_amount: revenueCashCountsTotal(counts),
    cash_counts: counts,
    card_amount: revenueAmountValue(rec.card_amount),
    receivable_income: revenueAmountValue(rec.receivable_income),
    transfer_amount: revenueAmountValue(rec.transfer_amount),
    unpaid_amount: revenueAmountValue(rec.unpaid_amount),
    health_living_fee: revenueAmountValue(rec.health_living_fee),
    certificate_amount: revenueAmountValue(rec.certificate_amount),
    disability_fund: revenueAmountValue(rec.disability_fund),
    uninsured_amount: revenueAmountValue(rec.uninsured_amount),
    meal_amount: revenueAmountValue(rec.meal_amount),
    other_amount: revenueAmountValue(rec.other_amount),
    discount_amount: revenueAmountValue(rec.discount_amount),
    free_amount: revenueAmountValue(rec.free_amount),
    cash_expense_amount: revenueAmountValue(rec.cash_expense_amount),
    field_memos: rec.field_memos || {},
    memo: rec.memo || '',
  };
  try {
    const r = await adminFetch('/api/revenue/records/grid', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({date_from: dateStr, date_to: dateStr, category_id: '', entries:[entry]}),
    });
    const data = await r.json().catch(() => ({}));
    if(!r.ok || data.ok === false) throw new Error(data.detail || data.error || r.statusText);
    DAILY_CASH_LEDGER = data;
    renderDailyCashLedger(data);
  } catch(e){
    alert('현금기입장 저장 실패: ' + (e && e.message ? e.message : e));
  }
}

function revenueDateLabel(dateStr){
  const parts = String(dateStr || '').split('-').map(x => parseInt(x, 10));
  if(parts.length !== 3 || parts.some(Number.isNaN)) return dateStr || '-';
  const d = new Date(parts[0], parts[1]-1, parts[2]);
  return `${parts[1]}/${parts[2]} (${['일','월','화','수','목','금','토'][d.getDay()]})`;
}

function normalizeRevenueAmount(input){
  if(String(input.value || '').trim() === '-' || String(input.value || '').trim() === '−'){
    recalcRevenueRecordTotals();
    return;
  }
  input.value = revenueAmountDisplay(input.value);
  recalcRevenueRecordTotals();
}

function recalcRevenueRecordTotals(){
  revenueVisibleDates().forEach(dateStr => {
    const amounts = revenueAmountsForDate(dateStr);
    const totals = revenueCalculatedTotals(amounts);
    REVENUE_TOTAL_FIELDS.forEach(field => {
      const cell = document.querySelector(
        `[data-revenue-date-total="${dateStr}"][data-revenue-total-field="${field.key}"]`
      );
      if(cell) cell.textContent = revenueMoney(totals[field.key]);
    });
  });
}

async function loadRevenueRecords(){
  const dateStr = revenueRecordDate();
  const categoryId = '';
  if(!dateStr) return;
  const loading = document.getElementById('revenue-record-loading');
  const body = document.getElementById('revenue-record-body');
  try {
    if(loading) loading.style.display = 'block';
    const params = new URLSearchParams({date_from: dateStr, date_to: dateStr});
    if(categoryId) params.set('category_id', categoryId);
    const r = await adminFetch(`/api/revenue/records?${params.toString()}`);
    const data = await r.json().catch(() => ({}));
    if(!r.ok) throw new Error(data.detail || r.statusText);
    REVENUE_RECORDS = data;
    syncRevenueCategorySelects(data.categories || [], data.category_id || '');
    renderRevenueRecords(data);
  } catch(e){
    if(body) body.innerHTML = `<p class="muted" style="color:#DC2626;padding:12px;">매출 기록 조회 실패: ${escapeHtml(e && e.message ? e.message : e)}</p>`;
  } finally {
    if(loading) loading.style.display = 'none';
  }
}

function triggerRevenueRecordImport(){
  document.getElementById('revenue-record-import-file')?.click();
}

async function importRevenueRecordsExcel(input){
  const file = input?.files?.[0];
  if(!file) return;
  const form = new FormData();
  form.append('file', file);
  form.append('labels_json', JSON.stringify(revenueCurrentFieldLabels()));
  const loading = document.getElementById('revenue-record-loading');
  const body = document.getElementById('revenue-record-body');
  try {
    if(loading) loading.style.display = 'block';
    const r = await adminFetch('/api/revenue/records/import-preview', {
      method: 'POST',
      body: form,
    });
    const data = await r.json().catch(() => ({}));
    if(!r.ok || data.ok === false) throw new Error(data.detail || data.error || r.statusText);
    const records = data.records || [];
    const currentDate = revenueRecordDate();
    const selected = records.find(rec => rec.record_date === currentDate) || records[0];
    if(!selected) throw new Error('가져올 매출 기록 데이터가 없습니다.');
    if((data.existing_dates || []).includes(selected.record_date)){
      const replaceOk = confirm(`${revenueDateLabel(selected.record_date)}에는 이미 저장된 매출 기록이 있습니다.\n엑셀 데이터로 교체할까요?\n\n불러온 뒤 저장 버튼을 누르면 기존 금액·권종별 현금·항목별 메모가 엑셀 내용으로 바뀝니다.`);
      if(!replaceOk) return;
    }
    const viewData = {
      ...data,
      date_from: selected.record_date,
      date_to: selected.record_date,
      records: [selected],
    };
    revenueSetRange('rev-record', selected.record_date, selected.record_date);
    REVENUE_RECORDS = viewData;
    syncRevenueCategorySelects(viewData.categories || [], viewData.category_id || '');
    renderRevenueRecords(viewData);
    const imported = Number(data.imported || records.length || 0);
    const skipped = Number(data.skipped || 0);
    const extra = imported > 1
      ? `\n엑셀에는 ${imported.toLocaleString()}일치가 있어 ${revenueDateLabel(selected.record_date)} 데이터만 입력칸에 불러왔습니다.`
      : '';
    alert(`엑셀 데이터 ${revenueDateLabel(selected.record_date)} 자료를 입력칸에 불러왔습니다.\n확인 후 저장 버튼을 눌러 반영하세요.${extra}${skipped ? `\n건너뛴 행 ${skipped.toLocaleString()}개` : ''}`);
  } catch(e){
    if(body) body.innerHTML = `<p class="muted" style="color:#DC2626;padding:12px;">엑셀 불러오기 실패: ${escapeHtml(e && e.message ? e.message : e)}</p>`;
    alert('엑셀 불러오기 실패: ' + (e && e.message ? e.message : e));
  } finally {
    if(loading) loading.style.display = 'none';
    if(input) input.value = '';
  }
}

function renderRevenueRecords(data){
  const body = document.getElementById('revenue-record-body');
  if(!body) return;
  const requestedDate = data?.date_from || revenueRecordDate();
  const rec = (data?.records || []).find(row => row.record_date === requestedDate)
    || (data?.records || [])[0]
    || {record_date: requestedDate, field_memos: {}};
  const recordDate = rec.record_date || requestedDate;
  const dateEl = document.getElementById('rev-record-date');
  if(dateEl) dateEl.value = recordDate;
  const fieldMemos = revenueRecordFieldMemos(rec);
  const totals = revenueCalculatedTotals(rec);
  const legacyNotice = rec.legacy_format
    ? '<div class="revenue-legacy-notice">⚠ 이 날짜는 총진료비·공단부담총액이 입력되지 않은 기록입니다. 수납액·총지출·현금 계산이 정확하지 않으니, 업데이트 이전에 저장된 날짜라면 일계표를 보고 다시 입력해 주세요.</div>'
    : '';
  const rows = revenueOrderedRecordFields().map(field => {
    const fieldKind = revenueFieldKind(field.key);
    const rowHandlers = `ondragover="overRevenueFieldDrag(event)" ondragleave="leaveRevenueFieldDrag(event)" ondrop="dropRevenueField(event)"`;
    if(fieldKind === 'total'){
      return `
        <tr class="revenue-total-row" data-revenue-field-row="${escapeAttr(field.key)}" ${rowHandlers}>
          <th class="revenue-field-cell revenue-total-head">${renderRevenueEditableHeader(field.key)}</th>
          <td class="revenue-total-cell" data-revenue-date-total="${escapeAttr(recordDate)}" data-revenue-total-field="${escapeAttr(field.key)}">${revenueMoney(totals[field.key])}</td>
          <td><input class="revenue-field-memo-input" data-date="${escapeAttr(recordDate)}" data-field="${escapeAttr(field.key)}" maxlength="300" value="${escapeAttr(fieldMemos[field.key] || '')}" placeholder="메모"></td>
        </tr>`;
    }
    return `
      <tr class="revenue-field-row" data-revenue-field-row="${escapeAttr(field.key)}" ${rowHandlers}>
        <th class="revenue-field-cell">${renderRevenueEditableHeader(field.key)}</th>
        <td><input class="revenue-amount-input" data-date="${escapeAttr(recordDate)}" data-field="${escapeAttr(field.key)}" inputmode="decimal" value="${escapeAttr(revenueAmountDisplay(rec[field.key]))}" oninput="normalizeRevenueAmount(this)"></td>
        <td><input class="revenue-field-memo-input" data-date="${escapeAttr(recordDate)}" data-field="${escapeAttr(field.key)}" maxlength="300" value="${escapeAttr(fieldMemos[field.key] || '')}" placeholder="메모"></td>
      </tr>`;
  }).join('');
  body.innerHTML = `${legacyNotice}<div style="overflow-x:auto;">
        <table class="data-table revenue-record-table revenue-record-table-transposed">
          <colgroup>
            <col class="revenue-col-item">
            <col class="revenue-col-amount">
            <col class="revenue-col-memo">
          </colgroup>
          <thead><tr><th class="revenue-field-axis">항목</th><th class="revenue-date-head" data-revenue-date-col="${escapeAttr(recordDate)}">${escapeHtml(revenueDateLabel(recordDate))}</th><th class="revenue-memo-head">메모</th></tr></thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      </div>`;
  refreshRevenueFieldLabels();
  recalcRevenueRecordTotals();
}

async function saveRevenueRecords(){
  const dateStr = revenueRecordDate();
  if(!dateStr){ alert('날짜를 선택하세요.'); return; }
  if(!REVENUE_RECORDS){ await loadRevenueRecords(); if(!REVENUE_RECORDS) return; }
  const categoryId = '';
  const previousRecords = Object.fromEntries((REVENUE_RECORDS?.records || []).map(rec => [rec.record_date, rec]));
  const entry = {
    record_date: dateStr,
    category_id: categoryId,
    memo: previousRecords[dateStr]?.memo || '',
    field_memos: {},
  };
  REVENUE_PAYMENT_FIELDS.forEach(field => { entry[field.key] = 0; });
  document.querySelectorAll('.revenue-amount-input').forEach(inp => {
    if(inp.dataset.date === dateStr){
      entry[inp.dataset.field] = revenueAmountValue(inp.value);
    }
  });
  const memoKeys = new Set(revenueAllRecordFields().map(field => field.key));
  document.querySelectorAll('.revenue-field-memo-input').forEach(inp => {
    if(inp.dataset.date !== dateStr) return;
    const key = inp.dataset.field || '';
    if(!memoKeys.has(key)) return;
    const text = String(inp.value || '').trim();
    if(text) entry.field_memos[key] = text;
  });
  const storedCashCounts = revenueCashCounts(previousRecords[dateStr]);
  if(revenueCashCountsHasValue(storedCashCounts) && entry.cash_amount === revenueCashCountsTotal(storedCashCounts)){
    entry.cash_counts = storedCashCounts;
  }
  try {
    const r = await adminFetch('/api/revenue/records/grid', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({date_from: dateStr, date_to: dateStr, category_id: categoryId, entries:[entry]}),
    });
    const data = await r.json().catch(() => ({}));
    if(!r.ok || data.ok === false) throw new Error(data.detail || data.error || r.statusText);
    REVENUE_RECORDS = data;
    renderRevenueRecords(data);
    await loadRevenueStats();
  } catch(e){
    alert('매출 기록 저장 실패: ' + (e && e.message ? e.message : e));
  }
}

async function loadRevenueStats(){
  const fromStr = document.getElementById('rev-stat-from')?.value || '';
  const toStr = document.getElementById('rev-stat-to')?.value || '';
  const categoryId = document.getElementById('rev-stat-category')?.value || '';
  if(!fromStr || !toStr) return;
  if(fromStr > toStr){ alert('시작일이 종료일보다 늦을 수 없습니다.'); return; }
  const loading = document.getElementById('revenue-stat-loading');
  const body = document.getElementById('revenue-stat-body');
  try {
    if(loading) loading.style.display = 'block';
    const params = new URLSearchParams({date_from: fromStr, date_to: toStr});
    if(categoryId) params.set('category_id', categoryId);
    const r = await adminFetch(`/api/revenue/stats?${params.toString()}`);
    const data = await r.json().catch(() => ({}));
    if(!r.ok) throw new Error(data.detail || r.statusText);
    REVENUE_STATS = data;
    syncRevenueCategorySelects(data.categories || [], data.category_id || '');
    renderRevenueStats(data);
  } catch(e){
    if(body) body.innerHTML = `<p class="muted" style="color:#DC2626;padding:12px;">매출 통계 조회 실패: ${escapeHtml(e && e.message ? e.message : e)}</p>`;
  } finally {
    if(loading) loading.style.display = 'none';
  }
}

function revenueDeltaText(delta){
  if(!delta || delta.pct === null || delta.pct === undefined) return '직전 기간 없음';
  const sign = delta.amount > 0 ? '+' : '';
  return `${sign}${revenueMoney(delta.amount)} (${sign}${delta.pct}%)`;
}

function revenueDeltaFromAmounts(current, previous){
  const amount = Number(current || 0) - Number(previous || 0);
  const pct = Number(previous || 0) === 0 ? null : Math.round((amount / Number(previous || 0)) * 1000) / 10;
  return {amount, pct};
}

function revenueSummaryWithCurrentFormulas(summary){
  const base = summary || {};
  const daily = (base.daily || []).map(row => {
    const amounts = {};
    REVENUE_PAYMENT_FIELDS.forEach(field => {
      amounts[field.key] = Number(row[field.key] || 0);
    });
    const totals = revenueCalculatedTotals(amounts);
    return {
      ...row,
      ...totals,
      total_amount: totals.collected_amount || 0,
    };
  });
  const out = {...base, daily};
  REVENUE_TOTAL_FIELDS.forEach(field => {
    out[field.key] = daily.reduce((sum, row) => sum + Number(row[field.key] || 0), 0);
  });
  out.revenue_total = out.collected_amount || 0;
  return out;
}

function revenuePieChart(items, title){
  const filtered = (items || []).filter(x => Number(x.amount || 0) > 0);
  const total = filtered.reduce((s,x) => s + Number(x.amount || 0), 0);
  const colors = ['#2F86CB','#3BA67D','#F59E0B','#7957AC','#9CA3AF'];
  if(total <= 0){
    return `<div class="revenue-pie-card"><h3>${escapeHtml(title)}</h3><div class="revenue-empty-pie">데이터 없음</div></div>`;
  }
  let acc = 0;
  const stops = filtered.map((x, idx) => {
    const start = acc;
    acc += (Number(x.amount || 0) / total) * 100;
    return `${colors[idx % colors.length]} ${start.toFixed(2)}% ${acc.toFixed(2)}%`;
  }).join(', ');
  const legend = filtered.map((x, idx) => {
    const pct = Math.round((Number(x.amount || 0) / total) * 100);
    return `<div class="revenue-legend-row"><span class="revenue-legend-color" style="background:${colors[idx % colors.length]}"></span><span>${escapeHtml(x.label || '-')}</span><b>${revenueMoney(x.amount)} · ${pct}%</b></div>`;
  }).join('');
  return `<div class="revenue-pie-card">
    <h3>${escapeHtml(title)}</h3>
    <div class="revenue-pie-layout">
      <div class="revenue-pie" style="background:conic-gradient(${stops});"><span>${revenueMoney(total)}</span></div>
      <div class="revenue-legend">${legend}</div>
    </div>
  </div>`;
}

function renderRevenueStats(data){
  const body = document.getElementById('revenue-stat-body');
  if(!body) return;
  const cur = revenueSummaryWithCurrentFormulas(data.current || {});
  const prev = revenueSummaryWithCurrentFormulas(data.previous || {});
  const settlement = {...(data.settlement || {})};
  settlement.revenue_minus_settlement_price = Number(cur.revenue_total || 0) - Number(settlement.price_total || 0);
  settlement.revenue_after_incentive = Number(cur.revenue_total || 0) - Number(settlement.incentive_total || 0);
  settlement.incentive_rate = Number(cur.revenue_total || 0)
    ? Math.round((Number(settlement.incentive_total || 0) / Number(cur.revenue_total || 0)) * 1000) / 10
    : 0;
  settlement.settlement_price_rate = Number(cur.revenue_total || 0)
    ? Math.round((Number(settlement.price_total || 0) / Number(cur.revenue_total || 0)) * 1000) / 10
    : 0;
  const settlementPriceTotal = Math.max(0, Number(settlement.price_total || 0));
  const settlementQuantityTotal = Math.max(0, Number(settlement.quantity_total || 0));
  const settlementAveragePrice = settlementQuantityTotal
    ? Math.round(settlementPriceTotal / settlementQuantityTotal)
    : 0;
  const settlementPie = (settlement.by_treatment || []).map(row => ({
    label: row.treatment_short || row.treatment_name || '-',
    amount: row.price_total || 0,
  }));
  const medicalRatioPie = [
    {
      key: 'nhis_burden_total',
      label: revenueFieldLabel('nhis_burden_total'),
      amount: Number(cur.nhis_burden_total || 0),
    },
    {
      key: 'cash_card_amount',
      label: `${revenueFieldLabel('cash_amount')}+${revenueFieldLabel('card_amount')}`,
      amount: Number(cur.cash_amount || 0) + Number(cur.card_amount || 0),
    },
    {
      key: 'uninsured_amount',
      label: revenueFieldLabel('uninsured_amount'),
      amount: Number(cur.uninsured_amount || 0),
    },
  ];
  const dailyFields = revenueDailyFieldsForStats();
  const dailyRows = (cur.daily || []).map(row => `
    <tr>
      <td>${escapeHtml(revenueDateLabel(row.date))}</td>
      ${dailyFields.map(field => `<td>${revenueMoney(row[field.key])}</td>`).join('')}
    </tr>`).join('');
  const dailyHeaders = [
    '<th>날짜</th>',
    ...dailyFields.map(field => `<th>${escapeHtml(revenueFieldLabel(field.key))}</th>`),
  ].join('');
  const legacyCount = Number((data.current || {}).legacy_count || 0);
  const legacyNotice = legacyCount
    ? `<div class="revenue-legacy-notice">⚠ 기간 내 ${legacyCount}일은 총진료비가 없는 이전 형식의 기록이라 수납액·총지출·현금 합계가 정확하지 않습니다. 매출 기록 탭에서 해당 날짜를 다시 입력해 주세요.</div>`
    : '';
  body.innerHTML = `
    ${legacyNotice}
    <div class="stats-summary-grid">
      <div class="stat-card"><div class="stat-label">${escapeHtml(revenueFieldLabel('collected_amount'))}</div><div class="stat-value">${revenueMoney(cur.collected_amount)}</div></div>
      <div class="stat-card"><div class="stat-label">${escapeHtml(revenueFieldLabel('total_expense'))}</div><div class="stat-value">${revenueMoney(cur.total_expense)}</div></div>
      <div class="stat-card"><div class="stat-label">${escapeHtml(revenueFieldLabel('cash_total'))}</div><div class="stat-value">${revenueMoney(cur.cash_total)}</div></div>
      <div class="stat-card"><div class="stat-label">직전 동일기간</div><div class="stat-value">${revenueMoney(prev.revenue_total)}</div></div>
      <div class="stat-card"><div class="stat-label">증감</div><div class="stat-value">${escapeHtml(revenueDeltaText(revenueDeltaFromAmounts(cur.revenue_total, prev.revenue_total)))}</div></div>
      <div class="stat-card"><div class="stat-label">기록일수</div><div class="stat-value">${revenueQuantity(cur.record_count)}</div></div>
    </div>
    <div class="revenue-chart-grid">
      ${revenuePieChart(medicalRatioPie, '진료비 비율')}
      ${revenuePieChart(settlementPie, '치료항목별 정산')}
    </div>
    <div class="settlement-note revenue-settlement-help">
      <b>정산 참고</b>
      <span>정산 수가 ${revenueMoney(settlement.price_total)}</span>
      <span>실매출-정산수가 ${revenueMoney(settlement.revenue_minus_settlement_price)}</span>
      <span>정산 건수 ${revenueQuantity(settlement.quantity_total)}건</span>
      <span>건당 평균 수가 ${revenueMoney(settlementAveragePrice)}</span>
    </div>
    <div class="stats-section">
      <div class="stats-section-title-row">
        <h3 class="stats-section-title">일별 매출</h3>
        <button type="button" class="revenue-section-edit-btn" onclick="openRevenueDailyFieldEditor()" title="일별 매출 항목 선택" aria-label="일별 매출 항목 선택">✎</button>
      </div>
      ${dailyRows
        ? `<div style="overflow-x:auto;"><table class="data-table revenue-stat-daily-table"><thead><tr>${dailyHeaders}</tr></thead><tbody>${dailyRows}</tbody></table></div>`
        : '<p class="muted" style="margin:0;">해당 기간 매출 기록이 없습니다.</p>'}
    </div>`;
}

let _statsMode = 'reserved';
let _statsFilterCode = '';
let _statsTreatmentList = [];
function _getFilterLabel(){ return '전체'; }
async function loadStatsTreatmentFilter(){ /* removed */ }
function renderStatsTreatmentFilter(){ /* removed */ }
function switchStatsFilter(){ /* removed */ }
function switchStatsMode(){ /* removed */ }

function makeBarChart(items, labelKey, countKey, color){
  if(!items || !items.length) return '<p style="color:#4B5563;font-size:13px;margin:0;">데이터 없음</p>';
  const maxV=Math.max(1,...items.map(x=>x[countKey]));
  const topItem=items.reduce((a,b)=>b[countKey]>a[countKey]?b:a, items[0]);
  const topLabel=`🏆 최다: ${topItem[labelKey]} (${topItem[countKey]}건)`;
  const chartH=180;
  const bars=items.map(it=>{
    const barH=it[countKey]>0?Math.max(6,Math.round((it[countKey]/maxV)*chartH)):0;
    return `
      <div style="display:flex;flex-direction:column;align-items:center;justify-content:flex-end;gap:5px;flex:1;min-width:48px;max-width:80px;">
        <div style="font-size:11px;font-weight:600;color:#374151;text-align:center;">${it[countKey]}</div>
        <div style="width:72%;background:${color};border-radius:6px 6px 0 0;height:${barH}px;transition:height .3s;box-shadow:0 2px 4px rgba(0,0,0,0.10);"></div>
        <div style="font-size:11px;color:#4B5563;text-align:center;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100%;padding:0 4px;line-height:1.3;" title="${it[labelKey]}">${it[labelKey]}</div>
      </div>
    `;
  }).join('');
  return `
    <div style="font-size:11px;color:#4B5563;margin-bottom:12px;padding:5px 10px;background:#F9FAFB;border-radius:6px;border-left:3px solid ${color};">${topLabel}</div>
    <div style="display:flex;align-items:flex-end;gap:8px;height:${chartH+46}px;overflow-x:auto;padding:0 4px 4px;border-bottom:2px solid #E5E7EB;">
      ${bars}
    </div>
  `;
}

// ──────────── 집계 탭 전용 함수 ────────────

// 기간 프리셋 계산 — 'YYYY-MM-DD' 문자열 [from, to] 반환
function _presetRange(kind){
  const now = new Date(); now.setHours(0,0,0,0);
  const fmt = d => {
    const y=d.getFullYear(), m=String(d.getMonth()+1).padStart(2,'0'), dd=String(d.getDate()).padStart(2,'0');
    return `${y}-${m}-${dd}`;
  };
  if(kind==='today'){ return [fmt(now), fmt(now)]; }
  if(kind==='week'){
    const from=new Date(now); from.setDate(from.getDate()-6);
    return [fmt(from), fmt(now)];
  }
  if(kind==='30d'){
    const from=new Date(now); from.setDate(from.getDate()-29);
    return [fmt(from), fmt(now)];
  }
  if(kind==='month_now'){
    const from=new Date(now.getFullYear(), now.getMonth(), 1);
    const to  =new Date(now.getFullYear(), now.getMonth()+1, 0); // 이번달 마지막날
    return [fmt(from), fmt(to)];
  }
  if(kind==='month_prev'){
    const from=new Date(now.getFullYear(), now.getMonth()-1, 1);
    const to  =new Date(now.getFullYear(), now.getMonth(), 0); // 지난달 마지막날
    return [fmt(from), fmt(to)];
  }
  return [fmt(now), fmt(now)];
}

function applyAggPreset(kind){
  const [from,to] = _presetRange(kind);
  document.getElementById('agg-from').value = from;
  document.getElementById('agg-to').value   = to;
  loadAggregate();
}

function initAggregate(){
  const fi = document.getElementById('agg-from');
  const ti = document.getElementById('agg-to');
  // 처음엔 이번 달로 디폴트
  if(!fi.value || !ti.value){
    const [from,to] = _presetRange('month_now');
    fi.value = from; ti.value = to;
  }
  loadAggregate();
}

function populateAggCategorySelect(categories, selectedId){
  const sel = document.getElementById('agg-category');
  if(!sel) return;
  const prev = sel.value;
  const rows = categories || [];
  sel.innerHTML = rows.length
    ? rows.map(c => `<option value="${c.id}">${escapeHtml(c.name||'')}</option>`).join('')
    : '<option value="">과 없음</option>';
  sel.value = selectedId || prev || (rows[0] && rows[0].id) || '';
}

function _aggUnitInc(code){
  const priceMap = (TX_META && TX_META.treatment_price) || {};
  const pctMap   = (TX_META && TX_META.treatment_incentive_pct) || {};
  const amtMap   = (TX_META && TX_META.treatment_incentive_amount) || {};
  const a = amtMap[code]; if(a && a > 0) return a;
  const p = pctMap[code]; if(p && p > 0) return Math.round((priceMap[code]||0) * p / 100);
  return 0;
}

function recalcAggregateTotals(){
  const totals = {};
  document.querySelectorAll('.agg-count-input').forEach(inp => {
    if(inp.disabled) return;
    const emp = inp.dataset.employeeId;
    const code = inp.dataset.code;
    const n = Math.max(0, parseInt(inp.value || '0') || 0);
    totals[emp] = totals[emp] || {};
    totals[emp][code] = (totals[emp][code] || 0) + n;
  });
  document.querySelectorAll('[data-agg-total-employee]').forEach(cell => {
    const emp = cell.dataset.aggTotalEmployee;
    const code = cell.dataset.aggTotalCode;
    const v = (totals[emp] && totals[emp][code]) || 0;
    cell.textContent = v > 0 ? v : '-';
  });
  document.querySelectorAll('[data-agg-incentive-employee]').forEach(cell => {
    const emp = cell.dataset.aggIncentiveEmployee;
    const byCode = totals[emp] || {};
    let total = 0;
    Object.entries(byCode).forEach(([code, count]) => { total += count * _aggUnitInc(code); });
    cell.textContent = total > 0 ? total.toLocaleString() + '원' : '-';
  });
}

function normalizeAggregateInput(input){
  if(!input) return;
  const cleaned = String(input.value || '').replace(/\D/g, '');
  if(input.value !== cleaned) input.value = cleaned;
  recalcAggregateTotals();
}

function handleAggregateInputKeydown(event, input){
  if(event.key === 'Enter'){
    event.preventDefault();
    input.blur();
  }
}

async function saveAggregateCell(input){
  if(!input || input.disabled) return;
  normalizeAggregateInput(input);
  const n = Math.max(0, parseInt(input.value || '0') || 0);
  input.value = n > 0 ? String(n) : '';
  const saveKey = `${input.dataset.date}|${input.dataset.employeeId}|${input.dataset.code}|${n}`;
  if(input.dataset.savedKey === saveKey) return;
  input.dataset.savedKey = saveKey;
  input.classList.add('saving');
  try {
    const r = await fetch('/api/manual-counts', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        date: input.dataset.date,
        therapist_id: input.dataset.employeeId,
        treatment_code: input.dataset.code,
        count: n,
      }),
    });
    const d = await r.json().catch(() => ({}));
    if(!r.ok || !d.ok){
      input.dataset.savedKey = '';
      alert('저장 실패: ' + (d.detail || d.error || r.statusText));
      return;
    }
    recalcAggregateTotals();
  } catch(e){
    input.dataset.savedKey = '';
    alert('저장 요청 실패: ' + e.message);
  } finally {
    input.classList.remove('saving');
  }
}

async function loadAggregate(){
  const loading = document.getElementById('agg-loading');
  const bodyEl = document.getElementById('agg-body');
  try {
  const fromStr = document.getElementById('agg-from').value;
  const toStr   = document.getElementById('agg-to').value;
  if(!fromStr || !toStr){ alert('기간(시작일/종료일)을 선택하세요'); return; }
  if(fromStr > toStr){ alert('시작일이 종료일보다 클 수 없습니다.'); return; }

  if(loading) loading.style.display='block';
  if(bodyEl) bodyEl.innerHTML='';
  await loadTreatmentMeta();

  const categoryId = document.getElementById('agg-category')?.value || '';
  const params = new URLSearchParams({date_from: fromStr, date_to: toStr});
  if(categoryId) params.set('category_id', categoryId);
  const data = await fetch(`/api/stats/direct-aggregate?${params.toString()}`).then(r=>r.json());
  if(loading) loading.style.display='none';

  const categories = data.categories || [];
  const selectedCategoryId = data.category_id || categoryId || '';
  populateAggCategorySelect(categories, selectedCategoryId);

  const employees = data.employees || [];
  const treatments = data.treatments || [];
  const items = data.items || [];
  if(!treatments.length){
    if(bodyEl) bodyEl.innerHTML='<p class="muted" style="padding:16px;">선택한 과에 활성 치료항목이 없습니다.</p>';
    return;
  }
  if(!employees.length){
    if(bodyEl) bodyEl.innerHTML='<p class="muted" style="padding:16px;">선택한 과/치료항목에 집계할 직원이 없습니다.</p>';
    return;
  }

  const colsPerEmployee = treatments.length;
  const th1Employees = employees.map(e => `
    <th colspan="${colsPerEmployee}" class="agg-employee-head">
      <span class="color-dot" style="background:${e.color||'#9CA3AF'}"></span>${escapeHtml(e.name||'')}
    </th>`).join('');
  const th2Treatments = employees.map(() => treatments.map(t => `
    <th class="agg-treatment-head" title="${escapeAttr(t.name||t.code)}">${escapeHtml(t.short || t.name || t.code)}</th>
  `).join('')).join('');

  const totals = {};
  employees.forEach(e => { totals[e.id] = {}; treatments.forEach(t => { totals[e.id][t.code] = 0; }); });
  const dow = ['일','월','화','수','목','금','토'];
  const bodyRows = items.map(row => {
    const dObj = new Date(row.date + 'T00:00:00');
    const wd = dow[dObj.getDay()];
    const dateLabel = `${dObj.getMonth()+1}/${dObj.getDate()} (${wd})`;
    const dateClass = wd === '일' ? 'agg-sun' : (wd === '토' ? 'agg-sat' : '');
    const cells = employees.map(e => {
      const counts = ((row.employee_data || {})[e.id] || {}).counts || {};
      return treatments.map(t => {
        const enabled = employeeCanSelectedTreatments(e, [t.code]);
        if(!enabled){
          return '<td class="agg-disabled-cell">-</td>';
        }
        const v = counts[t.code] || 0;
        totals[e.id][t.code] += v;
        return `<td class="agg-input-cell">
          <input class="agg-count-input" type="text" inputmode="numeric" pattern="[0-9]*"
                 autocomplete="off" enterkeyhint="done"
                 value="${v > 0 ? v : ''}"
                 data-date="${row.date}"
                 data-employee-id="${e.id}"
                 data-treatment-id="${t.id}"
                 data-code="${t.code}"
                 data-saved-key="${row.date}|${e.id}|${t.code}|${v}"
                 onfocus="this.select()"
                 oninput="normalizeAggregateInput(this)"
                 onkeydown="handleAggregateInputKeydown(event, this)"
                 onblur="saveAggregateCell(this)">
        </td>`;
      }).join('');
    }).join('');
    return `<tr>
      <td class="agg-date-cell ${dateClass}">${dateLabel}</td>
      ${cells}
    </tr>`;
  }).join('');

  const totalCells = employees.map(e => treatments.map(t => {
    const v = totals[e.id][t.code] || 0;
    return `<td class="agg-total-cell" data-agg-total-employee="${e.id}" data-agg-total-code="${t.code}">${v > 0 ? v : '-'}</td>`;
  }).join('')).join('');

  const incentiveCells = employees.map(e => {
    let total = 0;
    treatments.forEach(t => { total += (totals[e.id][t.code] || 0) * _aggUnitInc(t.code); });
    return `<td colspan="${colsPerEmployee}" class="agg-incentive-cell" data-agg-incentive-employee="${e.id}">
      ${total > 0 ? total.toLocaleString() + '원' : '-'}
    </td>`;
  }).join('');

  if(bodyEl) bodyEl.innerHTML = `
    <div class="agg-help">
      선택한 과의 치료항목별 횟수를 직접 입력합니다. 입력이 끝나면 상단의 정산 반영을 눌러 정산 탭에 스냅샷으로 넘깁니다.
    </div>
    <div style="overflow-x:auto;margin-top:8px;">
      <table class="agg-direct-table">
        <thead>
          <tr>
            <th rowspan="2" class="agg-date-head">날짜</th>
            ${th1Employees}
          </tr>
          <tr>${th2Treatments}</tr>
        </thead>
        <tbody>
          ${bodyRows}
          <tr class="agg-footer-row"><td class="agg-date-cell">기간합계</td>${totalCells}</tr>
          <tr class="agg-footer-row"><td class="agg-date-cell">인센티브</td>${incentiveCells}</tr>
        </tbody>
      </table>
    </div>`;
  } catch(e){
    console.error('[aggregate] load failed', e);
    if(bodyEl){
      bodyEl.innerHTML = '<p class="muted" style="padding:16px;color:#DC2626;">집계 렌더링 실패: '
        + escapeHtml(e && e.message ? e.message : e)
        + '</p>';
    }
  } finally {
    if(loading) loading.style.display='none';
  }
}

async function applyAggregateToSettlement(){
  const fromStr = document.getElementById('agg-from').value;
  const toStr = document.getElementById('agg-to').value;
  const categoryId = document.getElementById('agg-category')?.value || '';
  if(!fromStr || !toStr){ alert('기간(시작일/종료일)을 선택하세요'); return; }
  if(fromStr > toStr){ alert('시작일이 종료일보다 클 수 없습니다.'); return; }

  const inputs = [...document.querySelectorAll('#agg-body .agg-count-input')]
    .filter(inp => inp.dataset.employeeId && inp.dataset.treatmentId && inp.dataset.date);
  if(!inputs.length){
    alert('먼저 집계 조회를 해서 반영할 그리드를 불러오세요.');
    return;
  }
  if(!confirm('현재 집계 화면의 수량을 정산에 반영할까요? 기존 같은 날짜/직원/치료항목 정산은 현재 수량으로 갱신됩니다.')){
    return;
  }

  const entries = inputs.map(inp => ({
    performed_on: inp.dataset.date,
    employee_id: inp.dataset.employeeId,
    treatment_id: inp.dataset.treatmentId,
    quantity: Math.max(0, parseInt(inp.value || '0') || 0),
    memo: '',
  }));

  try {
    inputs.forEach(inp => inp.classList.add('saving'));
    const r = await adminFetch('/api/settlement/records/grid', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        date_from: fromStr,
        date_to: toStr,
        category_id: categoryId,
        entries,
      }),
    });
    const data = await r.json().catch(() => ({}));
    if(!r.ok || data.ok === false){
      throw new Error(data.detail || data.error || r.statusText);
    }
    const sf = document.getElementById('settle-from');
    const st = document.getElementById('settle-to');
    const sc = document.getElementById('settle-category');
    if(sf) sf.value = fromStr;
    if(st) st.value = toStr;
    if(sc && categoryId) sc.value = categoryId;
    if(document.getElementById('admin-settlement')?.classList.contains('active')){
      await loadSettlement();
    }
    await loadAggregate();
    const changed = data.changed || {};
    alert(`정산에 반영했습니다. 저장 ${changed.upserted || 0}건, 삭제 ${changed.deleted || 0}건`);
  } catch(e){
    alert('정산 반영 실패: ' + (e && e.message ? e.message : e));
  } finally {
    inputs.forEach(inp => inp.classList.remove('saving'));
  }
}

let SETTLEMENT_GRID = null;

function applySettlementPreset(kind){
  const [from,to] = _presetRange(kind);
  document.getElementById('settle-from').value = from;
  document.getElementById('settle-to').value = to;
  loadSettlement();
}

function initSettlement(){
  const fi = document.getElementById('settle-from');
  const ti = document.getElementById('settle-to');
  if(!fi.value || !ti.value){
    const [from,to] = _presetRange('month_now');
    fi.value = from; ti.value = to;
  }
  loadSettlement();
}

function populateSettlementCategorySelect(categories, selectedId){
  const sel = document.getElementById('settle-category');
  if(!sel) return;
  const prev = sel.value;
  const rows = categories || [];
  sel.innerHTML = rows.length
    ? rows.map(c => `<option value="${c.id}">${escapeHtml(c.name||'')}</option>`).join('')
    : '<option value="">과 없음</option>';
  sel.value = selectedId || prev || (rows[0] && rows[0].id) || '';
}

function settlementMoney(v){
  const n = Math.round(Number(v || 0));
  return n > 0 ? n.toLocaleString() + '원' : '-';
}

function settlementMoneyAlways(v){
  const n = Math.round(Number(v || 0));
  return n.toLocaleString() + '원';
}

function settlementQuantity(v){
  const n = Math.max(0, parseInt(v || '0') || 0);
  return n.toLocaleString();
}

function settlementRuleLabel(rec){
  const rule = rec && rec.incentive_type_snapshot || 'none';
  const value = rec && rec.incentive_value_snapshot || 0;
  if(rule === 'fixed') return `고정 ${settlementMoneyAlways(value)}`;
  if(rule === 'percent') return `${Number(value || 0).toLocaleString()}%`;
  return '없음';
}

function settlementRecordTreatmentLabel(rec){
  return rec && (rec.treatment_short_snapshot || rec.treatment_name_snapshot) || '-';
}

function settlementRecordPriceTotal(rec, qty){
  if(rec && rec.price_total !== undefined && rec.price_total !== null){
    return Math.round(Number(rec.price_total || 0));
  }
  return Math.round(Number(rec && rec.price_snapshot || 0) * qty);
}

function settlementDateLabel(dateStr){
  if(!dateStr) return '-';
  const parts = String(dateStr).split('-').map(x => parseInt(x, 10));
  if(parts.length !== 3 || parts.some(Number.isNaN)) return String(dateStr);
  const d = new Date(parts[0], parts[1] - 1, parts[2]);
  const weekdays = ['일', '월', '화', '수', '목', '금', '토'];
  return `${parts[1]}/${parts[2]} (${weekdays[d.getDay()]})`;
}

function settlementAddTreatmentCount(box, key, label, qty){
  const txKey = key || label || '-';
  const item = box[txKey] || {label: label || '-', quantity: 0};
  item.quantity += qty;
  box[txKey] = item;
}

function settlementTreatmentCountBadges(byTreatment){
  const items = Object.values(byTreatment || {})
    .filter(x => Number(x.quantity || 0) > 0)
    .sort((a,b) => String(a.label || '').localeCompare(String(b.label || ''), 'ko'));
  if(!items.length) return '<span class="muted">-</span>';
  return `<div class="settlement-treatment-count-list">${
    items.map(x => `<span class="settlement-treatment-count"><b>${escapeHtml(x.label || '-')}</b> ${settlementQuantity(x.quantity)}개</span>`).join('<span class="settlement-treatment-separator">|</span>')
  }</div>`;
}

function buildSettlementReportGroups(records){
  const employees = {};
  const dates = {};
  (records || []).forEach(rec => {
    const qty = Math.max(0, parseInt(rec.quantity || '0') || 0);
    if(qty <= 0) return;
    const priceTotal = settlementRecordPriceTotal(rec, qty);
    const incentive = Math.round(Number(rec.incentive_amount || 0));
    const empKey = rec.employee_id || rec.employee_name_snapshot || '-';
    const txKey = rec.treatment_id || settlementRecordTreatmentLabel(rec);
    const txLabel = settlementRecordTreatmentLabel(rec);
    const dateKey = rec.performed_on || '-';

    const emp = employees[empKey] || {
      employee_id: rec.employee_id || '',
      employee_name: rec.employee_name_snapshot || '-',
      category_name: rec.employee_category_name_snapshot || '-',
      quantity_total: 0,
      price_total: 0,
      incentive_total: 0,
      adjustment_total: 0,
      payment_total: 0,
      byTreatment: {},
    };
    emp.quantity_total += qty;
    emp.price_total += priceTotal;
    emp.incentive_total += incentive;
    settlementAddTreatmentCount(emp.byTreatment, txKey, txLabel, qty);
    employees[empKey] = emp;

    const group = dates[dateKey] || {
      date: dateKey,
      quantity_total: 0,
      price_total: 0,
      incentive_total: 0,
      byTreatment: {},
      byEmployee: {},
    };
    group.quantity_total += qty;
    group.price_total += priceTotal;
    group.incentive_total += incentive;
    settlementAddTreatmentCount(group.byTreatment, txKey, txLabel, qty);

    const dayEmp = group.byEmployee[empKey] || {
      employee_name: rec.employee_name_snapshot || '-',
      category_name: rec.employee_category_name_snapshot || '-',
      quantity_total: 0,
      price_total: 0,
      incentive_total: 0,
      byTreatment: {},
    };
    dayEmp.quantity_total += qty;
    dayEmp.price_total += priceTotal;
    dayEmp.incentive_total += incentive;
    settlementAddTreatmentCount(dayEmp.byTreatment, txKey, txLabel, qty);
    group.byEmployee[empKey] = dayEmp;
    dates[dateKey] = group;
  });

  Object.values(employees).forEach(emp => {
    emp.payment_total = intOrZero(emp.incentive_total) + intOrZero(emp.adjustment_total);
  });

  return {
    employees: Object.values(employees).sort((a,b) => String(a.employee_name || '').localeCompare(String(b.employee_name || ''), 'ko')),
    dates: Object.values(dates).sort((a,b) => String(a.date || '').localeCompare(String(b.date || ''))),
  };
}

function intOrZero(v){
  return Math.round(Number(v || 0));
}

function renderSettlementDateGroups(groups){
  if(!groups || !groups.length){
    return '<p class="muted" style="margin:0;">집계 탭에서 정산 반영한 내역이 없습니다.</p>';
  }
  return `<div class="settlement-date-groups">${groups.map(group => {
    const employees = Object.values(group.byEmployee || {})
      .sort((a,b) => String(a.employee_name || '').localeCompare(String(b.employee_name || ''), 'ko'));
    const employeeRows = employees.map(emp => `
      <tr>
        <td>${escapeHtml(emp.employee_name || '-')}</td>
        <td>${escapeHtml(emp.category_name || '-')}</td>
        <td>${settlementTreatmentCountBadges(emp.byTreatment)}</td>
        <td>${settlementMoneyAlways(emp.price_total)}</td>
        <td>${settlementMoneyAlways(emp.incentive_total)}</td>
      </tr>`).join('');
    const dateLabel = settlementDateLabel(group.date);
    return `<details class="settlement-date-group">
      <summary class="settlement-date-card" aria-label="${escapeAttr(dateLabel)} 정산 상세 열고 닫기">
        <span class="settlement-date-main">
          <span class="settlement-date-title">${escapeHtml(dateLabel)}</span>
          <span class="settlement-date-sub">직원 ${settlementQuantity(employees.length)}명 · 항목 ${settlementQuantity(Object.keys(group.byTreatment || {}).length)}개</span>
        </span>
        <div class="settlement-date-treatment-summary">
          <span>치료항목별 건수</span>
          ${settlementTreatmentCountBadges(group.byTreatment)}
        </div>
        <span class="settlement-date-metric"><span>총 수가</span><b>${settlementMoneyAlways(group.price_total)}</b></span>
        <span class="settlement-date-metric settlement-date-incentive"><span>세전 인센티브</span><b>${settlementMoneyAlways(group.incentive_total)}</b></span>
        <span class="settlement-date-toggle" aria-hidden="true"></span>
      </summary>
      <div class="settlement-date-body">
        <div class="settlement-date-treatment-line">${settlementTreatmentCountBadges(group.byTreatment)}</div>
        <div style="overflow-x:auto;">
          <table class="settlement-summary-table settlement-report-table settlement-detail-table">
            <thead><tr><th>직원</th><th>과</th><th>치료항목별 건수</th><th>총 수가</th><th>세전 인센티브</th></tr></thead>
            <tbody>${employeeRows}</tbody>
          </table>
        </div>
      </div>
    </details>`;
  }).join('')}</div>`;
}

function settlementCellAllowed(employee, treatment){
  const ids = employee.treatment_ids || [];
  if(employee.treatment_override_enabled){
    return ids.includes(treatment.id);
  }
  if(ids.length){
    return ids.includes(treatment.id);
  }
  if(employee.category_id){
    return !treatment.category_id || treatment.category_id === employee.category_id;
  }
  return false;
}

function normalizeSettlementInput(input){
  if(!input) return;
  const cleaned = String(input.value || '').replace(/\D/g, '');
  if(input.value !== cleaned) input.value = cleaned;
  recalcSettlementTotals();
}

function handleSettlementInputKeydown(event, input){
  if(event.key === 'Enter'){
    event.preventDefault();
    input.blur();
  }
}

function recalcSettlementTotals(){
  const employeeTotals = {};
  const treatmentTotals = {};
  let quantityTotal = 0;
  let incentiveTotal = 0;
  document.querySelectorAll('.settle-count-input').forEach(inp => {
    if(inp.disabled) return;
    const emp = inp.dataset.employeeId;
    const tid = inp.dataset.treatmentId;
    const qty = Math.max(0, parseInt(inp.value || '0') || 0);
    const unit = Math.max(0, Number(inp.dataset.unitIncentive || 0));
    const inc = qty * unit;
    employeeTotals[emp] = employeeTotals[emp] || {quantity:0, incentive:0, byTreatment:{}};
    treatmentTotals[tid] = treatmentTotals[tid] || {quantity:0, incentive:0};
    employeeTotals[emp].quantity += qty;
    employeeTotals[emp].incentive += inc;
    employeeTotals[emp].byTreatment[tid] = (employeeTotals[emp].byTreatment[tid] || 0) + qty;
    treatmentTotals[tid].quantity += qty;
    treatmentTotals[tid].incentive += inc;
    quantityTotal += qty;
    incentiveTotal += inc;
  });

  document.querySelectorAll('[data-settle-total-employee]').forEach(cell => {
    const emp = cell.dataset.settleTotalEmployee;
    const tid = cell.dataset.settleTotalTreatment;
    const v = employeeTotals[emp] && employeeTotals[emp].byTreatment[tid] || 0;
    cell.textContent = v > 0 ? v : '-';
  });
  document.querySelectorAll('[data-settle-incentive-employee]').forEach(cell => {
    const emp = cell.dataset.settleIncentiveEmployee;
    const v = employeeTotals[emp] && employeeTotals[emp].incentive || 0;
    cell.textContent = settlementMoney(v);
  });

  const qtyEl = document.getElementById('settle-summary-qty');
  const incEl = document.getElementById('settle-summary-incentive');
  const empEl = document.getElementById('settle-summary-employees');
  const txEl = document.getElementById('settle-summary-treatments');
  if(qtyEl) qtyEl.textContent = quantityTotal.toLocaleString();
  if(incEl) incEl.textContent = settlementMoney(incentiveTotal);
  if(empEl) empEl.textContent = Object.values(employeeTotals).filter(x => x.quantity > 0).length.toLocaleString();
  if(txEl) txEl.textContent = Object.values(treatmentTotals).filter(x => x.quantity > 0).length.toLocaleString();

  const empBox = document.getElementById('settle-employee-summary');
  if(empBox && SETTLEMENT_GRID){
    const names = Object.fromEntries((SETTLEMENT_GRID.employees || []).map(e => [e.id, e.name || '']));
    const rows = Object.entries(employeeTotals)
      .filter(([,v]) => v.quantity > 0)
      .sort((a,b) => (names[a[0]] || '').localeCompare(names[b[0]] || ''))
      .map(([id,v]) => `<tr><td>${escapeHtml(names[id] || '-')}</td><td>${v.quantity.toLocaleString()}</td><td>${settlementMoney(v.incentive)}</td></tr>`)
      .join('');
    empBox.innerHTML = rows
      ? `<table class="settlement-summary-table"><thead><tr><th>직원</th><th>수량</th><th>세전 인센티브</th></tr></thead><tbody>${rows}</tbody></table>`
      : '<p class="muted" style="margin:0;">저장할 수량이 없습니다.</p>';
  }

  const txBox = document.getElementById('settle-treatment-summary');
  if(txBox && SETTLEMENT_GRID){
    const names = Object.fromEntries((SETTLEMENT_GRID.treatments || []).map(t => [t.id, t.short || t.name || t.code || '']));
    const rows = Object.entries(treatmentTotals)
      .filter(([,v]) => v.quantity > 0)
      .sort((a,b) => (names[a[0]] || '').localeCompare(names[b[0]] || ''))
      .map(([id,v]) => `<tr><td>${escapeHtml(names[id] || '-')}</td><td>${v.quantity.toLocaleString()}</td><td>${settlementMoney(v.incentive)}</td></tr>`)
      .join('');
    txBox.innerHTML = rows
      ? `<table class="settlement-summary-table"><thead><tr><th>치료항목</th><th>수량</th><th>세전 인센티브</th></tr></thead><tbody>${rows}</tbody></table>`
      : '<p class="muted" style="margin:0;">저장할 수량이 없습니다.</p>';
  }
}

async function loadSettlement(){
  const loading = document.getElementById('settle-loading');
  const bodyEl = document.getElementById('settle-body');
  try {
    const fromStr = document.getElementById('settle-from').value;
    const toStr = document.getElementById('settle-to').value;
    if(!fromStr || !toStr){ alert('기간을 선택하세요.'); return; }
    if(fromStr > toStr){ alert('시작일이 종료일보다 늦을 수 없습니다.'); return; }
    if(loading) loading.style.display = 'block';
    if(bodyEl) bodyEl.innerHTML = '';
    const categoryId = document.getElementById('settle-category')?.value || '';
    const params = new URLSearchParams({date_from: fromStr, date_to: toStr});
    if(categoryId) params.set('category_id', categoryId);
    const r = await adminFetch(`/api/settlement/reports/incentives?${params.toString()}`);
    const data = await r.json().catch(() => ({}));
    if(!r.ok) throw new Error(data.detail || r.statusText);
    SETTLEMENT_GRID = data;
    renderSettlement(data);
  } catch(e){
    console.error('[settlement] load failed', e);
    if(bodyEl){
      bodyEl.innerHTML = '<p class="muted" style="padding:16px;color:#DC2626;">정산 조회 실패: '
        + escapeHtml(e && e.message ? e.message : e)
        + '</p>';
    }
  } finally {
    if(loading) loading.style.display = 'none';
  }
}

function renderSettlement(data){
  const bodyEl = document.getElementById('settle-body');
  if(!bodyEl) return;
  populateSettlementCategorySelect(data.categories || [], data.category_id || '');
  const summary = data.summary || {};
  const records = data.records || [];
  const grouped = buildSettlementReportGroups(records);
  const employeeRows = grouped.employees.map(emp => `
    <tr>
      <td>${escapeHtml(emp.employee_name || '-')}</td>
      <td>${escapeHtml(emp.category_name || '-')}</td>
      <td>${settlementTreatmentCountBadges(emp.byTreatment)}</td>
      <td>${settlementMoneyAlways(emp.incentive_total)}</td>
      <td>${settlementMoneyAlways(emp.adjustment_total)}</td>
      <td>${settlementMoneyAlways(emp.payment_total)}</td>
    </tr>`).join('');
  const treatmentRows = (summary.by_treatment || []).map(tx => `
    <tr>
      <td>${escapeHtml(tx.treatment_name || tx.treatment_short || '-')}</td>
      <td>${settlementQuantity(tx.quantity_total)}</td>
      <td>${settlementMoneyAlways(tx.price_total)}</td>
      <td>${settlementMoneyAlways(tx.incentive_total)}</td>
    </tr>`).join('');
  const detailGroups = renderSettlementDateGroups(grouped.dates);

  bodyEl.innerHTML = `
    <div class="settlement-note">
      집계 탭에서 정산 반영한 스냅샷 기준입니다. 이후 치료항목 수가나 인센티브 규칙을 바꿔도 기존 정산 금액은 유지됩니다.
    </div>
    <div class="settlement-summary-grid settlement-summary-grid-wide">
      <div class="stat-card"><div class="stat-label">기간 건수</div><div class="stat-value">${settlementQuantity(summary.quantity_total)}</div></div>
      <div class="stat-card"><div class="stat-label">직원수</div><div class="stat-value">${settlementQuantity((summary.by_employee || []).length)}</div></div>
      <div class="stat-card"><div class="stat-label">치료항목</div><div class="stat-value">${settlementQuantity((summary.by_treatment || []).length)}</div></div>
      <div class="stat-card"><div class="stat-label">총 수가</div><div class="stat-value">${settlementMoneyAlways(summary.price_total)}</div></div>
      <div class="stat-card"><div class="stat-label">세전 인센티브</div><div class="stat-value">${settlementMoneyAlways(summary.incentive_total)}</div></div>
    </div>
    <div id="settlement-revenue-help"></div>
    <div class="settlement-summary-panels">
      <div>
        <h3 class="stats-section-title">직원별 합계</h3>
        ${employeeRows
          ? `<div style="overflow-x:auto;"><table class="settlement-summary-table settlement-report-table">
              <thead><tr><th>직원</th><th>과</th><th>치료항목별 건수</th><th>세전 인센티브</th><th>조정금액</th><th>최종 지급액</th></tr></thead>
              <tbody>${employeeRows}</tbody>
            </table></div>`
          : '<p class="muted" style="margin:0;">정산 반영된 직원별 내역이 없습니다.</p>'}
      </div>
      <div>
        <h3 class="stats-section-title">치료항목별 합계</h3>
        ${treatmentRows
          ? `<div style="overflow-x:auto;"><table class="settlement-summary-table settlement-report-table">
              <thead><tr><th>치료항목</th><th>총 건수</th><th>총 수가</th><th>세전 인센티브</th></tr></thead>
              <tbody>${treatmentRows}</tbody>
            </table></div>`
          : '<p class="muted" style="margin:0;">정산 반영된 치료항목 내역이 없습니다.</p>'}
      </div>
    </div>
    <div style="margin-top:12px;">
      <h3 class="stats-section-title">상세 내역</h3>
      ${detailGroups}
    </div>`;
  loadSettlementRevenueHelp();
}

async function loadSettlementRevenueHelp(){
  const el = document.getElementById('settlement-revenue-help');
  if(!el) return;
  const fromStr = document.getElementById('settle-from')?.value || '';
  const toStr = document.getElementById('settle-to')?.value || '';
  if(!fromStr || !toStr) return;
  const params = new URLSearchParams({date_from: fromStr, date_to: toStr});
  const categoryId = document.getElementById('settle-category')?.value || '';
  if(categoryId) params.set('category_id', categoryId);
  try {
    const r = await adminFetch(`/api/revenue/stats?${params.toString()}`);
    const data = await r.json().catch(() => ({}));
    if(!r.ok) throw new Error(data.detail || data.error || r.statusText);
    const current = data.current || {};
    const settlement = data.settlement || {};
    const settlementQuantityTotal = Math.max(0, Number(settlement.quantity_total || 0));
    const settlementAveragePrice = settlementQuantityTotal
      ? Math.round(Number(settlement.price_total || 0) / settlementQuantityTotal)
      : 0;
    el.innerHTML = `
      <div class="settlement-note revenue-settlement-help">
        <b>매출 기준 참고</b>
        <span>실매출 ${revenueMoney(current.revenue_total)}</span>
        <span>정산 수가 ${revenueMoney(settlement.price_total)}</span>
        <span>차이 ${revenueMoney(settlement.revenue_minus_settlement_price)}</span>
        <span>정산 건수 ${revenueQuantity(settlement.quantity_total)}건</span>
        <span>건당 평균 수가 ${revenueMoney(settlementAveragePrice)}</span>
      </div>`;
  } catch(e){
    el.innerHTML = '<div class="settlement-note" style="color:#DC2626;">매출 참고 조회 실패: '
      + escapeHtml(e && e.message ? e.message : e)
      + '</div>';
  }
}

async function saveSettlementGrid(){
  if(!SETTLEMENT_GRID){ await loadSettlement(); if(!SETTLEMENT_GRID) return; }
  const inputs = [...document.querySelectorAll('.settle-count-input')];
  const entries = inputs.map(inp => ({
    performed_on: inp.dataset.date,
    employee_id: inp.dataset.employeeId,
    treatment_id: inp.dataset.treatmentId,
    quantity: Math.max(0, parseInt(inp.value || '0') || 0),
    memo: '',
  }));
  try {
    inputs.forEach(inp => inp.classList.add('saving'));
    const body = {
      date_from: document.getElementById('settle-from').value,
      date_to: document.getElementById('settle-to').value,
      category_id: document.getElementById('settle-category')?.value || '',
      entries,
    };
    const r = await adminFetch('/api/settlement/records/grid', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify(body),
    });
    const data = await r.json().catch(() => ({}));
    if(!r.ok || data.ok === false){
      throw new Error(data.detail || data.error || r.statusText);
    }
    SETTLEMENT_GRID = data;
    renderSettlement(data);
  } catch(e){
    alert('정산 저장 실패: ' + (e && e.message ? e.message : e));
  } finally {
    inputs.forEach(inp => inp.classList.remove('saving'));
  }
}

function _safeDownloadName(value){
  return String(value || '전체').replace(/[\\/:*?"<>|]+/g, '_').trim() || '전체';
}

async function downloadSettlementXlsx(){
  try {
    const fromStr = document.getElementById('settle-from').value;
    const toStr = document.getElementById('settle-to').value;
    if(!fromStr || !toStr){ alert('기간을 선택하세요.'); return; }
    if(fromStr > toStr){ alert('시작일이 종료일보다 늦을 수 없습니다.'); return; }
    const categoryId = document.getElementById('settle-category')?.value || '';
    const params = new URLSearchParams({date_from: fromStr, date_to: toStr});
    if(categoryId) params.set('category_id', categoryId);
    const r = await adminFetch(`/api/settlement/reports/incentives.xlsx?${params.toString()}`);
    if(!r.ok) throw new Error(await _apiErrorText(r));
    const blob = await r.blob();
    const sel = document.getElementById('settle-category');
    const categoryName = sel && sel.selectedOptions && sel.selectedOptions[0]
      ? sel.selectedOptions[0].textContent
      : '전체';
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `정산_${fromStr}_${toStr}_${_safeDownloadName(categoryName)}.xlsx`;
    document.body.appendChild(a);
    a.click();
    URL.revokeObjectURL(a.href);
    a.remove();
  } catch(e){
    alert('엑셀 다운로드 실패: ' + (e && e.message ? e.message : e));
  }
}

function printSettlement(){
  window.print();
}

function makeTherapistChart(items, manualCodes, manualNames){
  // ⚠️ 레거시 — 현재는 makeManualByTherapistTable 사용 (도수치료 예약/완료 카드)
  // 다른 곳에서 호출할 가능성 대비해 단순 fallback 으로 유지
  if(!items || !items.length) return '<p style="color:#4B5563;font-size:13px;margin:0;">데이터 없음</p>';
  return items.map(it =>
    `<div style="font-size:13px;margin:2px 0;">${it.therapist_name||'?'} : ${it.total||0}</div>`
  ).join('');
}

// ─────── 도수치료 예약/완료 (치료사별 × 시간항목 + 재진률) ───────
function makeManualByTherapistTable(data){
  if(!data || !data.items || !data.items.length){
    return '<p style="color:#4B5563;font-size:13px;margin:0;">데이터 없음</p>';
  }
  const manualCodes = data.manual_codes || [];
  const manualNames = data.manual_names || {};
  if(!manualCodes.length){
    return '<p style="color:#4B5563;font-size:13px;margin:0;">활성 도수치료 시간항목 없음</p>';
  }

  // 헤더: 치료사 | [도수30] [도수60] [도수90] ... | 재진률
  const headerManualCols = manualCodes.map(code =>
    `<th style="padding:8px 12px;text-align:center;font-size:12px;color:#374151;white-space:nowrap;font-weight:600;border-left:1px solid #E5E7EB;">${manualNames[code]||code}</th>`
  ).join('');

  // 행: 치료사당 1줄, 각 시간항목 셀 = "예 n / 완 n", 마지막 셀 = 재진률 %
  const rows = data.items.map(it => {
    const bd = it.breakdown || {};
    const t = THERAPISTS.find(x => x.id === it.therapist_id);
    const dotColor = t ? t.color : '#9CA3AF';

    const dataCols = manualCodes.map(code => {
      const cell = bd[code] || {reserved:0, approved:0};
      const r = cell.reserved || 0;
      const a = cell.approved || 0;
      if(r === 0 && a === 0){
        return `<td style="padding:8px 10px;text-align:center;font-size:13px;color:#4B5563;border-left:1px solid #F3F4F6;">-</td>`;
      }
      // 예 n / 완 n — 완료수가 예약수보다 낮으면 완료 색을 강조
      const doneColor = (a > 0 && a === r) ? '#059669' : (a > 0 ? '#2563EB' : '#9CA3AF');
      return `<td style="padding:8px 10px;text-align:center;font-size:13px;white-space:nowrap;border-left:1px solid #F3F4F6;">
        <span style="color:#111827;">예 <b>${r}</b></span>
        <span style="color:#D1D5DB;"> / </span>
        <span style="color:${doneColor};">완 <b>${a}</b></span>
      </td>`;
    }).join('');

    // 재진률: 완료 건수 없으면 "-"
    let revisitCell;
    if(it.revisit_rate === null || it.revisit_rate === undefined){
      revisitCell = `<td style="padding:8px 10px;text-align:center;font-size:13px;color:#4B5563;border-left:2px solid #E5E7EB;background:#FAFAFA;">-</td>`;
    } else {
      const rate = it.revisit_rate;
      const color = rate >= 70 ? '#059669' : (rate >= 40 ? '#D97706' : '#DC2626');
      revisitCell = `<td style="padding:8px 10px;text-align:center;font-size:13px;border-left:2px solid #E5E7EB;background:#FAFAFA;white-space:nowrap;">
        <b style="color:${color};font-size:14px;">${rate.toFixed(1)}%</b>
        <div style="font-size:11px;color:#4B5563;margin-top:2px;">재진 ${it.revisit_revisit}/${it.revisit_approved_total}</div>
      </td>`;
    }

    return `<tr style="border-top:1px solid #F3F4F6;">
      <td style="padding:8px 12px;font-size:13px;white-space:nowrap;">
        <span style="display:inline-block;width:10px;height:10px;background:${dotColor};border-radius:50%;margin-right:6px;vertical-align:middle;"></span>
        ${it.therapist_name}
      </td>
      ${dataCols}
      ${revisitCell}
    </tr>`;
  }).join('');

  return `
    <div style="overflow-x:auto;margin-top:4px;">
      <table style="min-width:100%;border-collapse:collapse;border:1px solid #E5E7EB;border-radius:6px;overflow:hidden;">
        <thead style="background:#F3F4F6;">
          <tr>
            <th style="padding:8px 12px;text-align:left;font-size:12px;color:#374151;font-weight:600;white-space:nowrap;">치료사</th>
            ${headerManualCols}
            <th style="padding:8px 12px;text-align:center;font-size:12px;color:#374151;font-weight:600;white-space:nowrap;border-left:2px solid #D1D5DB;background:#EEF2FF;">재진률</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
      <p class="muted" style="font-size:11px;margin:6px 0 0;">※ "예"=발생한 전체 예약(취소·노쇼 포함), "완"=완료(approved) 건수. 재진률 = 완료된 도수치료 예약 중 신환이 아닌 비율.</p>
    </div>
  `;
}

async function loadStatsCharts(fromStr, toStr){
  // 분석 영역 = 매출 중심 · 2카드 (v1.2.3+, v1.2.9 기간형).
  //   카드 1: 치료항목별 예상 매출 · 카드 2: 치료사별 예상 매출
  // 집계 기준:
  //   - /api/stats/daily-by-therapist 응답 재사용 (기간 전체, 완료 예약 기준)
  //   - 각 치료사의 manual_breakdown + eswt_count(ManualCount) 로 항목별 건수 산출
  //   - TX_META.treatment_price 로 매출 = 건수 × 수가 계산
  const data = await fetch(`/api/stats/daily-by-therapist?date_from=${fromStr}&date_to=${toStr}`).then(r=>r.json());
  const therapists   = data.therapists   || [];
  const manualCodes  = data.manual_codes || [];   // 활성 도수치료 시간항목 코드들
  const manualNames  = data.manual_names || {};
  const eswtName     = data.eswt_name    || '체외충격파';
  const eswtCode     = (TX_META && TX_META.eswt_code) || '';
  const priceMap     = (TX_META && TX_META.treatment_price) || {};
  const itemNameMap  = (TX_META && TX_META.treatment_names) || {};

  // ─── 항목별 집계 ───
  //  manualCodes 각 코드: sum of manual_breakdown[code] across all therapists, across all days
  //  eswtCode: sum of eswt_count across all therapists, across all days
  const codeCounts = {};
  manualCodes.forEach(c => { codeCounts[c] = 0; });
  codeCounts[eswtCode] = 0;

  const therapistRev = {}; // therapistId → 매출
  therapists.forEach(t => { therapistRev[t.id] = 0; });

  (data.items || []).forEach(row => {
    therapists.forEach(t => {
      const td = (row.therapist_data || {})[t.id] || {};
      const bd = td.manual_breakdown || {};
      // 도수 시간 항목 집계
      manualCodes.forEach(code => {
        const n = bd[code] || 0;
        codeCounts[code] += n;
        therapistRev[t.id] += n * (priceMap[code] || 0);
      });
      // 체외충격파 집계
      const eswtN = td.eswt_count || 0;
      codeCounts[eswtCode] += eswtN;
      therapistRev[t.id] += eswtN * (priceMap[eswtCode] || 0);
    });
  });

  // 항목별 매출 계산
  const revByCode = [];
  manualCodes.forEach(code => {
    revByCode.push({
      code,
      label: itemNameMap[code] || manualNames[code] || code,
      count: codeCounts[code] || 0,
      revenue: (codeCounts[code] || 0) * (priceMap[code] || 0),
    });
  });
  revByCode.push({
    code: eswtCode,
    label: itemNameMap[eswtCode] || eswtName,
    count: codeCounts[eswtCode] || 0,
    revenue: (codeCounts[eswtCode] || 0) * (priceMap[eswtCode] || 0),
  });

  const therapistRevItems = therapists.map(t => ({
    label: t.name,
    revenue: therapistRev[t.id] || 0,
    color: t.color || '#9CA3AF',
  })).sort((a,b) => b.revenue - a.revenue);

  const totalRevenue = revByCode.reduce((s,x) => s + x.revenue, 0);
  const totalRevStr = totalRevenue > 0
    ? `<span style="font-weight:700;color:#0F766E;">${totalRevenue.toLocaleString()} 원</span>`
    : '<span class="muted">0</span>';

  document.getElementById('stats-charts').innerHTML = `
    <div class="stats-chart-box">
      <div class="stats-chart-title">₩ 치료항목별 예상 매출
        <span class="muted" style="font-size:12px;font-weight:normal;">· 기간 합계 ${totalRevStr}</span>
      </div>
      <div style="flex:1;">${_makeRevenueBarChart(revByCode,'label','revenue','count','#0EA5E9')}</div>
    </div>
    <div class="stats-chart-box">
      <div class="stats-chart-title">◈ 치료사별 예상 매출</div>
      <div style="flex:1;">${_makeTherapistRevenueBar(therapistRevItems)}</div>
    </div>
  `;
}

// 치료항목별 매출 막대 — 금액 라벨 + 건수 보조 표시
function _makeRevenueBarChart(items, labelKey, valueKey, countKey, color){
  if (!items || !items.length)
    return '<p style="color:#4B5563;font-size:13px;margin:0;">데이터 없음</p>';
  // 모든 항목의 매출이 0이면 "수가 미설정" 안내
  if (items.every(x => !x[valueKey]))
    return '<p style="color:#4B5563;font-size:13px;margin:0;line-height:1.6;">기간 예상 매출 0원 — <b>관리자 › 치료항목</b> 에서 항목별 수가를 입력하세요.</p>';
  const maxV = Math.max(1, ...items.map(x => x[valueKey]));
  const topItem = items.reduce((a,b) => b[valueKey] > a[valueKey] ? b : a, items[0]);
  const topLabel = `🏆 최다 매출: ${topItem[labelKey]} (${topItem[valueKey].toLocaleString()}원)`;
  const chartH = 180;
  const bars = items.map(it => {
    const barH = it[valueKey] > 0 ? Math.max(6, Math.round((it[valueKey]/maxV)*chartH)) : 0;
    const amt = (it[valueKey] || 0).toLocaleString();
    const cnt = it[countKey] || 0;
    return `
      <div style="display:flex;flex-direction:column;align-items:center;justify-content:flex-end;gap:5px;flex:1;min-width:62px;max-width:100px;">
        <div style="font-size:11px;font-weight:700;color:#0F766E;text-align:center;white-space:nowrap;">${amt}</div>
        <div style="font-size:10px;color:#4B5563;">${cnt}건</div>
        <div style="width:72%;background:${color};border-radius:6px 6px 0 0;height:${barH}px;transition:height .3s;box-shadow:0 2px 4px rgba(0,0,0,0.10);"></div>
        <div style="font-size:11px;color:#4B5563;text-align:center;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100%;padding:0 4px;line-height:1.3;" title="${it[labelKey]}">${it[labelKey]}</div>
      </div>
    `;
  }).join('');
  return `
    <div style="font-size:11px;color:#4B5563;margin-bottom:12px;padding:5px 10px;background:#F9FAFB;border-radius:6px;border-left:3px solid ${color};">${topLabel}</div>
    <div style="display:flex;align-items:flex-end;gap:8px;height:${chartH+66}px;overflow-x:auto;padding:0 4px 4px;border-bottom:2px solid #E5E7EB;">
      ${bars}
    </div>
  `;
}

// 치료사별 매출 막대 — 각 치료사 색상 반영
function _makeTherapistRevenueBar(items){
  if (!items || !items.length)
    return '<p style="color:#4B5563;font-size:13px;margin:0;">치료사 없음</p>';
  if (items.every(x => !x.revenue))
    return '<p style="color:#4B5563;font-size:13px;margin:0;line-height:1.6;">기간 예상 매출 0원 — 치료항목에 수가가 설정되어 있는지 확인하세요.</p>';
  const maxV = Math.max(1, ...items.map(x => x.revenue));
  const chartH = 180;
  const bars = items.map(it => {
    const barH = it.revenue > 0 ? Math.max(6, Math.round((it.revenue/maxV)*chartH)) : 0;
    const amt = (it.revenue || 0).toLocaleString();
    return `
      <div style="display:flex;flex-direction:column;align-items:center;justify-content:flex-end;gap:5px;flex:1;min-width:62px;max-width:100px;">
        <div style="font-size:11px;font-weight:700;color:#0F766E;text-align:center;white-space:nowrap;">${amt}</div>
        <div style="width:72%;background:${it.color};border-radius:6px 6px 0 0;height:${barH}px;transition:height .3s;box-shadow:0 2px 4px rgba(0,0,0,0.10);"></div>
        <div style="font-size:11px;color:#4B5563;text-align:center;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100%;padding:0 4px;line-height:1.3;" title="${it.label}">${it.label}</div>
      </div>
    `;
  }).join('');
  return `
    <div style="display:flex;align-items:flex-end;gap:8px;height:${chartH+52}px;overflow-x:auto;padding:0 4px 4px;border-bottom:2px solid #E5E7EB;">
      ${bars}
    </div>
  `;
}

async function loadStats(){
  const fromStr = document.getElementById('stat-from').value;
  const toStr   = document.getElementById('stat-to').value;
  if(!fromStr || !toStr){ alert('기간을 선택하세요.'); return; }
  if(fromStr > toStr){ alert('시작일이 종료일보다 늦을 수 없습니다.'); return; }
  _statsFrom = fromStr; _statsTo = toStr;

  document.getElementById('stats-loading').style.display='block';
  document.getElementById('stats-body').style.display='none';
  document.getElementById('stats-loading').textContent='불러오는 중...';
  try{
    const qs = `date_from=${fromStr}&date_to=${toStr}`;
    const [summary, daily] = await Promise.all([
      fetch('/api/stats/summary?'+qs).then(r=>r.json()),
      fetch('/api/stats/daily?'+qs).then(r=>r.json()),
    ]);

    const total          = summary.total || 0;
    const approved       = summary.approved || 0;
    const manual         = summary.manual || 0;
    const manualApproved = summary.manual_approved || 0;
    const canceled       = summary.canceled || 0;
    // 20-3-1-UI (post-19-P / F-10): 노쇼 별도 집계 (cancel 의 부분집합 — 사용자 §3-7 (ii))
    const noShow         = summary.no_show_count || 0;
    const visitRate      = total > 0 ? Math.round((approved / total) * 100) : 0;
    const cancelRate     = total > 0 ? Math.round((canceled / total) * 100) : 0;
    const noShowRate     = canceled > 0 ? Math.round((noShow / canceled) * 100) : 0;
    const manualRate     = total > 0 ? Math.round((manual / total) * 100) : 0;
    const manualDoneRate = manual > 0 ? Math.round((manualApproved / manual) * 100) : 0;

    const titleEl = document.getElementById('stats-cards-title');
    if(titleEl) titleEl.textContent = `• 기간 요약 (${fromStr} ~ ${toStr})`;
    const cards=[
      {label:'총 예약',   value:total,         icon:'▦', color:'#2F86CB', sub:'완료율 '+visitRate+'%'},
      {label:'총 완료',   value:approved,       icon:'✓', color:'#3BA67D', sub:'예약 대비 '+visitRate+'%'},
      {label:'도수 예약', value:manual,         icon:'◐', color:'#7957AC', sub:'전체의 '+manualRate+'%'},
      {label:'도수 완료', value:manualApproved, icon:'●', color:'#5F4391', sub:'도수 중 '+manualDoneRate+'%'},
      {label:'취소',      value:canceled,       icon:'×', color:'#D7625C', sub:'취소율 '+cancelRate+'%'},
      {label:'노쇼',      value:noShow,         icon:'⚠', color:'#B45309', sub:'취소 중 '+noShowRate+'%'},
    ];
    document.getElementById('stats-cards').innerHTML=cards.map(function(c){
      return '<div class="stats-card" style="border-top:3px solid '+c.color+';">'
        +'<div style="font-size:20px;margin-bottom:6px;">'+c.icon+'</div>'
        +'<div style="font-size:28px;font-weight:700;color:'+c.color+';line-height:1;">'+c.value+'</div>'
        +'<div style="font-size:12px;color:#4B5563;margin-top:6px;">'+c.label+'</div>'
        +'<div style="font-size:11px;color:#4B5563;margin-top:4px;">'+c.sub+'</div>'
        +'</div>';
    }).join('');

    await loadStatsCharts(fromStr, toStr);

    // 영업일 = 기간 내 주말(토/일) 제외한 날 중 오늘까지
    const today=new Date(); today.setHours(0,0,0,0);
    const items = daily.items || [];
    let bizDays=0;
    items.forEach(function(row){
      const dateObj=new Date(row.date+'T00:00:00');
      const wd=dateObj.getDay();
      if(wd!==0&&wd!==6&&dateObj<=today) bizDays++;
    });
    const manualCodes = daily.manual_codes || [];
    const manualNames = daily.manual_names || {};

    let tbl='<div style="font-size:12px;color:#4B5563;margin-bottom:8px;">영업일: <b style="color:#111827;">'+bizDays+'일</b> (주말 제외 · 오늘까지 · 기간 '+fromStr+' ~ '+toStr+')</div>';

    const manualHeaderCols = manualCodes.map(function(code){ return '<th style="text-align:center;">'+( manualNames[code]||code)+'</th>'; }).join('');
    tbl+='<table class="data-table"><thead><tr>'
      +'<th>날짜</th>'
      +'<th style="text-align:center;">총 예약</th>'
      +'<th style="text-align:center;">총 완료</th>'
      +'<th style="text-align:center;">도수 예약</th>'
      +'<th style="text-align:center;">도수 완료</th>'
      +manualHeaderCols
      +'<th style="text-align:center;">체외충격파</th>'
      +'<th style="text-align:center;">취소</th>'
      +'</tr></thead><tbody>';
    let sumTotal=0,sumApproved=0,sumManual=0,sumManualApproved=0,sumEswt=0,sumCanceled=0;
    const sumByCode={};
    manualCodes.forEach(function(code){ sumByCode[code]=0; });
    items.forEach(function(row){
      const dateStr=row.date;
      const dObj=new Date(dateStr+'T00:00:00');
      const dow=['일','월','화','수','목','금','토'][dObj.getDay()];
      const isSat=dow==='토', isSun=dow==='일', isZero=row.total===0;
      sumTotal+=row.total; sumApproved+=row.approved;
      sumManual+=row.manual||0; sumManualApproved+=row.manual_approved||0;
      sumEswt+=row.eswt||0; sumCanceled+=row.canceled;
      manualCodes.forEach(function(code){ sumByCode[code]+=((row.manual_by_code||{})[code]||0); });
      let rowStyle='', dateStyle='';
      if(isSat){rowStyle='background:#EFF6FF;'; dateStyle='color:#1D4ED8;font-weight:700;';}
      else if(isSun){rowStyle='background:#FEF2F2;'; dateStyle='color:#DC2626;font-weight:700;';}
      if(isZero) rowStyle+='opacity:0.38;';
      function cv(v){ return v>0?v:'-'; }
      const manualDataCols=manualCodes.map(function(code){ return '<td style="text-align:center;">'+cv((row.manual_by_code||{})[code]||0)+'</td>'; }).join('');
      tbl+='<tr style="'+rowStyle+'">'
        +'<td style="white-space:nowrap;'+dateStyle+'">'+(dObj.getMonth()+1)+'/'+dObj.getDate()+' ('+dow+')</td>'
        +'<td style="text-align:center;">'+cv(row.total)+'</td>'
        +'<td style="text-align:center;">'+cv(row.approved)+'</td>'
        +'<td style="text-align:center;">'+cv(row.manual||0)+'</td>'
        +'<td style="text-align:center;">'+cv(row.manual_approved||0)+'</td>'
        +manualDataCols
        +'<td style="text-align:center;">'+cv(row.eswt||0)+'</td>'
        +'<td style="text-align:center;color:'+(row.canceled>0?'#EF4444':'inherit')+';">'+cv(row.canceled)+'</td>'
        +'</tr>';
    });
    const sumManualCodeCols=manualCodes.map(function(code){ return '<td style="text-align:center;">'+(sumByCode[code]||0)+'</td>'; }).join('');
    tbl+='<tr style="background:#EFF6FF;font-weight:700;">'
      +'<td>합계</td>'
      +'<td style="text-align:center;">'+sumTotal+'</td>'
      +'<td style="text-align:center;">'+sumApproved+'</td>'
      +'<td style="text-align:center;">'+sumManual+'</td>'
      +'<td style="text-align:center;">'+sumManualApproved+'</td>'
      +sumManualCodeCols
      +'<td style="text-align:center;">'+sumEswt+'</td>'
      +'<td style="text-align:center;color:#EF4444;">'+sumCanceled+'</td>'
      +'</tr></tbody></table>';

    document.getElementById('stats-table').innerHTML=tbl;
    document.getElementById('stats-loading').style.display='none';
    document.getElementById('stats-body').style.display='block';
    // 새로고침마다 날짜별 통계표는 기본 접힘 상태로 리셋
    _setDailyStatsTableCollapsed(true);
  }catch(e){
    document.getElementById('stats-loading').textContent='불러오기 실패: '+e.message;
  }
}

// ─────── 날짜별 통계표 접기/펼치기 ───────
function _setDailyStatsTableCollapsed(collapsed){
  const wrap  = document.getElementById('stats-table-wrap');
  const caret = document.getElementById('stats-table-caret');
  const hint  = document.getElementById('stats-table-hint');
  if(!wrap) return;
  if(collapsed){
    wrap.style.display = 'none';
    if(caret){ caret.textContent = '▶'; caret.style.transform = ''; }
    if(hint){ hint.textContent = '— 클릭하면 펼쳐집니다'; }
  } else {
    wrap.style.display = 'block';
    if(caret){ caret.textContent = '▼'; }
    if(hint){ hint.textContent = '— 클릭하면 접힙니다'; }
  }
}
function toggleDailyStatsTable(){
  const wrap = document.getElementById('stats-table-wrap');
  if(!wrap) return;
  const isCollapsed = (wrap.style.display === 'none' || !wrap.style.display);
  _setDailyStatsTableCollapsed(!isCollapsed);
}

// ─────── 관리자 > AI 설정 ───────

function _aiEsc(s){
  return String(s==null?'':s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

async function loadAiSettingForm(){
  if(!await ensureAdmin()){
    document.getElementById('ai-setting-form').innerHTML = '<p class="muted">인증 필요</p>';
    return;
  }
  const r = await adminFetch('/api/ai/settings');
  if(!r.ok){
    document.getElementById('ai-setting-form').innerHTML = '<p class="muted">불러오기 실패 (' + r.status + ')</p>';
    return;
  }
  const s = await r.json();
  const prov = s.provider || 'openai';
  const masked = _aiEsc(s.api_key_masked || '');
  const model = _aiEsc(s.model || '');

  const openaiKeyHint = (s.api_key_set && prov==='openai')
    ? ('저장됨 (' + masked + ') · 변경하려면 새 키 입력')
    : 'sk-...';
  const anthroKeyHint = (s.api_key_set && prov==='anthropic')
    ? ('저장됨 (' + masked + ') · 변경하려면 새 키 입력')
    : 'sk-ant-...';

  document.getElementById('ai-setting-form').innerHTML = `
    <div class="settings-card">
      <div class="settings-card-head">
        <h3>🤖 AI 기능 설정</h3>
        <small class="muted">예약문자 초안 / 업무매뉴얼 검색 등 LLM 기반 기능</small>
      </div>

      <div class="sf-row">
        <label class="sf-label">기능 사용</label>
        <label style="display:flex;align-items:center;gap:6px;">
          <input type="checkbox" id="ai-enabled" ${s.enabled?'checked':''}>
          <span>AI 기능 ON/OFF <small class="muted">(기본 OFF)</small></span>
        </label>
      </div>

      <hr class="sf-sep">

      <div class="sf-row">
        <label class="sf-label">Provider</label>
        <select id="ai-provider">
          <option value="openai" ${prov==='openai'?'selected':''}>OpenAI</option>
          <option value="anthropic" ${prov==='anthropic'?'selected':''}>Anthropic (Claude)</option>
          <option value="local" disabled>Local (v2 보류)</option>
        </select>
      </div>

      <div id="ai-openai-block" style="${prov==='openai'?'':'display:none;'}">
        <div class="sf-row">
          <label class="sf-label">OpenAI 모델</label>
          <input id="ai-openai-model" list="ai-openai-models" value="${prov==='openai'?model:''}" placeholder="gpt-4o-mini">
          <datalist id="ai-openai-models">
            <option value="gpt-4o-mini">
            <option value="gpt-4o">
            <option value="gpt-4-turbo">
          </datalist>
        </div>
        <div class="sf-row">
          <label class="sf-label">OpenAI API Key</label>
          <input id="ai-openai-key" type="password" autocomplete="off" placeholder="${_aiEsc(openaiKeyHint)}">
        </div>
      </div>

      <div id="ai-anthropic-block" style="${prov==='anthropic'?'':'display:none;'}">
        <div class="sf-row">
          <label class="sf-label">Anthropic 모델</label>
          <input id="ai-anthropic-model" list="ai-anthropic-models" value="${prov==='anthropic'?model:''}" placeholder="claude-haiku-4-5">
          <datalist id="ai-anthropic-models">
            <option value="claude-haiku-4-5">
            <option value="claude-sonnet-4-6">
            <option value="claude-opus-4-7">
          </datalist>
        </div>
        <div class="sf-row">
          <label class="sf-label">Anthropic API Key</label>
          <input id="ai-anthropic-key" type="password" autocomplete="off" placeholder="${_aiEsc(anthroKeyHint)}">
        </div>
      </div>

      <hr class="sf-sep">

      <div class="sf-actions">
        <button class="primary" onclick="saveAiSetting()">💾 저장</button>
        <button class="small" onclick="testAiConnection()">🔌 연결 테스트</button>
      </div>
    </div>

    <div class="settings-card" style="margin-top:14px;background:#FEF9E7;border-color:#F5DC8B;">
      <div class="settings-card-head"><h3 style="color:#9A6F00;">🔒 개인정보 보호 안내</h3></div>
      <ul style="margin:6px 0 0 18px;padding:0;font-size:13px;line-height:1.7;color:#5A4A00;">
        <li>전화번호 전송 금지</li>
        <li>생년월일 전송 금지</li>
        <li>차트번호 전송 금지</li>
        <li>환자/예약 메모 전송 금지</li>
        <li>직원 개인정보 전송 금지</li>
      </ul>
      <small class="muted" style="display:block;margin-top:8px;">
        ※ PII 가드는 백엔드에서 토큰화로 자동 차단됩니다 (기본 ON). 환자명은 토큰('환자A')으로 LLM에 전달되며, 응답에서 실명을 복원합니다.
      </small>
    </div>`;

  document.getElementById('ai-provider').addEventListener('change', e => {
    const p = e.target.value;
    document.getElementById('ai-openai-block').style.display    = (p==='openai')    ? '' : 'none';
    document.getElementById('ai-anthropic-block').style.display = (p==='anthropic') ? '' : 'none';
  });

  loadAiHealthBox();
}

async function saveAiSetting(){
  const prov = _v('ai-provider');
  const body = {
    enabled: document.getElementById('ai-enabled').checked,
    provider: prov,
  };
  if(prov === 'openai'){
    body.model = _v('ai-openai-model');
    const k = _v('ai-openai-key');
    if(k) body.api_key = k;
  } else if(prov === 'anthropic'){
    body.model = _v('ai-anthropic-model');
    const k = _v('ai-anthropic-key');
    if(k) body.api_key = k;
  }
  const r = await adminFetch('/api/ai/settings', {
    method:'PUT',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body),
  });
  if(!r.ok){ alert('저장 실패\n' + await r.text()); return; }
  alert('저장되었습니다.');
  loadAiSettingForm();
}

async function loadAiHealthBox(){
  const box = document.getElementById('ai-health-box');
  if(!box) return;
  const r = await adminFetch('/api/ai/health');
  if(!r.ok){ box.innerHTML = '<p class="muted">상태 조회 실패 (' + r.status + ')</p>'; return; }
  const h = await r.json();
  const sdkOk = !!(h.sdk_installed && h.sdk_installed[h.provider]);
  const sdkErr = (h.sdk_errors && h.sdk_errors[h.provider]) || '';
  const docCount = (typeof h.knowledge_doc_count === 'number') ? h.knowledge_doc_count : 0;
  const smsDraftReady = !!h.ready;
  const manualSearchReady = docCount > 0;

  let warn = '';
  if(!h.enabled){
    warn = '<p class="muted" style="color:#D7625C;margin:0 0 10px;">⚠ AI 기능이 꺼져 있습니다. 위에서 ON 으로 변경 후 저장하세요.</p>';
  } else if(!h.api_key_set){
    warn = '<p class="muted" style="color:#D7625C;margin:0 0 10px;">⚠ API Key 가 설정되지 않았습니다.</p>';
  }

  let sdkLine;
  if(sdkOk){
    sdkLine = '✅ '+_aiEsc(h.provider)+' SDK 사용 가능';
  } else if(sdkErr){
    const shortErr = sdkErr.length > 80 ? sdkErr.slice(0, 80) + '…' : sdkErr;
    sdkLine = '⛔ '+_aiEsc(h.provider)+' SDK 미설치 <span class="muted" style="font-size:11px;">('+_aiEsc(shortErr)+')</span>';
  } else {
    sdkLine = '⛔ '+_aiEsc(h.provider)+' SDK 미설치';
  }

  box.innerHTML = warn + `
    <div style="display:grid;grid-template-columns:160px 1fr;gap:6px 14px;font-size:13px;">
      <div class="muted">AI 기능</div>          <div>${h.enabled ? '✅ ON' : '⛔ OFF'}</div>
      <div class="muted">Provider</div>         <div>${_aiEsc(h.provider || '-')}</div>
      <div class="muted">모델</div>             <div>${h.model ? _aiEsc(h.model) : '<span class="muted">미설정</span>'}</div>
      <div class="muted">API Key 설정</div>     <div>${h.api_key_set ? '✅ 설정됨' : '⛔ 미설정'}</div>
      <div class="muted">SDK 설치</div>         <div>${sdkLine}</div>
      <div class="muted">knowledge 문서</div>   <div>${docCount} 개</div>
      <div class="muted">SMS draft</div>        <div>${smsDraftReady ? '✅ 사용 가능' : '⛔ 추가 설정 필요'}</div>
      <div class="muted">manual search</div>   <div>${manualSearchReady ? '✅ 사용 가능 ('+docCount+'개 문서)' : '⛔ 인덱스 비어있음'}</div>
      <div class="muted">전체 준비</div>        <div>${h.ready ? '✅ 사용 가능' : '⛔ 추가 설정 필요'}</div>
    </div>`;
}

async function testAiConnection(){
  const r = await adminFetch('/api/ai/health');
  if(!r.ok){ alert('연결 테스트 실패: ' + r.status); return; }
  const h = await r.json();
  const sdkOk = !!(h.sdk_installed && h.sdk_installed[h.provider]);
  const sdkErr = (h.sdk_errors && h.sdk_errors[h.provider]) || '';
  const docCount = (typeof h.knowledge_doc_count === 'number') ? h.knowledge_doc_count : 0;
  let msg = '[연결 테스트 결과]\n\n';
  msg += '· AI 기능: ' + (h.enabled ? 'ON' : 'OFF') + '\n';
  msg += '· Provider: ' + (h.provider || '-') + '\n';
  msg += '· 모델: ' + (h.model || '미설정') + '\n';
  msg += '· API Key: ' + (h.api_key_set ? '설정됨' : '미설정') + '\n';
  msg += '· SDK: ' + (sdkOk ? '사용 가능' : '미설치') + '\n';
  if(!sdkOk && sdkErr){
    const shortErr = sdkErr.length > 160 ? sdkErr.slice(0, 160) + '…' : sdkErr;
    msg += '   └ 사유: ' + shortErr + '\n';
  }
  msg += '· knowledge 문서: ' + docCount + '개\n';
  msg += '· SMS draft: ' + (h.ready ? '사용 가능' : '추가 설정 필요') + '\n';
  msg += '· manual search: ' + (docCount > 0 ? '사용 가능' : '인덱스 비어있음') + '\n';
  msg += '· 전체 준비: ' + (h.ready ? '사용 가능' : '추가 설정 필요') + '\n';
  if(!h.ready){
    const missing = [];
    if(!h.enabled) missing.push('기능 ON 토글');
    if(!h.api_key_set) missing.push('API Key 입력');
    if(!h.model) missing.push('모델명 입력');
    if(!sdkOk) missing.push((h.provider||'') + ' SDK 설치');
    if(missing.length) msg += '\n부족 항목: ' + missing.join(', ');
  }
  msg += '\n\n※ v1: 실제 LLM 호출은 하지 않고 설정/SDK 점검만 수행합니다.';
  alert(msg);
  loadAiHealthBox();
}


// ─────── 관리자 > 버전 / 업데이트 확인 ───────

// /api/about 응답 캐시 — checkUpdate 가 다운로드/설치 버튼을 렌더할 때
// is_frozen 여부 참조해 dev 모드면 disabled 처리. 매번 about 재호출 안 해도 되게.
let _LAST_ABOUT = null;

function maybeShowUpdateCompletedNotice(a){
  const info = a && a.update_completed;
  if(!info || !info.version) return;
  const key = 'dosu-update-completed-' + info.version;
  try {
    if(sessionStorage.getItem(key) === '1') return;
    sessionStorage.setItem(key, '1');
  } catch(e) {}
  alert(info.message || ('업데이트가 완료되었습니다.\n현재 버전은 v' + info.version + '입니다.'));
}

async function loadAboutBox(){
  const box = document.getElementById('about-box');
  if(!box) return;
  try {
    const a = await (await fetch('/api/about')).json();
    _LAST_ABOUT = a;
    maybeShowUpdateCompletedNotice(a);
    // is_frozen 누락 시(구 백엔드 호환) 안전하게 true 로 간주 — 빌드본 기준 동작 유지
    const isFrozen = (a.is_frozen !== false);
    const devBanner = isFrozen ? '' : `
      <div style="margin-top:14px;padding:12px 14px;background:#FFFBEB;border:1px solid #FCD34D;border-radius:10px;font-size:13px;color:#92400E;line-height:1.7;">
        <div style="font-weight:700;margin-bottom:4px;">⚠️ 개발 모드 (dev / uvicorn) 환경입니다</div>
        <div>자동 업데이트는 빌드된 exe(메인서버)에서만 동작합니다. 여기서는 "다운로드 / 지금 설치" 버튼을 눌러도 차단됩니다 — <b>메인서버에서 업데이트 해주세요.</b></div>
      </div>
    `;
    box.innerHTML = `
      <div style="display:grid;grid-template-columns:auto 1fr;gap:8px 16px;font-size:13px;align-items:center;">
        <span class="muted">앱 이름</span><b>${a.app_name}</b>
        <span class="muted">현재 버전</span><b style="color:#2F86CB;font-size:15px;">v${a.version}</b>
        <span class="muted">빌드 날짜</span><span>${a.build_date}</span>
        <span class="muted">실행 환경</span>${isFrozen ? '<span style="color:#3BA67D;">● 빌드본 (exe)</span>' : '<span style="color:#92400E;">● 개발 모드 (dev / uvicorn)</span>'}
        <span class="muted">데이터 폴더</span><code style="font-size:12px;background:#F3F4F6;padding:2px 6px;border-radius:4px;word-break:break-all;">${a.data_dir}</code>
        <span class="muted">백업 폴더</span><code style="font-size:12px;background:#F3F4F6;padding:2px 6px;border-radius:4px;word-break:break-all;">${a.backup_dir}</code>
      </div>

      ${devBanner}

      <div style="margin-top:14px;padding:12px;background:#FAFCFE;border:1px solid #E5EDF5;border-radius:10px;">
        <div style="font-size:13px;font-weight:600;color:#3D4A5C;margin-bottom:8px;">업데이트 매니페스트 URL <span class="muted" style="font-weight:normal;font-size:12px;">(선택 — 비워두면 수동 교체 방식)</span></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
          <input id="update-url-input" type="text" style="flex:1;min-width:220px;padding:7px 10px;border:1px solid #E5EDF5;border-radius:8px;font-size:13px;"
                 value="${(a.update_manifest_url||'').replace(/"/g,'&quot;')}" placeholder="https://example.com/dosu-clinic/manifest.json">
          <button class="mini" onclick="saveUpdateUrl()">URL 저장</button>
        </div>
        <p class="muted" style="font-size:11px;margin:8px 0 0;line-height:1.5;">
          매니페스트 형식 예: <code>{"version":"1.2.3","download_url":"...","notes":"...","mandatory":false}</code>
        </p>
      </div>

      <div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
        <button class="primary" onclick="checkUpdate()">업데이트 확인</button>
        <span id="update-result" class="muted" style="font-size:13px;"></span>
      </div>

      <p class="muted" style="font-size:12px;margin-top:14px;line-height:1.5;">
        ※ 업데이트 방법: 새 버전 ZIP 을 받아 프로그램 폴더 전체를 교체하세요.
        데이터 폴더(<code style="font-size:11px;">${a.data_dir}</code>)는 교체하지 않으므로 환자·예약·설정은 그대로 유지됩니다.
      </p>
    `;
  } catch(e){
    box.innerHTML = `<p class="muted">버전 정보 조회 실패: ${e.message}</p>`;
  }
}

async function saveUpdateUrl(){
  const el = document.getElementById('update-url-input');
  if(!el) return;
  const url = el.value.trim();
  try {
    const r = await adminFetch('/api/config', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ update_manifest_url: url }),
    });
    if(!r.ok){ alert('저장 실패: ' + await r.text()); return; }
    const res = document.getElementById('update-result');
    if(res) res.innerHTML = `<span style="color:#3BA67D;">✓ URL 저장됨</span>`;
  } catch(e){ alert('저장 실패: ' + e.message); }
}

// 최근 check-update 결과 캐시 — 다운로드/설치 버튼에서 참조
let _LAST_UPDATE_CHECK = null;

async function checkUpdate(){
  const r = document.getElementById('update-result');
  if(r) r.textContent = '확인 중...';
  try {
    const url = (document.getElementById('update-url-input')?.value || '').trim();
    const res = await adminFetch('/api/about/check-update', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ update_manifest_url: url }),
    });
    if(!res.ok){
      if(r) r.textContent = '요청 실패: ' + await res.text();
      return;
    }
    const d = await res.json();
    _LAST_UPDATE_CHECK = d;
    if(d.configured === false){
      if(r) r.innerHTML = `<span style="color:#4B5563;">${d.message}</span>`;
      return;
    }
    if(d.error){
      if(r) r.innerHTML = `<span style="color:#B74841;">⚠ ${d.error}</span>`;
      return;
    }
    if(d.up_to_date){
      if(r) r.innerHTML = `<span style="color:#3BA67D;">✓ 최신 버전입니다 (v${d.current_version})</span>`;
      return;
    }
    if(d.available){
      const notes = d.notes ? `<div style="margin-top:8px;padding:10px;background:#F9FAFB;border-radius:6px;font-size:12px;line-height:1.6;color:#374151;white-space:pre-wrap;">${d.notes.replace(/</g,'&lt;').replace(/>/g,'&gt;')}</div>` : '';
      const mandatoryTag = d.mandatory ? ' <span style="background:#FEE2E2;color:#B74841;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;">필수 업데이트</span>' : '';
      const shaBadge = d.sha256 ? ' <span class="muted" style="font-size:11px;">(SHA256 검증 지원)</span>' : '';
      const dlLink = d.download_url ? ` · <a href="${d.download_url}" target="_blank" rel="noopener" style="font-size:12px;">수동 다운로드</a>` : '';
      // dev 모드면 다운로드 버튼은 disabled — _is_frozen() 가드로 백엔드에서 어차피 400 차단됨.
      const isFrozen = !(_LAST_ABOUT && _LAST_ABOUT.is_frozen === false);
      const dlBtnHtml = isFrozen
        ? `<button class="primary" onclick="downloadUpdate()">⬇ 업데이트 다운로드</button>`
        : `<button class="primary" disabled title="메인서버(빌드된 exe)에서 업데이트 해주세요" style="opacity:0.5;cursor:not-allowed;">⬇ 업데이트 다운로드 (dev 차단)</button>`;
      const devNote = isFrozen ? '' : `<span class="muted" style="font-size:12px;color:#92400E;">메인서버에서 업데이트 해주세요</span>`;
      if(r) r.innerHTML = `
        <div style="margin-bottom:10px;">
          <span style="color:#2F86CB;">● 새 버전 <b>v${d.latest_version}</b> 사용 가능</span>
          <span class="muted" style="font-size:12px;"> · 현재 v${d.current_version}</span>
          ${mandatoryTag}${shaBadge}${dlLink}
        </div>
        ${notes}
        <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
          ${dlBtnHtml}
          <span id="update-download-status" class="muted" style="font-size:12px;">${devNote}</span>
        </div>
        <div id="update-install-zone" style="margin-top:10px;"></div>
      `;
    }
  } catch(e){
    if(r) r.textContent = '오류: ' + e.message;
  }
}

async function downloadUpdate(){
  if(_LAST_ABOUT && _LAST_ABOUT.is_frozen === false){
    alert('개발 모드(dev / uvicorn)에서는 자동 업데이트가 지원되지 않습니다.\n메인서버(빌드된 exe)에서 업데이트 해주세요.');
    return;
  }
  if(!_LAST_UPDATE_CHECK || !_LAST_UPDATE_CHECK.available){
    alert('먼저 "업데이트 확인"을 눌러 새 버전을 조회하세요.'); return;
  }
  const s = document.getElementById('update-download-status');
  const zone = document.getElementById('update-install-zone');
  if(s) s.textContent = '다운로드 중... (ZIP 크기에 따라 20~60초)';
  if(zone) zone.innerHTML = '';
  try {
    const res = await adminFetch('/api/about/download-update', {method:'POST'});
    const txt = await res.text();
    let data = {};
    try { data = JSON.parse(txt); } catch(e){ data = { error: txt }; }
    if(!res.ok){
      if(s) s.innerHTML = `<span style="color:#B74841;">⚠ ${data.detail || data.error || txt}</span>`;
      return;
    }
    const verify = (data.sha256_matched === true)
      ? '<span style="color:#3BA67D;">✓ SHA256 검증 완료</span>'
      : (data.sha256_matched === null ? '<span class="muted">(SHA256 제공 안됨 — 무결성 미검증)</span>' : '');
    if(s) s.innerHTML = `<span style="color:#3BA67D;">✓ 다운로드 완료 (${data.size_mb} MB)</span> ${verify}`;
    if(zone) zone.innerHTML = `
      <div style="margin-top:6px;padding:12px;background:#FFFBEB;border:1px solid #FCD34D;border-radius:8px;">
        <div style="font-size:13px;font-weight:600;color:#92400E;margin-bottom:6px;">⚠️ 업데이트 설치 주의사항</div>
        <div style="font-size:12px;color:#78350F;line-height:1.7;">
          • 클릭하면 약 15~20초간 프로그램이 재시작됩니다<br>
          • 진료 중이 아닌 시간(점심·퇴근 후)에 진행하세요<br>
          • 다른 PC/폰에서 접속 중이라면 잠시 끊겼다가 자동 복구됩니다<br>
          • 업데이트 실패 시 자동으로 이전 버전으로 복구됩니다
        </div>
        <button class="primary" style="margin-top:10px;background:#D97706;" onclick="applyUpdate()">✔ 지금 설치 (재시작)</button>
      </div>
    `;
  } catch(e){
    if(s) s.innerHTML = `<span style="color:#B74841;">⚠ 오류: ${e.message}</span>`;
  }
}

async function applyUpdate(){
  // dev 모드는 백엔드에서 _is_frozen() 가드로 어차피 400 차단되지만,
  // confirm 띄우기 전에 미리 안내해 헛클릭 방지.
  if(_LAST_ABOUT && _LAST_ABOUT.is_frozen === false){
    alert('개발 모드(dev / uvicorn)에서는 자동 업데이트가 지원되지 않습니다.\n메인서버(빌드된 exe)에서 업데이트 해주세요.');
    return;
  }
  if(!confirm('업데이트를 지금 설치하시겠습니까?\n\n• 설치 직전 DB가 자동 백업됩니다.\n• 진행 중 화면은 업데이트 안내 화면으로 바뀌고, 새 버전이 준비되면 자동 새로고침됩니다.')) return;
  try {
    const res = await adminFetch('/api/about/apply-update', {method:'POST'});
    if(!res.ok){
      const t = await res.text();
      alert('업데이트 실행 실패: ' + t); return;
    }
    let data = {};
    try { data = await res.json(); } catch(e){}
    const backup = data.backup || {};
    const updaterLogPath = data.updater_log_path || '%TEMP%\\도수치료예약_updater.log';

    // 백업 결과 박스 (성공/실패 모두 노출 — 투명성)
    let backupBox = '';
    if(backup.ok){
      backupBox = `
        <div style="margin-top:16px;padding:12px;background:#ECFDF5;border:1px solid #A7F3D0;border-radius:8px;font-size:12px;color:#065F46;line-height:1.6;text-align:left;">
          <div style="font-weight:700;margin-bottom:4px;">✅ 업데이트 전 DB 자동 백업 완료</div>
          <div>파일: <code style="font-size:11px;">${backup.filename||'-'}</code></div>
          <div>크기: ${backup.size_mb || 0} MB · 위치: <b>자동 백업 폴더</b></div>
          <div style="margin-top:4px;color:#047857;">문제 생기면 이 백업으로 언제든 복구 가능합니다.</div>
        </div>
      `;
    } else if(backup.error){
      backupBox = `
        <div style="margin-top:16px;padding:12px;background:#FFFBEB;border:1px solid #FCD34D;border-radius:8px;font-size:12px;color:#92400E;line-height:1.6;text-align:left;">
          <div style="font-weight:700;margin-bottom:4px;">⚠️ 자동 백업은 실패했지만 업데이트는 진행됩니다</div>
          <div class="muted" style="color:#78350F;">사유: ${backup.error}</div>
          <div style="margin-top:4px;">데이터 폴더(%APPDATA%\\도수치료예약\\) 는 업데이트의 영향을 받지 않으므로 안전합니다.</div>
        </div>
      `;
    }

    // 업데이트 진행 안내 페이지로 전환 (서버가 곧 꺼지므로 이후 요청은 실패)
    document.body.innerHTML = `
      <div style="max-width:560px;margin:60px auto;padding:30px;background:#fff;border-radius:12px;box-shadow:0 4px 24px rgba(0,0,0,0.08);font-family:system-ui;text-align:center;">
        <div style="font-size:48px;margin-bottom:16px;">🔄</div>
        <h2 style="margin:0 0 10px;color:#1F2937;">업데이트 진행 중</h2>
        <p style="color:#4B5563;line-height:1.7;">
          프로그램이 종료되고 업데이트가 적용됩니다.<br>
          새 버전이 준비되면 이 페이지가 <b>자동 새로고침</b> 됩니다.
        </p>
        ${backupBox}
        <div style="margin-top:20px;padding:12px;background:#F3F4F6;border-radius:6px;font-size:12px;color:#4B5563;line-height:1.6;">
          이 화면은 서버가 다시 뜰 때까지 유지됩니다.<br>
          업데이터 창이 별도로 떠서 자동으로 닫힙니다.
        </div>

        <!-- 30초 경과 시 표시 -->
        <div id="upd-warn30" style="display:none;margin-top:16px;padding:12px;background:#FFFBEB;border:1px solid #FCD34D;border-radius:8px;font-size:13px;color:#92400E;line-height:1.6;text-align:left;">
          <div style="font-weight:700;margin-bottom:6px;">⏳ 진행이 평소보다 오래 걸리고 있어요</div>
          <div>30초가 넘었습니다. 어디서 멈췄는지 업데이터 로그를 확인할 수 있습니다.</div>
          <button onclick="showUpdateLog()" style="margin-top:8px;padding:6px 14px;background:#F59E0B;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:600;">업데이터 로그 보기</button>
        </div>

        <!-- 60초 경과 시 표시 -->
        <div id="upd-warn60" style="display:none;margin-top:12px;padding:12px;background:#FEF2F2;border:1px solid #FCA5A5;border-radius:8px;font-size:12px;color:#991B1B;line-height:1.7;text-align:left;">
          <div style="font-weight:700;margin-bottom:6px;">⚠️ 업데이트가 멈춰 있을 수 있습니다</div>
          <div>다음을 순서대로 시도하세요:</div>
          <ol style="margin:6px 0 0 18px;padding:0;">
            <li>위 "업데이터 로그 보기" 버튼으로 마지막 단계 확인</li>
            <li>작업표시줄에 "도수치료예약 업데이트 진행 중..." 콘솔 창이 떠 있는지 확인 — 떠 있다면 그 창의 메시지를 따르세요</li>
            <li>로그 파일을 직접 열기: <code style="font-size:11px;background:#fff;padding:1px 4px;border-radius:3px;">${updaterLogPath}</code></li>
            <li>여전히 안 되면 작업관리자에서 "도수치료예약" 프로세스를 모두 종료한 뒤, 프로그램 폴더에서 <b>도수치료예약.exe</b> 를 다시 실행하세요. 롤백이 자동 적용되어 이전 버전으로 복구됩니다.</li>
          </ol>
        </div>

        <!-- 6분 (자동 폴링 한계) 경과 시 표시 — 자동 새로고침이 더 이상 안 됨을 알려줌 -->
        <div id="upd-warn-timeout" style="display:none;margin-top:12px;padding:12px;background:#1F2937;color:#F9FAFB;border-radius:8px;font-size:12px;line-height:1.7;text-align:left;">
          <div style="font-weight:700;margin-bottom:6px;">⏹ 자동 새로고침을 더 이상 시도하지 않습니다 (6분 경과)</div>
          <div style="color:#D1D5DB;">서버에서 응답이 없습니다. 새 버전이 떴는지 직접 확인이 필요합니다.</div>
          <div style="margin-top:8px;">
            <button onclick="window.location.reload()" style="padding:6px 14px;background:#3B82F6;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:600;">지금 새로고침</button>
            <button onclick="showUpdateLog()" style="margin-left:6px;padding:6px 14px;background:transparent;color:#F9FAFB;border:1px solid #6B7280;border-radius:6px;cursor:pointer;">로그 보기</button>
          </div>
          <div style="margin-top:8px;color:#4B5563;font-size:11px;">
            ※ 새로고침 후 페이지가 안 열리면 작업관리자에서 "도수치료예약" 프로세스를 모두 종료하고 프로그램 폴더의 <b>도수치료예약.exe</b> 를 다시 실행하세요.
          </div>
        </div>
      </div>

      <!-- 로그 모달 -->
      <div id="upd-log-modal" style="display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);z-index:9999;padding:40px 20px;overflow:auto;">
        <div style="max-width:760px;margin:0 auto;background:#fff;border-radius:10px;padding:20px;font-family:system-ui;">
          <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #E5E7EB;padding-bottom:10px;margin-bottom:12px;">
            <h3 id="upd-log-title" style="margin:0;color:#1F2937;font-size:16px;">업데이터 로그</h3>
            <button onclick="document.getElementById('upd-log-modal').style.display='none'" style="padding:4px 12px;border:1px solid #D1D5DB;background:#fff;border-radius:6px;cursor:pointer;">닫기</button>
          </div>
          <pre id="upd-log-body" style="background:#1F2937;color:#E5E7EB;padding:12px;border-radius:6px;font-size:12px;line-height:1.5;max-height:60vh;overflow:auto;white-space:pre-wrap;word-break:break-all;margin:0;">로그 불러오는 중...</pre>
          <div id="upd-log-footer" style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;"></div>
        </div>
      </div>
    `;

    // 30초/60초 경과 안내 표시
    setTimeout(function(){
      const el = document.getElementById('upd-warn30');
      if(el) el.style.display = 'block';
    }, 30000);
    setTimeout(function(){
      const el = document.getElementById('upd-warn60');
      if(el) el.style.display = 'block';
    }, 60000);

    // 새 서버 health-check 폴링 — 떠오르면 자동 새로고침.
    // /api/treatments 는 인증 불필요한 가벼운 GET (smoke test 에서도 사용).
    let healthTries = 0;
    const healthInterval = setInterval(async function(){
      healthTries += 1;
      // 6분 (72회) 후에는 폴링 중단 — 무한 반복 방지.
      // silent 종료하면 사용자가 무한정 기다리게 되므로 마지막 안내 박스 노출.
      if(healthTries > 72){
        clearInterval(healthInterval);
        const elTimeout = document.getElementById('upd-warn-timeout');
        if(elTimeout) elTimeout.style.display = 'block';
        return;
      }
      try {
        const r = await fetch('/api/treatments', { cache: 'no-store' });
        if(r && (r.ok || r.status === 401 || r.status === 403)){
          clearInterval(healthInterval);
          // 잠시 후 새로고침 (응답 직후 reload 하면 새 인스턴스 startup 중일 수 있음)
          setTimeout(function(){ window.location.reload(); }, 1500);
        }
      } catch(e){
        // 서버가 죽어있는 정상 상태 — 다음 시도 대기
      }
    }, 5000);

    // "업데이터 로그 보기" 버튼 핸들러 — window 에 노출 (인라인 onclick 에서 호출)
    //
    // 동작 흐름:
    //   1) 즉시 1차 fetch — 성공하면 그대로 렌더 (드물게 새 서버가 이미 떠 있는 경우)
    //   2) 실패 시 2초 간격 × 5회(=10초) 자동 재시도 — "재시작 중" 진행 표시
    //   3) 그래도 실패하면 fallback 뷰: "오류" 라는 단어 빼고, 진행 중임을 명확히 안내 +
    //      로그 파일 경로 복사 / 다시 시도 버튼 제공
    //   4) 모달이 닫히면 진행 중 setTimeout 체인 즉시 중단 (가드)
    window.showUpdateLog = async function(){
      const modal = document.getElementById('upd-log-modal');
      const body = document.getElementById('upd-log-body');
      const footer = document.getElementById('upd-log-footer');
      const title = document.getElementById('upd-log-title');
      if(!modal || !body) return;
      modal.style.display = 'block';
      if(title) title.textContent = '업데이터 로그';
      if(footer) footer.innerHTML = '';
      body.textContent = '로그 불러오는 중...';

      // 모달이 닫혀 있으면 후속 작업 중단 — setTimeout 체인 안전장치
      const isOpen = function(){ return modal.style.display !== 'none'; };

      // 한 번의 fetch 시도. 성공: 렌더 후 true, 실패(네트워크/HTTP): false 반환.
      const tryFetchOnce = async function(){
        try {
          const r = await adminFetch('/api/about/update-log');
          if(!r.ok) return false;
          const j = await r.json();
          if(!isOpen()) return true;
          if(!j.exists){
            body.textContent = '로그 파일이 아직 생성되지 않았습니다.\n경로: ' + (j.path || updaterLogPath) + '\n\n'
              + 'updater.bat 가 시작 전이거나, 경로가 다를 수 있습니다.';
            renderRetryFooter();
            return true;
          }
          const head = '[파일] ' + j.path
            + '\n[수정시각] ' + (j.mtime || '-')
            + '\n[크기] ' + (j.size_bytes || 0) + ' bytes'
            + '\n[줄 수] ' + (j.total_lines || (j.lines||[]).length)
            + '\n──────────────────────────────────────────\n';
          body.textContent = head + (j.lines || []).join('\n');
          renderRetryFooter();
          return true;
        } catch(e){
          return false;
        }
      };

      // 클립보드 복사 — secure context 가 아닐 때를 대비해 textarea fallback 포함.
      const copyPath = async function(btn){
        const path = updaterLogPath;
        let ok = false;
        try {
          if(navigator.clipboard && window.isSecureContext){
            await navigator.clipboard.writeText(path);
            ok = true;
          }
        } catch(e){ /* fallback */ }
        if(!ok){
          try {
            const ta = document.createElement('textarea');
            ta.value = path;
            ta.style.position = 'fixed';
            ta.style.opacity = '0';
            document.body.appendChild(ta);
            ta.select();
            ok = document.execCommand('copy');
            document.body.removeChild(ta);
          } catch(e){ ok = false; }
        }
        if(btn){
          const orig = btn.textContent;
          btn.textContent = ok ? '✓ 복사됨' : '⚠ 복사 실패 — 직접 선택해 주세요';
          btn.disabled = true;
          setTimeout(function(){
            if(!isOpen()) return;
            btn.textContent = orig;
            btn.disabled = false;
          }, 1500);
        }
      };

      // 정상 응답 후에도 "다시 시도" 정도는 노출 — 로그가 갱신됐는지 다시 보고 싶을 때 사용.
      const renderRetryFooter = function(){
        if(!footer) return;
        footer.innerHTML = '';
        const retryBtn = document.createElement('button');
        retryBtn.textContent = '🔁 다시 불러오기';
        retryBtn.style.cssText = 'padding:6px 14px;background:#fff;color:#374151;border:1px solid #D1D5DB;border-radius:6px;cursor:pointer;font-size:12px;';
        retryBtn.onclick = function(){ window.showUpdateLog(); };
        footer.appendChild(retryBtn);
      };

      // fallback 뷰 — 5회 재시도 모두 실패 시.
      const renderFallback = function(){
        if(!isOpen()) return;
        if(title) title.textContent = '업데이터 로그 — 서버 재시작 중';
        body.textContent =
          '⏸ 서버가 아직 재시작 중이에요\n'
          + '업데이트가 진행 중이라 로그 조회 API 가 잠시 응답하지 않습니다.\n'
          + '로그 파일을 직접 열면 진행 상황을 확인할 수 있어요.\n\n'
          + '[파일 경로]\n'
          + '  ' + updaterLogPath + '\n\n'
          + '[여는 방법]\n'
          + '  1) 아래 "경로 복사" 버튼을 누른다\n'
          + '  2) 파일 탐색기 주소창에 붙여넣고 Enter\n'
          + '     (또는 Win+R → 붙여넣기 → 확인)';
        if(!footer) return;
        footer.innerHTML = '';
        const copyBtn = document.createElement('button');
        copyBtn.textContent = '📋 경로 복사';
        copyBtn.style.cssText = 'padding:6px 14px;background:#2F86CB;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:600;';
        copyBtn.onclick = function(){ copyPath(copyBtn); };
        const retryBtn = document.createElement('button');
        retryBtn.textContent = '🔁 다시 시도';
        retryBtn.style.cssText = 'padding:6px 14px;background:#fff;color:#374151;border:1px solid #D1D5DB;border-radius:6px;cursor:pointer;';
        retryBtn.onclick = function(){ window.showUpdateLog(); };
        footer.appendChild(copyBtn);
        footer.appendChild(retryBtn);
      };

      // 1차 즉시 시도
      if(await tryFetchOnce()) return;
      if(!isOpen()) return;

      // 자동 재시도 (2초 × 5회)
      const MAX_RETRY = 5;
      const INTERVAL_MS = 2000;
      for(let i = 1; i <= MAX_RETRY; i++){
        if(!isOpen()) return;
        body.textContent =
          '⏳ 서버 재시작 대기 중... (재시도 ' + i + '/' + MAX_RETRY + ')\n'
          + '경로: ' + updaterLogPath + '\n\n'
          + '잠시만요 — 새 서버가 떠오르면 자동으로 로그를 보여드립니다.';
        await new Promise(function(resolve){ setTimeout(resolve, INTERVAL_MS); });
        if(!isOpen()) return;
        if(await tryFetchOnce()) return;
      }

      // 끝까지 실패 → fallback
      renderFallback();
    };
  } catch(e){
    alert('업데이트 요청 중 오류: ' + e.message);
  }
}

// ─────── 관리자 > 데이터변환 ───────
// 상태: 이번 변환 결과만 보관. 다음 변환 시 덮어씀.
let _DC_STATE = null;

// HTML 이스케이프 (데이터변환 표 렌더용)
function escapeHtml(s){
  if(s === null || s === undefined) return '';
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}  // { total, new_count, existing_count, error_count, new_patients, file_name }
function escapeAttr(s){
  return escapeHtml(s);
}

function dcReset(){
  _DC_STATE = null;
  const f = document.getElementById('dc-file'); if(f) f.value = '';
  const r = document.getElementById('dc-result'); if(r) r.innerHTML = '';
}

async function dcPreview(){
  const file = document.getElementById('dc-file').files[0];
  if(!file){ alert('엑셀 파일을 선택하세요'); return; }
  const result = document.getElementById('dc-result');
  const btn = document.getElementById('dc-preview-btn');
  // 진행 표시: spinner + 버튼 비활성화 (중복 클릭 방지)
  result.innerHTML = `
    <div style="padding:14px;display:flex;align-items:center;gap:10px;color:#475569;">
      <span class="dc-spinner" style="width:16px;height:16px;border:2px solid #E2E8F0;border-top-color:#2F86CB;border-radius:50%;display:inline-block;animation:dc-spin 0.8s linear infinite;"></span>
      <span>엑셀 파일 분석 중... <span class="muted" style="font-size:12px;">(파일이 크면 수 초 소요)</span></span>
    </div>
    <style>@keyframes dc-spin { to { transform: rotate(360deg); } }</style>
  `;
  const prevBtnText = btn ? btn.textContent : '';
  if(btn){ btn.disabled = true; btn.textContent = '분석 중...'; btn.style.opacity = '0.6'; btn.style.cursor = 'wait'; }

  // 90초 타임아웃 — 매우 큰 엑셀 + 느린 디스크 IO 도 커버
  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(), 90000);

  const fd = new FormData();
  fd.append('file', file);
  try {
    const r = await adminFetch('/api/data-convert/preview', { method:'POST', body: fd, signal: ac.signal });
    if(!r.ok){
      const t = await r.text();
      result.innerHTML = `<div style="padding:12px;color:#B74841;">분석 실패: ${escapeHtml(t)}</div>`;
      return;
    }
    _DC_STATE = await r.json();
    dcRenderResult();
  } catch(e){
    if(e && e.name === 'AbortError'){
      result.innerHTML = `<div style="padding:12px;color:#B74841;">⏱ 분석 시간 초과(90초). 파일이 너무 크거나 서버 응답이 없습니다. 잠시 후 다시 시도하거나 파일 크기를 줄여 주세요.</div>`;
    } else {
      result.innerHTML = `<div style="padding:12px;color:#B74841;">오류: ${escapeHtml(e.message)}</div>`;
    }
  } finally {
    clearTimeout(timer);
    if(btn){ btn.disabled = false; btn.textContent = prevBtnText || '분석 (미리보기)'; btn.style.opacity = ''; btn.style.cursor = ''; }
  }
}

function dcRenderResult(){
  const s = _DC_STATE;
  const box = document.getElementById('dc-result');
  if(!s){ box.innerHTML = ''; return; }

  // 요약 5카드 (검토필요 추가)
  const reviewCnt = s.review_count || 0;
  const summary = `
    <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-top:4px;">
      ${[
        ['총 행 수',    s.total,           '#2F86CB'],
        ['추가 대상',   s.new_count,       '#3BA67D'],
        ['검토 필요',   reviewCnt,         reviewCnt>0?'#D97706':'#94A3B8'],
        ['기존 건너뜀', s.existing_count, '#7957AC'],
        ['오류',        s.error_count,    s.error_count>0?'#D7625C':'#94A3B8'],
      ].map(([lbl,val,col]) => `
        <div class="stats-card" style="border-top:3px solid ${col};text-align:center;padding:14px 8px;">
          <div style="font-size:24px;font-weight:700;color:${col};line-height:1;">${val}</div>
          <div style="font-size:12px;color:#4B5563;margin-top:6px;">${lbl}</div>
        </div>`).join('')}
    </div>
    <p class="muted" style="font-size:12px;margin:10px 0;">
      파일: <b>${escapeHtml(s.file_name||'')}</b> · 인식된 헤더: <code style="background:#F3F4F6;padding:2px 6px;border-radius:4px;font-size:11px;">${(s.header||[]).map(escapeHtml).join(' / ')}</code>
      <br><span style="font-size:11px;">※ 자동 분석(규칙 기반): 컬럼 자동 인식 · 전화/생일/성별 형식 통일 · 검토 필요 분류.<br>
      ※ 외부 AI 호출 없음 — 개인정보 외부 전송되지 않습니다.</span>
    </p>
    ${(s.parse_info && s.parse_info.fallback_used) ? `
      <div style="padding:10px 12px;background:#FEF6EC;border:1px solid #F6DBA3;border-radius:8px;margin-bottom:10px;font-size:12px;color:#B45309;">
        ⚠ <b>엑셀 파싱 fallback 모드로 진행됨</b> (CSV 방식)<br>
        사유: ${escapeHtml(s.parse_info.fallback_reason||'')}<br>
        <span style="color:#4B5563;font-size:11px;">→ 결과 정확도는 같지만, 가능하면 최신 배포본(v1.2.1+)으로 교체하시면 xlsx 직접 파싱으로 더 안전합니다.</span>
      </div>
    ` : ''}
  `;

  // 신환 추가 대상 표 (검토 필요 행은 살짝 주황 틴트)
  let newTable;
  if(!s.new_patients || !s.new_patients.length){
    newTable = `<p class="muted" style="padding:14px;background:#FAFCFE;border:1px solid #E5EDF5;border-radius:10px;">
      추가할 신환이 없습니다. (파일 내 모든 환자가 이미 DB에 있거나, 이름 열이 비어있음)
    </p>`;
  } else {
    const gtag = p => (p.gender === 'M') ? '<span class="gender-tag m">M</span>'
                    : (p.gender === 'F') ? '<span class="gender-tag f">F</span>'
                    : '<span class="muted">-</span>';
    const rows = s.new_patients.map((p,i) => {
      const isRev = !!(p.review_reasons && p.review_reasons.length);
      const bg = isRev ? 'background:#FEF6EC;' : '';
      return `<tr style="${bg}">
        <td style="text-align:center;color:#4B5563;font-size:12px;">${i+1}</td>
        <td><b>${escapeHtml(p.name||'')}</b>${isRev?' <span style="color:#D97706;font-size:11px;">●</span>':''}</td>
        <td>${escapeHtml(p.chart_no||'-')}</td>
        <td style="text-align:center;">${gtag(p)}</td>
        <td>${escapeHtml(p.phone||'-')}</td>
        <td>${escapeHtml(p.birth_date||'-')}</td>
        <td class="muted" style="text-align:center;font-size:11px;">${p.row||'-'}</td>
      </tr>`;
    }).join('');
    newTable = `
      <h4 style="margin:16px 0 8px;color:#3D4A5C;">추가 대상 ${s.new_patients.length}명 <span class="muted" style="font-weight:normal;font-size:12px;">· ●표시 = 검토 필요</span></h4>
      <div style="max-height:420px;overflow:auto;border:1px solid #E5EDF5;border-radius:10px;">
        <table class="data-table" style="margin:0;">
          <thead>
            <tr>
              <th style="width:44px;text-align:center;">#</th>
              <th>이름</th><th>차트번호</th>
              <th style="text-align:center;width:48px;">성별</th>
              <th>연락처</th><th>생년월일</th>
              <th style="width:60px;text-align:center;">행</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }

  // 검토 필요 별도 표 (이동전화 2개 / 필수값 누락 / 중복 의심 / 형식 오류)
  let reviewTable = '';
  if(s.review_list && s.review_list.length){
    const rRows = s.review_list.map(p => {
      const extras = (p.extra_phones && p.extra_phones.length) ? p.extra_phones.join(', ') : '-';
      return `<tr>
        <td><b>${escapeHtml(p.name||'')}</b></td>
        <td>${escapeHtml(p.chart_no||'-')}</td>
        <td>${escapeHtml(p.phone||'-')}</td>
        <td>${escapeHtml(extras)}</td>
        <td style="color:#B45309;font-size:12px;">${escapeHtml(p.review_reason||'')}</td>
      </tr>`;
    }).join('');
    reviewTable = `
      <h4 style="margin:18px 0 8px;color:#B45309;">⚠ 검토 필요 ${s.review_list.length}명 <span class="muted" style="font-weight:normal;font-size:12px;">· DB에는 추가되지만 사유가 memo 에 함께 기록됩니다</span></h4>
      <div style="max-height:320px;overflow:auto;border:1px solid #F6DBA3;border-radius:10px;background:#FFFBF2;">
        <table class="data-table" style="margin:0;">
          <thead>
            <tr>
              <th>이름</th><th>차트번호</th><th>메인 연락처</th>
              <th>추가 번호</th><th>상태 (사유)</th>
            </tr>
          </thead>
          <tbody>${rRows}</tbody>
        </table>
      </div>`;
  }

  // 오류 목록 (있을 때만)
  let errBlock = '';
  if(s.errors && s.errors.length){
    errBlock = `<h4 style="margin:14px 0 6px;color:#B74841;">⚠ 오류 ${s.errors.length}건</h4>
      <ul style="margin:0;padding-left:18px;color:#B74841;font-size:12px;">
      ${s.errors.map(e => `<li>행 ${e.row||'-'}: ${escapeHtml(e.reason||e.message||'')}</li>`).join('')}
      </ul>`;
  }

  // 액션
  const actions = `
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:18px;padding-top:14px;border-top:1px solid #EEF2F7;">
      <button id="dc-apply-btn" class="primary" onclick="dcApply()" ${s.new_count===0?'disabled style="opacity:.5;cursor:not-allowed;"':''}>
        현재 DB에 적용 (${s.new_count}명)
      </button>
      <button class="mini" onclick="dcExportCsv()" ${s.new_count===0?'disabled':''}>CSV로 내보내기</button>
      <button class="mini" onclick="dcReset()">초기화</button>
      <span id="dc-apply-result" class="muted" style="font-size:13px;align-self:center;"></span>
    </div>
  `;

  box.innerHTML = summary + newTable + reviewTable + errBlock + actions;
}

async function dcApply(){
  if(!_DC_STATE || !_DC_STATE.new_patients || !_DC_STATE.new_patients.length) return;
  const n = _DC_STATE.new_patients.length;
  if(!confirm(`${n}명을 현재 프로그램 DB에 추가합니다. 계속하시겠습니까?`)) return;

  const res = document.getElementById('dc-apply-result');
  const btn = document.getElementById('dc-apply-btn');
  // 진행 표시: spinner + 버튼 비활성화 (중복 클릭 방지)
  if(res) res.innerHTML = `
    <span class="dc-spinner" style="width:14px;height:14px;border:2px solid #E2E8F0;border-top-color:#2F86CB;border-radius:50%;display:inline-block;animation:dc-spin 0.8s linear infinite;vertical-align:middle;margin-right:6px;"></span>
    <span style="vertical-align:middle;color:#475569;">DB 에 ${n}명 추가 중...</span>
    <style>@keyframes dc-spin { to { transform: rotate(360deg); } }</style>
  `;
  const prevBtnText = btn ? btn.textContent : '';
  if(btn){ btn.disabled = true; btn.textContent = '적용 중...'; btn.style.opacity = '0.6'; btn.style.cursor = 'wait'; }

  // 90초 타임아웃 — 수백 명 import + 느린 DB 라도 커버
  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(), 90000);

  try {
    const r = await adminFetch('/api/data-convert/apply', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ items: _DC_STATE.new_patients }),
      signal: ac.signal,
    });
    if(!r.ok){
      if(res) res.innerHTML = `<span style="color:#B74841;">적용 실패: ${escapeHtml(await r.text())}</span>`;
      return;
    }
    const d = await r.json();
    if(res) res.innerHTML = `<span style="color:#3BA67D;">✓ ${d.inserted}명 추가 완료${d.skipped?` · 건너뜀 ${d.skipped}`:''}</span>`;
    // 환자 캐시 새로고침
    try { await loadMasters?.(); } catch(e){}
    // 이번 변환 결과의 new_count 를 0 으로 갱신 (재적용 방지)
    _DC_STATE.existing_count += d.inserted;
    _DC_STATE.new_count = 0;
    _DC_STATE.new_patients = (d.inserted_patients || []);
    // 적용된 목록을 "이번 추가된 환자들" 로 갱신 재렌더
    dcRenderAfterApply(d);
  } catch(e){
    if(e && e.name === 'AbortError'){
      if(res) res.innerHTML = `<span style="color:#B74841;">⏱ 적용 시간 초과(90초). 서버 응답이 없습니다. <b>중복 적용을 막기 위해 새로고침 전에 환자 목록을 먼저 확인</b>해 주세요.</span>`;
    } else {
      if(res) res.innerHTML = `<span style="color:#B74841;">오류: ${escapeHtml(e.message)}</span>`;
    }
  } finally {
    clearTimeout(timer);
    // 성공 시 dcRenderAfterApply 가 화면을 갈아엎으므로 버튼 자체가 사라짐.
    // 실패/타임아웃 시는 버튼이 그대로 있으므로 복구.
    if(btn && document.body.contains(btn)){
      btn.disabled = false; btn.textContent = prevBtnText || '현재 DB에 적용';
      btn.style.opacity = ''; btn.style.cursor = '';
    }
  }
}

// 적용 완료 후 — 추가된 환자 목록을 강조 표시
function dcRenderAfterApply(d){
  const box = document.getElementById('dc-result');
  const rows = (d.inserted_patients||[]).map((p,i) => {
    const extras = (p.extra_phones && p.extra_phones.length) ? p.extra_phones.join(', ') : '';
    const reasons = (p.review_reasons && p.review_reasons.length) ? p.review_reasons.join(' · ') : '';
    const isRev = !!reasons;
    const bg = isRev ? 'background:#FEF6EC;' : '';
    return `<tr style="${bg}">
      <td style="text-align:center;color:#4B5563;font-size:12px;">${i+1}</td>
      <td><b>${escapeHtml(p.name||'')}</b>${isRev?' <span style="color:#D97706;font-size:11px;">●</span>':''}</td>
      <td>${escapeHtml(p.chart_no||'-')}</td>
      <td>${escapeHtml(p.phone||'-')}</td>
      <td>${escapeHtml(extras||'-')}</td>
      <td>${escapeHtml(p.birth_date||'-')}</td>
      <td style="color:#B45309;font-size:11px;">${escapeHtml(reasons||'')}</td>
    </tr>`;
  }).join('');
  const reviewNote = d.review_inserted > 0
    ? ` · 검토 필요 <b style="color:#D97706;">${d.review_inserted}명</b> 포함 (memo 에 사유 기록됨)`
    : '';
  box.innerHTML = `
    <div style="padding:16px;background:#EBF6F1;border:1px solid #AFDCC6;border-radius:12px;">
      <div style="display:flex;align-items:center;gap:10px;">
        <span style="font-size:22px;color:#3BA67D;">✓</span>
        <div>
          <div style="font-weight:700;color:#24885F;">적용 완료</div>
          <div class="muted" style="font-size:12px;">이번 변환에서 <b>${d.inserted}명</b> 추가됨 · 건너뜀 ${d.skipped||0}건${reviewNote}</div>
        </div>
      </div>
    </div>
    <h4 style="margin:16px 0 8px;color:#3D4A5C;">이번 변환에서 추가된 환자들 <span class="muted" style="font-weight:normal;font-size:12px;">· ●표시 = 검토 필요</span></h4>
    <div style="max-height:420px;overflow:auto;border:1px solid #E5EDF5;border-radius:10px;">
      <table class="data-table" style="margin:0;">
        <thead><tr>
          <th style="width:44px;text-align:center;">#</th>
          <th>이름</th><th>차트번호</th><th>메인 연락처</th>
          <th>추가 번호</th><th>생년월일</th><th>상태 (사유)</th>
        </tr></thead>
        <tbody>${rows || '<tr><td colspan="7" class="muted" style="text-align:center;padding:16px;">(추가된 환자 없음)</td></tr>'}</tbody>
      </table>
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:14px;">
      <button class="mini" onclick="dcReset()">초기화 (다음 파일 준비)</button>
    </div>
  `;
}

function dcExportCsv(){
  if(!_DC_STATE || !_DC_STATE.new_patients || !_DC_STATE.new_patients.length) return;
  const rows = [['name','chart_no','phone','birth_date']];
  _DC_STATE.new_patients.forEach(p => rows.push([
    p.name||'', p.chart_no||'', p.phone||'', p.birth_date||''
  ]));
  const csv = rows.map(r => r.map(v => {
    const s = String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g,'""')}"` : s;
  }).join(',')).join('\n');
  // UTF-8 BOM 붙여야 엑셀에서 한글 깨지지 않음
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  const ts = new Date().toISOString().slice(0,19).replace(/[:T]/g,'-');
  a.download = `신환_${ts}.csv`;
  document.body.appendChild(a); a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 100);
}

// ─────── 관리자 > 시스템 설정 (카드형 레이아웃) ───────

async function loadSystemForm(){
  if(!await ensureAdmin()){
    document.getElementById('system-form').innerHTML='<p class="muted">인증 필요</p>';
    return;
  }

  const cfg = await (await fetch('/api/config')).json();
  const sys = await (await fetch('/api/system-settings')).json();

  const slotOpts = [10,15,20,30,40,50,60].map(
    d => `<option value="${d}" ${d===cfg.slot_minutes?'selected':''}>${d}분</option>`
  ).join('');

  document.getElementById('system-form').innerHTML = `
    <div class="settings-grid">

      <!-- 운영 시간 -->
      <div class="settings-card">
        <div class="settings-card-head">
          <h3>🕐 운영 시간</h3>
          <small class="muted">표 표시 범위 / 슬롯 단위</small>
        </div>
        <div class="settings-card-body">
          <div class="sf-row">
            <label class="sf-label">영업 시작</label>
            <input id="s-open" type="time" value="${cfg.open_time}">
          </div>
          <div class="sf-row">
            <label class="sf-label">영업 종료</label>
            <input id="s-close" type="time" value="${cfg.close_time}">
          </div>
          <div class="sf-row">
            <label class="sf-label">표 슬롯</label>
            <select id="s-slot">${slotOpts}</select>
          </div>
          <div class="sf-row">
            <label class="sf-label">오전반차 기준</label>
            <input id="s-leave-am" type="time" value="${cfg.leave_am_until || '14:00'}">
          </div>
          <div class="sf-row">
            <label class="sf-label">오후반차 기준</label>
            <input id="s-leave-pm" type="time" value="${cfg.leave_pm_from || '13:00'}">
          </div>
          <div class="sf-row" style="border-top:1px dashed #E5E7EB; padding-top:8px; margin-top:4px">
            <label class="sf-label">🍱 점심시간 사용</label>
            <input id="s-lunch-enabled" type="checkbox" ${cfg.lunch_enabled?'checked':''}>
          </div>
          <div class="sf-row">
            <label class="sf-label">점심 시작</label>
            <input id="s-lunch-start" type="time" value="${cfg.lunch_start || '12:30'}">
          </div>
          <div class="sf-row">
            <label class="sf-label">점심 종료</label>
            <input id="s-lunch-end" type="time" value="${cfg.lunch_end || '13:30'}">
          </div>
          <p class="muted" style="font-size:12px; margin-top:0">
            점심시간 사용 시 그 시간대 셀이 가로로 병합되고 신규 예약·드래그 이동이 차단됩니다.<br>
            그 시간대에 이미 예약이 있는 날은 병합이 적용되지 않습니다.
          </p>
          <div class="sf-actions">
            <button class="primary" onclick="saveSystem()">💾 저장 (재시작 필요)</button>
          </div>
        </div>
      </div>

      <!-- (치료항목 기본 시간 카드는 관리자 탭의 "💊 치료항목" 카드로 이동됨) -->

      <!-- 도수치료 한도 -->
      <div class="settings-card">
        <div class="settings-card-head">
          <h3>🧮 도수치료 동시 예약 한도</h3>
          <small class="muted">한 30분 슬롯당 최대 N명 (비워두면 자동)</small>
        </div>
        <div class="settings-card-body">
          <div class="sf-row">
            <label class="sf-label">최대 인원</label>
            <input id="s-manual-limit" type="number" min="0" max="20"
                   value="${sys.manual_slot_limit!=null?sys.manual_slot_limit:''}"
                   placeholder="자동">
            <span class="sf-suffix">명</span>
          </div>
          <p class="muted" style="font-size:12px">
            자동 모드: 그 시간에 근무 중인 도수치료 가능 치료사 수.<br>
            설정값 입력 시: 자동값과 설정값 중 <b>작은 쪽</b>이 실효 한도.<br>
            한도 초과 시 예약은 가능하나 경고 모달이 뜹니다.
          </p>
          <div class="sf-actions">
            <button class="primary" onclick="saveManualLimit()">💾 저장</button>
          </div>
        </div>
      </div>


      <!-- 관리자 비밀번호 -->
      <div class="settings-card">
        <div class="settings-card-head">
          <h3>🔑 관리자 비밀번호</h3>
          <small class="muted">삭제 등 보호 작업에 사용</small>
        </div>
        <div class="settings-card-body">
          <div class="sf-row">
            <label class="sf-label">현재 비밀번호</label>
            <input id="pw-cur" type="password">
          </div>
          <div class="sf-row">
            <label class="sf-label">새 비밀번호</label>
            <input id="pw-new" type="password">
          </div>
          <div class="sf-row">
            <label class="sf-label">확인</label>
            <input id="pw-new2" type="password">
          </div>
          <div class="sf-actions">
            <button class="primary" onclick="changePassword()">비밀번호 변경</button>
          </div>
        </div>
      </div>

      <!-- 단계 G #18: 자동 백업 + 복원 -->
      <div class="settings-card settings-card-wide">
        <div class="settings-card-head">
          <h3>💾 자동 백업 / 복원</h3>
          <small class="muted">앱 시작 시 1회 + 주기적으로 자동 백업</small>
        </div>
        <div class="settings-card-body">
          <div class="sf-row">
            <label class="sf-label">자동 백업</label>
            <label class="chk-label-inline" style="padding:0">
              <input type="checkbox" id="s-bk-enabled"
                     ${sys.auto_backup_enabled?'checked':''}>
              <span>활성</span>
            </label>
          </div>
          <div class="sf-row">
            <label class="sf-label">백업 주기</label>
            <input id="s-bk-interval" type="number" min="5" max="1440"
                   value="${sys.auto_backup_interval_min||60}">
            <span class="sf-suffix">분 (최소 5분)</span>
          </div>
          <div class="sf-row">
            <label class="sf-label">보관 개수</label>
            <input id="s-bk-keep" type="number" min="1" max="365"
                   value="${sys.auto_backup_keep_count||30}">
            <span class="sf-suffix">개 (초과 시 오래된 것 자동 삭제)</span>
          </div>
          <div class="sf-actions">
            <button class="primary" onclick="saveBackupSettings()">💾 설정 저장</button>
          </div>

          <hr class="sf-sep">

          <div class="sf-actions" style="justify-content:flex-start; gap:8px;">
            <button onclick="backupNow()">📦 지금 백업</button>
            <button onclick="location.href='/api/backup'">📥 백업 다운로드 (현재 DB)</button>
            <button class="danger" onclick="restoreLatest()">⚠️ 가장 최근 백업으로 복원</button>
          </div>

          <hr class="sf-sep">

          <div class="bk-list-head">
            <b>최근 백업 목록</b>
            <button class="mini" onclick="reloadBackupList()">🔄 새로고침</button>
          </div>
          <div id="backup-list" class="bk-list">불러오는 중...</div>

          <hr class="sf-sep">

          <details>
            <summary class="muted" style="cursor:pointer">파일 직접 업로드해서 복원하기 (위험)</summary>
            <div class="sf-row" style="margin-top:10px; align-items:center; gap:8px; flex-wrap:wrap;">
              <label class="sf-label">백업 폴더 경로</label>
              <code id="s-backup-dir-path" style="font-size:12px; color:#555; flex:1; word-break:break-all;">불러오는 중...</code>
              <button class="mini" onclick="copyBackupDirPath()" title="경로 복사">📋 경로 복사</button>
            </div>
            <div class="sf-row" style="margin-top:8px">
              <label class="sf-label">복원 파일</label>
              <input id="s-restore" type="file" accept=".db">
            </div>
            <div class="sf-actions">
              <button class="danger" onclick="doRestore()">⚠️ 파일로 복원 (덮어쓰기)</button>
            </div>
          </details>
        </div>
      </div>

      <!-- 개발자 문의 -->
      <div class="settings-card settings-card-wide">
        <div class="settings-card-head">
          <h3>💬 개발자 문의</h3>
          <small class="muted">오류 신고 / 기능 요청</small>
        </div>
        <div class="settings-card-body">
          <p style="margin:0 0 12px; font-size:14px; color:var(--gray-700)">
            프로그램 오류나 개선 사항은 아래 카카오톡 채널로 문의해 주세요.
          </p>
          <div class="sf-actions">
            <a href="https://open.kakao.com/o/sqWmuIqi"
               target="_blank" rel="noopener noreferrer"
               style="display:inline-flex; align-items:center; gap:8px;
                      background:#FAE100; color:#3A1D1D; font-weight:700;
                      padding:10px 20px; border-radius:8px; text-decoration:none;
                      font-size:14px; border:none; cursor:pointer;">
              <img src="https://developers.kakao.com/assets/img/about/logos/kakaolink/kakaolink_btn_medium.png"
                   style="width:20px; height:20px; border-radius:4px;" alt="">
              카카오톡으로 문의하기
            </a>
          </div>
        </div>
      </div>

    </div>
  `;
  // 카드 렌더 후 백업 목록 자동 로드
  reloadBackupList();
  loadBackupDirPath();
}

async function saveSystem(){
  const lunchEnabled = document.getElementById('s-lunch-enabled')?.checked || false;
  const lunchStart = _v('s-lunch-start') || '12:30';
  const lunchEnd   = _v('s-lunch-end')   || '13:30';
  if(lunchEnabled && timeToMinutes(lunchEnd) <= timeToMinutes(lunchStart)){
    alert('점심 종료 시간은 시작 시간보다 뒤여야 합니다.');
    return;
  }
  const body = {
    open_time: _v('s-open'),
    close_time: _v('s-close'),
    slot_minutes: parseInt(_v('s-slot')),
    leave_am_until: _v('s-leave-am') || '14:00',
    leave_pm_from: _v('s-leave-pm') || '13:00',
    lunch_enabled: lunchEnabled,
    lunch_start: lunchStart,
    lunch_end: lunchEnd,
  };
  const r = await adminFetch('/api/config', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body),
  });
  if(!r.ok){ alert('저장 실패\n' + await r.text()); return; }
  alert('저장되었습니다. 새로고침합니다.');
  location.reload();
}

async function saveTreatmentMinutes(){
  // 더 이상 사용되지 않음 — 치료항목 카드(loadTreatmentsCard)에서 항목별 default_minutes 로 관리
  alert('이 기능은 관리자 탭의 "💊 치료항목" 카드로 이동되었습니다.');
}

// ─────── 관리자 > 치료항목 관리 카드 ───────

async function loadTreatmentsCard(){
  if(!await ensureAdmin()){
    document.getElementById('treatments-list').innerHTML = '<p class="muted">인증 필요</p>';
    return;
  }
  await loadTreatmentMeta();
  const items = await (await fetch('/api/treatments')).json();

  if(!items.length){
    document.getElementById('treatments-list').innerHTML =
      '<p class="muted">등록된 치료항목이 없습니다. "+ 새 치료항목" 으로 추가하세요.</p>';
    return;
  }

  const fmtPrice = v => (v && v > 0) ? (Number(v).toLocaleString() + '원') : '-';
  const fmtIncentive = t => {
    // pct 와 amount 는 "둘 중 하나만" 규약 (서버에서 강제).
    if (t.incentive_amount && t.incentive_amount > 0) {
      return `<span class="tx-badge tx-badge-on">${Number(t.incentive_amount).toLocaleString()}원</span>`;
    }
    if (t.incentive_pct && t.incentive_pct > 0) {
      return `<span class="tx-badge tx-badge-on">${t.incentive_pct}%</span>`;
    }
    return '<span class="muted">-</span>';
  };

  const rows = items.map((t, idx) => {
    const categoryBadge = `<span class="tx-badge" style="background:${(EMPLOYEE_CATEGORIES.find(c=>c.id===t.category_id)||{}).color||'#E5E7EB'}22;color:#374151;border:1px solid #E5E7EB;">${t.category_name || '-'}</span>`;
    const activeBadge = t.active
      ? '<span class="tx-badge tx-badge-on">활성</span>'
      : '<span class="tx-badge tx-badge-off">비활성</span>';
    const showBadge = t.show_in_patient
      ? '<span class="tx-badge tx-badge-on">표시 ON</span>'
      : '<span class="tx-badge tx-badge-off">표시 OFF</span>';
    return `<tr data-id="${t.id}">
      <td class="drag-handle" title="드래그하여 순서 변경">⠿</td>
      <td>${idx+1}</td>
      <td><b>${t.name}</b></td>
      <td><code>${t.short}</code></td>
      <td>${t.default_minutes}분</td>
      <td>${categoryBadge}</td>
      <td>+${t.count_increment}</td>
      <td style="text-align:right;font-variant-numeric:tabular-nums;">${fmtPrice(t.price)}</td>
      <td style="text-align:center;">${fmtIncentive(t)}</td>
      <td>${showBadge}</td>
      <td>${activeBadge}</td>
      <td>
        <button class="mini" onclick='editTreatmentModal(${JSON.stringify(t).replace(/'/g,"&#39;")})'>수정</button>
        <button class="mini danger" onclick="deleteTreatment('${t.id}')">삭제</button>
      </td>
    </tr>`;
  }).join('');

  document.getElementById('treatments-list').innerHTML = `
    <table class="data-table">
      <thead><tr>
        <th style="width:32px"></th><th>#</th><th>이름</th><th>약자</th><th>기본 시간</th><th>과</th>
        <th>완료 +N</th><th>수가</th><th>인센티브</th><th>표 표시</th><th>상태</th><th>관리</th>
      </tr></thead>
      <tbody class="tx-sortable-body">${rows}</tbody>
    </table>
    <p class="muted" style="font-size:12px;margin-top:10px">
      • <b>표 표시 ON</b>: 환자 관리 표·편집 모달에서 처방/완료 카운트 입력란 노출<br>
      • <b>과</b>: 선택한 과의 직원과 예약/집계 화면에서 연결됩니다<br>
      • <b>체외충격파(eswt)</b>는 별도 공용 열 유지 (코드 변경 불가)<br>
      • <b>수가</b>: 통계 "분석"의 매출 계산에 사용 (예약 건수 × 수가)<br>
      • <b>인센티브</b>: 퍼센티지 또는 고정 금액 중 하나만 설정. 집계 탭 치료사별 인센티브 합계 계산에 사용<br>
      • 약자는 모든 치료항목 사이에 중복될 수 없습니다
    </p>
  `;
  initTreatmentSortable();
}

function editTreatmentModal(t){
  const isNew = !t;
  const firstCat = (EMPLOYEE_CATEGORIES || []).find(c => c.active !== false) || {};
  t = t || {
    code:'', name:'', short:'', category_id:firstCat.id||'', default_minutes:30, role:'therapist',
    count_increment:1, show_in_patient:false, active:true, sort_order:0,
    price:0, incentive_pct:null, incentive_amount:null,
  };
  // 기존 인센티브 값에 따라 라디오 초기 상태 결정:
  //  - 고정 금액 있음 → mode=amount
  //  - % 있음         → mode=pct
  //  - 둘 다 없음     → mode=none  (미설정)
  let initMode = 'none';
  if (t.incentive_amount && t.incentive_amount > 0) initMode = 'amount';
  else if (t.incentive_pct && t.incentive_pct > 0)  initMode = 'pct';

  showModal(`<h3>${isNew?'+ 새 치료항목':'치료항목 수정'}</h3>
    <label>이름 * <input id="t-name" value="${t.name||''}" placeholder="예: 영양제, 주사 등"></label>
    <label>내부 코드
      <input id="t-code" value="${t.code||''}" ${isNew?'':'readonly'} placeholder="예: manual90">
      <small class="muted">${isNew?'비워두면 자동 생성됩니다.':'기존 예약 참조 보호를 위해 수정할 수 없습니다.'}</small>
    </label>
    <label>과 *
      <select id="t-category">${employeeCategoryOptions(t.category_id || firstCat.id || '')}</select>
    </label>
    <div class="row-3">
      <label>약자 *
        <input id="t-short" value="${t.short||''}" maxlength="10" placeholder="셀에 표시될 약자 (예: 영)">
      </label>
      <label>기본 시간(분) *
        <input id="t-min" type="number" min="5" max="480" step="5" value="${t.default_minutes||30}">
      </label>
      <label>완료 +N
        <input id="t-inc" type="number" min="0" max="10" value="${t.count_increment||1}">
        <small class="muted">치료완료 시 누적량</small>
      </label>
    </div>

    <!-- ── 수가 / 인센티브 ── -->
    <div style="border-top:1px solid #E5E7EB;margin-top:10px;padding-top:10px;">
      <label>수가 (원)
        <input id="t-price" type="number" min="0" step="1000" value="${t.price||0}" placeholder="예: 50000">
        <small class="muted">통계 '분석'의 매출 계산 기준</small>
      </label>
      <div style="margin-top:8px;">
        <div class="t-field-label" style="display:block;margin-bottom:4px;">치료사 인센티브 <small class="muted" style="font-weight:normal;">· 하나만 선택</small></div>
        <div class="role-radios" style="margin-bottom:6px;">
          <label><input type="radio" name="t-inc-mode" value="none" ${initMode==='none'?'checked':''} onchange="_onIncModeChange()"> 미설정</label>
          <label><input type="radio" name="t-inc-mode" value="pct" ${initMode==='pct'?'checked':''} onchange="_onIncModeChange()"> 퍼센티지(%)</label>
          <label><input type="radio" name="t-inc-mode" value="amount" ${initMode==='amount'?'checked':''} onchange="_onIncModeChange()"> 고정 금액(원)</label>
        </div>
        <div class="row-3">
          <label>인센티브 %
            <input id="t-inc-pct" type="number" min="0" max="100" step="0.1"
                   value="${t.incentive_pct!=null?t.incentive_pct:''}"
                   placeholder="예: 10">
          </label>
          <label>인센티브 고정 금액
            <input id="t-inc-amount" type="number" min="0" step="1000"
                   value="${t.incentive_amount!=null?t.incentive_amount:''}"
                   placeholder="예: 5000">
          </label>
          <div></div>
        </div>
      </div>
    </div>

    <div class="t-checks-row">
      <label class="chk-label-inline">
        <input type="checkbox" id="t-show" ${t.show_in_patient?'checked':''}>
        <span>환자 관리 표·편집에 표시 (ON)</span>
      </label>
      <label class="chk-label-inline">
        <input type="checkbox" id="t-active" ${t.active!==false?'checked':''}>
        <span>활성화</span>
      </label>
    </div>
    <input type="hidden" id="t-id" value="${t.id||''}">
    <input type="hidden" id="t-sort" value="${t.sort_order||0}">
    <div class="modal-actions">
      <button onclick="closeModal()">취소</button>
      <button class="primary" onclick="saveTreatment()">${isNew?'추가':'저장'}</button>
    </div>
  `);
  // 모달이 DOM 에 붙은 후 초기 상태 반영
  _onIncModeChange();
}

// 인센티브 입력 모드 전환 — 선택된 쪽만 활성/포커스, 나머지는 비활성+클리어
function _onIncModeChange(){
  const mode = (document.querySelector('input[name="t-inc-mode"]:checked')||{}).value || 'none';
  const pct = document.getElementById('t-inc-pct');
  const amt = document.getElementById('t-inc-amount');
  if (!pct || !amt) return;
  if (mode === 'pct') {
    pct.disabled = false; amt.disabled = true;  amt.value = '';
  } else if (mode === 'amount') {
    pct.disabled = true;  pct.value = '';       amt.disabled = false;
  } else { // none
    pct.disabled = true;  pct.value = '';
    amt.disabled = true;  amt.value = '';
  }
}

async function saveTreatment(){
  const id = _v('t-id');
  const name = _v('t-name').trim();
  const short = _v('t-short').trim();
  const code = _v('t-code').trim();
  if(!name){ alert('이름을 입력하세요'); return; }
  if(!short){ alert('약자를 입력하세요'); return; }
  const categoryId = _v('t-category');
  if(!categoryId){ alert('과를 선택하세요'); return; }
  const cat = (EMPLOYEE_CATEGORIES || []).find(c => c.id === categoryId);
  const role = (cat && cat.default_can_doctor_treatment && cat.default_can_manual === false) ? 'doctor' : 'therapist';

  // 인센티브 모드에 따라 pct/amount 중 하나만 전송 (나머지는 null)
  const incMode = (document.querySelector('input[name="t-inc-mode"]:checked')||{}).value || 'none';
  let incPct = null, incAmount = null;
  if (incMode === 'pct') {
    const v = parseFloat(_v('t-inc-pct'));
    if (isNaN(v) || v <= 0) { alert('인센티브 퍼센티지를 입력하세요 (0 초과)'); return; }
    if (v > 100) { alert('인센티브 퍼센티지는 100 이하만 가능합니다'); return; }
    incPct = v;
  } else if (incMode === 'amount') {
    const v = parseInt(_v('t-inc-amount'));
    if (isNaN(v) || v <= 0) { alert('인센티브 고정 금액을 입력하세요 (0 초과)'); return; }
    incAmount = v;
  }

  const body = {
    name,
    short,
    category_id: categoryId,
    default_minutes: parseInt(_v('t-min'))||30,
    role,
    count_increment: parseInt(_v('t-inc'))||1,
    show_in_patient: document.getElementById('t-show').checked,
    active: document.getElementById('t-active').checked,
    sort_order: parseInt(_v('t-sort'))||0,
    price: parseInt(_v('t-price'))||0,
    incentive_pct: incPct,
    incentive_amount: incAmount,
  };
  if(!id && code) body.code = code;

  if(!await ensureAdmin()) return;
  const url = id ? `/api/treatments/${id}` : '/api/treatments';
  const r = await adminFetch(url, {
    method: id ? 'PUT' : 'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body),
  });
  if(!r.ok){
    const t = await r.text();
    let msg = '저장 실패\n' + t;
    try { msg = JSON.parse(t).detail || msg; } catch(e){}
    alert(msg); return;
  }
  closeModal();
  await loadTreatmentMeta();   // TX_META 갱신
  loadTreatmentsCard();
}

function initTreatmentSortable(){
  const tbody = document.querySelector('.tx-sortable-body');
  if(!tbody) return;
  if(tbody._sortable){ tbody._sortable.destroy(); }
  tbody._sortable = Sortable.create(tbody, {
    handle: '.drag-handle',
    animation: 150,
    ghostClass: 'sortable-ghost',
    onEnd: async () => {
      if(!await ensureAdmin()) return;
      const rows = [...tbody.querySelectorAll('tr[data-id]')].map((tr, idx) => ({
        id: tr.dataset.id, sort_order: idx + 1,
      }));
      const r = await adminFetch('/api/treatments/reorder', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify(rows),
      });
      if(!r.ok){ alert('순서 저장 실패\n' + await r.text()); return; }
      await loadTreatmentMeta();
      loadTreatmentsCard();
    },
  });
}

async function deleteTreatment(tid){
  if(!await ensureAdmin()) return;
  // 먼저 참조 조회
  const r = await adminFetch(`/api/treatments/${tid}/references`, {method:'GET'});
  if(!r.ok){ alert('참조 조회 실패\n' + await r.text()); return; }
  const data = await r.json();
  const refs = data.references || [];
  const t = data.treatment;

  if(refs.length){
    // 참조 있음 → 모달로 목록 + 비활성화 옵션
    const refRows = refs.slice(0, 50).map(r => {
      const dt = new Date(r.start_at);
      const dtStr = `${dt.getFullYear()}-${String(dt.getMonth()+1).padStart(2,'0')}-${String(dt.getDate()).padStart(2,'0')} ${String(dt.getHours()).padStart(2,'0')}:${String(dt.getMinutes()).padStart(2,'0')}`;
      const stMark = {reserved:'📅', approved:'✅', canceled:'❌'}[r.status] || '';
      return `<div class="tx-ref-line">${stMark} ${dtStr} · <b>${r.patient_name}</b> (차트 ${r.chart_no})</div>`;
    }).join('');
    const more = refs.length > 50 ? `<div class="muted">… 외 ${refs.length-50}건 더</div>` : '';
    showModal(`<h3>⚠️ 삭제 불가</h3>
      <p>이 치료항목 <b>${t.name}</b>(${t.short})을 사용하는 예약이 <b>${refs.length}건</b> 있어 삭제할 수 없습니다.</p>
      <div class="tx-ref-list">${refRows}${more}</div>
      <p class="muted">참조 예약을 정리한 후 다시 시도하거나, 비활성화로 전환하세요.</p>
      <div class="modal-actions">
        <button onclick="closeModal()">닫기</button>
        ${t.active ? `<button class="primary" onclick="deactivateTreatment('${tid}')">비활성화로 전환</button>` : ''}
      </div>
    `);
    return;
  }

  if(!confirm(`치료항목 "${t.name}" 을(를) 완전히 삭제합니다.\n계속하시겠습니까?`)) return;
  const dr = await adminFetch(`/api/treatments/${tid}`, {method:'DELETE'});
  if(!dr.ok){ alert('삭제 실패\n' + await dr.text()); return; }
  await loadTreatmentMeta();
  loadTreatmentsCard();
}

async function deactivateTreatment(tid){
  // 현재 정보 가져와서 active=false 로 PUT
  const all = await (await fetch('/api/treatments')).json();
  const t = all.find(x => x.id === tid);
  if(!t){ alert('치료항목 없음'); return; }
  if(!await ensureAdmin()) return;
  const body = {
    name: t.name, short: t.short,
    category_id: t.category_id,
    default_minutes: t.default_minutes, role: t.role,
    count_increment: t.count_increment, show_in_patient: t.show_in_patient,
    active: false, sort_order: t.sort_order,
    // 비활성화 시 수가/인센티브 설정은 그대로 보존
    price: t.price || 0,
    incentive_pct: t.incentive_pct,
    incentive_amount: t.incentive_amount,
  };
  const r = await adminFetch(`/api/treatments/${tid}`, {
    method:'PUT', headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body),
  });
  if(!r.ok){ alert('비활성화 실패\n' + await r.text()); return; }
  closeModal();
  await loadTreatmentMeta();
  loadTreatmentsCard();
}

async function saveManualLimit(){
  const v = document.getElementById('s-manual-limit').value.trim();
  const body = { manual_slot_limit: v === '' ? null : parseInt(v) };
  const r = await fetch('/api/system-settings', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body),
  });
  if(!r.ok){ alert('저장 실패\n' + await r.text()); return; }
  alert('한도가 저장되었습니다.');
  MANUAL_SLOT_LIMIT = body.manual_slot_limit;
}


async function changePassword(){
  const cur = _v('pw-cur'), nw = _v('pw-new'), nw2 = _v('pw-new2');
  if(!cur || !nw){ alert('현재/새 비밀번호를 입력하세요'); return; }
  if(nw !== nw2){ alert('새 비밀번호 확인 불일치'); return; }
  if(nw.length < 4){ alert('4자 이상'); return; }
  const r = await adminFetch('/api/admin/change-password', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({current_password: cur, new_password: nw}),
  });
  const d = await r.json();
  if(!r.ok){ alert(d.detail || '실패'); return; }
  alert(d.msg); setToken('');
}

async function doRestore(){
  const f = document.getElementById('s-restore').files[0];
  if(!f){ alert('파일 선택'); return; }
  if(!confirm('현재 DB를 덮어씁니다. 계속?')) return;
  const fd = new FormData(); fd.append('file', f);
  const r = await adminFetch('/api/restore', {method:'POST', body: fd});
  const d = await r.json();
  alert(d.msg || '완료');
}

async function copyBackupDirPath(){
  const el = document.getElementById('s-backup-dir-path');
  const path = el ? el.textContent : '';
  if(!path || path === '불러오는 중...') { alert('경로를 아직 불러오지 못했습니다.'); return; }
  try {
    await navigator.clipboard.writeText(path);
    alert('📋 경로가 복사되었습니다!\n\n' + path + '\n\n파일 선택창에서 주소창에 붙여넣기(Ctrl+V) 하세요.');
  } catch(e) {
    prompt('아래 경로를 복사하세요 (Ctrl+A → Ctrl+C):', path);
  }
}

async function loadBackupDirPath(){
  try {
    const r = await adminFetch('/api/backup/dir', {method:'GET'});
    if(!r.ok) return;
    const d = await r.json();
    const el = document.getElementById('s-backup-dir-path');
    if(el && d.path) el.textContent = d.path;
  } catch(e){}
}

// ─────── 단계 G #18: 자동 백업 관리 ───────

async function saveBackupSettings(){
  const enabled = document.getElementById('s-bk-enabled').checked;
  const interval = Math.max(5, parseInt(document.getElementById('s-bk-interval').value)||60);
  const keep = Math.max(1, parseInt(document.getElementById('s-bk-keep').value)||30);
  const r = await fetch('/api/system-settings', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({
      auto_backup_enabled: enabled,
      auto_backup_interval_min: interval,
      auto_backup_keep_count: keep,
    }),
  });
  if(!r.ok){ alert('저장 실패\n' + await r.text()); return; }
  alert('자동 백업 설정이 저장되었습니다.\n변경된 주기는 다음 백업부터 적용됩니다.');
  // 입력값 정규화 반영
  document.getElementById('s-bk-interval').value = interval;
  document.getElementById('s-bk-keep').value = keep;
}

async function backupNow(){
  if(!await ensureAdmin()) return;
  const r = await adminFetch('/api/backup/now', {method:'POST'});
  if(!r.ok){ alert('백업 실패\n' + await r.text()); return; }
  const d = await r.json();
  alert(`백업 완료: ${d.name}`);
  reloadBackupList();
}

async function restoreLatest(){
  if(!await ensureAdmin()) return;
  const ok = await confirmBlock(
    '⚠️ <b>가장 최근 백업으로 복원</b>합니다.<br><br>' +
    '• 현재 DB는 안전망 백업으로 자동 저장됩니다.<br>' +
    '• 복원 후 <b>서버 재시작이 필요</b>합니다.<br>' +
    '• 진행 중인 작업은 손실될 수 있습니다.<br><br>' +
    '계속하시겠습니까?'
  );
  if(!ok) return;
  const r = await adminFetch('/api/backup/restore-latest', {method:'POST'});
  if(!r.ok){ alert('복원 실패\n' + await r.text()); return; }
  const d = await r.json();
  alert(`복원 완료: ${d.restored_from}\n\n⚠️ 서버를 재시작하세요.`);
}

async function reloadBackupList(){
  const box = document.getElementById('backup-list');
  if(!box) return;
  if(!await ensureAdmin()){ box.innerHTML = '<p class="muted">인증 필요</p>'; return; }
  try {
    const list = await (await adminFetch('/api/backup/list', {method:'GET'})).json();
    if(!list.length){
      box.innerHTML = '<p class="muted">백업 파일 없음</p>'; return;
    }
    const fmtSize = (b) => b < 1024 ? b+'B' : b < 1024*1024 ? (b/1024).toFixed(1)+'KB' : (b/1024/1024).toFixed(1)+'MB';
    const fmtTime = (iso) => {
      const d = new Date(iso);
      return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}:${String(d.getSeconds()).padStart(2,'0')}`;
    };
    const rows = list.slice(0, 30).map((f, i) => `
      <div class="bk-item" style="display:flex;align-items:center;gap:8px;padding:4px 2px;border-bottom:1px solid #f0f0f0;">
        <span class="bk-num" style="min-width:22px;color:#aaa;font-size:12px;">${i+1}</span>
        <span class="bk-time" style="min-width:140px;font-size:13px;">${fmtTime(f.mtime)}</span>
        <span class="bk-size" style="min-width:52px;font-size:12px;color:#888;">${fmtSize(f.size)}</span>
        <span class="bk-name muted" style="flex:1;font-size:11px;color:#aaa;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${f.name}</span>
        <button onclick="restoreByName('${f.name}')"
          style="font-size:11px;padding:2px 8px;background:#e74c3c;color:#fff;border:none;border-radius:4px;cursor:pointer;white-space:nowrap;">
          ↩ 복원
        </button>
      </div>`).join('');
    box.innerHTML = rows + (list.length > 30 ? `<p class="muted" style="font-size:12px;margin-top:6px">... 외 ${list.length-30}개 더</p>` : '');
  } catch(e){
    box.innerHTML = '<p class="muted">목록 조회 실패</p>';
  }
}

async function restoreByName(filename){
  const confirmed = confirm(
    '⚠️ [' + filename + '] 으로 복원합니다.\n\n' +
    '• 현재 DB는 안전망 백업으로 자동 저장됩니다.\n' +
    '• 복원 후 서버 재시작이 필요합니다.\n\n' +
    '계속하시겠습니까?'
  );
  if(!confirmed) return;
  const r = await adminFetch('/api/backup/restore-by-name', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({filename})
  });
  if(!r.ok){ alert('복원 실패\n' + await r.text()); return; }
  const d = await r.json();
  alert('복원 완료: ' + d.restored_from + '\n\n⚠️ 서버를 재시작하세요.');
  reloadBackupList();
}

async function syncNow(){
  const el = document.getElementById('sync-status');
  if(el) el.textContent = '동기화 중...';
  try {
    await fetch('/api/sync/now', {method:'POST'});
    if(el) el.textContent = 'OK';
    refresh();
  } catch(e){
    if(el) el.textContent = '실패';
  }
}

// 서브 주소(내부 IP) 복사 — 다른 PC/폰에서 쓸 URL
function copySubAddr(){
  const el = document.getElementById('sub-addr');
  if(!el) return;
  const hostPort = el.textContent.trim();
  const url = 'http://' + hostPort + '/';
  const notify = (msg) => {
    const status = document.getElementById('sync-status');
    if (status) {
      const prev = status.textContent;
      status.textContent = msg;
      setTimeout(() => { if (status.textContent === msg) status.textContent = prev; }, 2000);
    } else {
      alert(msg);
    }
  };
  // 1순위: Clipboard API (HTTPS 또는 localhost 에서 동작)
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(url)
      .then(() => notify('✓ 복사됨: ' + url))
      .catch(() => fallback());
  } else {
    fallback();
  }
  function fallback(){
    // 2순위: 구버전 브라우저용 textarea 방식
    const ta = document.createElement('textarea');
    ta.value = url;
    ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand('copy');
      notify('✓ 복사됨: ' + url);
    } catch(e) {
      alert('복사 실패 — 직접 복사해주세요:\n' + url);
    }
    document.body.removeChild(ta);
  }
}

