/**
 * 수집 이력 시트에 붙여 쓰는 웹 앱(D14, D19, D28~D32). 토스트 명의 Google 계정의 시트에서 실행한다.
 *
 * 요청(POST JSON, 모두 token 필요):
 *   upsert {rows}        행 추가·갱신. 코드가 쓰는 열만 갱신하고 '상태'와 '대표 메모'는 건드리지 않는다.
 *   rows                 '수집 이력'의 행을 돌려준다. 대표 메모는 돌려주지 않는다.
 *   status {key, status} 상태 칸을 바꾼다(review-requests가 씀).
 *   mail {subject, html} 대표에게 메일을 보낸다(주소는 스크립트 속성에만 둔다).
 * 시간 트리거 cleanup(): 마감 지난 행을 정리하고, 검토 기록이 있는 행은 '지난 공고' 탭으로 옮긴다(D29, D34).
 *
 * 스크립트 속성: TOKEN(웹 앱 토큰), CEO_EMAIL(대표 메일 주소).
 */
const SHEET = '수집 이력';
const PAST = '지난 공고';
const COLS = ['key', 'alt_keys', 'source', 'kind', 'title', 'agency', 'price', 'deadline', 'registered', 'url',
              'matched', 'status', 'memo', 'updated'];
const HEAD = ['키', '같은 사업 키', '소스', '종류', '제목', '기관·작성자', '추정가격', '마감일', '등록일', '원문 링크',
              '일치 키워드', '상태', '대표 메모', '최근 갱신'];
const KEEP = ['status', 'memo'];  // 코드가 덮어쓰지 않는 열
// 상태 값(D26)의 정본은 docs/decisions.md D26이다. 파이썬 쪽 목록 두 개(gov_agent/runner.py REQUESTED,
// daily_report/deliver.py REVIEWING)는 plugin/tests/test_contract.py가 서로 같은지 검사한다. 여기서는 '신규'만 쓴다.
const NO_DEADLINE_DAYS = 30;

function doPost(e) {
  let req;
  try {
    req = JSON.parse(e.postData.contents);
  } catch (err) {
    return json_({ ok: false, error: 'json' });
  }
  const props = PropertiesService.getScriptProperties();
  if (!req.token || req.token !== props.getProperty('TOKEN')) return json_({ ok: false, error: 'token' });
  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    if (req.action === 'upsert') return json_(upsert_(req.rows || []));
    if (req.action === 'rows') return json_({ ok: true, rows: readRows_() });
    if (req.action === 'status') return json_(setStatus_(req.key, req.status));
    if (req.action === 'mail') {
      MailApp.sendEmail({ to: props.getProperty('CEO_EMAIL'), subject: req.subject, htmlBody: req.html });
      return json_({ ok: true });
    }
    return json_({ ok: false, error: 'action' });
  } finally {
    lock.releaseLock();
  }
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function sheet_(name) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(name);
  if (!sh) {
    sh = ss.insertSheet(name);
    sh.getRange(1, 1, 1, HEAD.length).setValues([HEAD]);
    sh.getRange('A:N').setNumberFormat('@');  // 날짜 문자열이 날짜 값으로 바뀌지 않게 한다
    sh.setFrozenRows(1);
  }
  return sh;
}

function values_(sh) {
  const n = sh.getLastRow() - 1;
  return n > 0 ? sh.getRange(2, 1, n, COLS.length).getValues() : [];
}

function today_() {
  return Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd');
}

function upsert_(rows) {
  const sh = sheet_(SHEET);
  const data = values_(sh);
  const at = {};
  data.forEach((r, i) => { at[r[0]] = i; });
  const stamp = today_();
  rows.forEach(row => {
    const line = COLS.map(c => (c === 'alt_keys' ? (row.alt_keys || []).join(', ')
      : c === 'updated' ? stamp : c === 'status' ? (row.status || '신규') : c === 'memo' ? '' : (row[c] == null ? '' : String(row[c]))));
    if (row.key in at) {
      const cur = data[at[row.key]];
      COLS.forEach((c, j) => { if (KEEP.indexOf(c) < 0) cur[j] = line[j]; });
    } else {
      at[row.key] = data.length;
      data.push(line);
    }
  });
  if (data.length) sh.getRange(2, 1, data.length, COLS.length).setValues(data);
  return { ok: true, count: rows.length };
}

function readRows_() {
  return values_(sheet_(SHEET)).map(r => {
    const o = {};
    COLS.forEach((c, j) => { if (c !== 'memo') o[c] = String(r[j]); });
    return o;
  });
}

function setStatus_(key, status) {
  const sh = sheet_(SHEET);
  const data = values_(sh);
  const i = data.findIndex(r => r[0] === key);
  if (i < 0) return { ok: false, error: 'key' };
  sh.getRange(i + 2, COLS.indexOf('status') + 1).setValue(status);
  return { ok: true };
}

/** 시간 트리거로 매일 한 번 실행한다(installTrigger 참고). 마감일 당일 행은 남긴다. */
function cleanup() {
  const sh = sheet_(SHEET);
  const past = sheet_(PAST);
  const data = values_(sh);
  const today = today_();
  const limit = Utilities.formatDate(new Date(Date.now() - NO_DEADLINE_DAYS * 86400000), 'Asia/Seoul', 'yyyy-MM-dd');
  const iDeadline = COLS.indexOf('deadline'), iReg = COLS.indexOf('registered');
  const iStatus = COLS.indexOf('status'), iMemo = COLS.indexOf('memo');
  for (let i = data.length - 1; i >= 0; i--) {  // 아래에서 위로 지워야 행 번호가 밀리지 않는다
    const r = data[i];
    const deadline = String(r[iDeadline]).slice(0, 10), reg = String(r[iReg]).slice(0, 10);
    const expired = deadline ? deadline < today : (reg !== '' && reg < limit);
    if (!expired) continue;
    const reviewed = (String(r[iStatus]) || '신규') !== '신규' || String(r[iMemo]).trim() !== '';
    if (reviewed) past.appendRow(r);
    sh.deleteRow(i + 2);
  }
}

/** 처음 한 번 편집기에서 실행해 새벽 6시 정리 트리거를 만든다. */
function installTrigger() {
  ScriptApp.getProjectTriggers().filter(t => t.getHandlerFunction() === 'cleanup').forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('cleanup').timeBased().atHour(6).everyDays(1).inTimezone('Asia/Seoul').create();
}
