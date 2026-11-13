// Giriş / kayıt sayfası (index.html)

const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');

function showTab(name) {
  document.querySelectorAll('.tab').forEach((t) => t.classList.toggle('active', t.dataset.tab === name));
  loginForm.classList.toggle('hidden', name !== 'login');
  registerForm.classList.toggle('hidden', name !== 'register');
}

document.querySelectorAll('.tab').forEach((tab) => {
  tab.addEventListener('click', () => { clearMessages(); showTab(tab.dataset.tab); });
});

// Zaten giriş yapılmışsa doğrudan rezervasyon sayfasına geç
api.get('/auth/me').then(() => { window.location.href = 'reserve.html'; }).catch(() => {});

loginForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = new FormData(loginForm);
  try {
    await api.post('/auth/login', {
      student_no: form.get('student_no'),
      password: form.get('password'),
    });
    window.location.href = 'reserve.html';
  } catch (err) {
    showMessage(err.message, 'error');
  }
});

registerForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = new FormData(registerForm);
  try {
    const data = await api.post('/auth/register', Object.fromEntries(form));
    registerForm.reset();
    showTab('login');
    loginForm.elements.student_no.value = form.get('student_no');
    showMessage(data.message, 'success');
  } catch (err) {
    showMessage(err.message, 'error');
  }
});
