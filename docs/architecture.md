# Architecture (matches the implemented code)

## 1. System architecture
```mermaid
flowchart TD
  F[Farmer] & V[Veterinarian] & A[Administrator] --> UI[Streamlit frontend<br/>frontend/app.py + pages]
  UI -- "REST + JWT" --> API[FastAPI backend<br/>backend/main.py]
  API --> AUTH[Auth & RBAC<br/>api/deps.py]
  API --> IMG[Image validation/storage<br/>image_service.py]
  API --> PRED[Prediction service<br/>prediction_service.py]
  API --> REP[Report service<br/>report_service.py]
  API --> NOTIF[Notification + Audit services]
  PRED --> ML[MobileNetV2 inference<br/>machine_learning/inference/predictor.py]
  API --> DB[(SQLite via SQLAlchemy)]
  ML --> MF[model/*.h5, class_names.json, model_metadata.json]
  IMG --> FS[uploads/poultry_images<br/>generated filenames]
```

## 2. End-to-end block diagram
```mermaid
flowchart LR
  A[Farmer login] --> B[Register poultry] --> C[Upload image] --> D[Validate type/size/readability/dimensions]
  D --> E[Preprocess 224x224x3] --> F[MobileNetV2] --> G[4-class softmax]
  G --> H[Confidence + probabilities] --> I[AI report + knowledge base + care suggestion]
  I --> J[(prediction_history)] --> K[Veterinary queue]
  K --> L[Veterinarian review] --> M[Confirm / revise diagnosis] --> N[Treatment + prescription]
  N --> O[Veterinary report] --> P[Farmer notification & view]
```

## 3. Level-1 DFD
```mermaid
flowchart LR
  Farmer -- "credentials, poultry data, image, symptoms" --> P1((1 Manage accounts & poultry))
  Farmer --> P2((2 Validate image & predict))
  P2 <--> ML[MobileNetV2 model]
  P2 --> P3((3 Generate AI report))
  P3 <--> KB[(Disease knowledge / medication reference)]
  P2 & P3 --> D1[(prediction_history, reports)]
  D1 --> P4((4 Veterinary review))
  Vet[Veterinarian] <--> P4
  P4 --> D2[(veterinary_review, reports)]
  P4 --> P5((5 Notifications))
  P5 --> Farmer
  Admin[Administrator] <--> P6((6 Administration & audit))
  P6 <--> D3[(users, audit_logs, knowledge)]
  P1 --> D3
```

## 4. Use-case diagram
```mermaid
flowchart LR
  Farmer --- UC1[Register / Login / Profile] & UC2[Manage poultry] & UC3[Upload image & detect] & UC4[View AI report & care suggestion] & UC5[Request consultation] & UC6[View veterinary diagnosis & prescription] & UC7[History / Reports / Notifications]
  Vet[Veterinarian] --- V1[View case queue] & V2[Review image, poultry, AI] & V3[Confirm / revise diagnosis] & V4[Treatment & prescription] & V5[Veterinary report] & V6[Message farmer / update status]
  Admin[Administrator] --- A1[Manage users] & A2[Manage knowledge & medication refs] & A3[Model info & evaluation] & A4[Statistics, logs, broadcast]
  UC3 -. includes .-> AI[AI: preprocess, classify, probabilities, report]
```

## 5. Input design
| Screen | Field | Rules |
|---|---|---|
| Register | name, email, password, phone, location, licence (vets) | email format; password ≥ 8 with letters+digits/symbols; vets need licence |
| Poultry | type, breed, age (weeks), flock size, production, health history | flock ≥ 1, age 0–500 |
| Detect Disease | poultry, image, symptoms, observations | JPG/JPEG/PNG, ≤ 5 MB, ≥ 64 px, real image content |
| Veterinary review | diagnosis, assessment, treatment, medication, dosage, frequency, duration, instructions, follow-up, comments | prescription needs dosage+frequency+duration; "confirmed" must equal AI class |

## 6. AI report generation flowchart
```mermaid
flowchart TD
  S[Valid image] --> P[Preprocess] --> M{Model available?}
  M -- no --> E[HTTP 503 model_unavailable; nothing stored]
  M -- yes --> I[Inference → probabilities] --> C{confidence < threshold?}
  C -- yes --> L[Set low_confidence flag + warning]
  C -- no --> R
  L --> R[Look up disease knowledge] --> G[Compose AI report + care suggestion<br/>'Not a Prescription']
  G --> DB[(Save prediction + report)] --> Q[Status: Pending Veterinary Review] --> N[Notify farmer & veterinarians]
```

## 7. Medication recommendation flowchart
```mermaid
flowchart TD
  P[Predicted class] --> K{Class}
  K -- Healthy --> H[No medication indicated; hygiene, water, nutrition]
  K -- Coccidiosis --> C[Anticoccidial category may be relevant → consult vet]
  K -- Newcastle Disease --> N[Supportive care → vet to confirm; vaccination status]
  K -- Salmonella --> S[Antibiotics need vet assessment/prescription → do not self-administer]
  H & C & N & S --> T["Display 'AI Care Suggestion – Not a Prescription' (no name/dose/duration)"]
  T --> V[Veterinarian alone enters medication, dosage, frequency, duration]
```

## 8. ER diagram
```mermaid
erDiagram
  USERS ||--o{ POULTRY : owns
  POULTRY ||--o{ PREDICTION_HISTORY : has
  UPLOADED_IMAGES ||--o| PREDICTION_HISTORY : "image of"
  PREDICTION_HISTORY ||--o| VETERINARY_REVIEW : "reviewed by"
  USERS ||--o{ VETERINARY_REVIEW : "vet writes"
  PREDICTION_HISTORY ||--o{ CONSULTATIONS : has
  PREDICTION_HISTORY ||--o{ REPORTS : has
  USERS ||--o{ NOTIFICATIONS : receives
  DISEASE_KNOWLEDGE ||--o{ MEDICATION_REFERENCE : lists
  USERS ||--o{ AUDIT_LOGS : "acts in"
```
Full column definitions: `database/schema.sql`, `docs/database.md`.

## 9. Design decisions
* Single source of truth for class order (`backend/core/config.py`); folder names map to labels explicitly.
* Normalisation lives **inside** the Keras model (`Rescaling`), so training and inference cannot diverge.
* Predictor is a FastAPI dependency → swappable/testable; missing model ⇒ explicit 503, never fake output.
* AI and veterinary data live in different tables/fields/reports and different UI sections.
* Record-level access control (`get_prediction_for_user`) on every endpoint, not only role checks.
