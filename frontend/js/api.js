// Backend ile konuşan tek dosya.
// Bütün istekler buradan geçer; sayfalar fetch'i doğrudan kullanmaz.
// Backend hata döndürürse ({"error": "..."}) bu mesajla bir Error fırlatılır.

const api = {
  async request(path, { method = 'GET', body } = {}) {
    let res;
    try {
      res = await fetch('/api' + path, {
        method,
        headers: body ? { 'Content-Type': 'application/json' } : {},
        body: body ? JSON.stringify(body) : undefined,
        credentials: 'same-origin', // oturum çerezi gönderilsin
      });
    } catch {
      throw Object.assign(new Error('Sunucuya ulaşılamadı. Uygulama çalışıyor mu?'), { status: 0 });
    }

    let data = null;
    try { data = await res.json(); } catch { /* boş cevap */ }

    if (!res.ok) {
      const message = (data && data.error) || `Beklenmeyen hata (${res.status}).`;
      throw Object.assign(new Error(message), { status: res.status });
    }
    return data;
  },

  get(path) { return this.request(path); },
  post(path, body = {}) { return this.request(path, { method: 'POST', body }); },
};
