// ─────────────────────────────────────────
// DATABASE (localStorage)
// ─────────────────────────────────────────
const DB = {
  get: k => JSON.parse(localStorage.getItem(k) || '[]'),
  set: (k, v) => localStorage.setItem(k, JSON.stringify(v)),
  getOne: k => JSON.parse(localStorage.getItem(k) || 'null'),
  setOne: (k, v) => localStorage.setItem(k, JSON.stringify(v)),
  nextId: k => { const d = DB.get(k); return d.length ? Math.max(...d.map(x => x.id)) + 1 : 1; },
};

// ─────────────────────────────────────────
// SETTINGS
// ─────────────────────────────────────────
function getSettings() {
  return DB.getOne('settings') || {
    name: 'Anthony', company: 'Capital Solutions Group',
    phone: '', commissionRate: 2, weeklyGoal: 1,
    ejsKey: '', ejsService: '', ejsTemplate: '',
  };
}
function saveSettings() {
  const s = {
    name: v('s-name'), company: v('s-company'), phone: v('s-phone'),
    commissionRate: parseFloat(v('s-commission') || 2),
    weeklyGoal: parseInt(v('s-goal') || 1),
    ejsKey: v('s-ejs-key'), ejsService: v('s-ejs-service'), ejsTemplate: v('s-ejs-template'),
  };
  DB.setOne('settings', s);
  toast('Settings saved!', 'success');
}
function loadSettingsForm() {
  const s = getSettings();
  sv('s-name', s.name); sv('s-company', s.company); sv('s-phone', s.phone);
  sv('s-commission', s.commissionRate); sv('s-goal', s.weeklyGoal);
  sv('s-ejs-key', s.ejsKey); sv('s-ejs-service', s.ejsService); sv('s-ejs-template', s.ejsTemplate);
}

// ─────────────────────────────────────────
// EMAIL TEMPLATES
// ─────────────────────────────────────────
const TEMPLATES = {
  initial_outreach: {
    label: 'Initial Outreach',
    subject: 'Quick question about funding for {company}',
    body: `Hi {firstName},

I hope this finds you well. My name is {yourName} from {yourCompany} — we specialize in fast, flexible business loans for small business owners.

I noticed that {company} has previously worked with us, and I wanted to personally reach out. Many of our clients are using this time to secure additional capital for growth, inventory, or cash flow needs.

We currently offer:
• Loans from $10,000 – $500,000
• Approval in as little as 24–48 hours
• Flexible repayment terms (6–60 months)
• No collateral required for qualifying businesses

Would you have 10 minutes this week for a quick call?

Looking forward to reconnecting,
{yourName}
{yourCompany}
{yourPhone}`,
    tip: 'Best sent Tue–Thu, 9–11am. Mention their previous loan to show you know them. Keep subject short and curiosity-driven.',
  },
  follow_up_1: {
    label: 'Follow-Up #1',
    subject: 'Re: Funding options for {company} — following up',
    body: `Hi {firstName},

I wanted to follow up on my previous message about business funding options for {company}.

I understand you're busy — that's exactly why I want to make this as simple as possible. Many owners I speak with are surprised at how quickly we can get capital into their hands (sometimes same-week).

Would any time this week work for a quick 10-minute call?

Best,
{yourName}
{yourCompany}
{yourPhone}`,
    tip: 'Wait 3–5 days after initial outreach. Reference your last email. Add urgency without pressure.',
  },
  follow_up_2: {
    label: 'Follow-Up #2 (Final)',
    subject: 'Last reach-out — {company} funding options',
    body: `Hi {firstName},

I don't want to keep filling your inbox, so this will be my last note for now.

If you ever find yourself in need of fast business capital — whether it's to cover a slow season, jump on a growth opportunity, or manage cash flow — please don't hesitate to reach out.

You can reach me directly at {yourPhone} or reply to this email.

Wishing you and {company} continued success,
{yourName}
{yourCompany}`,
    tip: 'Last touch. Keep it short and gracious. Leave the door open — many deals come from "last chance" emails.',
  },
  proposal: {
    label: 'Proposal',
    subject: 'Your personalized loan proposal — {company}',
    body: `Hi {firstName},

Thank you for speaking with me! As discussed, here is the loan option I believe fits {company} best:

Loan Amount:    $[FILL IN]
Interest Rate:  [FILL IN]% APR
Term:           [FILL IN] months
Est. Monthly:   ~$[FILL IN]/month

Next steps:
1. Reply to this email or call me at {yourPhone}
2. I'll send a short application (takes ~5 minutes)
3. We review and respond within 24–48 hours

Looking forward to getting this done for you,
{yourName}
{yourCompany}
{yourPhone}`,
    tip: 'Fill in the loan numbers before sending. Confirm verbally first if possible. Clear next steps = faster close.',
  },
};

function renderTemplate(tmplKey, contact) {
  const s = getSettings();
  const t = TEMPLATES[tmplKey];
  if (!t || !contact) return { subject: '', body: '' };
  const replace = str => str
    .replace(/{firstName}/g, (contact.name || '').split(' ')[0] || 'there')
    .replace(/{company}/g, contact.company || 'your business')
    .replace(/{yourName}/g, s.name || 'Anthony')
    .replace(/{yourCompany}/g, s.company || '')
    .replace(/{yourPhone}/g, s.phone || '');
  return { subject: replace(t.subject), body: replace(t.body) };
}

// ─────────────────────────────────────────
// NAVIGATION
// ─────────────────────────────────────────
const PAGES = ['dashboard','contacts','emails','deals','commission','settings'];
function navigate(page) {
  PAGES.forEach(p => {
    el(`page-${p}`).classList.toggle('d-none', p !== page);
  });
  document.querySelectorAll('.nav-link[data-page]').forEach(a => {
    a.classList.toggle('active', a.dataset.page === page);
  });
  if (page === 'dashboard') renderDashboard();
  if (page === 'contacts') renderContacts();
  if (page === 'emails') renderEmails();
  if (page === 'deals') renderDeals();
  if (page === 'commission') renderCommission();
  if (page === 'settings') loadSettingsForm();
}
function switchTab(tab) {
  document.querySelectorAll('.email-tab').forEach(a => a.classList.toggle('active', a.dataset.tab === tab));
  ['log','drafts','compose'].forEach(t => {
    const el2 = el(`email-tab-${t}`);
    if (el2) el2.classList.toggle('d-none', t !== tab);
  });
  if (tab === 'log') renderEmailLog();
  if (tab === 'drafts') renderDraftQueue();
  if (tab === 'compose') initCompose();
}

// ─────────────────────────────────────────
// DASHBOARD
// ─────────────────────────────────────────
function renderDashboard() {
  const s = getSettings();
  const now = new Date();
  const hr = now.getHours();
  const greet = hr < 12 ? 'morning' : hr < 17 ? 'afternoon' : 'evening';
  el('greeting').textContent = `Good ${greet}, ${s.name || 'Anthony'} 👋`;
  el('todayDate').textContent = now.toLocaleDateString('en-US', { weekday:'long', year:'numeric', month:'long', day:'numeric' });
  el('sidebarDate').textContent = now.toLocaleDateString('en-US', { month:'short', day:'numeric', year:'numeric' });

  const deals = DB.get('deals');
  const emails = DB.get('emails');
  const followUps = DB.get('followups');

  // Weekly deals
  const weekStart = getWeekStart(0);
  const weekDeals = deals.filter(d => d.status === 'closed_won' && new Date(d.closedAt) >= weekStart);
  const goal = s.weeklyGoal || 1;
  const weekComm = weekDeals.reduce((sum, d) => sum + d.loanAmount * (d.commissionRate / 100), 0);
  el('d-week-deals').innerHTML = `${weekDeals.length}<span style="font-size:1rem;font-weight:400;color:#8b949e;">/${goal}</span>`;
  const bar = el('d-week-bar');
  const pct = Math.min(weekDeals.length / goal * 100, 100);
  bar.style.width = pct + '%';
  bar.className = `progress-bar ${weekDeals.length >= goal ? 'bg-success' : 'bg-warning'}`;
  el('d-week-comm').textContent = '$' + fmt(weekComm);

  // Reply rate
  const sent = emails.filter(e => e.status === 'sent');
  const replied = emails.filter(e => e.replied);
  const rate = sent.length ? Math.round(replied.length / sent.length * 100) : 0;
  el('d-reply-rate').textContent = rate + '%';
  el('d-reply-sub').textContent = `${replied.length} of ${sent.length} emails`;
  el('d-drafts').textContent = emails.filter(e => e.status === 'draft').length;
  el('d-waiting').textContent = sent.filter(e => !e.replied).length;
  el('d-replied').textContent = replied.length;

  // YTD
  const thisYear = now.getFullYear();
  const ytdDeals = deals.filter(d => d.status === 'closed_won' && new Date(d.closedAt).getFullYear() === thisYear);
  const ytdComm = ytdDeals.reduce((sum, d) => sum + d.loanAmount * (d.commissionRate / 100), 0);
  const ytdVol = ytdDeals.reduce((sum, d) => sum + d.loanAmount, 0);
  el('d-ytd').textContent = '$' + fmt(ytdComm);
  el('d-ytd-sub').textContent = `${ytdDeals.length} deals · $${fmt(ytdVol)} volume`;

  // Pipeline
  const stages = ['prospect','contacted','interested','proposal_sent','negotiating','closed_won','closed_lost'];
  const contacts = DB.get('contacts');
  const pipeline = {};
  stages.forEach(s2 => { pipeline[s2] = { count: 0, value: 0 }; });
  deals.forEach(d => {
    if (pipeline[d.status]) { pipeline[d.status].count++; pipeline[d.status].value += d.loanAmount; }
  });
  contacts.forEach(c => {
    if (!deals.find(d => d.contactId === c.id)) {
      if (pipeline[c.status]) pipeline[c.status].count++;
    }
  });
  el('d-pipeline').innerHTML = stages.filter(s2 => pipeline[s2].count > 0).map(s2 =>
    `<div class="d-flex justify-content-between px-3 py-2 border-bottom" style="border-color:#21262d!important;">
      <span class="pipeline-badge stage-${s2}">${s2.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}</span>
      <span>${pipeline[s2].count}</span>
      <span class="text-muted small">$${fmt(pipeline[s2].value)}</span>
    </div>`
  ).join('') || '<div class="p-3 text-muted text-center small">No deals yet</div>';

  // Follow-ups due
  const today = new Date().toISOString().slice(0,10);
  const due = followUps.filter(f => !f.completed && f.scheduledDate <= today);
  const fuHeader = el('d-fu-header');
  fuHeader.innerHTML = `<i class="bi bi-bell me-2"></i>Follow-ups Due${due.length ? ` <span class="badge bg-danger ms-2">${due.length}</span>` : ''}`;
  if (due.length === 0) {
    el('d-followups').innerHTML = '<div class="p-3 text-muted text-center small"><i class="bi bi-check-circle text-success me-1"></i>All caught up!</div>';
  } else {
    const contactMap = Object.fromEntries(DB.get('contacts').map(c => [c.id, c]));
    el('d-followups').innerHTML = due.map(f => {
      const c = contactMap[f.contactId] || {};
      return `<div class="d-flex align-items-center justify-content-between px-3 py-2 border-bottom" style="border-color:#21262d!important;">
        <div>
          <div class="fw-bold small">${c.name || '?'}</div>
          <div class="text-muted" style="font-size:.75rem;">${f.type} · ${f.scheduledDate}</div>
        </div>
        <button class="btn btn-sm btn-outline-success" onclick="completeFollowup(${f.id})"><i class="bi bi-check"></i></button>
      </div>`;
    }).join('');
  }
}

// ─────────────────────────────────────────
// CONTACTS
// ─────────────────────────────────────────
const STATUSES = ['prospect','contacted','interested','proposal_sent','negotiating','closed_won','closed_lost'];
let contactStatusFilter = null;

function renderContacts() {
  const contacts = DB.get('contacts');
  const q = (el('contactSearch')?.value || '').toLowerCase();
  // Filter buttons
  el('contactFilters').innerHTML = [
    `<button class="btn btn-sm ${!contactStatusFilter ? 'btn-secondary' : 'btn-outline-secondary'}" onclick="setContactFilter(null)">All</button>`,
    ...STATUSES.map(s => `<button class="btn btn-sm ${contactStatusFilter===s ? 'btn-secondary' : 'btn-outline-secondary'}" onclick="setContactFilter('${s}')">${s.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}</button>`)
  ].join('');
  let filtered = contacts;
  if (contactStatusFilter) filtered = filtered.filter(c => c.status === contactStatusFilter);
  if (q) filtered = filtered.filter(c => `${c.name} ${c.company} ${c.email} ${c.industry}`.toLowerCase().includes(q));
  el('contactsBody').innerHTML = filtered.length ? filtered.map(c => `
    <tr>
      <td><span class="fw-bold" style="cursor:pointer;color:#58a6ff;" onclick="viewContact(${c.id})">${esc(c.name)}</span></td>
      <td>${esc(c.company)}</td>
      <td>${esc(c.phone)}</td>
      <td><a href="mailto:${esc(c.email)}" class="text-muted small">${esc(c.email)}</a></td>
      <td>${esc(c.industry)}</td>
      <td>$${fmt(c.prevLoan||0)}</td>
      <td><select class="form-select form-select-sm" style="width:auto;" onchange="updateContactStatus(${c.id},this.value)">
        ${STATUSES.map(s=>`<option ${s===c.status?'selected':''}>${s}</option>`).join('')}
      </select></td>
      <td>
        <button class="btn btn-sm btn-outline-primary" title="Compose" onclick="composeFor(${c.id})"><i class="bi bi-envelope"></i></button>
        <button class="btn btn-sm btn-outline-secondary" onclick="viewContact(${c.id})"><i class="bi bi-chevron-right"></i></button>
      </td>
    </tr>`).join('')
    : '<tr><td colspan="8" class="text-center text-muted py-4">No contacts yet. Add one above!</td></tr>';
}
function setContactFilter(s) { contactStatusFilter = s; renderContacts(); }
function updateContactStatus(id, status) {
  const contacts = DB.get('contacts');
  const c = contacts.find(x => x.id === id);
  if (c) { c.status = status; DB.set('contacts', contacts); }
}
function addContact() {
  const name = v('ac-name').trim();
  if (!name) return toast('Name is required.','danger');
  const contacts = DB.get('contacts');
  const email = v('ac-email').trim().toLowerCase();
  if (email && contacts.find(c => c.email === email)) return toast('Email already exists.','danger');
  contacts.push({
    id: DB.nextId('contacts'), name, company: v('ac-company'), phone: v('ac-phone'),
    email, industry: v('ac-industry'), prevLoan: parseFloat(v('ac-loan')||0),
    notes: v('ac-notes'), status: 'prospect', createdAt: new Date().toISOString(),
  });
  DB.set('contacts', contacts);
  bootstrap.Modal.getInstance(el('addContactModal'))?.hide();
  ['ac-name','ac-company','ac-phone','ac-email','ac-industry','ac-notes'].forEach(id => sv(id,''));
  sv('ac-loan','0');
  toast(`Contact added!`,'success');
  renderContacts();
}
function viewContact(id) {
  const c = DB.get('contacts').find(x => x.id === id);
  if (!c) return;
  const calls = DB.get('calls').filter(x => x.contactId === id);
  const emails2 = DB.get('emails').filter(x => x.contactId === id);
  const deals2 = DB.get('deals').filter(x => x.contactId === id);
  el('cdm-title').textContent = `${c.name} — ${c.company||''}`;
  el('cdm-body').innerHTML = `
    <div class="row g-3 mb-3">
      <div class="col-md-6">
        <div class="small text-muted">Phone</div><div>${c.phone||'—'}</div>
        <div class="small text-muted mt-2">Email</div><div><a href="mailto:${c.email}">${c.email||'—'}</a></div>
        <div class="small text-muted mt-2">Industry</div><div>${c.industry||'—'}</div>
        <div class="small text-muted mt-2">Prev Loan</div><div>$${fmt(c.prevLoan||0)}</div>
        <div class="small text-muted mt-2">Notes</div><div>${c.notes||'—'}</div>
      </div>
      <div class="col-md-6">
        <div class="mb-2 small text-muted">Log a Call</div>
        <select id="vc-outcome" class="form-select form-select-sm mb-2">
          <option value="">— Outcome —</option>
          ${['no_answer','left_voicemail','not_interested','callback_scheduled','interested','meeting_set','deal_closed'].map(o=>`<option>${o}</option>`).join('')}
        </select>
        <input type="text" id="vc-notes" class="form-control form-control-sm mb-2" placeholder="Notes">
        <input type="number" id="vc-followup" class="form-control form-control-sm mb-2" placeholder="Follow-up in X days (optional)">
        <button class="btn btn-sm btn-primary w-100" onclick="logCall(${c.id})">Log Call</button>
      </div>
    </div>
    ${calls.length ? `<div class="small fw-bold mb-1">Call History</div>
    <table class="table table-sm mb-3"><thead><tr><th>Date</th><th>Outcome</th><th>Notes</th></tr></thead><tbody>
    ${calls.slice(-5).reverse().map(cl=>`<tr><td class="small">${cl.calledAt?.slice(0,10)}</td><td><span class="pipeline-badge stage-contacted">${cl.outcome}</span></td><td class="small">${cl.notes||'—'}</td></tr>`).join('')}
    </tbody></table>` : ''}
    ${emails2.length ? `<div class="small fw-bold mb-1">Emails</div>
    <table class="table table-sm mb-3"><thead><tr><th>Template</th><th>Subject</th><th>Status</th></tr></thead><tbody>
    ${emails2.map(e=>`<tr><td class="small">${(e.templateName||'—').replace(/_/g,' ')}</td><td class="small">${e.subject||''}</td>
    <td>${e.replied?'<i class="bi bi-check-circle-fill status-check"></i>':e.status==='sent'?'<i class="bi bi-x-circle status-x"></i>':'<i class="bi bi-pencil-square status-clock"></i>'}</td></tr>`).join('')}
    </tbody></table>` : ''}
    ${deals2.length ? `<div class="small fw-bold mb-1">Deals</div>
    <table class="table table-sm"><thead><tr><th>Amount</th><th>Commission</th><th>Status</th><th></th></tr></thead><tbody>
    ${deals2.map(d=>`<tr><td>$${fmt(d.loanAmount)}</td><td class="text-success">$${fmt2(d.loanAmount*(d.commissionRate/100))}</td>
    <td><span class="pipeline-badge stage-${d.status}">${d.status.replace(/_/g,' ')}</span></td>
    <td>${d.status!=='closed_won'&&d.status!=='closed_lost'?`<button class="btn btn-sm btn-success" onclick="closeDeal(${d.id},true);bootstrap.Modal.getInstance(el('contactDetailModal')).hide()">Won</button>`:''}</td></tr>`).join('')}
    </tbody></table>` : ''}`;
  new bootstrap.Modal(el('contactDetailModal')).show();
}
function logCall(contactId) {
  const outcome = v('vc-outcome');
  if (!outcome) return toast('Select an outcome.','warning');
  const calls = DB.get('calls');
  calls.push({ id: DB.nextId('calls'), contactId, outcome, notes: v('vc-notes'), calledAt: new Date().toISOString() });
  DB.set('calls', calls);
  const fuDays = parseInt(v('vc-followup'));
  if (fuDays > 0) {
    const d = new Date(); d.setDate(d.getDate() + fuDays);
    const followups = DB.get('followups');
    followups.push({ id: DB.nextId('followups'), contactId, type: 'call', scheduledDate: d.toISOString().slice(0,10), notes: v('vc-notes'), completed: false });
    DB.set('followups', followups);
  }
  // Update contact status
  if (['interested','meeting_set'].includes(outcome)) updateContactStatus(contactId, 'interested');
  if (outcome === 'deal_closed') updateContactStatus(contactId, 'closed_won');
  toast('Call logged!','success');
  sv('vc-outcome',''); sv('vc-notes',''); sv('vc-followup','');
}
function completeFollowup(id) {
  const fus = DB.get('followups');
  const f = fus.find(x => x.id === id);
  if (f) { f.completed = true; DB.set('followups', fus); }
  renderDashboard();
}

// ─────────────────────────────────────────
// EMAILS
// ─────────────────────────────────────────
function renderEmails() {
  renderEmailLog();
  const drafts = DB.get('emails').filter(e => e.status === 'draft');
  el('tab-draft-count').textContent = drafts.length || '';
  el('tab-log-count').textContent = DB.get('emails').filter(e => e.status === 'sent').length || '';
}
function renderEmailLog() {
  const emails = DB.get('emails').filter(e => e.status === 'sent' || e.replied);
  const contactMap = Object.fromEntries(DB.get('contacts').map(c => [c.id, c]));
  el('emailLogBody').innerHTML = emails.length ? [...emails].reverse().map(e => {
    const c = contactMap[e.contactId] || {};
    let icon = e.replied
      ? `<i class="bi bi-check-circle-fill status-check fs-5" title="Replied"></i>`
      : `<i class="bi bi-x-circle status-x fs-5" title="No reply yet"></i>`;
    return `<tr>
      <td class="text-center">${icon}</td>
      <td><span class="fw-bold">${esc(c.name||'?')}</span><div class="text-muted small">${esc(c.email||'')}</div></td>
      <td><span class="badge" style="background:#1a2233;color:#58a6ff;">${(e.templateName||'—').replace(/_/g,' ').replace(/\b\w/g,x=>x.toUpperCase())}</span></td>
      <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${esc(e.subject||'')}</td>
      <td class="small">${e.sentAt?.slice(0,16)||'—'}</td>
      <td>${e.replied ? '<span class="text-success fw-bold">✓ Replied</span>' : '<span class="text-muted small">Waiting…</span>'}</td>
      <td>
        ${!e.replied ? `<button class="btn btn-sm btn-outline-warning" onclick="openReplyModal(${e.id})">Mark Replied</button>` : ''}
        ${e.replied && e.replyBody ? `<button class="btn btn-sm btn-outline-success" onclick="viewReply(${e.id})">View Reply</button>` : ''}
      </td>
    </tr>`;
  }).join('') : '<tr><td colspan="7" class="text-center text-muted py-4">No sent emails yet. Compose one →</td></tr>';
}
function renderDraftQueue() {
  const drafts = DB.get('emails').filter(e => e.status === 'draft');
  const contactMap = Object.fromEntries(DB.get('contacts').map(c => [c.id, c]));
  el('draftQueueNote').textContent = `${drafts.length} email(s) staged — review each before sending`;
  el('draftQueueList').innerHTML = drafts.length ? [...drafts].reverse().map(d => {
    const c = contactMap[d.contactId] || {};
    return `<div class="card mb-3"><div class="card-body">
      <div class="d-flex align-items-start justify-content-between">
        <div style="flex:1;">
          <div class="fw-bold">${esc(c.name||'?')} <span class="text-muted fw-normal">· ${esc(c.company||'')}</span></div>
          <div class="text-muted small"><span class="badge" style="background:#1a2233;color:#58a6ff;">${(d.templateName||'').replace(/_/g,' ').replace(/\b\w/g,x=>x.toUpperCase())}</span> ${esc(c.email||'')}</div>
          <div class="fw-semibold mt-2">${esc(d.subject||'')}</div>
          <div class="text-muted mt-1 small">${esc((d.body||'').slice(0,180))}${(d.body||'').length>180?'…':''}</div>
        </div>
        <div class="d-flex flex-column gap-2 ms-3" style="min-width:90px;">
          <button class="btn btn-sm btn-outline-secondary" onclick="editDraft(${d.id})"><i class="bi bi-pencil"></i> Edit</button>
          <button class="btn btn-sm btn-primary" onclick="sendDraft(${d.id})"><i class="bi bi-send"></i> Send</button>
          <button class="btn btn-sm btn-outline-danger" onclick="deleteDraft(${d.id})"><i class="bi bi-trash"></i></button>
        </div>
      </div>
    </div></div>`;
  }).join('') : '<div class="text-center py-5 text-muted"><i class="bi bi-inbox" style="font-size:3rem;"></i><div class="mt-2">No drafts. <a href="#" onclick="switchTab(\'compose\')">Compose one →</a></div></div>';
}
function initCompose() {
  const contacts = DB.get('contacts');
  el('c-contact').innerHTML = '<option value="">— Select contact —</option>' +
    contacts.map(c => `<option value="${c.id}">${esc(c.name)} — ${esc(c.company||'No company')}</option>`).join('');
  el('c-template').innerHTML = Object.entries(TEMPLATES).map(([k,t]) =>
    `<option value="${k}">${t.label}</option>`).join('');
  updateTips();
}
function previewTemplate() {
  const cid = parseInt(el('c-contact').value);
  const tmplKey = el('c-template').value;
  const contact = DB.get('contacts').find(c => c.id === cid);
  const { subject, body } = renderTemplate(tmplKey, contact || {});
  sv('c-subject', subject);
  sv('c-body', body);
  updateTips();
  if (contact) {
    el('c-contact-panel').style.display = '';
    el('c-contact-info').innerHTML = `
      <div class="mb-2"><span class="text-muted small">COMPANY</span><br>${esc(contact.company||'—')}</div>
      <div class="mb-2"><span class="text-muted small">INDUSTRY</span><br>${esc(contact.industry||'—')}</div>
      <div class="mb-2"><span class="text-muted small">PHONE</span><br>${esc(contact.phone||'—')}</div>
      <div class="mb-2"><span class="text-muted small">PREV LOAN</span><br>$${fmt(contact.prevLoan||0)}</div>
      <div class="mb-2"><span class="text-muted small">NOTES</span><br>${esc(contact.notes||'—')}</div>`;
  }
}
function updateTips() {
  const tmplKey = el('c-template')?.value;
  const t = TEMPLATES[tmplKey];
  el('c-tips').innerHTML = t ? `<strong style="color:#e3b341;">${t.label}</strong><br>${t.tip}` : '';
}
function saveDraft() {
  const cid = parseInt(el('c-contact').value);
  if (!cid) return toast('Select a contact.','warning');
  const subject = v('c-subject').trim();
  const body = v('c-body').trim();
  if (!subject || !body) return toast('Subject and body are required.','warning');
  const emails = DB.get('emails');
  emails.push({
    id: DB.nextId('emails'), contactId: cid,
    templateName: el('c-template').value, subject, body,
    status: 'draft', replied: false, createdAt: new Date().toISOString(),
  });
  DB.set('emails', emails);
  toast('Draft saved to queue!','success');
  switchTab('drafts');
}
function sendDraft(id) {
  const emails = DB.get('emails');
  const e = emails.find(x => x.id === id);
  if (!e) return;
  const contact = DB.get('contacts').find(c => c.id === e.contactId);
  if (!contact?.email) return toast('Contact has no email address.','danger');
  doSendEmail(e, contact, () => {
    e.status = 'sent'; e.sentAt = new Date().toISOString();
    DB.set('emails', emails);
    toast(`Email sent to ${contact.name}!`,'success');
    renderEmails(); switchTab('drafts');
  });
}
function sendAllDrafts() {
  const drafts = DB.get('emails').filter(e => e.status === 'draft');
  if (!drafts.length) return toast('No drafts to send.','info');
  const contacts = DB.get('contacts');
  let sent = 0;
  drafts.forEach(d => {
    const c = contacts.find(x => x.id === d.contactId);
    if (!c?.email) return;
    doSendEmail(d, c, () => {
      const emails = DB.get('emails');
      const e2 = emails.find(x => x.id === d.id);
      if (e2) { e2.status = 'sent'; e2.sentAt = new Date().toISOString(); DB.set('emails', emails); }
      sent++;
    });
  });
  setTimeout(() => { toast(`Sent ${sent} of ${drafts.length} emails.`,'success'); renderEmails(); switchTab('log'); }, 500);
}
function deleteDraft(id) {
  if (!confirm('Delete this draft?')) return;
  const emails = DB.get('emails').filter(e => e.id !== id);
  DB.set('emails', emails);
  renderDraftQueue();
}
function editDraft(id) {
  const e = DB.get('emails').find(x => x.id === id);
  if (!e) return;
  sv('ed-subject', e.subject); sv('ed-body', e.body); sv('ed-id', id);
  new bootstrap.Modal(el('editDraftModal')).show();
}
function saveDraftEdit(sendNow) {
  const id = parseInt(v('ed-id'));
  const emails = DB.get('emails');
  const e = emails.find(x => x.id === id);
  if (!e) return;
  e.subject = v('ed-subject');
  e.body = v('ed-body');
  DB.set('emails', emails);
  bootstrap.Modal.getInstance(el('editDraftModal'))?.hide();
  if (sendNow) sendDraft(id);
  else { toast('Draft updated.','success'); renderDraftQueue(); }
}
function doSendEmail(draft, contact, onSuccess) {
  const s = getSettings();
  if (s.ejsKey && s.ejsService && s.ejsTemplate) {
    emailjs.init(s.ejsKey);
    emailjs.send(s.ejsService, s.ejsTemplate, {
      to_email: contact.email,
      to_name: contact.name,
      from_name: s.name,
      subject: draft.subject,
      message: draft.body,
    }).then(onSuccess, err => toast('EmailJS error: ' + JSON.stringify(err),'danger'));
  } else {
    // Fallback: open mailto (manual send)
    const url = `mailto:${contact.email}?subject=${encodeURIComponent(draft.subject)}&body=${encodeURIComponent(draft.body)}`;
    window.open(url);
    onSuccess();
  }
}
function openReplyModal(id) {
  sv('reply-log-id', id); sv('reply-body','');
  new bootstrap.Modal(el('replyModal')).show();
}
function markReplied() {
  const id = parseInt(v('reply-log-id'));
  const emails = DB.get('emails');
  const e = emails.find(x => x.id === id);
  if (e) { e.replied = true; e.replyBody = v('reply-body'); e.replyAt = new Date().toISOString(); DB.set('emails', emails); }
  bootstrap.Modal.getInstance(el('replyModal'))?.hide();
  toast('Marked as replied! ✓','success');
  renderEmailLog();
}
function viewReply(id) {
  const e = DB.get('emails').find(x => x.id === id);
  const c = DB.get('contacts').find(x => x.id === e?.contactId);
  if (!e) return;
  el('vr-name').textContent = c?.name || '?';
  el('vr-sent').textContent = e.body || '';
  el('vr-reply').textContent = e.replyBody || 'No reply body saved.';
  new bootstrap.Modal(el('viewReplyModal')).show();
}
function composeFor(contactId) {
  navigate('emails');
  switchTab('compose');
  setTimeout(() => { sv('c-contact', contactId); previewTemplate(); }, 50);
}

// ─────────────────────────────────────────
// DEALS
// ─────────────────────────────────────────
function renderDeals() {
  const deals = DB.get('deals');
  const contacts = DB.get('contacts');
  const ad = el('ad-contact');
  if (ad) ad.innerHTML = contacts.map(c => `<option value="${c.id}">${esc(c.name)} — ${esc(c.company||'')}</option>`).join('');

  // Pipeline summary
  const stageCounts = {};
  STATUSES.forEach(s => { stageCounts[s] = { count:0, value:0 }; });
  deals.forEach(d => { if (stageCounts[d.status]) { stageCounts[d.status].count++; stageCounts[d.status].value += d.loanAmount; } });
  el('pipelineSummary').innerHTML = STATUSES.map(s => `
    <div class="col"><div class="stat-card text-center p-2">
      <div style="font-size:.7rem;text-transform:uppercase;letter-spacing:.08em;color:#8b949e;">${s.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}</div>
      <div class="fw-bold fs-5">${stageCounts[s].count}</div>
      <div style="font-size:.75rem;color:#8b949e;">$${fmt(stageCounts[s].value)}</div>
    </div></div>`).join('');

  const contactMap = Object.fromEntries(contacts.map(c => [c.id, c]));
  el('dealsBody').innerHTML = deals.length ? [...deals].reverse().map(d => {
    const c = contactMap[d.contactId] || {};
    const comm = d.loanAmount * (d.commissionRate/100);
    const closed = d.status === 'closed_won' || d.status === 'closed_lost';
    return `<tr>
      <td><span class="fw-bold">${esc(c.name||'?')}</span><div class="text-muted small">${esc(c.company||'')}</div></td>
      <td class="fw-bold">$${fmt(d.loanAmount)}</td>
      <td>${d.interestRate}%</td>
      <td class="text-success fw-bold">$${fmt2(comm)}</td>
      <td><select class="form-select form-select-sm" style="width:auto;" onchange="updateDealStatus(${d.id},this.value)">
        ${STATUSES.map(s=>`<option ${s===d.status?'selected':''}>${s}</option>`).join('')}
      </select></td>
      <td class="small">${d.createdAt?.slice(0,10)||''}</td>
      <td>${!closed ? `
        <button class="btn btn-sm btn-success me-1" onclick="closeDeal(${d.id},true)">🎉 Won</button>
        <button class="btn btn-sm btn-outline-danger" onclick="closeDeal(${d.id},false)">Lost</button>` : `<span class="text-muted small">${d.closedAt?.slice(0,10)||''}</span>`}
      </td>
    </tr>`;
  }).join('') : '<tr><td colspan="7" class="text-center text-muted py-4">No deals yet.</td></tr>';
}
function addDeal() {
  const contactId = parseInt(v('ad-contact'));
  const amount = parseFloat(v('ad-amount'));
  if (!contactId || !amount) return toast('Contact and loan amount are required.','warning');
  const deals = DB.get('deals');
  deals.push({
    id: DB.nextId('deals'), contactId, loanAmount: amount,
    interestRate: parseFloat(v('ad-rate')||8),
    termMonths: parseInt(v('ad-term')||12),
    commissionRate: parseFloat(v('ad-comm')||2),
    notes: v('ad-notes'), status: 'interested',
    createdAt: new Date().toISOString(),
  });
  DB.set('deals', deals);
  updateContactStatus(contactId, 'interested');
  bootstrap.Modal.getInstance(el('addDealModal'))?.hide();
  toast('Deal added!','success');
  renderDeals();
}
function updateDealStatus(id, status) {
  const deals = DB.get('deals');
  const d = deals.find(x => x.id === id);
  if (d) { d.status = status; DB.set('deals', deals); }
}
function closeDeal(id, won) {
  const deals = DB.get('deals');
  const d = deals.find(x => x.id === id);
  if (d) {
    d.status = won ? 'closed_won' : 'closed_lost';
    d.closedAt = new Date().toISOString();
    DB.set('deals', deals);
    updateContactStatus(d.contactId, d.status);
  }
  toast(won ? 'Deal won! 🎉' : 'Deal marked lost.', won ? 'success' : 'warning');
  renderDeals();
}

// ─────────────────────────────────────────
// COMMISSION
// ─────────────────────────────────────────
function renderCommission() {
  const deals = DB.get('deals').filter(d => d.status === 'closed_won');
  const contacts = DB.get('contacts');
  const contactMap = Object.fromEntries(contacts.map(c => [c.id, c]));
  const now = new Date();
  const thisMonth = now.getMonth();
  const thisYear = now.getFullYear();

  const monthDeals = deals.filter(d => {
    const dt = new Date(d.closedAt);
    return dt.getMonth() === thisMonth && dt.getFullYear() === thisYear;
  });
  const ytdDeals = deals.filter(d => new Date(d.closedAt).getFullYear() === thisYear);

  const monthComm = monthDeals.reduce((s,d) => s + d.loanAmount*(d.commissionRate/100), 0);
  const monthVol  = monthDeals.reduce((s,d) => s + d.loanAmount, 0);
  const ytdComm   = ytdDeals.reduce((s,d) => s + d.loanAmount*(d.commissionRate/100), 0);
  const ytdVol    = ytdDeals.reduce((s,d) => s + d.loanAmount, 0);

  el('commStats').innerHTML = [
    ['Month Deals', monthDeals.length, ''],
    ['Month Volume', '$'+fmt(monthVol), ''],
    ['Month Earned', '$'+fmt2(monthComm), 'text-success'],
    ['YTD Earned', '$'+fmt2(ytdComm), 'text-success'],
  ].map(([label,val,cls]) => `
    <div class="col-md-3"><div class="stat-card">
      <div class="label">${label}</div>
      <div class="value ${cls}">${val}</div>
    </div></div>`).join('');

  el('commMonthLabel').textContent = now.toLocaleString('default',{month:'long',year:'numeric'}) + ' Deals';
  el('commDealsBody').innerHTML = monthDeals.length ? monthDeals.map(d => {
    const c = contactMap[d.contactId] || {};
    return `<tr>
      <td>${esc(c.name||'?')}</td><td>${esc(c.company||'—')}</td>
      <td>$${fmt(d.loanAmount)}</td>
      <td class="text-success fw-bold">$${fmt2(d.loanAmount*(d.commissionRate/100))}</td>
      <td class="small">${d.closedAt?.slice(0,10)||'—'}</td>
    </tr>`;
  }).join('') : '<tr><td colspan="5" class="text-center text-muted py-3">No closed deals this month.</td></tr>';

  // Monthly breakdown
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const byMonth = {};
  months.forEach((m,i) => { byMonth[i] = { name:m, deals:0, volume:0, commission:0 }; });
  ytdDeals.forEach(d => {
    const m = new Date(d.closedAt).getMonth();
    byMonth[m].deals++;
    byMonth[m].volume += d.loanAmount;
    byMonth[m].commission += d.loanAmount*(d.commissionRate/100);
  });
  el('commBreakdown').innerHTML = Object.values(byMonth).filter(m => m.deals > 0).map(m =>
    `<tr><td class="fw-bold">${m.name}</td><td>${m.deals}</td><td>$${fmt(m.volume)}</td><td class="text-success fw-bold">$${fmt2(m.commission)}</td></tr>`
  ).join('') || '<tr><td colspan="4" class="text-center text-muted py-3">No data for this year.</td></tr>';
}

// ─────────────────────────────────────────
// UTILS
// ─────────────────────────────────────────
function el(id) { return document.getElementById(id); }
function v(id) { return el(id)?.value || ''; }
function sv(id, val) { const e = el(id); if (e) e.value = val; }
function esc(str) { return String(str||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function fmt(n) { return Number(n||0).toLocaleString('en-US',{maximumFractionDigits:0}); }
function fmt2(n) { return Number(n||0).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}); }
function getWeekStart(weeksBack) {
  const d = new Date(); d.setDate(d.getDate() - d.getDay() - weeksBack*7); d.setHours(0,0,0,0); return d;
}
function toast(msg, type='info') {
  const div = document.createElement('div');
  div.className = `alert alert-${type} alert-dismissible fade show mb-2`;
  div.innerHTML = `${msg}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
  el('toast-area').prepend(div);
  setTimeout(() => div.remove(), 4000);
}

// ─────────────────────────────────────────
// INIT
// ─────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Sidebar navigation
  document.querySelectorAll('.nav-link[data-page]').forEach(a => {
    a.addEventListener('click', e => { e.preventDefault(); navigate(a.dataset.page); });
  });
  // Email tabs
  document.querySelectorAll('.email-tab').forEach(a => {
    a.addEventListener('click', e => { e.preventDefault(); switchTab(a.dataset.tab); });
  });
  navigate('dashboard');
});
