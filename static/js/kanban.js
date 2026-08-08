let justDragged = false;

function updateColumnCount(column) {
    const countBadge = column.closest('.kanban-column').querySelector('.kanban-count');
    countBadge.textContent = column.children.length;
}

function initKanban() {
    document.querySelectorAll('.kanban-column-cards').forEach((column) => {
        if (column.dataset.sortableInitialized) return;
        column.dataset.sortableInitialized = 'true';
        new Sortable(column, {
            group: 'leads',
            animation: 150,
            ghostClass: 'sortable-ghost',
            chosenClass: 'sortable-chosen',
            onEnd: (event) => {
                if (event.from === event.to && event.oldIndex === event.newIndex) return;
                justDragged = true;
                updateColumnCount(event.from);
                updateColumnCount(event.to);
                const card = event.item;
                htmx.ajax('POST', card.dataset.stageUrl, {
                    target: card,
                    swap: 'outerHTML',
                    values: { stage: event.to.dataset.stage },
                });
            },
        });
    });
}

initKanban();

document.addEventListener('htmx:afterSwap', (event) => {
    if (event.detail.target.id === 'kanban-container' || event.detail.target.id === 'kanban-board') {
        initKanban();
    }
});

document.addEventListener('click', (event) => {
    if (justDragged) {
        justDragged = false;
        return;
    }
    const card = event.target.closest('.kanban-card');
    if (card && card.dataset.href) {
        window.location.href = card.dataset.href;
    }
});
