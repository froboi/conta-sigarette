const state = { user: null, authMode: 'login' };
const $ = (selector) => document.querySelector(selector);

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error || 'Si è verificato un errore.');
  return body;
}
function showToast(message) { const toast = $('#toast'); toast.textContent = message; toast.classList.add('show'); setTimeout(() => toast.classList.remove('show'), 2600); }
function renderWeekly(target, weekly = []) {
  const byDay = Object.fromEntries(weekly.map((item) => [item.day, item.count]));
  const today = new Date(); const monday = new Date(today); monday.setHours(0, 0, 0, 0); monday.setDate(today.getDate() - ((today.getDay() + 6) % 7));
  const days = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']; const counts = days.map((label, index) => { const day = new Date(monday); day.setDate(monday.getDate() + index); const key = day.toISOString().slice(0, 10); return { label, key, count: byDay[key] || 0 }; }); const max = Math.max(...counts.map((item) => item.count), 1);
  $(target).innerHTML = counts.map((item) => `<div class="bar-item"><div class="bar"><i class="${item.key === today.toISOString().slice(0, 10) ? 'today' : ''}" style="height:${Math.max(5, item.count / max * 95)}px"></i></div>${item.label}<br>${item.count}</div>`).join('');
}
function renderStats(stats) {
  $('#today-count').textContent = stats.today; $('#month-count').textContent = stats.month; $('#total-count').textContent = stats.total;
  $('#average-count').textContent = (stats.month / Math.max(new Date().getDate(), 1)).toFixed(1);
  $('#weekly-total').textContent = stats.weekly_total; $('#weekly-average').textContent = stats.weekly_average;
  renderWeekly('#weekly-chart', stats.weekly); renderWeekly('#stats-weekly-chart', stats.weekly);
  $('#today-cigarettes').innerHTML = stats.today_cigarettes.length
    ? stats.today_cigarettes.map((cigarette, index) => `<div class="cigarette-row"><span>Sigaretta ${stats.today_cigarettes.length - index}<small>${new Date(cigarette.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</small></span><button class="remove-cigarette" data-cigarette-id="${cigarette.id}" type="button">Rimuovi</button></div>`).join('')
    : '<p class="muted">Nessuna sigaretta registrata oggi.</p>';
  document.querySelectorAll('.remove-cigarette').forEach((button) => button.addEventListener('click', removeCigarette));
}
async function loadSmoker() { const data = await api('/api/smoker/stats'); renderStats(data.stats); $('#friend-code').textContent = state.user.friend_code || 'Non ancora generato'; await loadSmokerSupport(); }
async function loadSmokerSupport() {
  const data = await api('/api/supporter/dashboard'); const connected = Boolean(data.supported_user); $('#smoker-supported-panel').hidden = !connected;
  if (connected) { $('#smoker-supported-name').textContent = data.supported_user.username; $('#smoker-supported-today').textContent = data.stats.today; $('#smoker-supported-month').textContent = data.stats.month; $('#smoker-supported-total').textContent = data.stats.total; $('#smoker-supported-weekly-total').textContent = data.stats.weekly_total; $('#smoker-supported-weekly-average').textContent = data.stats.weekly_average; renderWeekly('#smoker-supported-chart', data.stats.weekly); }
}
async function removeCigarette(event) {
  if (!window.confirm('Rimuovere questa sigaretta?')) return;
  try { const data = await api(`/api/smoker/cigarettes/${event.currentTarget.dataset.cigaretteId}`, { method: 'DELETE' }); renderStats(data.stats); showToast('Sigaretta rimossa'); }
  catch (error) { showToast(error.message); }
}
async function loadSupporter() {
  const data = await api('/api/supporter/dashboard'); const connected = Boolean(data.supported_user); $('#connect-panel').hidden = connected; $('#supported-panel').hidden = !connected;
  if (connected) { $('#supported-name').textContent = data.supported_user.username; $('#supported-today').textContent = data.stats.today; $('#supported-month').textContent = data.stats.month; $('#supported-total').textContent = data.stats.total; $('#supporter-weekly-total').textContent = data.stats.weekly_total; $('#supporter-weekly-average').textContent = data.stats.weekly_average; renderWeekly('#supported-chart', data.stats.weekly); }
}
async function showApp(user) {
  state.user = user; $('#auth-view').hidden = true; $('#app-view').hidden = false; $('#session-controls').hidden = false; $('#user-label').textContent = user.username;
  const smoker = user.role === 'fumatore'; $('#dashboard-title').textContent = smoker ? 'Il tuo percorso' : 'Dashboard supporto'; $('#role-pill').textContent = smoker ? 'Fumatore' : 'Sostenitore'; $('#smoker-dashboard').hidden = !smoker; $('#supporter-dashboard').hidden = smoker; $('#smoker-nav').hidden = !smoker;
  try { if (smoker) await loadSmoker(); else await loadSupporter(); } catch (error) { showToast(error.message); }
}
function setAuthMode(mode) { state.authMode = mode; document.querySelectorAll('.tab').forEach((tab) => tab.classList.toggle('active', tab.dataset.authMode === mode)); $('#role-field').hidden = mode === 'login'; $('#auth-submit').textContent = mode === 'login' ? 'Accedi' : 'Crea account'; $('#password').autocomplete = mode === 'login' ? 'current-password' : 'new-password'; $('#auth-message').textContent = ''; }
function setPage(pageId) { document.querySelectorAll('.page-panel').forEach((panel) => { panel.hidden = panel.id !== pageId; }); document.querySelectorAll('#smoker-nav .page-tab').forEach((tab) => tab.classList.toggle('active', tab.dataset.page === pageId)); }

document.addEventListener('DOMContentLoaded', () => {
  const authForm = $('#auth-form');
  if (!authForm) return;
  authForm.addEventListener('submit', async (event) => { event.preventDefault(); const button = $('#auth-submit'); button.disabled = true; try { const data = await api(`/api/auth/${state.authMode}`, { method: 'POST', body: JSON.stringify({ username: $('#username').value.trim(), password: $('#password').value, role: $('#role').value }) }); showApp(data.user); } catch (error) { $('#auth-message').textContent = error.message; } finally { button.disabled = false; } });
  document.querySelectorAll('.tab').forEach((tab) => tab.addEventListener('click', () => setAuthMode(tab.dataset.authMode)));
  document.querySelectorAll('#smoker-nav .page-tab').forEach((tab) => tab.addEventListener('click', () => setPage(tab.dataset.page)));
  $('#add-cigarette').addEventListener('click', async () => { const button = $('#add-cigarette'); button.disabled = true; try { const data = await api('/api/smoker/cigarettes', { method: 'POST' }); renderStats(data.stats); showToast('Sigaretta registrata'); } catch (error) { showToast(error.message); } finally { button.disabled = false; } });
  $('#friend-code-button').addEventListener('click', async () => { try { const data = await api('/api/smoker/friend-code', { method: 'POST' }); state.user.friend_code = data.friend_code; $('#friend-code').textContent = data.friend_code; showToast('Codice amico pronto'); } catch (error) { showToast(error.message); } });
  $('#connect-form').addEventListener('submit', async (event) => { event.preventDefault(); try { await api('/api/supporter/connect', { method: 'POST', body: JSON.stringify({ friend_code: $('#friend-code-input').value }) }); await loadSupporter(); showToast('Collegamento effettuato'); } catch (error) { $('#connect-message').textContent = error.message; } });
  const smokerConnectForm = $('#smoker-connect-form');
  if (smokerConnectForm) smokerConnectForm.addEventListener('submit', async (event) => { event.preventDefault(); try { await api('/api/supporter/connect', { method: 'POST', body: JSON.stringify({ friend_code: $('#smoker-friend-code-input').value }) }); await loadSmokerSupport(); $('#smoker-connect-message').textContent = ''; showToast('Ora sostieni questo amico'); } catch (error) { $('#smoker-connect-message').textContent = error.message; } });
  $('#logout-button').addEventListener('click', async () => { try { await api('/api/auth/logout', { method: 'POST' }); window.location.reload(); } catch (error) { showToast(error.message); } });
  api('/api/auth/me').then((data) => showApp(data.user)).catch(() => {});
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('/static/service-worker.js').catch(() => {});
});
