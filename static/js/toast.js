// Lightweight toast for htmx-driven actions: a view sets
// `HX-Trigger: {"showToast": {"message": "..."}}` on its response and this
// listener surfaces it, without needing a full page reload like
// django.contrib.messages does.

function showToast(message) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = 'toast-item';
    toast.textContent = message;
    container.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('show'));
    setTimeout(() => {
        toast.classList.remove('show');
        toast.addEventListener('transitionend', () => toast.remove(), { once: true });
    }, 2500);
}

document.addEventListener('DOMContentLoaded', () => {
    document.body.addEventListener('showToast', (event) => {
        showToast(event.detail.message);
    });
});
