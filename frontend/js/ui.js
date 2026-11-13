// Sayfaların ortak kullandığı yardımcılar:
// mesaj kutusu, giriş kontrolü, çıkış, tarih/saat biçimleme.

const DAY_NAMES = ['Pazar', 'Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi'];

function showMessage(text, type = 'info') {
  const box = document.getElementById('messages');
  box.innerHTML = '';
  const div = document.createElement('div');
  div.className = `flash ${type}`;
  div.textContent = text;
  box.appendChild(div);
  box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function clearMessages() {
  document.getElementById('messages').innerHTML = '';
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

const pad = (n) => String(n).padStart(2, '0');

// "2026-11-13" -> Date (yerel saat). new Date("2026-11-13") UTC kabul ettiği için elle ayırıyoruz.
function parseDate(text) {
  const [y, m, d] = text.split('-').map(Number);
  return new Date(y, m - 1, d);
}

function toIsoDate(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

// Date -> "13.11.2026 Cuma"
function formatDay(date) {
  return `${pad(date.getDate())}.${pad(date.getMonth() + 1)}.${date.getFullYear()} ${DAY_NAMES[date.getDay()]}`;
}

// Date -> "14:00"
function formatTime(date) {
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

// Giriş yapılmamışsa giriş sayfasına yönlendirir, yapılmışsa kullanıcıyı döndürür.
async function requireLogin() {
  try {
    const { user } = await api.get('/auth/me');
    document.getElementById('user-name').textContent = user.full_name;
    return user;
  } catch (err) {
    if (err.status === 401) {
      window.location.href = 'index.html';
    } else {
      showMessage(err.message, 'error');
    }
    throw err;
  }
}

function setupLogout() {
  document.getElementById('logout').addEventListener('click', async () => {
    await api.post('/auth/logout').catch(() => {});
    window.location.href = 'index.html';
  });
}
