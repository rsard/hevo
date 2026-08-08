document.addEventListener('click', (event) => {
    const row = event.target.closest('[data-href]');
    if (row && !event.target.closest('a, button')) {
        window.location.href = row.dataset.href;
    }
});
