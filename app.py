import streamlit as st
from datetime import datetime, time, timedelta, date
from sqlalchemy import func 
from sqlalchemy.exc import OperationalError, IntegrityError 
# Importiamo SessionLocal e i modelli dal database
from database import init_db, Prenotazione, SessionLocal 


# --- 1. DATI STATICI DEL PROGETTO (Configurazione) ---

# Definisci i barbieri e gli ID (ID 1 e 2 devono corrispondere a database.py)
BARBIERI = {
    1: "Salvatore",
    2: "Raffaele"
}

# Definisci i servizi e la loro durata in minuti
SERVIZI = {
    "Taglio Uomo": 30,
    "Barba": 15,
    "Taglio + Barba": 45 
}

# Orari di apertura definitivi del barbiere
ORARI_APERTURA = [
    (time(8, 30), time(12, 30)),  # Mattina
    (time(15, 0), time(19, 30))   # Pomeriggio
]
SLOT_CADENZA = timedelta(minutes=30)
# 0=Lunedì, 6=Domenica. Si lavora da Martedì (2) a Sabato (5). Domenica (6) e Lunedì (0) chiusi.
GIORNI_CHIUSURA = [0, 6] 

# --- 2. LOGICA DI SCHEDULAZIONE (Motore di calcolo disponibilità) ---

def get_orari_disponibili(data_selezionata: date, durata_servizio_min: int, prenotazioni_esistenti: list) -> list:
    """
    Calcola gli orari di inizio disponibili per una data e durata specificate.
    """
    disponibilita = []
    durata_servizio = timedelta(minutes=durata_servizio_min)
    
    for start_time, end_time in ORARI_APERTURA:
        current_time = datetime.combine(data_selezionata, start_time)
        end_boundary = datetime.combine(data_selezionata, end_time)

        while current_time < end_boundary:
            
            fine_prenotazione = current_time + durata_servizio
            
            if fine_prenotazione > end_boundary:
                current_time += SLOT_CADENZA
                continue

            slot_libero = True
            for p in prenotazioni_esistenti:
                start_esistente = p['start']
                end_esistente = p['end']

                if current_time < end_esistente and fine_prenotazione > start_esistente:
                    slot_libero = False
                    break 

            if slot_libero:
                disponibilita.append(current_time)

            current_time += SLOT_CADENZA

    return disponibilita

# --- 3. FUNZIONE DI ACCESSO AL DATABASE (DB) E MESSAGGISTICA ---

def fetch_prenotazioni_per_barbiere(barbiere_id, data_selezionata: date):
    """
    Recupera le prenotazioni REALI dal database, filtrando sulla data.
    """
    db = SessionLocal()
    
    try:
        # Usa func.date() supportata da SQLite per filtrare correttamente
        prenotazioni_records = db.query(Prenotazione).filter(
            Prenotazione.barbiere_id == barbiere_id,
            func.date(Prenotazione.data_appuntamento) == data_selezionata.isoformat()
        ).order_by(Prenotazione.ora_inizio).all() 
    except OperationalError as e:
        # In caso di errore di lettura all'inizio, restituisce una lista vuota.
        return []

    db.close()
    
    risultati_formattati = []
    for p in prenotazioni_records:
        risultati_formattati.append({
            'id': p.id, 
            'start': p.ora_inizio,
            'end': p.ora_fine,
            'cliente_nome': p.cliente_nome,
            'servizio': p.servizio
        })
        
    return risultati_formattati

def delete_appointment(prenotazione_id):
    """Elimina una prenotazione dal database dato l'ID."""
    db = SessionLocal()
    appointment = db.query(Prenotazione).filter(Prenotazione.id == prenotazione_id).first()
    if appointment:
        db.delete(appointment)
        db.commit()
        db.close()
        return True
    db.close()
    return False

def send_confirmation_message(telefono, dati_finali):
    """
    Funzione placeholder per l'invio di SMS/WhatsApp.
    """
    nome_cliente = dati_finali.get('cliente_nome', 'Cliente') 
    st.toast(f"Tentativo di invio messaggio di conferma a {telefono}", icon='📱')
    return True 

# --- 4. INTERFACCIA DI GESTIONE (ADMIN PANEL) ---

def display_calendar_view(barbiere_id, nome_barbiere, data_selezionata):
    """Visualizza il calendario degli appuntamenti per un singolo barbiere, con opzione Elimina."""
    st.markdown(f"**{nome_barbiere}**")

    prenotazioni_del_giorno = fetch_prenotazioni_per_barbiere(barbiere_id, data_selezionata)
    
    if not prenotazioni_del_giorno:
        st.info("Nessun appuntamento prenotato.")
        
    else:
        st.markdown("##### Appuntamenti del Giorno:")
        
        col_ora, col_durata, col_cliente, col_azione = st.columns([1, 1, 2, 1])
        col_ora.markdown("**Ora**")
        col_durata.markdown("**Durata**")
        col_cliente.markdown("**Cliente/Servizio**")
        col_azione.markdown("**Elimina**")
        st.markdown("---")


        for p in prenotazioni_del_giorno:
            prenotazione_id = p['id']
            durata_min = int((p['end'] - p['start']).total_seconds() / 60) 
            
            col_ora, col_durata, col_cliente, col_azione = st.columns([1, 1, 2, 1])
            
            col_ora.write(p['start'].strftime("%H:%M"))
            col_durata.write(f"{durata_min} min")
            col_cliente.write(f"**{p['cliente_nome']}** - {p['servizio']}")
            
            with col_azione:
                if st.button("❌", help="Elimina appuntamento", key=f"delete_{prenotazione_id}"):
                    if delete_appointment(prenotazione_id):
                        st.toast(f"Appuntamento di {p['cliente_nome']} eliminato.", icon='🗑️')
                        st.rerun() 
                    else:
                        st.error("Errore nell'eliminazione dell'appuntamento.")
    
    st.markdown(f"**Aggiungi Appuntamento**")
    with st.expander("Inserimento Manuale"):
        with st.form(f"form_manuale_{barbiere_id}"):
            service_names = list(SERVIZI.keys())
            
            col_time, col_service = st.columns(2)
            with col_time:
                ora_manuale = st.time_input("Ora di Inizio", time(8, 30), key=f"time_{barbiere_id}")
            with col_service:
                servizio_manuale = st.selectbox("Servizio", options=service_names, key=f"service_{barbiere_id}")
            
            nome_cli = st.text_input("Nome Cliente", key=f"name_{barbiere_id}")
            tel_cli = st.text_input("Telefono Cliente", key=f"tel_{barbiere_id}")
            
            if st.form_submit_button("Salva Appuntamento Manuale"):
                durata_man_min = SERVIZI[servizio_manuale]
                
                data_ora_inizio = datetime.combine(data_selezionata, ora_manuale)
                data_ora_fine = data_ora_inizio + timedelta(minutes=durata_man_min)

                if data_ora_inizio.date() != data_selezionata:
                    st.error("Errore di data. Controlla l'ora.")
                elif not nome_cli or not tel_cli:
                    st.error("Nome e Telefono sono obbligatori.")
                else:
                    try:
                        db = SessionLocal()
                        nuova_prenotazione = Prenotazione(
                            barbiere_id=barbiere_id,
                            data_appuntamento=data_ora_inizio, 
                            ora_inizio=data_ora_inizio,
                            ora_fine=data_ora_fine,
                            servizio=f"{servizio_manuale}",
                            cliente_nome=nome_cli,
                            cliente_telefono=tel_cli
                        )
                        db.add(nuova_prenotazione)
                        db.commit()
                        db.close()
                        
                        send_confirmation_message(tel_cli, {
                            'cliente_nome': nome_cli, 
                            'servizio': servizio_manuale, 
                            'data': data_selezionata.strftime("%d/%m/%Y"), 
                            'ora_inizio': ora_manuale.strftime("%H:%M"), 
                            'barbiere_nome': nome_barbiere
                        })
                        
                        st.success(f"Appuntamento salvato per {nome_barbiere} alle {ora_manuale.strftime('%H:%M')}!")
                        st.rerun() 
                    except IntegrityError:
                        st.error("Errore: La chiave primaria del DB in memoria è stata resettata. Riprova.")
                    except OperationalError:
                        st.error("Errore DB: Tentativo fallito di scrivere. Riprova subito a salvare l'appuntamento.")
                    except Exception as e:
                        st.error(f"Errore DB: Impossibile salvare l'appuntamento. Dettagli: {e}")
                
def admin_app():
    st.title("✂️ Pannello di Gestione Appuntamenti")
    
    # AVVISO IMPORTANTE: Riguardo il DB in memoria
    st.warning("ATTENZIONE: Questa applicazione utilizza un database in memoria (SQLite). I dati vengono persi ogni volta che l'app viene riavviata su Streamlit Cloud. Le prenotazioni compaiono solo se fatte DURANTE questa sessione attiva dell'app.")

    if st.button("⬅️ Torna alla modalità Prenotazione Clienti"):
        st.session_state['current_view'] = 'client'
        st.rerun()
    
    st.markdown("---")
    
    min_date = date.today()
    data_scelta_admin = st.date_input(
        "Seleziona la data da visualizzare:",
        value=min_date,
        min_value=min_date,
        format="DD/MM/YYYY"
    )

    if data_scelta_admin.weekday() in GIORNI_CHIUSURA:
        st.warning("Giorno di chiusura. Nessuna prenotazione possibile.")
        return

    st.markdown("---")

    col_salvatore, col_raffaele = st.columns(2)

    with col_salvatore:
        display_calendar_view(1, "Salvatore", data_scelta_admin)

    with col_raffaele:
        display_calendar_view(2, "Raffaele", data_scelta_admin)


# --- 5. INTERFACCIA PRINCIPALE STREAMLIT (Lato Cliente) ---

def main_app():
    st.set_page_config(page_title="Prenotazione Barbiere", layout="centered")
    
    # --- GESTIONE MESSAGGI PERSISTENTI (Per visualizzare successo o errore dopo rerun) ---
    if 'last_action_status' in st.session_state:
        if st.session_state['last_action_status'] == 'success':
            st.success(st.session_state['last_action_message'])
        elif st.session_state['last_action_status'] == 'error':
            st.error(st.session_state['last_action_message'])
            
        # Pulisci lo stato dopo aver mostrato il messaggio una volta
        st.session_state.pop('last_action_status')
        st.session_state.pop('last_action_message')
    # --- FINE GESTIONE MESSAGGI PERSISTENTI ---
    
    # --- GRAFICA TESTUALE MIGLIORATA ---
    st.markdown(
        """
        <style>
        .barber-title {
            font-family: 'Playfair Display', serif; 
            font-size: 3.5em; 
            font-weight: bold;
            color: #f69a23; 
            text-align: center;
            margin-bottom: -15px; 
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5); 
        }
        .barber-subtitle {
            font-family: 'Open Sans', sans-serif; 
            font-size: 1.2em;
            color: #CCCCCC; 
            text-align: center;
            margin-bottom: 25px;
            letter-spacing: 2px; 
        }
        </style>
        <div class="barber-title">SALVATORE NATILLO</div>
        <div class="barber-subtitle">MODA CAPELLI UOMO</div>
        """, 
        unsafe_allow_html=True
    )
    # --- FINE GRAFICA TESTUALE ---
    
    st.subheader("1. Scegli il tuo servizio")
    
    service_options = ["Seleziona un servizio..."] + [f"{s} ({d} min)" for s, d in SERVIZI.items()]
    service_selection = st.selectbox(
        "Seleziona il trattamento desiderato:",
        options=service_options
    )
    
    if service_selection == "Seleziona un servizio...":
        return 
        
    service_name = service_selection.split(" (")[0]
    durata_servizio_min = SERVIZI[service_name]
    st.info(f"Durata stimata: **{durata_servizio_min} minuti**.")


    st.subheader("2. Scegli Barbiere e Data")

    barbiere_id_map = {name: id for id, name in BARBIERI.items()}
    
    # MODIFICA: Rimosso "Indifferente"
    barbiere_selection_options = ["Seleziona un barbiere..."] + list(BARBIERI.values())
    
    barbiere_scelto_nome = st.selectbox(
        "Preferisci prenotare con:",
        options=barbiere_selection_options
    )
    
    if barbiere_scelto_nome == "Seleziona un barbiere...":
        return 
    
    barbiere_id_scelto = barbiere_id_map[barbiere_scelto_nome]

    def is_day_available(check_date):
        return check_date.weekday() not in GIORNI_CHIUSURA 

    min_date = date.today()
    # Questa logica assicura che il default sia il prossimo giorno lavorativo (Oggi se aperto)
    while not is_day_available(min_date):
        min_date += timedelta(days=1)
    
    data_scelta = st.date_input(
        "Seleziona una data per l'appuntamento:",
        value=min_date, # Default al primo giorno disponibile
        min_value=min_date,
        format="DD/MM/YYYY"
    )

    if not is_day_available(data_scelta):
        st.error("Il Barbiere è chiuso di Lunedì e Domenica.")
        return

    st.subheader("3. Scegli l'ora disponibile")
    
    opzioni_disponibili = ["Seleziona un orario..."]
    slot_to_barbiere_map = {} 
    
    # Poiché il barbiere è già selezionato in modo univoco
    barbiere_id = barbiere_id_scelto
    nome_barbiere = barbiere_scelto_nome
    
    prenotazioni_barbiere_raw = fetch_prenotazioni_per_barbiere(barbiere_id, data_scelta)
    prenotazioni_barbiere = [{'start': p['start'], 'end': p['end']} for p in prenotazioni_barbiere_raw]

    slots_liberi = get_orari_disponibili(data_scelta, durata_servizio_min, prenotazioni_barbiere)

    for slot in slots_liberi:
        slot_time = slot.strftime("%H:%M")
        
        # MODIFICA: Rimosso il nome del barbiere dall'opzione (es. "15:30")
        opzione_completa = slot_time 

        if opzione_completa not in slot_to_barbiere_map:
            opzioni_disponibili.append(opzione_completa)
            # Associamo lo slot orario al Barbiere ID corretto (che è l'unico scelto)
            slot_to_barbiere_map[opzione_completa] = barbiere_id

    
    slot_options_sorted = sorted([o for o in opzioni_disponibili if o != "Seleziona un orario..."])
    final_options = [opzioni_disponibili[0]] + slot_options_sorted


    selected_slot_option = st.selectbox(
        "Orari disponibili (solo quelli liberi):",
        options=final_options,
        key='final_slot_selector'
    )
    
    
    # --- Modulo di Conferma Finale (Mostrato se viene selezionato uno slot) ---
    if selected_slot_option != "Seleziona un orario...":
        
        try:
            # selected_slot_option ORA contiene solo l'orario (es. "09:00")
            barbiere_id_finale = slot_to_barbiere_map[selected_slot_option]
        except KeyError:
            st.warning("Seleziona di nuovo l'orario, errore interno nel mapping.")
            st.session_state.pop('prenotazione_finale', None)
            return

        barbiere_nome_finale = BARBIERI[barbiere_id_finale]
        
        # L'ora inizio è l'opzione selezionata stessa, non c'è bisogno di fare split
        ora_inizio_finale = selected_slot_option 
        
        
        # Aggiorna lo stato della prenotazione in session_state
        if 'prenotazione_finale' not in st.session_state or st.session_state['prenotazione_finale'].get('ora_inizio') != ora_inizio_finale:
            st.session_state['prenotazione_finale'] = {
                'barbiere_id': barbiere_id_finale,
                'barbiere_nome': barbiere_nome_finale,
                'data': data_scelta.strftime("%d/%m/%Y"),
                'ora_inizio': ora_inizio_finale,
                'servizio': service_selection 
            }
        
        
    if len(final_options) <= 1 and selected_slot_option == "Seleziona un orario...":
        st.warning("Nessun orario disponibile per la data e il servizio selezionato.")
        
        
    # --- Modulo di Conferma Dati Cliente (Mostrato dopo la selezione dello slot) ---
    if 'prenotazione_finale' in st.session_state and selected_slot_option != "Seleziona un orario...":
        st.success(f"Conferma: {st.session_state['prenotazione_finale']['ora_inizio']} con {st.session_state['prenotazione_finale']['barbiere_nome']}")
        
        with st.form("form_prenotazione_finale"):
            st.write("Completa i tuoi dati per confermare l'appuntamento:")
            nome = st.text_input("Nome e Cognome", max_chars=100, key="client_nome_final")
            telefono = st.text_input("Numero di Telefono", max_chars=20, key="client_telefono_final")
            
            submitted = st.form_submit_button("CONFERMA LA PRENOTAZIONE")
            
            if submitted:
                if nome and telefono:
                    try:
                        dati_finali = st.session_state['prenotazione_finale']
                        
                        data_ora_inizio = datetime.strptime(f"{dati_finali['data']} {dati_finali['ora_inizio']}", "%d/%m/%Y %H:%M")
                        
                        durata_min = SERVIZI[dati_finali['servizio'].split(" (")[0]]
                        data_ora_fine = data_ora_inizio + timedelta(minutes=durata_min)
                        
                        # 1. SALVA SUL DB 
                        db = SessionLocal()
                        nuova_prenotazione = Prenotazione(
                            barbiere_id=dati_finali['barbiere_id'],
                            data_appuntamento=data_ora_inizio, 
                            ora_inizio=data_ora_inizio,
                            ora_fine=data_ora_fine,
                            servizio=dati_finali['servizio'],
                            cliente_nome=nome,
                            cliente_telefono=telefono
                        )
                        db.add(nuova_prenotazione) 
                        db.commit()
                        db.close()
                        
                        # 2. PREPARA E INVIA MESSAGGIO
                        dati_finali['cliente_nome'] = nome
                        send_confirmation_message(telefono, dati_finali)
                        
                        # 3. CONFERMA SU STATO PERSISTENTE E RERUN
                        st.session_state['last_action_status'] = 'success'
                        st.session_state['last_action_message'] = f"✂️ Appuntamento confermato! Ti aspettiamo il {dati_finali['data']} alle {dati_finali['ora_inizio']}. 💈"
                        st.session_state.pop('prenotazione_finale') 
                        st.rerun() 
                        
                    except OperationalError as e:
                        st.session_state['last_action_status'] = 'error'
                        st.session_state['last_action_message'] = f"Errore DB (Riprova): Impossibile scrivere i dati. Dettagli: {e}"
                        st.rerun() 
                    except Exception as e:
                        st.session_state['last_action_status'] = 'error'
                        st.session_state['last_action_message'] = f"Errore CRITICO durante il salvataggio. Dettagli: {e}"
                        st.rerun() 

                else:
                    st.error("Per favor, inserisci Nome e Telefono.")
    
    # --- SEZIONE DI ACCESSO ADMIN ---
    st.markdown("---")
    st.subheader("Accesso Riservato")
    
    with st.expander("Apri Pannello di Gestione"):
        password = st.text_input("Password Admin:", type="password", key="admin_password_input")
        
        if password == "totore":
            st.success("Accesso Gestione Effettuato.")
            if st.button("Vai al Pannello Admin"):
                st.session_state['current_view'] = 'admin'
                st.rerun()
        elif password and password != "totore":
            st.error("Password errata.")


# --- 6. AVVIO APPLICAZIONE (Logica di inizializzazione forzata) ---

if __name__ == "__main__":
    
    # AZIONE CRITICA: Forza l'inizializzazione del DB in memoria ad ogni esecuzione.
    try:
        init_db() 
    except Exception as e:
        st.error(f"Errore critico di inizializzazione del database. L'app non può funzionare. Dettagli: {e}")
        st.stop()
            
    
    if 'current_view' not in st.session_state:
        st.session_state['current_view'] = 'client'
        
    if st.session_state['current_view'] == 'admin':
        admin_app()
    else:
        main_app()
