// Masks any input marked with [data-currency-mask] as Brazilian currency
// while typing (17.500,00). Applied globally so every monetary field in the
// platform behaves the same way, without each page wiring it up by hand.

function formatCurrencyDigits(rawValue) {
    const digits = rawValue.replace(/\D/g, '').padStart(3, '0');
    const cents = digits.slice(-2);
    const intPart = digits.slice(0, -2).replace(/^0+(?=\d)/, '');
    return `${intPart.replace(/\B(?=(\d{3})+(?!\d))/g, '.')},${cents}`;
}

function initCurrencyMasks() {
    document.querySelectorAll('[data-currency-mask]').forEach((input) => {
        if (input.dataset.currencyMaskBound) return;
        input.dataset.currencyMaskBound = 'true';
        input.addEventListener('input', () => {
            input.value = formatCurrencyDigits(input.value);
        });
    });
}

document.addEventListener('DOMContentLoaded', initCurrencyMasks);
document.addEventListener('htmx:afterSwap', initCurrencyMasks);
