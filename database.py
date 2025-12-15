from sqlalchemy import create_engine, Column, Integer, String, Date, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import streamlit as st
import os

# --- CONFIGURAZIONE CRITICA PER STREAMLIT CLOUD (SQLite in Memoria) ---
# I dati NON VERRANNO SALVATI tra i riavvii dell'app.
DATABASE_URL = "sqlite:///:memory:"

# SQLite necessita di questo flag per la sicurezza del thread in ambienti concorrenti
connect_args={"check_same_thread": False}

# Inizializzazione del motore
engine = create_engine(
    DATABASE_URL, 
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Definizione dei Modelli (Allineati su DateTime) ---

class Barbiere(Base):
    __tablename__ = 'barbieri'
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)

class Prenotazione(Base):
    __tablename__ = 'prenotazioni'
    id = Column(Integer, primary_key=True, index=True)
    barbiere_id = Column(Integer)
    # MODIFICATO: Usiamo DateTime per coerenza con SQLite e la query 'extract' in app.py
    data_appuntamento = Column(DateTime) 
    ora_inizio = Column(DateTime)
    ora_fine = Column(DateTime)
    servizio = Column(String)
    cliente_nome = Column(String)
    cliente_telefono = Column(String)

# --- Funzione di Inizializzazione ---

def init_db():
    """
    Crea le tabelle del database e popola i dati statici dei barbieri.
    Viene eseguita a ogni avvio dell'app, ricreando il DB in memoria.
    """
    Base.metadata.create_all(bind=engine)
    
    # Popola la tabella barbieri
    db = SessionLocal()
    if db.query(Barbiere).count() == 0:
        barbieri_iniziali = [
            Barbiere(id=1, nome="Salvatore"),
            Barbiere(id=2, nome="Raffaele")
        ]
        db.add_all(barbieri_iniziali)
        db.commit()
    db.close()
