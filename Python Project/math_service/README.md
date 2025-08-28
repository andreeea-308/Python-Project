# Overview

`math_service` este un microserviciu modular, construit pe FastAPI, care oferă operații matematice (putere, factorial, Fibonacci), cu caching în memorie, persistență SQLite și o interfață simplă frontend. Expune atât un CLI (Click), cât și un API REST, și este acoperit de un pachet complet de teste.

---

## Structura proiectului
```text
math_service/
├── api/
│   ├── __init__.py           # Pachet API
│   └── main.py               # Endpoint REST principal
├── db/
│   ├── __init__.py           # Pachet DB
│   └── sqlite_handler.py     # Persistență în SQLite
├── exceptions/
│   ├── __init__.py           # Pachet excepții
│   └── handlers.py           # Gestionarea excepțiilor
├── frontend/
│   ├── database.html         # Pagina de administrare DB
│   ├── index.html            # Interfață utilizator
│   └── style.css             # Styling pentru frontend
├── operations/
│   ├── __init__.py           # Pachet operații
│   ├── factorial.py          # Logica de calcul factorial
│   ├── fibonacci.py          # Generarea șirului Fibonacci
│   └── pow.py                # Calculul puterii numerice
├── test/
│   ├── phase_1/
│   │   ├── __init__.py
│   │   ├── test_cache_integration.py       # Test integrare caching
│   │   ├── test_database_integration.py    # Test integrare DB
│   │   └── test_mathematical_operations.py # Test operații matematice
│   ├── phase_2/
│   │   ├── __init__.py
│   │   ├── test_end_to_end.py               # Test end-to-end
│   │   └── test_rest_api.py                 # Test REST API
│   └── phase_3/
│       ├── __init__.py
│       ├── conftest.py                      # Configurare pytest
│       ├── pytest.ini                       # Configurare pytest
│       └── test_performance_load.py         # Test de performanță
├── utils/
│   ├── __init__.py           # Pachet utilitare
│   ├── cache.py              # Caching in-memory
│   └── logger.py             # Logging structurat
├── workers/
│   ├── __init__.py           # Pachet workeri
│   └── thread_worker.py      # Worker thread-based
├── .flake8                    # Configurare linting
├── __init__.py                # Init modul principal
├── cli.py                     # CLI principal cu Click
├── cli_rest.py                # CLI REST-based cu Click
├── models.py                  # Modele Pydantic pentru input/output
├── operations.db              # Bază de date SQLite locală
├── README.md                  # Documentaţie şi instrucţiuni
└── requirements.txt           # Dependenţe proiect
```

## Componente cheie  
- **Operații** (`operations/`)  
  - `pow.py`, `factorial.py`, `fibonacci.py` implementează algoritmii de bază.  
- **Caching** (`utils/cache.py`)  
  - Cache în memorie pentru a evita scrierile repetate în bază de date și statistici hits/misses.  
- **Persistență** (`db/sqlite_handler.py`)  
  - Gestionează stocarea cererilor, timestamp-uri și filtrare.  
- **API** (`api/main.py`)  
  - Rute sub `/api/{operation}`, plus `/api/requests`, `/api/database/stats` și gestionarea cache-ului.  
- **CLI** (`cli.py`, `cli_rest.py`)  
  - Comenzi locale și remote pentru operații, prin Click.  
- **Frontend** (`frontend/`)  
  - Pagină web pentru efectuare operații și vizualizare cereri stocate.  
- **Worker** (`workers/thread_worker.py`)  
  - Colectează sarcini grele în afara buclei principale, pentru performanță.

## Testare  
- **Unit & Integrare**  
  - `test_mathematical_operations.py`, `test_cache_integration.py`, `test_database_integration.py`.  
- **API REST**  
  - `test_rest_api.py`: validare endpoint-uri și scheme.  
- **End-to-End**  
  - `test_end_to_end.py`: testează fluxul complet prin Uvicorn.  
- **Performanță & Load**  
  - `test_performance_load.py`: verifică scalabilitate, timpi de răspuns și limite.  
- **Configurare pytest**  
  - `conftest.py` (fixture-uri), `pytest.ini` (markeri, timeouts).

## Funcționalități  
- **Operații matematice**  
  - Calculul puterii (`pow`)  
  - Calculul factorialului (`factorial`)  
  - Generarea șirului Fibonacci (`fibonacci`)  
- **CLI (Click)**  
  - Comenzi locale rapide pentru fiecare operație  
  - CLI REST-aware pentru invocare prin API  
- **API REST (FastAPI)**  
  - Endpoint-uri individuale:  
    - `POST /api/pow`  
    - `POST /api/factorial`  
    - `POST /api/fibonacci`  
  - Endpoint-uri de administrare:  
    - `GET  /api/requests` — istoricul tuturor cererilor  
    - `GET  /api/database/stats` — statistici SQLite (număr cereri, timp total)  
    - `GET  /api/cache/stats` — hit/miss cache  
    - `POST /api/cache/clear` — resetare cache  
- **Caching în memorie**  
  - Evitarea scrierilor repetate în baza de date  
  - Statistici detaliate: hit-uri și miss-uri  
- **Persistență (SQLite)**  
  - Stocarea fiecărei cereri cu timestamp și parametri  
  - Filtrare și interogare a istoricului  
- **Worker thread-based**  
  - Preluarea sarcinilor costisitoare în fundal  
  - Îmbunătățirea performanței pentru calcule mari  
- **Frontend simplu**  
  - Pagina de calcul interactiv (`index.html`)  
  - Vizualizare tabelară a cererilor salvate (`database.html`)  
- **Testare completă**  
  - Unit, integrare, end-to-end și performanță  
  - Fixture-uri și configurare pytest pentru mediul de test

---

## Început rapid  
1. **Instalare**  
   ```bash
   pip install -r requirements.txt
    ```
2. **Pornire API**  
   ```bash
   uvicorn math_service.api.main:app --reload
    ```
3. **Utilizare CLI**  
   ```bash
   python cli.py pow --x 2 --y 8
   ```
4. **Frontend**  
   Deschide `frontend/index.html` în browser.





