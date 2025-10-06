# DynamicAI (DocumentAI)

> Applicazione per la gestione, visualizzazione e processamento di documenti (PDF/TIFF) con struttura modulare e icone dedicate.

---

## Struttura organizzativa

- **main.py** – Entry point semplice e pulito  
- **config/** – Gestione configurazione e costanti  
- **database/** – Persistenza e gestione database SQLite  
- **gui/dialogs/** – Finestre di dialogo (impostazioni, selezione categoria)  
- **gui/components/** – Componenti UI riutilizzabili (miniature, gruppi documento)  
- **loaders/** – Caricamento documenti PDF/TIFF  
- **export/** – Gestione export in tutti i formati  
- **gui/main_window.py** – Finestra principale semplificata  
- **utils/** – Helper e funzioni di utilità  
- **assets/icons/** – Icone dell’applicazione (runtime e build)

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
