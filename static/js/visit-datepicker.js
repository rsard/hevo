function initVisitDatepicker() {
    const input = document.getElementById('visit-date-input');
    if (!input || input.dataset.datepickerInitialized) return;
    input.dataset.datepickerInitialized = 'true';
    new Datepicker(input, {
        format: 'yyyy-mm-dd',
        autohide: true,
        todayHighlight: true,
        language: 'pt-BR',
    });
}

document.addEventListener('DOMContentLoaded', initVisitDatepicker);

document.addEventListener('htmx:afterSwap', (event) => {
    if (event.detail.target.id === 'visits-section') {
        initVisitDatepicker();
    }
});

document.addEventListener('htmx:configRequest', (event) => {
    const dateInput = document.getElementById('visit-date-input');
    const timeInput = document.getElementById('visit-time-input');
    if (dateInput && timeInput && dateInput.value && timeInput.value) {
        event.detail.parameters.scheduled_at = `${dateInput.value} ${timeInput.value}`;
    }
});
