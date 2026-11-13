// Rezervasyon sayfası (reserve.html)
// Backend'den günün doluluk tablosunu alır, tabloyu ve formu çizer.

const STATE_TITLES = { free: 'Boş', taken: 'Dolu', mine: 'Sizin rezervasyonunuz', past: 'Geçmiş saat' };

const params = new URLSearchParams(window.location.search);
let currentDate = params.get('date') || toIsoDate(new Date());
let currentKind = params.get('kind') || 'all';
let info = null; // son alınan /availability cevabı

const el = (id) => document.getElementById(id);

async function load() {
  try {
    info = await api.get(`/availability?date=${currentDate}&kind=${currentKind}`);
  } catch (err) {
    showMessage(err.message, 'error');
    return;
  }
  currentDate = info.date;
  history.replaceState(null, '', `?date=${currentDate}&kind=${currentKind}`);
  render();
}

function shiftDay(days) {
  const d = parseDate(currentDate);
  d.setDate(d.getDate() + days);
  currentDate = toIsoDate(d);
  clearMessages();
  load();
}

function render() {
  el('day-title').textContent = formatDay(parseDate(info.date));

  const dateInput = el('date-input');
  dateInput.value = info.date;
  dateInput.min = info.today;
  dateInput.max = info.max_date;
  el('kind-select').value = currentKind;
  el('prev-day').disabled = info.date <= info.today;
  el('next-day').disabled = info.date >= info.max_date;

  // Form seçenekleri (seçili değerleri koru)
  const spaceSel = el('f-space');
  const keepSpace = spaceSel.value;
  spaceSel.innerHTML = info.spaces.map((s) =>
    `<option value="${s.id}">${escapeHtml(s.name)} (${s.capacity} kişilik, ${s.floor}. kat)</option>`).join('');
  if (info.spaces.some((s) => String(s.id) === keepSpace)) spaceSel.value = keepSpace;

  const hourSel = el('f-hour');
  const keepHour = hourSel.value;
  hourSel.innerHTML = info.hours.map((h) => `<option value="${h}">${pad(h)}:00</option>`).join('');
  if (keepHour) hourSel.value = keepHour;

  const durSel = el('f-duration');
  const keepDur = durSel.value;
  durSel.innerHTML = Array.from({ length: info.max_hours }, (_, i) =>
    `<option value="${i + 1}">${i + 1} saat</option>`).join('');
  if (keepDur) durSel.value = keepDur;

  // Doluluk tablosu
  el('grid-head').innerHTML = '<th>Alan</th>' + info.hours.map((h) => `<th>${pad(h)}</th>`).join('');

  if (info.spaces.length === 0) {
    el('grid-body').innerHTML = `<tr><td colspan="${info.hours.length + 1}">Gösterilecek alan yok.</td></tr>`;
    return;
  }

  el('grid-body').innerHTML = info.spaces.map((s) => `
    <tr>
      <th class="space">${escapeHtml(s.name)}
        <small>${s.kind === 'room' ? 'Grup odası' : 'Masa'} · ${s.capacity} kişi</small>
      </th>
      ${s.slots.map((state, i) => `
        <td class="cell ${state}" title="${STATE_TITLES[state]}"
            ${state === 'free' ? `data-space="${s.id}" data-hour="${info.hours[i]}"` : ''}></td>`).join('')}
    </tr>`).join('');
}

// Boş hücreye tıklanınca formu doldur
el('grid-body').addEventListener('click', (e) => {
  const td = e.target.closest('td.cell.free');
  if (!td) return;
  el('f-space').value = td.dataset.space;
  el('f-hour').value = td.dataset.hour;
  document.querySelectorAll('td.selected').forEach((x) => x.classList.remove('selected'));
  td.classList.add('selected');
  el('reserve-form').scrollIntoView({ behavior: 'smooth', block: 'center' });
});

el('reserve-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    const data = await api.post('/reservations', {
      space_id: Number(el('f-space').value),
      date: currentDate,
      start_hour: Number(el('f-hour').value),
      duration: Number(el('f-duration').value),
    });
    showMessage(data.message, 'success');
    load();
  } catch (err) {
    showMessage(err.message, 'error');
  }
});

el('prev-day').addEventListener('click', () => shiftDay(-1));
el('next-day').addEventListener('click', () => shiftDay(1));
el('date-input').addEventListener('change', (e) => {
  if (e.target.value) { currentDate = e.target.value; clearMessages(); load(); }
});
el('kind-select').addEventListener('change', (e) => { currentKind = e.target.value; load(); });

setupLogout();
requireLogin().then(load).catch(() => {});
