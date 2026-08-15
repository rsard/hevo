// Meta Embedded Signup: lets a venue connect their own WhatsApp Business
// number to Hevo without handing over the account itself. Two independent
// async signals come back from the popup — FB.login's callback (an auth
// code) and a window "message" event (the phone/WABA the venue picked) —
// we send both to the backend once we have the phone/WABA, whichever code
// we've received by then.

let embeddedSignupCode = null;

window.fbAsyncInit = function () {
    FB.init({
        appId: window.HEVO_FACEBOOK_APP_ID,
        autoLogAppEvents: true,
        xfbml: false,
        version: window.HEVO_WHATSAPP_API_VERSION || 'v21.0',
    });
};

(function loadFacebookSdk(doc, tag, id) {
    if (doc.getElementById(id)) return;
    const firstScript = doc.getElementsByTagName(tag)[0];
    const script = doc.createElement(tag);
    script.id = id;
    script.src = 'https://connect.facebook.net/pt_BR/sdk.js';
    firstScript.parentNode.insertBefore(script, firstScript);
}(document, 'script', 'facebook-jssdk'));

window.addEventListener('message', (event) => {
    if (!/\.facebook\.com$/.test(new URL(event.origin).hostname)) return;

    let data;
    try {
        data = JSON.parse(event.data);
    } catch {
        return; // Meta also posts non-JSON messages we don't care about
    }
    if (data.type !== 'WA_EMBEDDED_SIGNUP') return;

    if (data.event === 'FINISH' || data.event === 'FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING') {
        // Coexistence (existing WhatsApp Business App number) doesn't return a
        // phone_number_id here — the number already exists, so the backend
        // looks it up from the WABA instead of registering a new one.
        submitConnection(data.data.phone_number_id, data.data.waba_id);
    } else if (data.event === 'CANCEL' || data.event === 'ERROR') {
        setStatus('Conexão cancelada ou interrompida. Tente novamente.', true);
    }
});

function submitConnection(phoneNumberId, wabaId) {
    setStatus('Conectando...', false);
    fetch(window.HEVO_WHATSAPP_CONNECT_URL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({
            phone_number_id: phoneNumberId,
            waba_id: wabaId,
            code: embeddedSignupCode,
        }),
    })
        .then((response) => response.json().then((body) => ({ ok: response.ok, body })))
        .then(({ ok, body }) => {
            if (ok) {
                setStatus('WhatsApp conectado com sucesso! Recarregando...', false);
                setTimeout(() => window.location.reload(), 1000);
            } else {
                setStatus(body.error || 'Não foi possível concluir a conexão.', true);
            }
        })
        .catch(() => setStatus('Não foi possível concluir a conexão. Tente novamente.', true));
}

function setStatus(text, isError) {
    const el = document.getElementById('whatsapp-connect-status');
    if (!el) return;
    el.textContent = text;
    el.className = isError ? 'small text-danger mt-2' : 'small text-muted mt-2';
}

function launchWhatsAppEmbeddedSignup() {
    embeddedSignupCode = null;
    FB.login(
        (response) => {
            if (response.authResponse && response.authResponse.code) {
                embeddedSignupCode = response.authResponse.code;
            } else {
                setStatus('Login cancelado.', true);
            }
        },
        {
            config_id: window.HEVO_WHATSAPP_EMBEDDED_SIGNUP_CONFIG_ID,
            response_type: 'code',
            override_default_response_type: true,
            extras: {
                setup: {},
                featureType: 'whatsapp_business_app_onboarding',
                sessionInfoVersion: '3',
                version: 'v4',
            },
        },
    );
}

document.addEventListener('DOMContentLoaded', () => {
    const button = document.getElementById('whatsapp-connect-btn');
    if (button) {
        button.addEventListener('click', launchWhatsAppEmbeddedSignup);
    }
});
