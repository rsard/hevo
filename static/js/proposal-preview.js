// Lead detail: keeps the proposal price in sync with the selected package,
// and opens a live PDF preview in a new tab without saving/sending anything.
// The price field's currency-as-you-type mask is shared (static/js/currency-mask.js).

function initProposalPreview() {
    const form = document.getElementById('proposal-form');
    const previewBtn = document.getElementById('proposal-preview-btn');
    const packageSelect = document.getElementById('proposal-package');
    const priceInput = document.getElementById('proposal-price');
    const notesInput = document.getElementById('proposal-notes');
    if (!form || !previewBtn || !packageSelect || !priceInput) return;

    if (!priceInput.value) {
        const selected = packageSelect.selectedOptions[0];
        if (selected) priceInput.value = selected.dataset.price;
    }

    packageSelect.addEventListener('change', () => {
        const selected = packageSelect.selectedOptions[0];
        if (selected) priceInput.value = selected.dataset.price;
    });

    previewBtn.addEventListener('click', () => {
        const params = new URLSearchParams({
            package: packageSelect.value,
            price: priceInput.value,
            notes: notesInput ? notesInput.value : '',
        });
        window.open(`${form.dataset.previewUrl}?${params}`, '_blank');
    });
}

document.addEventListener('DOMContentLoaded', initProposalPreview);
document.addEventListener('htmx:afterSwap', initProposalPreview);
