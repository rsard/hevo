function initVisitDatepicker() {
    const input = document.getElementById('visit-date-input');
    if (!input || input.dataset.datepickerInitialized) return;
    input.dataset.datepickerInitialized = 'true';
    new Datepicker(input, {
        format: 'dd/mm/yyyy',
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
    if (!dateInput || !timeInput || !timeInput.value) return;

    // Read through the Datepicker instance instead of dateInput.value: the
    // display format is dd/mm/yyyy, but the server expects an ISO date.
    const date = dateInput.datepicker && dateInput.datepicker.getDate();
    if (!date) return;

    const isoDate = [
        date.getFullYear(),
        String(date.getMonth() + 1).padStart(2, '0'),
        String(date.getDate()).padStart(2, '0'),
    ].join('-');

    event.detail.parameters.scheduled_at = `${isoDate} ${timeInput.value}`;
});
