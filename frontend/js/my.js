// Rezervasyonlarım sayfası (my.html)
// Aktif ve geçmiş rezervasyonları listeler, iptal işlemini yapar.

const STATE_LABELS = {
  upcoming: 'Yaklaşan', ongoing: 'Devam ediyor', completed: 'Tamamlandı', cancelled: 'İptal edildi',
};

const badge = (state) => `<span class="badge ${state}">${STATE_LABELS[state]}</span>`;

function timeRange(r) {
  return `${formatTime(new Date(r.starts_at))} - ${formatTime(new Date(r.ends_at))}`;
}

function renderActive(list) {
  const box = document.getElementById('active-list');
  if (list.length === 0) {
    box.innerHTML = '<p class="muted">Aktif rezervasyonunuz yok. <a href="reserve.html">Rezervasyon yapın</a></p>';
    return;
  }
  box.innerHTML = `
    <table class="list">
      <thead><tr><th>Alan</th><th>Tarih</th><th>Saat</th><th>Durum</th><th></th></tr></thead>
      <tbody>${list.map((r) => `
        <tr>
          <td>${escapeHtml(r.space_name)} <small class="muted">${r.floor}. kat</small></td>
          <td>${formatDay(new Date(r.starts_at))}</td>
          <td>${timeRange(r)}</td>
          <td>${badge(r.state)}</td>
          <td>${r.can_cancel ? `
            <form class="inline cancel-form" data-id="${r.id}">
              <input name="reason" placeholder="İptal nedeni (isteğe bağlı)" maxlength="200">
              <button type="submit" class="danger">İptal Et</button>
            </form>` : '<small class="muted">Başlamış rezervasyon iptal edilemez</small>'}
          </td>
        </tr>`).join('')}
      </tbody>
    </table>`;
}

function renderPast(list) {
  const box = document.getElementById('past-list');
  if (list.length === 0) {
    box.innerHTML = '<p class="muted">Henüz geçmiş rezervasyonunuz yok.</p>';
    return;
  }
  box.innerHTML = `
    <table class="list">
      <thead><tr><th>Alan</th><th>Tarih</th><th>Saat</th><th>Durum</th><th>Not</th></tr></thead>
      <tbody>${list.map((r) => {
        let note = '';
        if (r.state === 'cancelled') {
          const at = new Date(r.cancelled_at);
          note = `${formatDay(at).split(' ')[0]} ${formatTime(at)} tarihinde iptal edildi`;
          if (r.cancel_reason) note += `: “${escapeHtml(r.cancel_reason)}”`;
        }
        return `
        <tr class="${r.state}">
          <td>${escapeHtml(r.space_name)}</td>
          <td>${formatDay(new Date(r.starts_at))}</td>
          <td>${timeRange(r)}</td>
          <td>${badge(r.state)}</td>
          <td class="muted">${note}</td>
        </tr>`;
      }).join('')}
      </tbody>
    </table>`;
}

async function load() {
  try {
    const data = await api.get('/reservations/mine');
    renderActive(data.active);
    renderPast(data.past);
  } catch (err) {
    showMessage(err.message, 'error');
  }
}

// İptal formları sonradan çizildiği için olayı üst kutuda dinliyoruz
document.getElementById('active-list').addEventListener('submit', async (e) => {
  const form = e.target.closest('.cancel-form');
  if (!form) return;
  e.preventDefault();
  if (!confirm('Bu rezervasyonu iptal etmek istediğinize emin misiniz?')) return;
  try {
    const data = await api.post(`/reservations/${form.dataset.id}/cancel`, {
      reason: form.elements.reason.value,
    });
    showMessage(data.message, 'success');
    load();
  } catch (err) {
    showMessage(err.message, 'error');
  }
});

setupLogout();
requireLogin().then(load).catch(() => {});
