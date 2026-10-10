document.addEventListener('DOMContentLoaded', () => {

    // Elements — steps & wizard nav
    const step1 = document.getElementById('step-1');
    const step2 = document.getElementById('step-2');
    const step3 = document.getElementById('step-3');
    const btnNext = document.getElementById('btn-next');
    const btnPrev = document.getElementById('btn-prev');
    const btnSubmit = document.getElementById('btn-submit');

    const ind1 = document.getElementById('ind-1');
    const ind2 = document.getElementById('ind-2');
    const ind3 = document.getElementById('ind-3');

    // Elements — step 1 (description)
    const tipoPraticaSelect = document.getElementById('tipo-pratica');
    const descrizioneInput = document.getElementById('descrizione');
    const luogoInput = document.getElementById('luogo');
    const allegatiInput = document.getElementById('allegati');
    const fileChipsContainer = document.getElementById('file-chips-container');

    // Elements — step 2 (AI analysis)
    const aiLoading = document.getElementById('ai-loading');
    const aiErrorBox = document.getElementById('ai-error');
    const aiResultContainer = document.getElementById('ai-result-container');
    const aiBox = document.getElementById('ai-box');
    const dynamicFieldsContainer = document.getElementById('dynamic-fields-container');
    const confermaContainer = document.getElementById('conferma-container');
    const confermaCheckbox = document.getElementById('conferma-dati');
    const btnRetryAi = document.getElementById('btn-retry-ai');

    // Elements — step 3 (summary / success)
    const riepilogoContainer = document.getElementById('riepilogo-container');

    // Elements — info popover (step 1)
    const btnInfoTipoPratica = document.getElementById('btn-info-tipo-pratica');
    const infoPopoverTipoPratica = document.getElementById('info-popover-tipo-pratica');
    if (btnInfoTipoPratica && infoPopoverTipoPratica) {
        btnInfoTipoPratica.addEventListener('click', () => {
            infoPopoverTipoPratica.classList.toggle('active');
        });
    }

    // Simulated SPID identity: used to pre-fill known fields and to show
    // the confirmation email address at the end of the flow.
    const CITTADINO_SIMULATO = {
        nome: 'Mario Rossi',
        email: 'mario.rossi@email.it'
    };

    let currentStep = 1;

    // State accumulated across the whole wizard
    const praticaState = {
        requestType: '',
        requestTypeLabel: '',
        description: '',
        location: '',
        attachments: [], // { name, size, type }
        aiResponse: null, // filled in by URPAIService.classificaPratica()
        collectedData: {} // { "<label from dati_richiesti>": "<value>" }
    };

    const TIPO_PRATICA_LABELS = {
        segnalazione: 'Segnalazione',
        esposto: 'Esposto',
        accesso_atti: 'Richiesta di Accesso agli Atti (FOIA)',
        informazioni: 'Richiesta di Informazioni'
    };

    // ---------------------------------------------------------------
    // Attachments
    // ---------------------------------------------------------------
    allegatiInput.addEventListener('change', (e) => {
        const nuoviFile = Array.from(e.target.files).map(f => ({
            name: f.name, size: f.size, type: f.type
        }));
        praticaState.attachments = praticaState.attachments.concat(nuoviFile);
        allegatiInput.value = ''; // allow re-selecting / picking more afterwards
        renderFileChips();
    });

    function renderFileChips() {
        if (praticaState.attachments.length === 0) {
            fileChipsContainer.innerHTML = '';
            return;
        }
        fileChipsContainer.innerHTML = praticaState.attachments.map((f, idx) => `
            <span class="file-chip">
                ${escapeHtml(f.name)} <small>(${formatFileSize(f.size)})</small>
                <button type="button" data-idx="${idx}" class="remove-file-btn" aria-label="Rimuovi allegato">&times;</button>
            </span>
        `).join('');

        fileChipsContainer.querySelectorAll('.remove-file-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const idx = parseInt(btn.dataset.idx, 10);
                praticaState.attachments.splice(idx, 1);
                renderFileChips();
            });
        });
    }

    // ---------------------------------------------------------------
    // Validation helpers
    // ---------------------------------------------------------------
    function showFieldError(id) {
        const el = document.getElementById(id);
        if (el) el.classList.remove('hidden');
    }
    function hideFieldError(id) {
        const el = document.getElementById(id);
        if (el) el.classList.add('hidden');
    }

    function validateStep1() {
        let valid = true;

        if (!tipoPraticaSelect.value) {
            showFieldError('errore-tipo-pratica');
            valid = false;
        } else {
            hideFieldError('errore-tipo-pratica');
        }

        if (!descrizioneInput.value || descrizioneInput.value.trim().length < 15) {
            showFieldError('errore-descrizione');
            valid = false;
        } else {
            hideFieldError('errore-descrizione');
        }

        return valid;
    }

    function validateStep2() {
        let valid = true;

        dynamicFieldsContainer.querySelectorAll('input[data-campo]').forEach(input => {
            const errorEl = document.getElementById('errore-' + input.id);
            const campo = input.dataset.campo.trim().toLowerCase();
            const valore = input.value.trim();
            let campoValido = true;
            let messaggioErrore = 'Questo dato è necessario per proseguire.';

            if (!valore) {
                campoValido = false;
            } else if (campo === 'codice fiscale' && !validaCodiceFiscale(valore)) {
                campoValido = false;
                messaggioErrore = 'Il codice fiscale inserito non è valido (controllo formale sul formato e sul carattere di controllo).';
            }

            if (!campoValido) {
                valid = false;
                if (errorEl) {
                    errorEl.textContent = messaggioErrore;
                    errorEl.classList.remove('hidden');
                }
                input.classList.add('input-error');
            } else {
                if (errorEl) errorEl.classList.add('hidden');
                input.classList.remove('input-error');
            }
        });

        if (praticaState.aiResponse && praticaState.aiResponse.richiede_conferma) {
            if (!confermaCheckbox.checked) {
                showFieldError('errore-conferma');
                valid = false;
            } else {
                hideFieldError('errore-conferma');
            }
        }

        return valid;
    }

    // ---------------------------------------------------------------
    // Dynamic fields — generated from aiResponse.dati_richiesti.
    // Nothing here is hardcoded to a specific domain: whatever labels
    // the AI engine returns get turned into inputs automatically.
    // ---------------------------------------------------------------
    function getValoreNotoPerCampo(label) {
        const key = label.trim().toLowerCase();
        const mappa = {
            'descrizione dettagliata': praticaState.description,
            'descrizione': praticaState.description,
            'luogo della segnalazione': praticaState.location,
            'luogo': praticaState.location,
            'nome e cognome': CITTADINO_SIMULATO.nome // simulated: already known from the SPID login
        };
        return mappa[key] || '';
    }

    function slugify(text) {
        return text.toString().toLowerCase()
            .normalize('NFD').replace(/[\u0300-\u036f]/g, '') // strip accents
            .replace(/[^a-z0-9]+/g, '-')
            .replace(/(^-|-$)/g, '');
    }

    function renderDynamicFields(datiRichiesti) {
        dynamicFieldsContainer.innerHTML = (datiRichiesti || []).map(label => {
            const slug = slugify(label);
            const valoreNoto = getValoreNotoPerCampo(label);
            const fieldId = 'dynamic-field-' + slug;
            return `
                <div class="form-group campo-dinamico">
                    <label class="form-label" for="${fieldId}">${escapeHtml(label)} <span class="required-marker">*</span> ${valoreNoto ? '<span class="campo-noto-badge">Già fornito</span>' : ''}</label>
                    <input type="text" class="form-control" id="${fieldId}" data-campo="${escapeHtml(label)}" value="${escapeHtml(valoreNoto)}" required>
                    <small id="errore-${fieldId}" class="field-error hidden">Questo dato è necessario per proseguire.</small>
                </div>
            `;
        }).join('');
    }

    // ---------------------------------------------------------------
    // Step 2 — AI call (the actual "predisposizione frontoffice" flow):
    //   1. the citizen has written a description (collected in step 1)
    //   2. the frontend calls the dedicated API method
    //   3. the API returns a structured response (a Promise here)
    //   4. the frontend shows that response
    //   5. the citizen confirms or completes the requested data
    // ---------------------------------------------------------------
    async function runAIAnalysis() {
        aiLoading.classList.remove('hidden');
        aiErrorBox.classList.add('hidden');
        aiResultContainer.classList.add('hidden');
        btnNext.disabled = true;

        try {
            // Step 2 → 3 of the flow: send the text to the dedicated API method
            const response = await URPAIService.classificaPratica(praticaState.description, praticaState.requestType);

            // Step 4: the API returned a structured response
            praticaState.aiResponse = response;
            renderAIBox(response);
            renderDynamicFields(response.dati_richiesti);
            confermaContainer.classList.toggle('hidden', !response.richiede_conferma);

            aiLoading.classList.add('hidden');
            aiResultContainer.classList.remove('hidden');
            btnNext.disabled = false;
        } catch (err) {
            console.error('Errore durante la classificazione IA:', err);
            aiLoading.classList.add('hidden');
            aiErrorBox.classList.remove('hidden');
        }
    }

    function badgeStyleFor(ambito) {
        const c = getColorForAmbito(ambito);
        return `background:${c.bg};color:${c.text};`;
    }

    function renderAIBox(response) {
        aiBox.innerHTML = `
            <h4>Assistente IA Sportello Esposti <small style="font-weight:400;color:var(--color-text-muted);">(motore di classificazione simulato)</small></h4>
            <p><strong>Ambito rilevato:</strong> <span class="badge-ambito" style="${badgeStyleFor(response.ambito)}">${escapeHtml(response.ambito)}</span></p>
            <p>${escapeHtml(response.messaggio)}</p>
            <p><strong>Ufficio di destinazione suggerito:</strong> ${escapeHtml(response.ufficio_destinazione)}</p>
            ${response.confidenza ? `<p><strong>Confidenza:</strong> ${escapeHtml(response.confidenza)}</p>` : ''}
        `;
    }

    btnRetryAi.addEventListener('click', runAIAnalysis);

    // ---------------------------------------------------------------
    // Wizard navigation
    // ---------------------------------------------------------------
    btnNext.addEventListener('click', async () => {
        if (currentStep === 1) {
            if (!validateStep1()) return;

            praticaState.requestType = tipoPraticaSelect.value;
            praticaState.requestTypeLabel = TIPO_PRATICA_LABELS[praticaState.requestType] || praticaState.requestType;
            praticaState.description = descrizioneInput.value.trim();
            praticaState.location = luogoInput.value.trim();

            step1.classList.remove('active');
            step2.classList.add('active');
            ind1.classList.remove('active');
            ind1.classList.add('completed');
            ind2.classList.add('active');
            btnPrev.disabled = false;
            currentStep = 2;

            await runAIAnalysis();

        } else if (currentStep === 2) {
            if (!validateStep2()) return;

            dynamicFieldsContainer.querySelectorAll('input[data-campo]').forEach(input => {
                praticaState.collectedData[input.dataset.campo] = input.value.trim();
            });

            step2.classList.remove('active');
            step3.classList.add('active');
            ind2.classList.remove('active');
            ind2.classList.add('completed');
            ind3.classList.add('active');
            btnNext.classList.add('hidden');
            btnSubmit.classList.remove('hidden');
            currentStep = 3;

            renderRiepilogo();
        }
    });

    btnPrev.addEventListener('click', () => {
        if (currentStep === 2) {
            step2.classList.remove('active');
            step1.classList.add('active');
            ind2.classList.remove('active');
            ind1.classList.add('active');
            ind1.classList.remove('completed');
            btnPrev.disabled = true;
            currentStep = 1;
        } else if (currentStep === 3) {
            step3.classList.remove('active');
            step2.classList.add('active');
            ind3.classList.remove('active');
            ind2.classList.add('active');
            ind2.classList.remove('completed');
            btnNext.classList.remove('hidden');
            btnSubmit.classList.add('hidden');
            currentStep = 2;
        }
    });

    // ---------------------------------------------------------------
    // Step 3 — Summary before sending
    // ---------------------------------------------------------------
    function renderRiepilogo() {
        const r = praticaState.aiResponse;

        const datiAggiuntiviHtml = Object.entries(praticaState.collectedData)
            .map(([k, v]) => `<p><strong>${escapeHtml(k)}:</strong> ${escapeHtml(v)}</p>`)
            .join('') || '<p class="text-muted">Nessun dato aggiuntivo richiesto.</p>';

        const allegatiHtml = praticaState.attachments.length > 0
            ? praticaState.attachments.map(f => `<span class="file-chip">${escapeHtml(f.name)} <small>(${formatFileSize(f.size)})</small></span>`).join('')
            : '<p class="text-muted">Nessun allegato.</p>';

        riepilogoContainer.innerHTML = `
            <h2 style="margin-bottom:0.25rem;">Riepilogo Pratica</h2>
            <p style="color:var(--color-text-muted);margin-bottom:1.5rem;">Verifica i dati prima dell'invio definitivo.</p>

            <div class="riepilogo-section">
                <div class="riepilogo-label">Tipo di Pratica</div>
                <p>${escapeHtml(praticaState.requestTypeLabel)}</p>
            </div>
            <div class="riepilogo-section">
                <div class="riepilogo-label">Ambito Rilevato dall'IA</div>
                <p><span class="badge-ambito" style="${badgeStyleFor(r.ambito)}">${escapeHtml(r.ambito)}</span></p>
            </div>
            <div class="riepilogo-section">
                <div class="riepilogo-label">Ufficio di Destinazione</div>
                <p>${escapeHtml(r.ufficio_destinazione)}</p>
            </div>
            <div class="riepilogo-section">
                <div class="riepilogo-label">Descrizione</div>
                <p style="white-space:pre-wrap;">${escapeHtml(praticaState.description)}</p>
            </div>
            ${praticaState.location ? `
            <div class="riepilogo-section">
                <div class="riepilogo-label">Luogo</div>
                <p>${escapeHtml(praticaState.location)}</p>
            </div>` : ''}
            <div class="riepilogo-section">
                <div class="riepilogo-label">Dati Aggiuntivi Forniti</div>
                ${datiAggiuntiviHtml}
            </div>
            <div class="riepilogo-section">
                <div class="riepilogo-label">Allegati</div>
                ${allegatiHtml}
            </div>
        `;
    }

    // ---------------------------------------------------------------
    // Submission
    // ---------------------------------------------------------------
    btnSubmit.addEventListener('click', () => {
        const pratica = {
            id: generateId(),
            date: new Date().toISOString(),
            requestType: praticaState.requestType,
            requestTypeLabel: praticaState.requestTypeLabel,
            citizen: CITTADINO_SIMULATO.nome + ' (SPID)',
            description: praticaState.description,
            location: praticaState.location,
            attachments: praticaState.attachments,
            aiResponse: praticaState.aiResponse,
            ambito: praticaState.aiResponse.ambito,
            collectedData: praticaState.collectedData,
            status: 'RICEVUTA',
            assignedTo: '',
            internalNotes: '',
            internalNotesUpdatedAt: null
        };

        savePratica(pratica);
        renderSuccessState(pratica);
    });

    function renderSuccessState(pratica) {
        riepilogoContainer.innerHTML = `
            <div class="success-state">
                <div class="success-icon">
                    <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M20 6L9 17l-5-5"></path>
                    </svg>
                </div>
                <h2>Pratica Inviata con Successo</h2>
                <p style="color:var(--color-text-muted); margin-bottom:0.5rem;">Numero identificativo pratica:</p>
                <p style="font-size:1.5rem; font-weight:700; color:var(--color-primary); margin-bottom:1.5rem;">${pratica.id}</p>
                <p style="max-width:500px;margin:0 auto 1rem;color:var(--color-text-muted);">
                    La tua pratica è stata classificata nell'ambito <strong>${escapeHtml(pratica.ambito)}</strong>
                    e inoltrata a: <strong>${escapeHtml(pratica.aiResponse.ufficio_destinazione)}</strong>.
                </p>
                <p style="max-width:500px;margin:0 auto 2rem;color:var(--color-text-muted);">
                    È stata inviata una mail di conferma con il riepilogo della pratica a
                    <strong>${escapeHtml(CITTADINO_SIMULATO.email)}</strong>.
                </p>
                <a href="index.html" class="btn btn-primary">Torna alla Home</a>
            </div>
        `;
        btnPrev.classList.add('hidden');
        btnSubmit.classList.add('hidden');
    }
});
