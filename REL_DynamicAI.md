---
title: "Relazione Tecnica DynamicAI"
project_name: "DynamicAI"
version: "3.6 (BATCH EDITION)"
generated_at: "2025-01-11"
files_count: 35+
---

# Executive Summary
DynamicAI è un **editor documentale avanzato** scritto in Python, progettato per gestire documenti multipagina (PDF e TIFF) e dividerli in documenti singoli sulla base di un file JSON di struttura.

## Novità Versione 3.6 (BATCH EDITION)
- ✨ **Batch Manager**: elaborazione multipla documenti in sequenza
- ✨ **Lazy Loading**: caricamento progressivo thumbnail per performance ottimali
- ✨ **Export Background**: export non-bloccante con progress bar reale
- ✨ **Gestione Metadati Dinamica**: supporto metadati illimitati da JSON
- ✨ **CSV Configurabile**: modalità incremental/per-file con naming avanzato
- ✨ **Grid Layout Multi-riga**: visualizzazione ottimizzata con righe multiple

Il programma permette di:
- Caricare documenti multipagina (PDF/TIFF) singoli o in batch
- Leggere file JSON di riferimento che contengono:
  - Intervalli di pagine (`inizio`, `fine`) con categorie
  - Metadati di intestazione dinamici (illimitati)
- Creare **gruppi documentali** organizzati per categoria con grid layout multi-riga
- Consentire all'operatore la **validazione e modifica manuale dei metadati**
- Esportare documenti in formati multipli (JPEG, PDF, TIFF) con gestione avanzata conflitti
- Generare **CSV riepilogativo** con metadati completi in modalità configurabile
- Elaborare **batch di documenti** in sequenza con validazione progressiva

DynamicAI è dotato di un'interfaccia grafica Tkinter moderna, configurabile tramite file JSON utente, e utilizza SQLite per la gestione delle categorie documentali.

---

# Sommario
1. [Panoramica del Progetto](#1-panoramica-del-progetto)
2. [Inventario dei File](#2-inventario-dei-file)
3. [Dipendenze & Ambiente](#3-dipendenze--ambiente)
4. [Configurazione](#4-configurazione)
5. [Flusso Dati](#5-flusso-dati)
6. [Architettura & Design](#6-architettura--design)
7. [Batch Manager](#7-batch-manager)
8. [Esecuzione, Build & Distribuzione](#8-esecuzione-build--distribuzione)
9. [Persistenza, I/O e Integrazioni](#9-persistenza-io-e-integrazioni)
10. [Qualità, Robustezza, Sicurezza](#10-qualità-robustezza-sicurezza)
11. [Onboarding & Operatività](#11-onboarding--operatività)
12. [Roadmap & Domande Aperte](#12-roadmap--domande-aperte)
13. [Appendici](#appendici)

---

# 1. Panoramica del Progetto
- **Nome**: DynamicAI (alias DocumentAI)
- **Versione**: 3.6 BATCH EDITION
- **Obiettivo**: semplificare la suddivisione e classificazione di documenti multipagina con supporto batch, aggiungendo metadati strutturati e producendo output multipiattaforma
- **Utenti target**: operatori che gestiscono pratiche documentali (edilizie, amministrative, ecc.), integratori software, sviluppatori
- **Tecnologie chiave**: Python 3.10+, Tkinter, PyMuPDF, PIL (Pillow), SQLite, PyInstaller
- **Caratteristiche distintive**:
  - Elaborazione batch automatizzata
  - Lazy loading per performance ottimali
  - Export in background non-bloccante
  - Metadati dinamici illimitati
  - Grid layout multi-riga responsive

---

# 2. Inventario dei File

## Struttura Generale