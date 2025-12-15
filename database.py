from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, date

# Configurazione del Database (SQLite file)
DATABASE_URL = "sqlite:///barberia.db"
Engine = create_engine(DATABASE_URL)
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=Engine)

# --- Definizione del Modello (Tabelle) ---

# Tabella per i Barbieri (Salvatore e Raffaele)
class Barbiere(Base):
    __tablename__ = "barbieri"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True)
    
    prenotazioni = relationship("Prenotazione", back_populates="barbiere")

# Tabella per le Prenotazioni (Il cuore del sistema)
class Prenotazione(Base):
    __tablename__ = "prenotazioni"
    id = Column(Integer, primary_key=True, index=True)
    
    # Chiave esterna che lega la prenotazione al barbiere
    barbiere_id = Column(Integer, ForeignKey("barbieri.id"))
    barbiere = relationship("Barbiere", back_populates="prenotazioni")
    
    # Dati Appuntamento
    data_appuntamento = Column(Date, index=True)
    ora_inizio = Column(DateTime)
    ora_fine = Column(DateTime)
    servizio = Column(String) # Potrebbe essere un'altra FK, ma String è più semplice ora
    
    # Dati Cliente
    cliente_nome = Column(String)
    cliente_telefono = Column(String)

# --- Funzioni di Utility ---

def init_db():
    """Crea le tabelle se non esistono e popola i dati iniziali."""
    Base.metadata.create_all(bind=Engine)
    db = SessionLocal()
    
    # Popola i barbieri solo se non sono già presenti
    if db.query(Barbiere).count() == 0:
        salvatore = Barbiere(id=1, nome="Salvatore")
        raffaele = Barbiere(id=2, nome="Raffaele")
        db.add_all([salvatore, raffaele])
        db.commit()
        print("Database popolato con i barbieri iniziali.")
    
    db.close()
    
def get_db():
    """Generatore per la sessione del database (necessario per SQLAlchemy)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()