# Database (SQLite, SQLAlchemy ORM)
Foreign keys are enforced (`PRAGMA foreign_keys=ON`). DDL: `database/schema.sql`.

| Table | Purpose / key columns |
|---|---|
| users | user_id PK, full_name, role (farmer/veterinarian/admin), email UNIQUE, contact_number, location, license_number, password_hash (bcrypt), is_active, created/updated |
| poultry | poultry_id PK, user_id FK, poultry_type, breed, age, flock_size, production_type, health_history |
| uploaded_images | stored (generated) filename, size, width, height, sha256, uploaded_by |
| **prediction_history** | prediction_id PK, poultry_id FK, image_id FK, image_filename, predicted_class, confidence, healthy_prob, coccidiosis_prob, newcastle_prob, salmonella_prob, low_confidence, symptoms, farmer_observations, **status**, assigned_vet_id, model_version, created_at. `case_id = CASE-<id>` |
| veterinary_review | review_id PK, prediction_id FK **UNIQUE** (0..1 per case), vet_id FK, diagnosis, diagnosis_action, clinical_assessment, treatment_plan, prescription, dosage, frequency, duration, additional_instructions, follow_up_date, license_info, veterinary_comments, reviewed_at |
| disease_knowledge | disease_name UNIQUE, category, description, reference_symptoms, general_care, referral_guidance |
| medication_reference | disease_class FK→disease_knowledge, medicine_name, category, usage_notes (general info, no dosing) |
| consultations | prediction_id FK, sender_id FK, message, is_request |
| reports | prediction_id FK, report_type (ai/veterinary), content_json |
| notifications | user_id FK, title, message, prediction_id, is_read |
| audit_logs | user_id, action, entity, entity_id, timestamp, details |

Relationships: users 1─M poultry 1─M prediction_history 1─0..1 veterinary_review M─1 users(vet); disease_knowledge 1─M medication_reference.
Case statuses: Pending Review · Under Review · Diagnosis Confirmed · Diagnosis Revised · Treatment Issued · Follow-up Required · Completed · Rejected / Insufficient Information.
Poultry with diagnosis history cannot be deleted (clinical record protection).
