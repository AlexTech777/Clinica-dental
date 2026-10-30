(() => {
  const root = document.documentElement;
  const themeOptions = [...document.querySelectorAll('input[name="theme"]')];
  const savedTheme = (() => {
    try {
      const theme = localStorage.getItem('dental-theme');
      return theme === 'rosa' ? 'verde' : ['azul', 'gris', 'verde'].includes(theme) ? theme : 'azul';
    } catch { return 'azul'; }
  })();
  root.dataset.theme = savedTheme;
  themeOptions.forEach(option => {
    option.checked = option.value === savedTheme;
    option.addEventListener('change', () => {
      root.dataset.theme = option.value;
      try { localStorage.setItem('dental-theme', option.value); } catch {}
    });
  });

  const appointmentDialog = document.querySelector('#appointment-dialog');
  const waitlistDialog = document.querySelector('#waitlist-dialog');
  const appointmentForm = document.querySelector('#appointment-form');
  const createFields = [...document.querySelectorAll('.create-fields')];
  const nameInputs = appointmentForm ? [...appointmentForm.querySelectorAll('[name="name"],[name="phone"],[name="treatment"],[name="session_number"],[name="session_total"]')] : [];
  let lastTrigger = null;
  const close = dialog => { if (dialog?.open) dialog.close(); };
  const show = (dialog, trigger) => {
    lastTrigger = trigger;
    if (dialog?.showModal) dialog.showModal();
    const first = dialog?.querySelector('input:not([disabled]),select:not([disabled])');
    if (first) setTimeout(() => first.focus(), 20);
  };
  const setCreateMode = () => {
    if (!appointmentForm) return;
    appointmentForm.action = '/appointments/create';
    document.querySelector('#form-title').textContent = 'Agendar paciente';
    document.querySelector('#form-eyebrow').textContent = 'NUEVA CITA';
    document.querySelector('#form-intro').textContent = 'Registra la información mínima para organizar la visita.';
    appointmentForm.querySelector('button[type="submit"]').textContent = 'Guardar cita';
    createFields.forEach(field => field.hidden = false);
    nameInputs.forEach(input => { input.disabled = false; input.required = ['name','phone','treatment'].includes(input.name); });
    const day = appointmentForm.elements.day;
    day.min = new Date().toLocaleDateString('en-CA');
    day.value = day.min;
  };
  document.querySelectorAll('[data-open-create]').forEach(button => button.addEventListener('click', () => { setCreateMode(); show(appointmentDialog, button); }));
  document.querySelectorAll('.edit-appointment').forEach(button => button.addEventListener('click', () => {
    setCreateMode();
    appointmentForm.action = `/appointments/${button.dataset.id}/edit`;
    document.querySelector('#form-title').textContent = 'Editar cita';
    document.querySelector('#form-eyebrow').textContent = 'ACTUALIZAR HORARIO';
    document.querySelector('#form-intro').textContent = 'Ajusta la fecha, hora o duración de la cita.';
    appointmentForm.querySelector('button[type="submit"]').textContent = 'Guardar cambios';
    createFields.forEach(field => field.hidden = true);
    nameInputs.forEach(input => { input.disabled = true; input.required = false; });
    appointmentForm.elements.day.value = button.dataset.date;
    appointmentForm.elements.hour.value = button.dataset.time;
    appointmentForm.elements.duration.value = button.dataset.duration;
    show(appointmentDialog, button);
  }));
  document.querySelectorAll('[data-open-waitlist]').forEach(button => button.addEventListener('click', () => show(waitlistDialog, button)));
  document.querySelectorAll('[data-close-dialog]').forEach(button => button.addEventListener('click', () => close(button.closest('dialog'))));
  [appointmentDialog, waitlistDialog].forEach(dialog => dialog?.addEventListener('close', () => { if (lastTrigger?.isConnected) lastTrigger.focus(); }));
  document.querySelectorAll('.flash-close').forEach(button => button.addEventListener('click', () => button.closest('.flash').remove()));
  const menuButton = document.querySelector('.mobile-menu');
  const sidebar = document.querySelector('.sidebar');
  menuButton?.addEventListener('click', () => {
    const open = sidebar.classList.toggle('open');
    menuButton.setAttribute('aria-expanded', String(open));
    menuButton.setAttribute('aria-label', open ? 'Cerrar navegación' : 'Abrir navegación');
  });
  document.addEventListener('click', event => {
    if (event.target.closest('a.nav-item') && sidebar.classList.contains('open')) sidebar.classList.remove('open');
  });
  if (location.hash === '#agendar' && appointmentDialog) {
    setCreateMode(); show(appointmentDialog, document.querySelector('[data-open-create]'));
  }
})();
