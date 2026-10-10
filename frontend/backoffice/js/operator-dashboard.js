document.addEventListener('DOMContentLoaded', () => {

    const tbody = document.querySelector('#pratiche-table tbody');
    const refreshBtn = document.getElementById('btn-refresh');

    const filterAmbito = document.getElementById('filter-ambito');
    const filterStato = document.getElementById('filter-stato');
    const searchInput = document.getElementById('search-input');

    // Modal elements
    const modal = document.getElementById('modal-dettaglio');
    const modalClose = document.getElementById('modal-close');
    const modalContent = document.getElementById('modal-content');
    const modalTitle = document.getElementById('modal-title');

    // Login simulato (demo): selezione del profilo operatore
    const loginOverlay = document.getElementById('login-overlay');
    const loginSelect = document.getElementById('login-operatore-select');
    const btnLoginOperatore = document.getElementById('btn-login-operatore');
    const btnLogoutOperatore = document.getElementById('btn-logout-operatore');
    const operatoreInfoText = document.getElementById('operatore-info-text');
    const dashboardRoot = document.getElementById('dashboard-root');
    const dashboardHeading = document.getElementById('dashboard-heading');

    loginSelect.innerHTML = OPERATORI_DEMO.map(o =>
        `<option value="${o.id}">${escapeHtml(o.nome)} — ${escapeHtml(o.ufficio)}${o.ruolo === 'smistamento' ? ' (Smistamento URP)' : ''}</option>`
    ).join('');

    function aggiornaUIOperatore() {
        const operatore = getOperatoreCorrente();

        if (!operatore) {
            loginOverlay.classList.add('active');
            dashboardRoot.classList.add('hidden');
            btnLogoutOperatore.classList.add('hidden');
            return;
        }

        loginOverlay.classList.remove('active');
        dashboardRoot.classList.remove('hidden');
        btnLogoutOperatore.classList.remove('hidden');
        operatoreInfoText.textContent = `${operatore.nome} — ${operatore.ufficio}`;
        dashboardHeading.textContent = operatore.ruolo === 'smistamento'
            ? 'Gestione Pratiche — Smistamento URP'
            : `Pratiche — ${operatore.ufficio}`;

        renderTable();
    }

    btnLoginOperatore.addEventListener('click', () => {
        setOperatoreCorrente(loginSelect.value);
        aggiornaUIOperatore();
    });

    btnLogoutOperatore.addEventListener('click', () => {
        logoutOperatore();
        aggiornaUIOperatore();
    });

    // Pratiche visibili per l'operatore attualmente collegato: l'operatore
    // di smistamento URP vede tutto, un operatore di ufficio vede solo le
    // pratiche già assegnate al proprio ufficio.
    function getPraticheVisibili() {
        const tutte = getPratiche();
        const operatore = getOperatoreCorrente();
        if (!operatore || operatore.ruolo === 'smistamento') return tutte;
        return tutte.filter(p => p.assignedTo === operatore.ufficio);
    }

    const STATO_LABELS = {
        RICEVUTA: 'Ricevuta',
        DA_VALUTARE: 'Da Valutare',
        ASSEGNATA: 'Assegnata',
        IN_LAVORAZIONE: 'In Lavorazione',
        CHIUSA: 'Chiusa'
    };

    const STATO_BADGE_CLASS = {
        RICEVUTA: 'badge-ricevuta',
        DA_VALUTARE: 'badge-da-valutare',
        ASSEGNATA: 'badge-assegnata',
        IN_LAVORAZIONE: 'badge-in-lavorazione',
        CHIUSA: 'badge-chiusa'
    };

    // Used only to sort "needs attention first"; not shown to the citizen.
    const STATO_WEIGHT = { RICEVUTA: 4, DA_VALUTARE: 3, ASSEGNATA: 2, IN_LAVORAZIONE: 1, CHIUSA: 0 };

    function badgeVerificaIA(p) {
        if (!p.classificazioneIA) return '<span class="badge badge-ricevuta">In attesa</span>';
        return p.classificazioneIA.confermata
            ? '<span class="badge badge-chiusa">&#10003; Confermata</span>'
            : '<span class="badge badge-da-valutare">&#10007; Corretta</span>';
    }

    function popolaFiltroAmbiti() {
        const pratiche = getPraticheVisibili();
        const valoreAttuale = filterAmbito.value;
        const ambitiUnici = [...new Set(pratiche.map(p => p.ambito).filter(Boolean))].sort();

        filterAmbito.innerHTML = '<option value="">Tutti gli ambiti</option>' +
            ambitiUnici.map(a => `<option value="${escapeHtml(a)}">${escapeHtml(a)}</option>`).join('');

        if (ambitiUnici.includes(valoreAttuale)) {
            filterAmbito.value = valoreAttuale;
        }
    }

    function renderCards(pratiche) {
        document.getElementById('count-totale').innerText = pratiche.length;
        document.getElementById('count-da-valutare').innerText =
            pratiche.filter(p => p.status === 'RICEVUTA' || p.status === 'DA_VALUTARE').length;
        document.getElementById('count-in-lavorazione').innerText =
            pratiche.filter(p => p.status === 'ASSEGNATA' || p.status === 'IN_LAVORAZIONE').length;
        document.getElementById('count-chiuse').innerText =
            pratiche.filter(p => p.status === 'CHIUSA').length;
    }

    function renderTable() {
        const pratiche = getPraticheVisibili();

        popolaFiltroAmbiti();
        renderCards(pratiche);

        const ambitoSel = filterAmbito.value;
        const statoSel = filterStato.value;
        const search = searchInput.value.trim().toLowerCase();

        let filtrate = pratiche.filter(p => {
            if (ambitoSel && p.ambito !== ambitoSel) return false;
            if (statoSel && p.status !== statoSel) return false;
            if (search) {
                const haystack = ((p.citizen || '') + ' ' + (p.description || '')).toLowerCase();
                if (!haystack.includes(search)) return false;
            }
            return true;
        });

        // Needs-attention-first, then most recent
        filtrate.sort((a, b) => {
            const pesoDiff = (STATO_WEIGHT[b.status] || 0) - (STATO_WEIGHT[a.status] || 0);
            if (pesoDiff !== 0) return pesoDiff;
            return new Date(b.date) - new Date(a.date);
        });

        tbody.innerHTML = '';

        if (filtrate.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;">Nessuna pratica trovata con i filtri selezionati.</td></tr>';
            return;
        }

        filtrate.forEach(p => {
            const tr = document.createElement('tr');
            const d = new Date(p.date);
            const colore = getColorForAmbito(p.ambito);
            const statoClass = STATO_BADGE_CLASS[p.status] || '';
            const statoLabel = STATO_LABELS[p.status] || p.status;
            const descrizioneBreve = p.description && p.description.length > 80
                ? p.description.slice(0, 80) + '…'
                : p.description;

            tr.innerHTML = `
                <td><strong>${escapeHtml(p.id)}</strong><br><small class="text-muted">${d.toLocaleDateString()} ${d.toLocaleTimeString()}</small></td>
                <td>${escapeHtml(p.citizen)}</td>
                <td><span class="badge-ambito" style="background:${colore.bg};color:${colore.text};">${escapeHtml(p.ambito)}</span></td>
                <td>${escapeHtml(descrizioneBreve)}</td>
                <td>${p.attachments && p.attachments.length ? p.attachments.length : '—'}</td>
                <td>${badgeVerificaIA(p)}</td>
                <td><span class="badge ${statoClass}">${statoLabel}</span></td>
                <td>${p.assignedTo ? escapeHtml(p.assignedTo) : '<span class="text-muted">Non assegnato</span>'}</td>
                <td><button class="btn btn-outline btn-sm" onclick="openDettaglio('${p.id}')">Gestisci</button></td>
            `;
            tbody.appendChild(tr);
        });
    }

    // Assign to window for inline onclick handlers
    window.openDettaglio = function (id) {
        const pratiche = getPratiche();
        const p = pratiche.find(x => x.id === id);
        if (!p) return;

        modalTitle.innerText = `Dettaglio Pratica: ${p.id}`;

        const r = p.aiResponse || {};
        const colore = getColorForAmbito(p.ambito);

        const datiRaccoltiHtml = Object.entries(p.collectedData || {}).length > 0
            ? Object.entries(p.collectedData).map(([k, v]) => `<p><strong>${escapeHtml(k)}:</strong> ${v ? escapeHtml(v) : '—'}</p>`).join('')
            : '<p class="text-muted">Nessun dato aggiuntivo raccolto.</p>';

        const allegatiHtml = (p.attachments && p.attachments.length > 0)
            ? p.attachments.map(f => {
                const classificazione = classificaDocumentoMock(f);
                return `
                    <div style="margin-bottom:0.6rem;">
                        <span class="file-chip">${escapeHtml(f.name)} <small>(${formatFileSize(f.size)})</small></span>
                        <span class="badge-ambito" style="background:rgba(0,51,102,0.08);color:var(--color-primary);margin-left:0.5rem;">&#128196; ${escapeHtml(classificazione.tipo)} · ${classificazione.confidenza}</span>
                    </div>
                `;
            }).join('')
            : '<p class="text-muted">Nessun allegato.</p>';

        // Make sure an ambito the AI suggested but that isn't in our base
        // list yet is still selectable — new domains should never get stuck.
        const uffici = getUfficiOperatori();
        if (r.ufficio_destinazione && uffici.indexOf(r.ufficio_destinazione) === -1) {
            uffici.push(r.ufficio_destinazione);
        }
        const assegnazioneCorrente = p.assignedTo || r.ufficio_destinazione || '';
        const opzioniUffici = ['<option value="">Non assegnato</option>']
            .concat(uffici.map(u => `<option value="${escapeHtml(u)}" ${u === assegnazioneCorrente ? 'selected' : ''}>${escapeHtml(u)}</option>`))
            .join('');

        const opzioniStato = Object.keys(STATO_LABELS).map(key =>
            `<option value="${key}" ${p.status === key ? 'selected' : ''}>${STATO_LABELS[key]}</option>`
        ).join('');

        // Solo l'operatore di smistamento URP può riassegnare la pratica a
        // un altro ufficio e validare/correggere la classificazione IA; un
        // operatore di ufficio lavora la pratica che gli è già arrivata.
        const operatoreCorrente = getOperatoreCorrente();
        const isSmistamento = !operatoreCorrente || operatoreCorrente.ruolo === 'smistamento';

        const assegnazioneHtml = isSmistamento
            ? `<div class="form-group">
                   <label class="form-label">Assegna a Ufficio / Operatore</label>
                   <select id="update-assegnazione" class="form-control form-select">
                       ${opzioniUffici}
                   </select>
               </div>`
            : `<div class="form-group">
                   <label class="form-label">Ufficio Assegnato</label>
                   <p style="padding:0.75rem 1rem;background:#f1f3f5;border-radius:var(--radius-sm);">${assegnazioneCorrente ? escapeHtml(assegnazioneCorrente) : '—'}</p>
               </div>`;

        const verificaIAHtml = isSmistamento ? `
            <div class="form-group" style="background:#fcfcfc;border:1px solid var(--color-border);padding:1rem;border-radius:var(--radius-sm);">
                <label class="form-label">La classificazione IA (ufficio suggerito) è corretta?</label>
                <div style="display:flex;gap:1.5rem;flex-wrap:wrap;">
                    <label style="display:flex;align-items:center;gap:0.4rem;font-weight:400;">
                        <input type="radio" name="verifica-ia" value="corretta" ${p.classificazioneIA && p.classificazioneIA.confermata === true ? 'checked' : ''}>
                        Sì, l'ufficio suggerito è corretto
                    </label>
                    <label style="display:flex;align-items:center;gap:0.4rem;font-weight:400;">
                        <input type="radio" name="verifica-ia" value="errata" ${p.classificazioneIA && p.classificazioneIA.confermata === false ? 'checked' : ''}>
                        No, l'ufficio corretto è diverso
                    </label>
                </div>
                <small class="text-muted">Se l'IA ha sbagliato, seleziona l'ufficio corretto nel campo "Assegna a Ufficio" qui sopra.</small>
            </div>
        ` : '';

        modalContent.innerHTML = `
            <div class="grid grid-2">
                <div>
                    <h4 style="margin-bottom:0.5rem">Cittadino</h4>
                    <p style="margin-bottom:1.5rem">${escapeHtml(p.citizen)}</p>

                    <h4 style="margin-bottom:0.5rem">Tipo di Pratica</h4>
                    <p style="margin-bottom:1.5rem">${escapeHtml(p.requestTypeLabel || p.requestType)}</p>

                    <h4 style="margin-bottom:0.5rem">Luogo</h4>
                    <p style="margin-bottom:1.5rem">${p.location ? escapeHtml(p.location) : '—'}</p>
                </div>
                <div>
                    <h4 style="margin-bottom:0.5rem">Descrizione dei fatti</h4>
                    <p style="margin-bottom:1.5rem; white-space:pre-wrap;">${escapeHtml(p.description)}</p>
                </div>
            </div>

            <div class="ai-box">
                <h4>Analisi Automatica <small style="font-weight:400;color:var(--color-text-muted);">(Assistente IA Sportello Esposti — motore simulato)</small></h4>
                <p><strong>Ambito rilevato:</strong> <span class="badge-ambito" style="background:${colore.bg};color:${colore.text};">${escapeHtml(p.ambito)}</span></p>
                <p><strong>Ufficio suggerito:</strong> ${escapeHtml(r.ufficio_destinazione || '—')}</p>
                ${r.confidenza ? `<p><strong>Confidenza:</strong> ${escapeHtml(r.confidenza)}</p>` : ''}
                <p><strong>Messaggio mostrato al cittadino:</strong> <em>${escapeHtml(r.messaggio || '—')}</em></p>
            </div>

            ${verificaIAHtml}

            <h4 style="margin-bottom:0.5rem;">Dati Raccolti dal Cittadino</h4>
            <div style="margin-bottom:1.5rem;">${datiRaccoltiHtml}</div>

            <h4 style="margin-bottom:0.5rem;">Allegati e Classificazione Automatica dei Documenti <small style="font-weight:400;color:var(--color-text-muted);">(mock)</small></h4>
            <div style="margin-bottom:0.5rem;">${allegatiHtml}</div>
            <small class="text-muted">Anteprima e download non disponibili in questo mockup: viene salvato solo il nome/dimensione del file; l'etichetta sui documenti è una classificazione fittizia a scopo dimostrativo.</small>

            <hr style="border:0; border-top:1px solid var(--color-border); margin: 2rem 0;">

            <h3>Gestione Pratica</h3>
            <div class="grid grid-2" style="margin-top:1rem;">
                <div class="form-group">
                    <label class="form-label">Stato Pratica</label>
                    <select id="update-stato" class="form-control form-select">
                        ${opzioniStato}
                    </select>
                </div>
                ${assegnazioneHtml}
            </div>
            <div class="form-group">
                <label class="form-label">Note Interne</label>
                <textarea id="update-note" class="form-control" style="min-height:100px;">${p.internalNotes ? escapeHtml(p.internalNotes) : ''}</textarea>
                ${p.internalNotesUpdatedAt ? `<small class="text-muted">Ultimo aggiornamento: ${new Date(p.internalNotesUpdatedAt).toLocaleString()}</small>` : ''}
            </div>

            <div style="display:flex; justify-content:flex-end; gap:1rem; margin-top:2rem;">
                <button class="btn btn-outline" onclick="closeModal()">Annulla</button>
                <button class="btn btn-primary" onclick="salvaGestione('${p.id}')">Salva Modifiche</button>
            </div>
        `;

        modal.classList.add('active');
    };

    window.closeModal = function () {
        modal.classList.remove('active');
    };

    window.salvaGestione = function (id) {
        const operatoreCorrente = getOperatoreCorrente();
        const isSmistamento = !operatoreCorrente || operatoreCorrente.ruolo === 'smistamento';

        const nuovoStato = document.getElementById('update-stato').value;
        const nuoveNote = document.getElementById('update-note').value;

        const pratiche = getPratiche();
        const esistente = pratiche.find(x => x.id === id);
        const noteCambiate = esistente && (esistente.internalNotes || '') !== nuoveNote;

        const aggiornamento = {
            id: id,
            status: nuovoStato,
            internalNotes: nuoveNote,
            internalNotesUpdatedAt: noteCambiate ? new Date().toISOString() : (esistente ? esistente.internalNotesUpdatedAt : null)
        };

        if (isSmistamento) {
            const assegnazioneEl = document.getElementById('update-assegnazione');
            aggiornamento.assignedTo = assegnazioneEl ? assegnazioneEl.value : (esistente ? esistente.assignedTo : '');

            const radioVerifica = document.querySelector('input[name="verifica-ia"]:checked');
            aggiornamento.classificazioneIA = radioVerifica
                ? {
                    confermata: radioVerifica.value === 'corretta',
                    verificatoDa: operatoreCorrente ? operatoreCorrente.nome : 'Operatore Smistamento',
                    verificatoIl: new Date().toISOString()
                }
                : (esistente ? esistente.classificazioneIA : null);
        }

        updatePratica(aggiornamento);
        closeModal();
        renderTable();
    };

    modalClose.addEventListener('click', closeModal);
    refreshBtn.addEventListener('click', renderTable);
    filterAmbito.addEventListener('change', renderTable);
    filterStato.addEventListener('change', renderTable);
    searchInput.addEventListener('input', renderTable);

    // Initial render: shows the login overlay if no operator is logged in,
    // otherwise renders the table filtered for that operator's office.
    aggiornaUIOperatore();
});
