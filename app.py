import streamlit as st
from datetime import datetime, time, timedelta, date
from database import init_db, Prenotazione, Barbiere, SessionLocal
from sqlalchemy import extract 

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
    
    # 1. Iterazione su tutti gli intervalli di apertura
    for start_time, end_time in ORARI_APERTURA:
        current_time = datetime.combine(data_selezionata, start_time)
        end_boundary = datetime.combine(data_selezionata, end_time)

        # 2. Iterazione su ogni slot di 30 minuti (la cadenza minima)
        while current_time < end_boundary:
            
            fine_prenotazione = current_time + durata_servizio
            
            # Se il servizio finisce oltre l'orario di chiusura, non è disponibile
            if fine_prenotazione > end_boundary:
                current_time += SLOT_CADENZA
                continue

            # 3. Verifica delle sovrapposizioni
            slot_libero = True
            for p in prenotazioni_esistenti:
                start_esistente = p['start']
                end_esistente = p['end']

                # Verifica se il nuovo slot si sovrappone a una prenotazione esistente
                if current_time < end_esistente and fine_prenotazione > start_esistente:
                    slot_libero = False
                    break 

            if slot_libero:
                disponibilita.append(current_time)

            current_time += SLOT_CADENZA

    return disponibilita

# --- 3. FUNZIONE DI ACCESSO AL DATABASE (DB) ---

def fetch_prenotazioni_per_barbiere(barbiere_id, data_selezionata):
    """
    Recupera le prenotazioni REALI dal database per l'Admin Panel.
    """
    db = SessionLocal()
    
    prenotazioni_records = db.query(Prenotazione).filter(
        Prenotazione.barbiere_id == barbiere_id,
        Prenotazione.data_appuntamento == data_selezionata
    ).order_by(Prenotazione.ora_inizio).all() 
    
    db.close()
    
    risultati_formattati = []
    for p in prenotazioni_records:
        risultati_formattati.append({
            'id': p.id, # <--- AGGIUNTO ID PER ELIMINAZIONE
            'start': p.ora_inizio,
            'end': p.ora_fine,
            'cliente_nome': p.cliente_nome,
            'servizio': p.servizio
        })
        
    return risultati_formattati

# --- NUOVA FUNZIONE HELPER PER L'ELIMINAZIONE ---
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
# -----------------------------------------------

# --- 4. INTERFACCIA DI GESTIONE (ADMIN PANEL) ---

def display_calendar_view(barbiere_id, nome_barbiere, data_selezionata):
    """Visualizza il calendario degli appuntamenti per un singolo barbiere, con opzione Elimina."""
    st.markdown(f"**{nome_barbiere}**")

    # 1. Recupera le prenotazioni dal DB
    prenotazioni_del_giorno = fetch_prenotazioni_per_barbiere(barbiere_id, data_selezionata)
    
    if not prenotazioni_del_giorno:
        st.info("Nessun appuntamento prenotato.")
        
    else:
        st.markdown("##### Appuntamenti del Giorno:")
        
        # Colonna per visualizzazione e eliminazione
        col_ora, col_durata, col_cliente, col_azione = st.columns([1, 1, 2, 1])
        col_ora.markdown("**Ora**")
        col_durata.markdown("**Durata**")
        col_cliente.markdown("**Cliente/Servizio**")
        col_azione.markdown("**Elimina**")
        st.markdown("---")


        for p in prenotazioni_del_giorno:
            prenotazione_id = p['id']
            durata_min = int((p['end'] - p['start']).total_seconds() / 60) 
            
            # Row for each appointment
            col_ora, col_durata, col_cliente, col_azione = st.columns([1, 1, 2, 1])
            
            col_ora.write(p['start'].strftime("%H:%M"))
            col_durata.write(f"{durata_min} min")
            col_cliente.write(f"**{p['cliente_nome']}** - {p['servizio']}")
            
            with col_azione:
                # Pulsante di eliminazione
                if st.button("❌", help="Elimina appuntamento", key=f"delete_{prenotazione_id}"):
                    if delete_appointment(prenotazione_id):
                        st.toast(f"Appuntamento di {p['cliente_nome']} eliminato.", icon='🗑️')
                        st.rerun() # Forza il refresh della pagina
                    else:
                        st.error("Errore nell'eliminazione dell'appuntamento.")
    
    # 4. Aggiungi la possibilità di inserire manualmente (RESTO DEL CODICE ADMIN)
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
                            data_appuntamento=data_selezionata,
                            ora_inizio=data_ora_inizio,
                            ora_fine=data_ora_fine,
                            servizio=f"{servizio_manuale}",
                            cliente_nome=nome_cli,
                            cliente_telefono=tel_cli
                        )
                        db.add(nuova_prenotazione)
                        db.commit()
                        db.close()
                        st.success(f"Appuntamento salvato per {nome_barbiere} alle {ora_manuale.strftime('%H:%M')}!")
                        st.rerun() 
                    except Exception as e:
                        st.error(f"Errore DB: Impossibile salvare l'appuntamento. {e}")
                
def admin_app():
    st.title("✂️ Pannello di Gestione Appuntamenti")
    
    # 1. Selettore di Data per l'Amministratore
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

    # 2. Visualizzazione Affiancata (due colonne)
    col_salvatore, col_raffaele = st.columns(2)

    with col_salvatore:
        # Usa l'ID 1 per Salvatore
        display_calendar_view(1, "Salvatore", data_scelta_admin)

    with col_raffaele:
        # Usa l'ID 2 per Raffaele
        display_calendar_view(2, "Raffaele", data_scelta_admin)


# --- 5. INTERFACCIA PRINCIPALE STREAMLIT (Lato Cliente) ---

def main_app():
    init_db() 
    st.set_page_config(page_title="Prenotazione Barbiere", layout="centered")
    
    # Setup del Logo e Titolo
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 20px;">
            <h1>SALVATORE NATILLO</h1>
            <p>MODA CAPELLI UOMO</p>
            <p style="font-size: small;">[Logo Barbiere Qui]</p>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    st.subheader("1. Scegli il tuo servizio")
    
    service_options = [f"{s} ({d} min)" for s, d in SERVIZI.items()]
    service_selection = st.selectbox(
        "Seleziona il trattamento desiderato:",
        options=service_options
    )
    
    if not service_selection:
        return 
        
    service_name = service_selection.split(" (")[0]
    durata_servizio_min = SERVIZI[service_name]
    st.info(f"Durata stimata: **{durata_servizio_min} minuti**.")


    # --- FASE 2: Scelta Barbiere e Data ---
    st.subheader("2. Scegli Barbiere e Data")

    barbiere_id_map = {name: id for id, name in BARBIERI.items()}
    barbiere_selection_options = ["Indifferente"] + list(BARBIERI.values())
    
    barbiere_scelto_nome = st.selectbox(
        "Preferisci prenotare con:",
        options=barbiere_selection_options
    )
    
    # Trova il primo giorno disponibile 
    def is_day_available(check_date):
        return check_date.weekday() not in GIORNI_CHIUSURA 

    min_date = date.today()
    while not is_day_available(min_date):
        min_date += timedelta(days=1)
    
    data_scelta = st.date_input(
        "Seleziona una data per l'appuntamento:",
        value=min_date,
        min_value=min_date,
        format="DD/MM/YYYY"
    )

    if not is_day_available(data_scelta):
        st.error("Il Barbiere è chiuso di Lunedì e Domenica.")
        return

    # --- FASE 3: Visualizzazione Slot (Menu a Tendina) ---
    st.subheader("3. Scegli l'ora disponibile")
    
    opzioni_disponibili = ["Seleziona un orario..."]
    slot_to_barbiere_map = {} 
    
    barbieri_da_controllare = []
    if barbiere_scelto_nome == "Indifferente":
        barbieri_da_controllare = list(BARBIERI.items())
    else:
        barbiere_id = barbiere_id_map[barbiere_scelto_nome]
        barbieri_da_controllare = [(barbiere_id, barbiere_scelto_nome)]
    

    # Itera sui barbieri per raccogliere gli slot
    for id_barbiere, nome_barbiere in barbieri_da_controllare:
        
        # Uso la funzione fetch_prenotazioni_per_barbiere per la schedulazione.
        prenotazioni_barbiere_raw = fetch_prenotazioni_per_barbiere(id_barbiere, data_scelta)
        
        # Filtro i dati per passarli alla schedulazione (la schedulazione non ha bisogno di nome/servizio)
        prenotazioni_barbiere = [{'start': p['start'], 'end': p['end']} for p in prenotazioni_barbiere_raw]

        slots_liberi = get_orari_disponibili(data_scelta, durata_servizio_min, prenotazioni_barbiere)

        for slot in slots_liberi:
            slot_time = slot.strftime("%H:%M")
            
            if barbiere_scelto_nome == "Indifferente":
                opzione_completa = f"{slot_time} con {nome_barbiere}"
            else:
                opzione_completa = slot_time

            opzioni_disponibili.append(opzione_completa)
            
            slot_to_barbiere_map[opzione_completa] = id_barbiere

    
    # Ordina gli slot per ora
    slot_options_sorted = sorted(opzioni_disponibili[1:])
    final_options = [opzioni_disponibili[0]] + slot_options_sorted


    # Visualizzazione Menu a Tendina
    selected_slot_option = st.selectbox(
        "Orari disponibili (solo quelli liberi):",
        options=final_options,
        key='final_slot_selector'
    )
    
    
    # --- Modulo di Conferma Finale (Attivato dalla selezione dal menu a tendina) ---
    if selected_slot_option != "Seleziona un orario...":
        
        barbiere_id_finale = slot_to_barbiere_map[selected_slot_option]
        barbiere_nome_finale = BARBIERI[barbiere_id_finale]
        
        ora_inizio_finale = selected_slot_option.split(" con")[0] 
        
        st.session_state['prenotazione_finale'] = {
            'barbiere_id': barbiere_id_finale,
            'barbiere_nome': barbiere_nome_finale,
            'data': data_scelta.strftime("%d/%m/%Y"),
            'ora_inizio': ora_inizio_finale,
            'servizio': service_selection 
        }
        st.rerun() 

    # Messaggio di avviso se non ci sono slot
    if len(final_options) <= 1:
        st.warning("Nessun orario disponibile per la data e il servizio selezionato.")
        
        
    # --- Modulo di Conferma Dati Cliente (Mostrato dopo st.rerun()) ---
    if 'prenotazione_finale' in st.session_state:
        st.success(f"Conferma: {st.session_state['prenotazione_finale']['ora_inizio']} con {st.session_state['prenotazione_finale']['barbiere_nome']}")
        
        with st.form("form_prenotazione_finale"):
            st.write("Completa i tuoi dati per confermare l'appuntamento:")
            nome = st.text_input("Nome e Cognome", max_chars=100)
            telefono = st.text_input("Numero di Telefono", max_chars=20)
            
            submitted = st.form_submit_button("CONFERMA LA PRENOTAZIONE")
            
            if submitted:
                if nome and telefono:
                    try:
                        dati_finali = st.session_state['prenotazione_finale']
                        
                        data_ora_inizio = datetime.strptime(f"{dati_finali['data']} {dati_finali['ora_inizio']}", "%d/%m/%Y %H:%M")
                        
                        durata_min = SERVIZI[dati_finali['servizio'].split(" (")[0]]
                        data_ora_fine = data_ora_inizio + timedelta(minutes=durata_min)
                        
                        # Salvataggio
                        db = SessionLocal()
                        nuova_prenotazione = Prenotazione(
                            barbiere_id=dati_finali['barbiere_id'],
                            data_appuntamento=data_ora_inizio.date(), 
                            ora_inizio=data_ora_inizio,
                            ora_fine=data_ora_fine,
                            servizio=dati_finali['servizio'],
                            cliente_nome=nome,
                            cliente_telefono=telefono
                        )
                        db.add(nuova_prenotazione)
                        db.commit()
                        db.close()
                        
                        st.balloons() 
                        st.success(f"🎉 Appuntamento confermato! Ti aspettiamo il {dati_finali['data']} alle {dati_finali['ora_inizio']}.")
                        st.session_state.pop('prenotazione_finale') 
                    except Exception as e:
                        st.error(f"Errore durante il salvataggio: {e}")
                else:
                    st.error("Per favore, inserisci Nome e Telefono.")

# --- 6. AVVIO APPLICAZIONE ---

if __name__ == "__main__":
    
    st.sidebar.title("Modalità")
    # Configurazione della Password Admin
    password = st.sidebar.text_input("Inserisci Password Admin ('admin'):", type="password")
    
    mode = "Clienti (Prenotazione)"
    if password == "admin":
        st.sidebar.success("Accesso Gestione Effettuato.")
        mode = st.sidebar.radio("Seleziona Interfaccia:", ["Clienti (Prenotazione)", "Gestione (Admin Panel)"])
    
    if mode == "Clienti (Prenotazione)":
        main_app()
    elif mode == "Gestione (Admin Panel)":
        admin_app()