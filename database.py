from sqlalchemy import create_engine, Column, Integer, String, Date, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import streamlit as st
import os

# --- CONFIGURAZIONE CRITICA PER STREAMLIT CLOUD SENZA DB ESTERNO ---
# Utilizza SQLite in memoria. I dati NON VERRANNO SALVATI TRA I RIAVVII.
DATABASE_URL = "sqlite:///:memory:"

# SQLite necessita di questo flag per la sicurezza del thread
connect_args={"check_same_thread": False}

# Inizializzazione del motore
engine = create_engine(
    DATABASE_URL, 
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Definizione del Modello (NON CAMBIA) ---

class Barbiere(Base):
    __tablename__ = 'barbieri'
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)

class Prenotazione(Base):
    __tablename__ = 'prenotazioni'
    id = Column(Integer, primary_key=True, index=True)
    barbiere_id = Column(Integer)
    data_appuntamento = Column(Date)
    ora_inizio = Column(DateTime)
    ora_fine = Column(DateTime)
    servizio = Column(String)
    cliente_nome = Column(String)
    cliente_telefono = Column(String)

# --- Funzione di Inizializzazione ---

def init_db():
    # Crea le tabelle (le ricrea in memoria a ogni avvio)
    Base.metadata.create_all(bind=engine)
    
    # Popola la tabella barbieri
    db = SessionLocal()
    # Controlliamo se i barbieri sono già stati creati in questa sessione in memoria
    if db.query(Barbiere).count() == 0:
        barbieri_iniziali = [
            Barbiere(id=1, nome="Salvatore"),
            Barbiere(id=2, nome="Raffaele")
        ]
        db.add_all(barbieri_iniziali)
        db.commit()
    db.close()
