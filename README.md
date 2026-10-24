<<<<<<< HEAD
# DEEP-LEARNING-BASED-POULTRY-DISEASE-DETECTION-USING-IMAGES
Deep learning-based system that uses image recognition and Convolutional Neural Networks (CNNs) to detect poultry diseases.  The system allows farmers to upload poultry images and receive disease predictions, confidence scores, and basic care guidance.
=======
# Deep Learning-Based Poultry Disease Detection Using Image Recognition
*AI-Assisted Poultry Health Management and Veterinary Support System*

> **The AI is an assistant. The veterinarian is the final clinical authority.**
> AI Prediction ≠ Veterinary Diagnosis · AI Care Suggestion ≠ Veterinary Prescription.

## Project Overview
An end-to-end decision-support platform: a farmer uploads a poultry image, a MobileNetV2 classifier
predicts one of four classes (Healthy, Coccidiosis, Newcastle Disease, Salmonella), the system produces an
AI decision-support report, and every case enters a **veterinary review queue** where a veterinarian
confirms/revises the diagnosis and issues treatment/prescription. The farmer is notified and sees the
professional plan. Everything is audited.

## Features
Farmer/vet/admin roles (JWT + bcrypt) · poultry records · secure image upload · MobileNetV2 inference with
probabilities and low-confidence handling · AI report · disease knowledge base · medication *reference*
(no dosages) · veterinary review, diagnosis confirm/revise, prescription (vet-only, validated) · separate AI and
veterinary reports · consultations · notifications · prediction history · audit log · admin dashboard ·
model info/evaluation view (never fabricated) · 41 automated tests.

## System Architecture
`Streamlit (frontend/) → REST/JWT → FastAPI (backend/) → {MobileNetV2 inference service, SQLite via SQLAlchemy}`.
Diagrams: [docs/architecture.md](docs/architecture.md).

## Technology Stack
Python 3.10+ · Streamlit · FastAPI · SQLAlchemy 2 + SQLite · TensorFlow/Keras (MobileNetV2) · OpenCV · NumPy ·
Pandas · scikit-learn · Matplotlib/Seaborn · PyJWT · bcrypt · pytest.

## Folder Structure
```
frontend/   Streamlit app (app.py, pages/, components/, services/, utils/)
backend/    FastAPI (main.py, api/, models/, schemas/, services/, core/, middleware/)
machine_learning/  preprocessing/ training/ evaluation/ inference/
dataset/    raw/<class>/ + generated train|validation|test
database/   schema.sql, seed_data.py, poultry.db (created at first start)
model/      poultry_mobilenetv2.h5, class_names.json, model_metadata.json (created by training)
uploads/    poultry_images/ (generated filenames only)   reports/  evaluation output
tests/  docs/  requirements.txt  .env.example  run.sh
```

## Installation (Ubuntu / Linux)
Ubuntu uses an *externally managed* system Python, so always use a virtual environment:
```bash
sudo apt install -y python3-venv python3-pip
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Environment Setup
```bash
./scripts/setup_env.sh your-email@example.com   # creates .env with a random SECRET_KEY + admin password
python -c "import secrets; print(secrets.token_hex(32))"   # paste into SECRET_KEY in .env
# also change ADMIN_EMAIL / ADMIN_PASSWORD (the first administrator is created from these)
```
Never commit `.env`. The backend refuses to start without `SECRET_KEY`.

## Dataset Setup
Put images in (JPG/PNG):
```
dataset/raw/Healthy/  dataset/raw/Coccidiosis/  dataset/raw/Newcastle_Disease/  dataset/raw/Salmonella/
```
Use only legally obtained data (public datasets such as Kaggle/Roboflow – check each licence – or your own
farm/lab images) and **record the source of every dataset** in `docs/dataset_sources.md`. Do not use synthetic
images as clinical evidence. Check/clean/split (70/15/15, seed 42, stratified, duplicate-free):
```bash
python -m machine_learning.preprocessing.preprocess --split            # add --remove-bad to delete unreadable/duplicates
```
Validation reports unreadable, tiny, blurry (flagged for manual review) and duplicate images and class balance.
Please also visually verify labels – automated checks cannot detect mislabelled images.

## Model Training
```bash
python -m machine_learning.training.train --epochs 15 --fine-tune-epochs 10
```
Stage 1 trains the new head on a frozen MobileNetV2 (ImageNet weights); stage 2 optionally fine-tunes the top 30
layers at lr 1e-5. Augmentation (flip, ±5° rotation, zoom, shift, mild brightness) is applied to **training data only**.
EarlyStopping, ModelCheckpoint, ReduceLROnPlateau are used. Outputs: `model/poultry_mobilenetv2.h5`,
`model/class_names.json`, `model/model_metadata.json` (real sizes, epochs, validation accuracy).
Class order is fixed in `backend/core/config.py` (`CLASS_NAMES`), never alphabetical-by-accident.

## Model Evaluation
```bash
python -m machine_learning.evaluation.evaluate
```
Evaluates on the isolated 15 % test split: accuracy, per-class/macro/weighted precision, recall, F1, 4×4 confusion
matrix → `reports/evaluation_results.json`, `reports/confusion_matrix.png`. Until you run it the admin dashboard shows
*"Model evaluation results are not yet available."* No numbers are hard-coded anywhere.

## Database Setup
Automatic on first backend start (tables + disease knowledge + medication references + first admin).
Manual: `python database/seed_data.py`. Schema: `database/schema.sql`.

## Running
```bash
# terminal 1
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
# terminal 2
streamlit run frontend/app.py            # http://127.0.0.1:8501
# or both:  ./run.sh all
```
Without a trained model the app runs, but predictions return *"The AI model has not been trained or installed yet"*
(HTTP 503) – it never fakes a prediction.

## API Documentation
Swagger UI `http://127.0.0.1:8000/docs` · ReDoc `/redoc` · summary in [docs/api.md](docs/api.md).

## User Roles
Farmer · Veterinarian (registers with a licence number) · Administrator (created from `.env`, can create other
admins). See `docs/user_manual_*.md`.

## Testing
```bash
pytest -q
```
Covers auth, role access, DB constraints, model/preprocessing/class mapping, upload security, privacy between
users, the complete acceptance workflow, dataset splitting and frontend smoke tests. Workflow tests use a clearly
labelled *stub predictor*; the real model test auto-skips until `model/poultry_mobilenetv2.h5` exists.

## Troubleshooting
| Problem | Fix |
|---|---|
| `SECRET_KEY is not set` | create `.env` (see Environment Setup) |
| "Cannot reach the server" in UI | start the backend; check `API_BASE_URL` |
| 503 model unavailable | train the model or place the three model files in `model/` |
| `externally-managed-environment` | use the virtualenv, not system pip |
| TensorFlow install slow/fails | needs Python 3.10–3.12; try `tensorflow-cpu` |
| No images to train | fill `dataset/raw/<class>/` |

## Limitations
Image classification ≠ laboratory diagnosis; overlapping visible signs; image quality and dataset bias affect results;
farm conditions differ from training data; confidence ≠ clinical certainty; only four classes; SQLite is single-node;
no login rate-limiting/email verification yet; vets self-register (licence number is stored, not independently
verified – the admin can deactivate accounts).

## Ethical Considerations
Human-in-the-loop by design; transparent limitations shown in the UI; privacy by access control (users see only their
records); antibiotics are never suggested by name/dose by the AI; audit trail; dataset provenance documented.

## Future Improvements
More diseases, Grad-CAM, object detection/lesion localisation, Android app, offline/edge inference, SMS/WhatsApp,
multilingual UI, lab-result integration, outbreak surveillance, PostgreSQL/cloud deployment.
>>>>>>> 456dbf0 (PoultryDx AI: poultry disease detection system)
