# DynamicAI (DocumentAI)

> Applicazione per la gestione, visualizzazione e processamento di documenti (PDF/TIFF) con struttura modulare e icone dedicate.

---

## Struttura organizzativa

DynamicAI/
├── main.py                    # Entry point con error handling robusto
├── batch/                     # Sistema batch multi-livello avanzato
│   ├── __init__.py
│   ├── scanner.py            # Scansione ricorsiva intelligente
│   ├── batch_database.py     # Database recovery crash
│   └── batch_exporter.py     # Export preservando struttura
├── config/                   # Configurazione multi-piattaforma
│   ├── __init__.py
│   ├── settings.py          # ConfigManager con path dinamici
│   └── constants.py         # DEFAULT_CONFIG v3.6 BATCH
├── database/                 # Database categorie avanzato
│   ├── __init__.py
│   └── category_db.py       # Dynamic JSON tracking + protezione
├── export/                   # Export manager enterprise
│   ├── __init__.py
│   └── export_manager.py    # 30K+ caratteri, 5 formati, numerazione
├── gui/                      # Interfaccia grafica suprema
│   ├── __init__.py
│   ├── main_window.py       # 150K+ caratteri, GUI professionale
│   ├── components/          # Componenti UI avanzati
│   │   ├── __init__.py
│   │   ├── thumbnail.py     # Lazy loading + drag&drop
│   │   └── document_group.py # Layout grid responsive
│   └── dialogs/             # Dialog system enterprise
│       ├── __init__.py
│       ├── batch_manager.py  # 55K+ caratteri batch supremo
│       ├── settings_dialog.py # 54K+ caratteri, 8 tab
│       ├── category_dialog.py # Selezione categorie intelligente
│       └── fix_database.py   # Utility migrazione schema
├── loaders/                  # Document loader enterprise
│   ├── __init__.py
│   └── document_loaders.py  # MemoryAwareLRUCache + PDF/TIFF
└── utils/                    # Utilities sistema enterprise
    ├── __init__.py
    ├── helpers.py           # 13K+ caratteri utilities supremo
    └── branding.py          # Sistema branding cross-platform

### Vantaggi principali
- Ogni classe ha una responsabilità specifica
- Facile manutenzione e debug
- Componenti testabili indipendentemente
- Aggiunta di nuove funzionalità più semplice
- Codice più leggibile e organizzato

### Processo di migrazione consigliato
1. Sposta le classi più indipendenti (**CategoryDatabase**, **DocumentLoaders**).  
2. Migra i **dialoghi**.  
3. Migra i **componenti UI**.  
4. Refactor della **finestra principale**.  

Questa struttura mantiene tutte le funzionalità esistenti ma le organizza in modo più gestibile.

---

## Struttura completa dei file

### File principale
- **main.py** – Entry point dell’applicazione

### Modulo `config`
- **config/__init__.py** – Esporta `ConfigManager` e costanti  
- **config/constants.py** – Costanti e configurazione default  
- **config/settings.py** – Gestione configurazione e percorsi file

### Modulo `database`
- **database/__init__.py** – Esporta `CategoryDatabase`  
- **database/category_db.py** – Gestione database SQLite per categorie

### Modulo `loaders`
- **loaders/__init__.py** – Esporta `DocumentLoaders`  
- **loaders/document_loaders.py** – Caricamento PDF e TIFF con factory function

### Modulo `export`
- **export/__init__.py** – Esporta `ExportManager`  
- **export/export_manager.py** – Gestione export in tutti i formati con file handling

### Modulo GUI – dialoghi
- **gui/dialogs/__init__.py** – Esporta dialoghi  
- **gui/dialogs/category_dialog.py** – Dialogo selezione categoria con ricerca  
- **gui/dialogs/settings_dialog.py** – Dialogo impostazioni completo con tabs

### Modulo GUI – componenti
- **gui/components/__init__.py** – Esporta componenti UI  
- **gui/components/thumbnail.py** – Componente miniatura con drag&drop  
- **gui/components/document_group.py** – Componente gruppo documento

### Modulo GUI – principale
- **gui/__init__.py** – Esporta `AIDOXAApp`  
- **gui/main_window.py** – Finestra principale  
  - Parte 1: setup UI, menu, eventi  
  - Parte 2: gestione documenti, zoom, drag&drop, context menu

### Modulo `utils`
- **utils/__init__.py** – Esporta helper comuni  
- **utils/helpers.py** – Funzioni di utilità (dialoghi progress, help, about, validazione)  
- **utils/branding.py** – Helper per icone e path PyInstaller-safe  
  - Funzione chiave:
    ```python
    from utils.branding import set_app_icon
    # all'interno di setup_window / __init__ della finestra principale:
    set_app_icon(self)  # usa assets/icons/documentai.png
    ```
  - Note: `resource_path()` gestisce correttamente l’accesso ai file sia in sviluppo che in bundle PyInstaller.

---

## Icone dell’applicazione

- **assets/icons/documentai.png** – Icona finestra (runtime Tkinter)  
- **assets/icons/documentai.ico** – Icona eseguibile (PyInstaller / Windows)

### Utilizzo a runtime (Tkinter)
In `gui/main_window.py`:
```python
from utils.branding import set_app_icon

def setup_window(self):
    # ...
    set_app_icon(self)  # carica assets/icons/documentai.png
    # ...
```

### Utilizzo in build (PyInstaller)
Nel file `.spec` (es. `DynamicAI_with_icon.spec`):
```python
a = Analysis(
    ['main.py'],
    # ...
    datas=[
        ('assets/icons/documentai.png', 'assets/icons'),
        ('assets/icons/documentai.ico', 'assets/icons'),
    ],
    # ...
)

exe = EXE(
    pyz,
    a.scripts,
    # ...
    icon='assets/icons/documentai.ico',  # icona EXE su Windows
)
```

Suggerimento: mantiene tutte le icone in `assets/icons/` per evitare path hardcoded e rendere il progetto portabile.

---

## Build & Run

### Requisiti
- **Python 3.10+** (consigliato)  
- Dipendenze del progetto (installa con `pip`)

### Setup ambiente (consigliato)
```bash
# Windows (PowerShell)
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> Se non hai un `requirements.txt`, installa i pacchetti necessari del progetto (esempio indicativo):  
> `pip install pillow pypdf2 tk`

### Avvio da sorgente
```bash
python main.py
```

### Build eseguibile (Windows, PyInstaller) con la console
```bash
pyinstaller DynamicAI_with_icon.spec
```
### Build eseguibile (Windows, PyInstaller) senza la console
```bash
pyinstaller --noconsole --onefile DynamicAI_with_icon.spec
pyinstaller DynamicAI_with_icon.spec
pyinstaller --noconsole --onefile --icon=assets/icons/app.ico main.py
# oppure: pyinstaller --noconfirm DynamicAI_with_icon.spec
```
L’eseguibile userà `assets/icons/documentai.ico` come icona.

---

## Note di manutenzione
- Evita path hardcoded: usa `pathlib.Path` e funzioni helper.  
- Nella UI **non** usare `time.sleep()` nel main thread (usa `after()` per non bloccare l’interfaccia).  
- Per operazioni lunghe: thread + `queue` e aggiornamenti UI con `after()`.  
- Limita `except:` e `except Exception`: preferisci eccezioni specifiche e logging strutturato.

---

## TODO / Roadmap (esempio)
- [ ] Test unitari per i componenti dei loaders/export  
- [ ] Migliorare gestione zoom/pan/scroll e comportamenti edge-case  
- [ ] Logging centralizzato e livelli (info/warn/error)  
- [ ] Profilazione performance su documenti molto grandi

---

Se vuoi, posso aggiornare automaticamente lo `.spec`, patchare `main_window.py` con `set_app_icon(self)` (se non già fatto), e creare uno script “one‑click build” per Windows.
