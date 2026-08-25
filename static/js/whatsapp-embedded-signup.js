// Meta Embedded Signup: lets a venue connect their own WhatsApp Business
// number to Hevo without handing over the account itself. Two independent
// async signals come back from the popup — FB.login's callback (an auth
// code) and a window "message" event (the phone/WABA the venue picked) —
// we send both to the backend once we have the phone/WABA, whichever code
// we've received by then.

let embeddedSignupCode = null;
let connectionSucceeded = false;

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
    let origin;
    try {
        origin = new URL(event.origin).hostname;
    } catch {
        return;
    }
    if (!/\.facebook\.com$/.test(origin)) return;

    let data;
    try {
        data = JSON.parse(event.data);
    } catch {
        console.debug('[WA signup] non-JSON message from ' + origin + ': ' + event.data);
        return; // Meta also posts non-JSON messages we don't care about
    }
    console.debug('[WA signup] message from ' + origin + ': ' + JSON.stringify(data));
    if (data.type !== 'WA_EMBEDDED_SIGNUP') return;

    if (data.event === 'FINISH' || data.event === 'FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING') {
        // Coexistence (existing WhatsApp Business App number) doesn't return a
        // phone_number_id here — the number already exists, so the backend
        // looks it up from the WABA instead of registering a new one.
        submitConnection(data.data.phone_number_id, data.data.waba_id);
    } else if (data.event === 'CANCEL' || data.event === 'ERROR') {
        console.debug('[WA signup] cancel/error event: ' + JSON.stringify(data));
        setStatus('Conexão cancelada ou interrompida. Tente novamente.', true);
    }
});

function submitConnection(phoneNumberId, wabaId) {
    console.debug('[WA signup] submitConnection: ' + JSON.stringify({ phoneNumberId, wabaId, code: embeddedSignupCode }));
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
            console.debug('[WA signup] connect response: ' + JSON.stringify({ ok, body }));
            if (ok) {
                connectionSucceeded = true;
                setStatus('WhatsApp conectado com sucesso! Recarregando...', false);
                setTimeout(() => window.location.reload(), 1000);
            } else {
                setStatus(body.error || 'Não foi possível concluir a conexão.', true);
            }
        })
        .catch((err) => {
            console.debug('[WA signup] connect request failed: ' + err);
            setStatus('Não foi possível concluir a conexão. Tente novamente.', true);
        });
}

function setStatus(text, isError) {
    const el = document.getElementById('whatsapp-connect-status');
    if (!el) return;
    el.textContent = text;
    el.className = isError ? 'small text-danger mt-2' : 'small text-muted mt-2';
}

function launchWhatsAppEmbeddedSignup() {
    embeddedSignupCode = null;
    connectionSucceeded = false;
    FB.login(
        (response) => {
            console.debug('[WA signup] FB.login callback: ' + JSON.stringify(response));
            if (response.authResponse && response.authResponse.code) {
                embeddedSignupCode = response.authResponse.code;
            } else if (!connectionSucceeded) {
                // The "message" event (not this callback) is what actually completes
                // the connection — by the time FB.login's callback fires the popup
                // has already closed, so only show "cancelled" if that didn't happen.
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
