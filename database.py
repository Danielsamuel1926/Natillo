# File: database.py

from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import streamlit as st # Importato per usare la cache di Streamlit

# --- Configurazione del Database PERSISTENTE ---
# Utilizziamo un file chiamato 'appuntamenti.db' nella directory dell'app
# Questo risolve il problema della perdita di dati tra i refresh.
DATABASE_URL = "sqlite:///appuntamenti.db"

Base = declarative_base()

# Definizione del modello
class Prenotazione(Base):
    __tablename__ = "prenotazioni"
    
    id = Column(Integer, primary_key=True, index=True)
    barbiere_id = Column(Integer, index=True) # 1 per Salvatore, 2 per Raffaele
    data_appuntamento = Column(DateTime, index=True) 
    ora_inizio = Column(DateTime, default=datetime.utcnow)
    ora_fine = Column(DateTime)
    servizio = Column(String)
    cliente_nome = Column(String)
    cliente_telefono = Column(String)

    def __repr__(self):
        return f"<Prenotazione(id={self.id}, barbiere={self.barbiere_id}, data='{self.data_appuntamento}')>"

# --- Funzioni di Inizializzazione con Cache di Streamlit ---

@st.cache_resource
def get_engine():
    """Crea e mette in cache il motore SQLAlchemy."""
    return create_engine(
        DATABASE_URL, connect_args={"check_same_thread": False}
    )

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Crea le tabelle se non esistono."""
    # Base.metadata.drop_all(bind=engine) # DEBUG: Decommenta per resettare
    Base.metadata.create_all(bind=engine)
