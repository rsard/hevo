function getCookie(name) {
    const match = document.cookie.match('(?:^|; )' + name + '=([^;]*)');
    return match ? decodeURIComponent(match[1]) : null;
}

document.addEventListener('htmx:configRequest', (event) => {
    event.detail.headers['X-CSRFToken'] = getCookie('csrftoken');
});
