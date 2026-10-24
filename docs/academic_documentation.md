# Academic documentation – B.Eng. final-year project
**Title:** Deep Learning-Based Poultry Disease Detection Using Image Recognition
**Period:** 09 September 2026 – 30 November 2026 (12 weeks)

| Weeks | Activity |
|---|---|
| W1–W2 | Literature survey & problem definition |
| W3–W4 | Dataset collection & selection |
| W5 | Preprocessing, augmentation & data splitting |
| W6–W7 | MobileNetV2 training & validation |
| W8 | Performance evaluation & tuning |
| W9–W10 | Application development & integration |
| W11–W12 | Final testing, documentation & report |

## Chapter 1 – Introduction
**Background.** Poultry diseases cause mortality and production loss; many smallholders have limited access to veterinarians.
**Problem.** Visual recognition is subjective and late; existing research mostly stops at image classification.
**Aim.** Develop a lightweight, accurate, user-friendly image-recognition system that supports early identification of Healthy, Coccidiosis, Newcastle Disease and Salmonella and connects farmers with veterinarians.
**Objectives.** (1) assemble/validate a four-class dataset; (2) train MobileNetV2 by transfer learning; (3) evaluate with accuracy/precision/recall/F1/confusion matrix; (4) build a FastAPI + Streamlit + SQLite system; (5) implement a veterinary human-in-the-loop workflow; (6) test the system.
**Research questions.** How accurately can MobileNetV2 classify the four classes? Can a decision-support workflow keep AI output clearly separate from professional diagnosis? Is the system usable by non-technical farmers?
**Significance.** Early triage, faster veterinary response, structured case history. **Scope.** four classes, image input, web application. **Limitations.** see README §Limitations.

## Chapter 2 – Literature review (outline – verify every citation before inclusion)
Topics: poultry disease detection; computer vision; deep learning and CNNs; transfer learning; MobileNetV2 (inverted residuals, linear bottlenecks, depthwise separable convolutions → lightweight); existing poultry-disease systems.
Works to review (confirm bibliographic details from the original sources yourself): Machuve; Suthagar; Degu & Simegn; Islam; Nahari; Mustopa; Cuan; Sharma.
**Research gap:** prior work focuses on *image classification*; few present a **complete AI-assisted poultry health management platform with a veterinary human-in-the-loop workflow** (history, knowledge base, review, professional treatment, audit).

## Chapter 3 – Methodology
Research: design-science / experimental. Development: incremental, staged (analysis → scaffold → DB → auth → AI → API → report → vet workflow → UI → integration → testing → documentation). Dataset: see `docs/dataset_sources.md`; validation (format, readability, duplicates, class balance, blur, manual label check); 70/15/15 stratified split with seed 42; augmentation on training only; input 224×224×3; model = MobileNetV2 (ImageNet) → GAP → Dropout → Dense(4, softmax); Adam, sparse categorical cross-entropy, EarlyStopping/ModelCheckpoint/ReduceLROnPlateau; optional fine-tuning; evaluation on isolated test set. Architecture and DB: `docs/architecture.md`, `docs/database.md`.

## Chapter 4 – System design and implementation
Architecture, DFD, use cases, ER and input design: `docs/architecture.md` (diagrams mirror the code). Implementation map:
| Concern | Location |
|---|---|
| Frontend | `frontend/` (role-based navigation, 14 pages) |
| Backend / REST | `backend/api/*` |
| AI | `machine_learning/*` |
| Vet workflow | `backend/api/veterinary.py`, `frontend/pages/veterinary_review.py` |
| Security | bcrypt, JWT, RBAC (`deps.py`), file validation (`image_service.py`), audit (`audit.py`) |

## Chapter 5 – Testing, results and discussion
*System testing:* `pytest -q` (41 tests: auth, RBAC, DB constraints, preprocessing, class mapping, upload security, privacy, full acceptance workflow, dataset split, UI smoke).
*Model results:* **to be inserted from `reports/evaluation_results.json` after training on the real dataset** (accuracy, per-class/macro/weighted precision-recall-F1, 4×4 confusion matrix `reports/confusion_matrix.png`). No results are reported here because none were fabricated.
*User testing:* run sessions with farmers and a veterinarian; record task success, errors, SUS score.
*Discussion:* compare with literature, discuss confusable classes (e.g. Salmonella vs Newcastle), dataset bias, field generalisation, low-confidence handling.

## Chapter 6 – Conclusion and recommendations
Summarise achieved objectives (integrated decision-support platform, not just a CNN). Recommend larger field datasets, Grad-CAM, lab integration, mobile/offline use, multilingual UI, vet verification of licences.
