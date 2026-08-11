document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('id_started_at');
    if (!input) return;
    new Datepicker(input, {
        format: 'dd/mm/yyyy',
        autohide: true,
        todayHighlight: true,
        language: 'pt-BR',
    });
});
