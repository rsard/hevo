document.addEventListener('htmx:afterRequest', (event) => {
    if (event.detail.successful && event.target.matches('.note-form')) {
        event.target.reset();
    }
});
