'use strict';

/* ---------- API layer ---------- */
const API = window.SRMS_API || '';
const TOKEN_KEY = 'srms.token';

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

let token = sessionStorage.getItem(TOKEN_KEY) || '';

async function api(path, { method = 'GET', body } = {}) {
  let res;
  try {
    res = await fetch(API + path, {
      method,
      headers: {
        ...(body ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: 'Bearer ' + token } : {})
      },
      body: body ? JSON.stringify(body) : undefined
    });
  } catch (e) {
    throw new Error('Cannot reach the server. Is the backend running?');
  }
  if (res.status === 401 && token) { signOut(); throw new Error('Session expired. Please sign in again.'); }
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const detail = data && data.detail;
    throw new Error(Array.isArray(detail) ? detail.map(d => d.msg).join(', ') : detail || 'Request failed.');
  }
  return data;
}

/* ---------- Shared display rules (the server is authoritative) ---------- */
const GR = [[90, 'A+', 10], [80, 'A', 9], [70, 'B+', 8], [60, 'B', 7], [50, 'C', 6], [40, 'D', 5], [0, 'F', 0]];
const gr = p => GR.find(r => p >= r[0]);
const LBL = { draft: 'Draft', submitted: 'Awaiting approval', approved: 'Approved' };

const NAV = {
  admin: [['dash', 'Overview'], ['students', 'Students'], ['subjects', 'Subjects and teachers'], ['approvals', 'Result approval']],
  teacher: [['marks', 'Marks entry'], ['perf', 'Class performance']],
  student: [['result', 'My results'], ['card', 'Report card']]
};
const DEMO = { admin: ['admin', 'admin123'], teacher: ['T1', 'teach123'], student: ['CS101', 'stud123'] };

let U = null, page = null, selSub = null, cardFor = null, role = 'student', curMax = 100, tt;
let mode = 'login';   // 'login' | 'register'

const stat = (v, l) => `<div class="stat"><b>${esc(v)}</b><span>${esc(l)}</span></div>`;
const bar = (l, w, v) => `<div class="bar"><span>${esc(l)}</span><i><u style="width:${Math.max(0, Math.min(100, w))}%"></u></i><em>${esc(v)}</em></div>`;
const chip = st => `<span class="chip ${st}">${LBL[st]}</span>`;
const toast = m => { const t = $('#toast'); t.textContent = m; t.className = 'show'; clearTimeout(tt); tt = setTimeout(() => t.className = '', 2600); };

const mtable = m => `<div class="tw"><table><thead><tr><th>Subject</th><th>Max</th><th>Obtained</th><th>Grade</th><th>Points</th></tr></thead><tbody>${
  m.rows.map(r => r.marks == null
    ? `<tr><td>${esc(r.name)}</td><td>${r.max}</td><td colspan="3" class="empty">Not entered</td></tr>`
    : `<tr><td>${esc(r.name)}</td><td>${r.max}</td><td>${r.marks}</td><td class="g ${r.grade === 'F' ? 'f' : ''}">${esc(r.grade)}</td><td>${r.points}</td></tr>`).join('')
  || '<tr><td colspan="5" class="empty">No results have been declared yet.</td></tr>'}</tbody></table></div>`;

/* ---------- Shell ---------- */
// Passwords are case sensitive, so mobile keyboards must not capitalise them.
const NO_CAP = 'autocapitalize="off" autocorrect="off" spellcheck="false"';
const CREDS = { student: 'CS101 - CS106', teacher: 'T1, T2', admin: 'admin' };
const PASSWORDS = { student: 'stud123', teacher: 'teach123', admin: 'admin123' };

const brand = () => `<section class="brand"><h1>Student Result Management System</h1>
<p>Enter marks, grade them automatically and download report cards, all in one place.</p><small>Department of Computer Science | Academic Year 2025-26</small></section>`;

const loginView = () => `<div class="login">${brand()}
<form class="box" id="login"><h2>Sign in</h2>
<div class="seg">${['student', 'teacher', 'admin'].map(r => `<button type="button" data-role="${r}" class="${r === role ? 'on' : ''}">${r[0].toUpperCase() + r.slice(1)}</button>`).join('')}</div>
<label>${role === 'student' ? 'Roll number' : role === 'teacher' ? 'Teacher ID' : 'Username'}<input name="uid" required autocomplete="username" autocapitalize="off" autocorrect="off" spellcheck="false"></label>
<label>Password<input name="pw" type="password" required autocomplete="current-password" ${NO_CAP}></label>
<p class="err" id="err" role="alert"></p><button class="btn">Sign in</button>
<div class="creds"><b>Demo logins</b>
<p class="row"><button type="button" class="link" data-role="${role}">${role[0].toUpperCase() + role.slice(1)}</button><span class="id">${CREDS[role]}</span><span class="pw">${PASSWORDS[role]}</span></p>
<small>Use the password exactly as shown - it is case sensitive.</small></div>
<p class="hint">${role === 'student' ? 'No account yet? ' : 'Students can register themselves. '}<button type="button" class="link" data-mode="register">Create a student account</button></p>
<p class="hint">Just looking around? <button type="button" class="link" id="fill">Fill ${role} demo login</button></p>
</form></div>`;

const CLASSES = ['BCA-1A', 'BCA-1B', 'BCA-2A', 'BCA-2B', 'BCA-3A', 'BCA-3B', 'BCA-4A', 'MCA-1A'];

const registerView = () => `<div class="login">${brand()}
<form class="box" id="reg"><h2>Create your account</h2>
<p class="sub">Pick any roll number and password you like. You will be signed in straight away.</p>
<label>Full name<input name="name" required maxlength="80" autocomplete="name" ${NO_CAP}></label>
<label>Roll number<input name="roll" required minlength="2" maxlength="20" placeholder="e.g. CS501" autocomplete="off" ${NO_CAP}></label>
<label>Class<select name="cls">${CLASSES.map(c => `<option${c === 'BCA-3A' ? ' selected' : ''}>${c}</option>`).join('')}</select></label>
<label>Date of birth<input name="dob" type="date" required max="2008-12-31"></label>
<label>Password<input name="pw" type="password" required minlength="6" autocomplete="new-password" ${NO_CAP}><small class="sub">At least 6 characters. This is case sensitive.</small></label>
<label>Confirm password<input name="pw2" type="password" required minlength="6" autocomplete="new-password" ${NO_CAP}></label>
<p class="err" id="err" role="alert"></p><button class="btn">Create account</button>
<p class="hint">Already registered? <button type="button" class="link" data-mode="login">Back to sign in</button></p>
</form></div>`;

const authView = () => (mode === 'register' ? registerView() : loginView());

const shell = body => `<div class="shell"><aside class="side noprint"><div class="logo">SRMS</div>
<nav>${NAV[U.role].map(([k, l]) => `<button data-go="${k}" class="${page === k ? 'on' : ''}">${l}</button>`).join('')}</nav>
<div class="who"><b>${esc(U.name)}</b><span>${esc(U.role)}</span><button class="link" id="out">Sign out</button></div></aside><main>${body}</main></div>`;

/* ---------- Pages ---------- */
const V = {
  async dash() {
    const d = await api('/api/admin/overview');
    const mx = Math.max(1, ...Object.values(d.distribution));
    return `<h2>Overview</h2><div class="stats">${stat(d.students, 'Students')}${stat(d.teachers, 'Teachers')}${stat(d.subjects, 'Subjects')}${stat(d.pass_rate + '%', 'Pass rate (declared results)')}</div>
  <div class="two"><section class="panel"><h3>Grade distribution</h3>${Object.entries(d.distribution).map(([g, n]) => bar(g, n / mx * 100, n)).join('')}</section>
  <section class="panel"><h3>Subject averages</h3>${d.subject_averages.map(s => bar(s.name, s.average, s.average.toFixed(1) + '%')).join('')}</section></div>`;
  },

  async students() {
    const list = await api('/api/admin/students');
    return `<h2>Students</h2>
  <form class="inline" id="addStu"><input name="name" placeholder="Full name" aria-label="Full name" required><input name="roll" placeholder="Roll no. e.g. CS107" aria-label="Roll number" required><input name="cls" placeholder="Class e.g. BCA-3A" aria-label="Class" required><input name="dob" type="date" aria-label="Date of birth" required><button class="btn">Add student</button></form>
  <div class="tw"><table><thead><tr><th>Roll no.</th><th>Name</th><th>Class</th><th>Date of birth</th><th></th></tr></thead><tbody>${
      list.map(s => `<tr><td>${esc(s.roll)}</td><td>${esc(s.name)}</td><td>${esc(s.cls)}</td><td>${esc(s.dob)}</td><td class="act"><button class="link" data-card="${s.id}">Report card</button><button class="link del" data-del="${s.id}">Remove</button></td></tr>`).join('')
      || '<tr><td colspan="5" class="empty">No students yet. Add the first one above.</td></tr>'}</tbody></table></div>`;
  },

  async subjects() {
    const { subjects, teachers } = await api('/api/admin/subjects');
    const opt = sel => teachers.map(t => `<option value="${esc(t.id)}" ${t.id === sel ? 'selected' : ''}>${esc(t.name)}</option>`).join('');
    return `<h2>Subjects and teachers</h2>
  <form class="inline" id="addSub"><input name="name" placeholder="Subject name" aria-label="Subject name" required><input name="max" type="number" min="1" max="1000" value="100" aria-label="Maximum marks" required><select name="teacher" aria-label="Teacher">${opt()}</select><button class="btn">Add subject</button></form>
  <div class="tw"><table><thead><tr><th>Subject</th><th>Max marks</th><th>Assigned teacher</th></tr></thead><tbody>${
      subjects.map(b => `<tr><td>${esc(b.name)}</td><td>${b.max_marks}</td><td><select data-assign="${b.id}" aria-label="Teacher for ${esc(b.name)}">${opt(b.teacher_id)}</select></td></tr>`).join('')
      || '<tr><td colspan="3" class="empty">No subjects yet.</td></tr>'}</tbody></table></div>`;
  },

  async approvals() {
    const list = await api('/api/admin/approvals');
    return `<h2>Result approval</h2><p class="sub">Students see a subject's results only after you approve it.</p>
  <div class="tw"><table><thead><tr><th>Subject</th><th>Teacher</th><th>Average</th><th>Status</th><th></th></tr></thead><tbody>${
      list.map(b => `<tr><td>${esc(b.name)}</td><td>${esc(b.teacher)}</td><td>${b.average.toFixed(1)}%</td><td>${chip(b.status)}</td><td class="act">${
        b.status === 'submitted' ? `<button class="btn sm" data-ok="${b.id}">Approve</button>` : ''}${b.status !== 'draft' ? `<button class="link" data-back="${b.id}">Return to teacher</button>` : ''}</td></tr>`).join('')
      || '<tr><td colspan="5" class="empty">No subjects yet.</td></tr>'}</tbody></table></div>`;
  },

  async marks() {
    const mine = await api('/api/teacher/subjects');
    if (!mine.length) return `<h2>Marks entry</h2><p class="empty">No subjects are assigned to you yet. Ask the admin to assign one.</p>`;
    const chosen = mine.find(x => x.id === selSub) || mine.find(x => x.status === 'draft') || mine[0];
    const data = await api('/api/teacher/marks?subject_id=' + chosen.id);
    selSub = chosen.id;
    curMax = data.subject.max;
    return `<h2>Marks entry</h2><div class="inline"><label>Subject<select id="subSel">${mine.map(x => `<option value="${x.id}" ${x.id === chosen.id ? 'selected' : ''}>${esc(x.name)}</option>`).join('')}</select></label>${chip(data.status)}</div>
  <div class="tw"><table><thead><tr><th>Roll no.</th><th>Name</th><th>Marks (out of ${data.subject.max})</th><th>Grade</th></tr></thead><tbody>${
      data.entries.map(e => `<tr><td>${esc(e.roll)}</td><td>${esc(e.name)}</td><td><input class="mk" type="number" min="0" max="${data.subject.max}" data-s="${esc(e.student_id)}" value="${e.marks ?? ''}" aria-label="Marks for ${esc(e.name)}" ${data.locked ? 'disabled' : ''}></td><td class="g ${e.grade === 'F' ? 'f' : ''}">${esc(e.grade || '-')}</td></tr>`).join('')
      || '<tr><td colspan="4" class="empty">No students in the class.</td></tr>'}</tbody></table></div>
  ${data.locked ? `<p class="note">${data.status === 'submitted' ? 'Submitted. Waiting for admin approval.' : 'Approved and locked by the admin.'}</p>`
      : `<div class="inline"><button class="btn ghost" id="saveM">Save draft</button><button class="btn" id="subM">Submit for approval</button></div>`}`;
  },

  async perf() {
    const list = await api('/api/teacher/performance');
    return `<h2>Class performance</h2>` + (list.map(b => `<section class="panel"><h3>${esc(b.name)}</h3><div class="stats">${stat(b.average.toFixed(1) + '%', 'Class average')}${stat(b.highest + ' / ' + b.max, 'Highest marks')}${stat(b.pass_rate.toFixed(0) + '%', 'Pass rate')}</div>${
      b.students.map(s => bar(s.name, s.percent, s.marks)).join('')}</section>`).join('')
      || '<p class="empty">No subjects are assigned to you yet.</p>');
  },

  async result() {
    const { student: s, result: m } = await api('/api/student/result');
    return `<h2>My results</h2><p class="sub">${esc(s.name)} | ${esc(s.roll)} | ${esc(s.cls)}</p>
  <div class="stats">${stat(m.percentage.toFixed(1) + '%', 'Percentage')}${stat(m.cgpa.toFixed(2), 'CGPA (out of 10)')}${stat(m.total + ' / ' + m.max, 'Total marks')}${stat(m.declared ? (m.pass ? 'Pass' : 'Fail') : '-', 'Result')}</div>
  ${mtable(m)}${m.pending_subjects ? `<p class="note">${m.pending_subjects} subject result(s) not declared yet.</p>` : ''}<button class="btn" data-card="${esc(s.id)}">View report card</button>`;
  },

  async card() {
    const data = U.role === 'student'
      ? await api('/api/student/card')
      : await api('/api/admin/students/' + encodeURIComponent(cardFor) + '/card');
    const s = data.student, m = data.result;
    return `<div class="inline noprint"><button class="btn" onclick="window.print()">Download PDF</button><span class="sub">In the print window, choose "Save as PDF".</span></div>
  <article class="sheet"><header><h1>Report Card</h1><p>Department of Computer Science | Academic Year 2025-26</p></header>
  <dl class="info"><div><dt>Name</dt><dd>${esc(s.name)}</dd></div><div><dt>Roll no.</dt><dd>${esc(s.roll)}</dd></div><div><dt>Class</dt><dd>${esc(s.cls)}</dd></div><div><dt>Date of birth</dt><dd>${esc(s.dob)}</dd></div></dl>
  ${mtable(m)}<div class="sum"><span>Total: ${m.total} / ${m.max}</span><span>Percentage: ${m.percentage.toFixed(1)}%</span><span>CGPA: ${m.cgpa.toFixed(2)}</span><span>Result: <span class="chip ${m.pass ? 'approved' : 'fail'}">${m.declared ? (m.pass ? 'Pass' : 'Fail') : '-'}</span></span></div>
  <p class="sub">Issued on ${new Date().toLocaleDateString('en-IN')}. Pass mark is 40% in every subject.</p>
  <footer><span>Class teacher</span><span>Controller of examinations</span></footer></article>`;
  }
};

/* ---------- Routing ---------- */
async function render() {
  const r = $('#app');
  if (!U) { r.innerHTML = authView(); return; }
  const keys = NAV[U.role].map(n => n[0]);
  if (!keys.includes(page) && !(page === 'card' && U.role === 'admin')) page = keys[0];
  r.innerHTML = shell('<p class="empty">Loading...</p>');
  try {
    r.innerHTML = shell(await V[page]());
  } catch (e) {
    r.innerHTML = shell(`<p class="empty">${esc(e.message)}</p>`);
  }
  window.scrollTo(0, 0);
}

function signOut() {
  token = '';
  U = null;
  page = null;
  selSub = null;
  cardFor = null;
  mode = 'login';
  sessionStorage.removeItem(TOKEN_KEY);
  render();
}

/* ---------- Actions ---------- */
async function saveMarks(submit) {
  const entries = $$('.mk').map(i => ({ student_id: i.dataset.s, marks: i.value === '' ? null : Number(i.value) }));
  const bad = entries.find(e => e.marks != null && (e.marks < 0 || e.marks > curMax));
  if (bad) return toast(`Marks must be between 0 and ${curMax}`);
  try {
    await api('/api/teacher/marks', {
      method: 'PUT',
      body: { subject_id: selSub, action: submit ? 'submitted' : 'draft', marks: entries }
    });
  } catch (e) { return toast(e.message); }
  render();
  toast(submit ? 'Submitted for approval' : 'Draft saved');
}

async function setStatus(subjectId, status, message) {
  try {
    await api('/api/admin/approvals/' + subjectId + '/status', { method: 'POST', body: { status } });
  } catch (e) { return toast(e.message); }
  render();
  toast(message);
}

/* ---------- Events ---------- */
document.addEventListener('click', async e => {
  const t = e.target.closest('button');
  if (!t) return;
  const d = t.dataset;
  try {
    if (d.role) { role = d.role; render(); }
    else if (d.mode) { mode = d.mode; render(); }
    else if (t.id === 'fill') { const f = $('#login'); [f.uid.value, f.pw.value] = DEMO[role]; }
    else if (d.go) { page = d.go; render(); }
    else if (d.card) { cardFor = d.card; page = 'card'; render(); }
    else if (d.del) {
      if (!confirm('Remove this student and all their marks?')) return;
      await api('/api/admin/students/' + d.del, { method: 'DELETE' });
      render();
      toast('Student removed');
    }
    else if (d.ok) await setStatus(d.ok, 'approved', 'Results approved and visible to students');
    else if (d.back) await setStatus(d.back, 'draft', 'Returned to teacher for changes');
    else if (t.id === 'saveM') await saveMarks(false);
    else if (t.id === 'subM') await saveMarks(true);
    else if (t.id === 'out') signOut();
  } catch (err) {
    toast(err.message);
  }
});

document.addEventListener('change', async e => {
  const t = e.target;
  try {
    if (t.id === 'subSel') { selSub = t.value; render(); }
    else if (t.dataset.assign) {
      await api('/api/admin/subjects/' + t.dataset.assign + '/teacher', { method: 'PATCH', body: { teacher_id: t.value } });
      toast('Teacher assigned');
    }
  } catch (err) { toast(err.message); }
});

document.addEventListener('input', e => {
  const i = e.target;
  if (!i.classList.contains('mk')) return;
  const c = i.closest('tr').querySelector('.g');
  const max = Number(i.max) || 100;
  const g = i.value === '' ? '-' : gr(Number(i.value) / max * 100)[1];
  c.textContent = g;
  c.className = 'g' + (g === 'F' ? ' f' : '');
});

document.addEventListener('submit', async e => {
  e.preventDefault();
  const f = e.target;
  const v = Object.fromEntries(new FormData(f));
  if (f.id === 'login') {
    const err = $('#err');
    err.textContent = '';
    try {
      const data = await api('/api/auth/login', { method: 'POST', body: { role, identifier: v.uid.trim(), password: v.pw.trim() } });
      token = data.token;
      sessionStorage.setItem(TOKEN_KEY, token);
      U = data.user;
      page = null;
      render();
    } catch (ex) { err.textContent = ex.message; }
  } else if (f.id === 'reg') {
    const err = $('#err');
    err.textContent = '';
    if (v.pw !== v.pw2) { err.textContent = 'The two passwords do not match.'; return; }
    try {
      const data = await api('/api/auth/register', { method: 'POST', body: { name: v.name.trim(), roll: v.roll.trim().toUpperCase(), cls: v.cls, dob: v.dob, password: v.pw } });
      token = data.token;
      sessionStorage.setItem(TOKEN_KEY, token);
      U = data.user;
      role = 'student';
      page = null;
      render();
      toast(`Welcome, ${data.user.name}. Your account is ready.`);
    } catch (ex) { err.textContent = ex.message; }
  } else if (f.id === 'addStu') {
    try {
      await api('/api/admin/students', { method: 'POST', body: { name: v.name.trim(), roll: v.roll.trim(), cls: v.cls.trim(), dob: v.dob } });
    } catch (ex) { return toast(ex.message); }
    render();
    toast('Student added. Default password is stud123');
  } else if (f.id === 'addSub') {
    try {
      await api('/api/admin/subjects', { method: 'POST', body: { name: v.name.trim(), max_marks: Number(v.max) || 100, teacher_id: v.teacher } });
    } catch (ex) { return toast(ex.message); }
    render();
    toast('Subject added');
  }
});

/* ---------- Boot ---------- */
(async function boot() {
  if (token) {
    try { U = await api('/api/auth/me'); }
    catch (e) { token = ''; sessionStorage.removeItem(TOKEN_KEY); }
  }
  render();
})();