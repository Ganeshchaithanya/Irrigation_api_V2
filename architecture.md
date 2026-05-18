# AquaSol — Complete System Architecture

> **Project:** Smart Precision Irrigation Platform  
> **Stack:** ESP32 Firmware · FastAPI Backend · Flutter App · PyTorch/XGBoost MLOps  
> **Workspace:** `e:\Irrigation_api_V2`

---

## 1. System Overview

```mermaid
graph TB
    subgraph HARDWARE["🔧 IoT Hardware Layer"]
        MASTER["Master Gateway\n(ESP32 + LoRa + WiFi)\nmaster_firmware/"]
        N1["Node 1\n(ESP32 + LoRa + Soil Sensors)\nnode1_firmware/"]
        N2["Node 2\n(ESP32 + LoRa + Soil Sensors)\nnode2_firmware/"]
        N1 -- "LoRa Radio (TDMA)" --> MASTER
        N2 -- "LoRa Radio (TDMA)" --> MASTER
    end

    subgraph BACKEND["⚙️ FastAPI Backend (Python)"]
        API["REST API Layer\nbackend/api/"]
        CORE["Core Engine\nbackend/core/"]
        CTRL["Control Engine\nbackend/control/"]
        SVC["Services Layer\nbackend/services/"]
        DB["PostgreSQL + Alembic\nbackend/db/"]
        MODELS["ML Models Store\nbackend/models_store/"]
    end

    subgraph MLOPS["🤖 MLOps Pipeline"]
        LSTM["LSTM (moisture forecasting)\nmlops/train_lstm.py"]
        XGB["XGBoost (irrigation stage)\nmlops/train_xgboost.py"]
        ANOMALY["Isolation Forest (anomaly)\nmlops/train_anomaly.py"]
        STAGE["Stage XGB (per-crop stage)\nmlops/train_stage_xgb.py"]
    end

    subgraph APP["📱 Flutter Mobile App"]
        FLUTTER["AquaSol App\naquasol_app/lib/"]
    end

    MASTER -- "HTTP POST /api/sensors" --> API
    API --> CORE
    CORE --> DB
    CORE --> CTRL
    CTRL --> DB
    SVC --> DB
    SVC --> MODELS
    MLOPS --> MODELS
    APP -- "REST API (Pinggy tunnel / local)" --> API
    API --> SVC
```

---

## 2. IoT Firmware Layer

| File | Role |
|------|------|
| `master_firmware/master_firmware.ino` | ESP32 Gateway — reads rain/flow sensors, collects node telemetry via LoRa TDMA, POSTs flat JSON to backend, drives relay outputs |
| `node1_firmware/node1_firmware.ino` | Node 1 — reads soil moisture/temperature, awaits LoRa time-slot, transmits telemetry to Master |
| `node2_firmware/node2_firmware.ino` | Node 2 — same role as Node 1, different MAC/pairing code |

**Key Firmware Concepts**
- **Pairing Code**: 6-char code derived from hardware MAC, displayed on LCD/OLED at boot for manual provisioning
- **TDMA Scheduling**: Master arbitrates time-slots to prevent LoRa collisions
- **WDT (Watchdog Timer)**: Prevents firmware lock-ups during radio wait states
- **Flat JSON Telemetry**: All sensors serialised in a single JSON payload per cycle

---

## 3. FastAPI Backend Layer

```mermaid
graph LR
    subgraph APP["app/"]
        MAIN["main.py — FastAPI app factory"]
        STARTUP["startup.py — lifespan hooks"]
        DEPS["dependencies.py — DI providers"]
    end

    subgraph API["api/ — Route Handlers"]
        auth["auth.py"]
        sensors["sensors.py"]
        dashboard["dashboard.py"]
        control["control.py"]
        device["device.py"]
        farm["farm.py"]
        pairing["pairing.py"]
        planner["planner.py"]
        reports["reports.py"]
        alerts["alerts.py"]
        chatbot["chatbot.py"]
        intelligence["intelligence.py"]
        stage["stage.py"]
    end

    subgraph CORE["core/ — Data Pipeline"]
        ingestion["ingestion/\nparser · mapper · validator"]
        aggregation["aggregation/\naggregator.py"]
        reliability["reliability/\nanomaly · trust · perception\nvirtual_sensing · control_loop\nml_supervisor"]
        spatial["spatial/\nroot_estimator.py"]
        state["state/\nstate_manager.py"]
    end

    subgraph CTRL["control/"]
        controller["controller.py"]
        failover["failover.py"]
        cmd_builder["command_builder.py"]
    end

    subgraph SVC["services/"]
        intelligence_engine["intelligence_engine.py\n(main AI orchestrator)"]
        advisory["advisory.py"]
        chatbot_svc["chatbot.py (Groq LLM)"]
        weather["weather.py"]
        alerts_svc["alerts.py"]
        diary_builder["diary_builder.py"]
        context_builder["context_builder.py"]
        health_monitor["health_monitor.py"]
        water_usage["water_usage.py"]
        i18n["i18n_service.py"]
    end

    subgraph DB["db/"]
        session["session.py — async SQLAlchemy"]
        base["base.py — declarative base"]
    end

    subgraph MODELS_ORM["models/ — ORM"]
        user_m["user.py"]
        farm_m["farm.py"]
        device_m["device.py"]
        sensor_m["sensor_data.py"]
        decision_m["decision.py"]
        state_m["state.py"]
        crop_m["crop.py"]
        pairing_m["pairing_session.py"]
        i18n_m["i18n.py"]
    end

    subgraph SCHEMAS["schemas/ — Pydantic"]
        auth_s["auth.py"]
        sensor_s["sensor.py"]
        dashboard_s["dashboard.py"]
        pairing_s["pairing.py"]
    end

    subgraph PLUGINS["plugins/"]
        ai_plugins["ai/ — AI plugin registry"]
        meta_plugins["meta/ — metadata plugins"]
    end

    MAIN --> API
    MAIN --> STARTUP
    API --> CORE
    API --> SVC
    API --> CTRL
    CORE --> DB
    SVC --> DB
    CTRL --> DB
    MODELS_ORM --> DB
```

### Backend Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `app/main.py` | FastAPI factory, mounts all routers, CORS |
| `app/startup.py` | Lifespan: DB init, model preload, background tasks |
| `core/ingestion/` | Parse → validate → map raw IoT JSON into ORM objects |
| `core/aggregation/` | Temporal aggregation of sensor windows |
| `core/reliability/` | Anomaly detection, sensor trust scoring, virtual sensing fallback, ML supervisor |
| `core/spatial/` | Root-zone depth estimation per crop |
| `core/state/` | In-memory device/zone state manager |
| `control/controller.py` | Decides irrigation ON/OFF per zone, writes commands to DB |
| `control/failover.py` | Failsafe rules when ML is unavailable |
| `services/intelligence_engine.py` | Orchestrates LSTM + XGBoost inference → irrigation decisions |
| `services/advisory.py` | Generates crop advisory messages |
| `services/chatbot.py` | Groq LLM chat with farm context |
| `services/weather.py` | External weather API integration |
| `services/diary_builder.py` | Daily farm diary generation |
| `plugins/ai/` | Pluggable AI provider registry |

---

## 4. Database Schema (ORM Models)

```mermaid
erDiagram
    USER {
        int id PK
        string email
        string hashed_password
        string language
    }
    FARM {
        int id PK
        int user_id FK
        string name
        string location
        string crop_type
        string season
    }
    DEVICE {
        int id PK
        int farm_id FK
        string mac_address
        string pairing_code
        string role
        string status
    }
    SENSOR_DATA {
        int id PK
        int device_id FK
        float moisture
        float temperature
        float rain
        float flow
        timestamp recorded_at
    }
    DECISION {
        int id PK
        int farm_id FK
        bool irrigate
        int duration_minutes
        string reason
        timestamp created_at
    }
    STATE {
        int id PK
        int device_id FK
        string relay_state
        timestamp updated_at
    }
    PAIRING_SESSION {
        int id PK
        string pairing_code
        string status
        timestamp expires_at
    }

    USER ||--o{ FARM : owns
    FARM ||--o{ DEVICE : has
    DEVICE ||--o{ SENSOR_DATA : emits
    FARM ||--o{ DECISION : receives
    DEVICE ||--o| STATE : tracks
```

---

## 5. MLOps Pipeline

```mermaid
graph LR
    RAW_DATA["Raw Sensor Data\ndataset_lstm.json\ndataset_xgb.json"]

    subgraph TRAINING["mlops/"]
        LSTM_T["train_lstm.py\nPyTorch LSTM"]
        XGB_T["train_xgboost.py\nXGBoost classifier + duration"]
        STAGE_T["train_stage_xgb.py\nPer-crop stage XGB"]
        ANOMALY_T["train_anomaly.py\nIsolation Forest"]
        GEN["dataset_generator.py\nSynthetic data generator"]
    end

    subgraph STORE["models_store/ (29 files)"]
        LSTM_M["lstm.pt + lstm_scaler.pkl"]
        XGB_M["xgb_classifier.pkl\nxgb_duration.pkl"]
        STAGE_M["stage_xgb_<Crop>_<Season>.pkl\n(17 crop-season combos)\n+ stage_kmeans_*.pkl (5)"]
        ANOMALY_M["isolation_forest.pkl\nanomaly_scaler.pkl"]
    end

    RAW_DATA --> TRAINING
    GEN --> TRAINING
    LSTM_T --> LSTM_M
    XGB_T --> XGB_M
    STAGE_T --> STAGE_M
    ANOMALY_T --> ANOMALY_M
```

| Model | Algorithm | Purpose |
|-------|-----------|---------|
| `lstm.pt` | PyTorch LSTM | Predict next-timestep soil moisture |
| `xgb_classifier.pkl` | XGBoost | Binary irrigate/skip decision |
| `xgb_duration.pkl` | XGBoost | Predict irrigation duration (minutes) |
| `stage_xgb_<Crop>_<Season>.pkl` | XGBoost (17 variants) | Identify crop growth stage from sensor features |
| `stage_kmeans_*.pkl` | K-Means (5 variants) | Stage clustering fallback |
| `isolation_forest.pkl` | Isolation Forest | Sensor anomaly detection |

---

## 6. Flutter Mobile App

```mermaid
graph TB
    subgraph LIB["lib/"]
        MAIN_D["main.dart"]

        subgraph APP_LAYER["app/"]
            ROUTER["router.dart (go_router)"]
        end

        subgraph CORE_LAYER["core/"]
            API_SVC["services/api_service.dart"]
            PAIR_SVC["services/pairing_service.dart"]
            LANG_SVC["services/language_provider.dart"]
            THEME_L["theme/"]
        end

        subgraph SHARED_LAYER["shared/"]
            WIDGETS["widgets/ — reusable UI components"]
        end

        subgraph FEATURES["features/ (14 modules)"]
            AUTH_F["auth/"]
            HOME_F["home/"]
            FARM_F["farm/"]
            CONTROL_F["control/"]
            ALERTS_F["alerts/"]
            ANALYTICS_F["analytics/"]
            CHATBOT_F["chatbot/"]
            DIARY_F["diary/"]
            HEALTH_F["health/"]
            PLANNER_F["planner/"]
            PREDICTIONS_F["predictions/"]
            SETTINGS_F["settings/"]
            SETUP_F["setup/"]
            STAGE_F["stage/"]
        end
    end

    MAIN_D --> ROUTER
    ROUTER --> FEATURES
    FEATURES --> API_SVC
    FEATURES --> PAIR_SVC
    FEATURES --> LANG_SVC
    FEATURES --> WIDGETS
```

### Feature Module Map

| Feature | Screen Purpose |
|---------|---------------|
| `auth/` | Login / Register |
| `setup/` | Pairing code entry → device provisioning |
| `farm/` | Farm & zone management |
| `home/` | Dashboard overview |
| `control/` | Manual relay ON/OFF, zone control |
| `alerts/` | Push alert feed |
| `analytics/` | Sensor history charts |
| `predictions/` | LSTM moisture forecast display |
| `stage/` | Crop growth stage tracking |
| `planner/` | Irrigation schedule planner |
| `diary/` | AI-generated daily farm diary |
| `chatbot/` | Groq LLM farm advisor chat |
| `health/` | Device health / connectivity monitor |
| `settings/` | Language (i18n), account, preferences |

---

## 7. End-to-End Data Flow

```mermaid
sequenceDiagram
    participant Node as Node 1/2
    participant Master as Master Gateway
    participant API as FastAPI Backend
    participant DB as PostgreSQL
    participant ML as Intelligence Engine
    participant App as Flutter App

    Node->>Master: LoRa telemetry (TDMA slot)
    Master->>API: POST /api/sensors (flat JSON)
    API->>API: ingestion/parser → mapper → validator
    API->>DB: INSERT sensor_data
    API->>ML: trigger intelligence_engine
    ML->>DB: fetch recent sensor window
    ML->>ML: LSTM moisture forecast
    ML->>ML: XGBoost irrigate + duration
    ML->>ML: Stage XGBoost (crop stage)
    ML->>ML: Isolation Forest (anomaly check)
    ML->>DB: INSERT decision
    ML->>DB: UPDATE state (relay command)
    Master->>API: GET /api/control/commands
    API->>Master: relay ON/OFF + duration
    App->>API: GET /api/dashboard
    API->>App: aggregated farm state + decisions
    App->>API: POST /api/chatbot/message
    API->>App: Groq LLM advisory response
```

---

## 8. Directory Reference

```
e:\Irrigation_api_V2\
├── main.py                         # Entry point (uvicorn)
├── requirements.txt
├── alembic/                        # DB migrations
│   └── versions/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI factory
│   │   ├── startup.py
│   │   └── dependencies.py
│   ├── api/                        # 13 route modules
│   │   ├── auth.py · sensors.py · dashboard.py
│   │   ├── control.py · device.py · farm.py
│   │   ├── pairing.py · planner.py · reports.py
│   │   ├── alerts.py · chatbot.py · intelligence.py
│   │   └── stage.py
│   ├── core/
│   │   ├── ingestion/  (parser · mapper · validator)
│   │   ├── aggregation/ (aggregator)
│   │   ├── reliability/ (anomaly · trust · perception · virtual_sensing · control_loop · ml_supervisor)
│   │   ├── spatial/    (root_estimator)
│   │   └── state/      (state_manager)
│   ├── control/        (controller · failover · command_builder)
│   ├── services/       (13 service modules incl. intelligence_engine · chatbot · weather · advisory)
│   ├── models/         (9 SQLAlchemy ORM models)
│   ├── models_store/   (29 trained ML model files)
│   ├── schemas/        (4 Pydantic schema modules)
│   ├── db/             (session · base)
│   ├── config/         (settings.py)
│   └── plugins/        (ai/ · meta/)
├── mlops/
│   ├── train_lstm.py
│   ├── train_xgboost.py
│   ├── train_stage_xgb.py
│   ├── train_anomaly.py
│   └── dataset_generator.py
├── aquasol_app/                    # Flutter app
│   └── lib/
│       ├── main.dart
│       ├── app/router.dart
│       ├── core/services/          (api_service · pairing_service · language_provider)
│       ├── core/theme/
│       ├── shared/widgets/
│       └── features/               (14 feature modules)
│           ├── auth/ · home/ · farm/ · control/
│           ├── alerts/ · analytics/ · chatbot/ · diary/
│           ├── health/ · planner/ · predictions/
│           ├── settings/ · setup/ · stage/
├── master_firmware/master_firmware.ino
├── node1_firmware/node1_firmware.ino
└── node2_firmware/node2_firmware.ino
```
