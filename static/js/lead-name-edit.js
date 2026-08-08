document.addEventListener('click', (event) => {
    const trigger = event.target.closest('.lead-name-edit-trigger');
    if (!trigger) return;
    const wrapper = trigger.closest('.lead-name-field');
    wrapper.querySelector('h1').classList.add('d-none');
    trigger.classList.add('d-none');
    const form = wrapper.querySelector('.lead-name-form');
    form.classList.remove('d-none');
    form.classList.add('d-flex');
    form.querySelector('input').focus();
});
