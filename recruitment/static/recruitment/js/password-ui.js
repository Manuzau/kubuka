/**
 * KUBUKA - UI de palavras-passe: botão mostrar/ocultar em qualquer
 * input[type=password], checklist de requisitos em tempo real nos campos
 * marcados com [data-password-strength], e indicador de correspondência nos
 * campos marcados com [data-password-confirm].
 */
(function () {
    'use strict';

    var EYE_OPEN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
    var EYE_OFF = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.94 10.94 0 0112 19c-7 0-11-7-11-7a20.4 20.4 0 015.06-5.94M9.9 4.24A10.94 10.94 0 0112 4c7 0 11 7 11 7a20.4 20.4 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><path d="M1 1l22 22"/></svg>';
    var CHECK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>';

    function injectStyles() {
        if (document.getElementById('kbk-password-ui-styles')) return;
        var style = document.createElement('style');
        style.id = 'kbk-password-ui-styles';
        style.textContent =
            '.kbk-pw-wrap { position: relative; }' +
            '.kbk-pw-wrap input[type="password"], .kbk-pw-wrap input[type="text"] { padding-right: 2.75rem !important; }' +
            '.kbk-pw-toggle { position: absolute; right: 0.6rem; top: 50%; transform: translateY(-50%); background: transparent; border: none; cursor: pointer; padding: 0.3rem; color: rgba(241,245,249,0.4); display: flex; line-height: 0; transition: color .2s; }' +
            '.kbk-pw-toggle:hover { color: #F1F5F9; }' +
            '.kbk-pw-toggle svg { width: 18px; height: 18px; }' +
            '.kbk-pw-checklist { margin-top: 0.65rem; display: flex; flex-direction: column; gap: 0.35rem; }' +
            '.kbk-pw-req { display: flex; align-items: center; gap: 0.5rem; font-size: 0.75rem; color: rgba(241,245,249,0.4); transition: color .25s ease; }' +
            '.kbk-pw-req .kbk-pw-dot { width: 16px; height: 16px; border-radius: 50%; flex-shrink: 0; display: flex; align-items: center; justify-content: center; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15); transition: all .25s ease; }' +
            '.kbk-pw-req .kbk-pw-dot svg { width: 9px; height: 9px; opacity: 0; transition: opacity .2s; }' +
            '.kbk-pw-req.met { color: #6EE7B7; }' +
            '.kbk-pw-req.met .kbk-pw-dot { background: rgba(16,185,129,0.2); border-color: rgba(16,185,129,0.45); color: #34D399; }' +
            '.kbk-pw-req.met .kbk-pw-dot svg { opacity: 1; }' +
            '.kbk-pw-hint { font-size: 0.7rem; color: rgba(241,245,249,0.3); margin-top: 0.5rem; }' +
            '.kbk-pw-match { font-size: 0.75rem; margin-top: 0.5rem; display: flex; align-items: center; gap: 0.4rem; color: rgba(241,245,249,0.4); }' +
            '.kbk-pw-match.ok { color: #6EE7B7; }' +
            '.kbk-pw-match.bad { color: #FCA5A5; }';
        document.head.appendChild(style);
    }

    function addToggle(input) {
        if (input.dataset.kbkToggled) return;
        input.dataset.kbkToggled = 'true';

        var wrap = document.createElement('div');
        wrap.className = 'kbk-pw-wrap';
        input.parentNode.insertBefore(wrap, input);
        wrap.appendChild(input);

        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'kbk-pw-toggle';
        btn.tabIndex = -1;
        btn.setAttribute('aria-label', 'Mostrar palavra-passe');
        btn.innerHTML = EYE_OPEN;
        wrap.appendChild(btn);

        btn.addEventListener('click', function () {
            var showing = input.type === 'password';
            input.type = showing ? 'text' : 'password';
            btn.innerHTML = showing ? EYE_OFF : EYE_OPEN;
            btn.setAttribute('aria-label', showing ? 'Ocultar palavra-passe' : 'Mostrar palavra-passe');
        });
    }

    function requirement(text) {
        var el = document.createElement('div');
        el.className = 'kbk-pw-req';
        el.innerHTML = '<span class="kbk-pw-dot">' + CHECK + '</span><span></span>';
        el.querySelector('span:last-child').textContent = text;
        return el;
    }

    function setMet(el, met) {
        el.classList.toggle('met', !!met);
    }

    function attachChecklist(input) {
        if (input.dataset.kbkChecklist) return;
        input.dataset.kbkChecklist = 'true';

        var container = document.createElement('div');
        container.className = 'kbk-pw-checklist';

        var reqLength = requirement('Pelo menos 8 caracteres');
        var reqNumeric = requirement('Não pode ser só números');
        container.appendChild(reqLength);
        container.appendChild(reqNumeric);

        var form = input.closest('form');
        var userField = form ? form.querySelector('input[name="username"]') : null;
        var reqUsername = null;
        if (userField) {
            reqUsername = requirement('Diferente do nome de utilizador');
            container.appendChild(reqUsername);
        }

        var hint = document.createElement('p');
        hint.className = 'kbk-pw-hint';
        hint.textContent = 'Estes pontos ajudam a evitar erros comuns — a palavra-passe também não pode ser demasiado óbvia (ex: "password123").';
        container.appendChild(hint);

        var anchor = input.closest('.kbk-pw-wrap') || input;
        anchor.parentNode.insertBefore(container, anchor.nextSibling);

        function evaluate() {
            var value = input.value || '';
            setMet(reqLength, value.length >= 8);
            setMet(reqNumeric, value.length > 0 && !/^\d+$/.test(value));
            if (reqUsername) {
                var uname = (userField.value || '').trim().toLowerCase();
                var similar = uname.length >= 3 && value.toLowerCase().indexOf(uname) !== -1;
                setMet(reqUsername, value.length > 0 && !similar);
            }
        }

        input.addEventListener('input', evaluate);
        if (userField) userField.addEventListener('input', evaluate);
        evaluate();
    }

    function attachMatch(input) {
        if (input.dataset.kbkMatch) return;
        input.dataset.kbkMatch = 'true';

        var form = input.closest('form');
        var target = form ? form.querySelector('[data-password-strength]') : null;
        if (!target) return;

        var el = document.createElement('p');
        el.className = 'kbk-pw-match';
        el.style.display = 'none';

        var anchor = input.closest('.kbk-pw-wrap') || input;
        anchor.parentNode.insertBefore(el, anchor.nextSibling);

        function evaluate() {
            if (!input.value) {
                el.style.display = 'none';
                return;
            }
            el.style.display = 'flex';
            var ok = input.value === target.value;
            el.classList.toggle('ok', ok);
            el.classList.toggle('bad', !ok);
            el.textContent = ok ? 'As palavras-passe coincidem' : 'As palavras-passe não coincidem';
        }

        input.addEventListener('input', evaluate);
        target.addEventListener('input', evaluate);
        evaluate();
    }

    document.addEventListener('DOMContentLoaded', function () {
        injectStyles();
        document.querySelectorAll('input[type="password"]').forEach(addToggle);
        document.querySelectorAll('input[data-password-strength]').forEach(attachChecklist);
        document.querySelectorAll('input[data-password-confirm]').forEach(attachMatch);
    });
})();
