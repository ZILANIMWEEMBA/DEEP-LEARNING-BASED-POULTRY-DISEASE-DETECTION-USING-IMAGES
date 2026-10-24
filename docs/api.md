# REST API summary  (interactive: `/docs`, `/redoc`)
Auth: `Authorization: Bearer <JWT>` from `POST /api/auth/login`. Errors: `{"detail": "...", "code": "..."}`.

| Method & path | Roles | Notes |
|---|---|---|
| POST /api/auth/register · /login | public | register role farmer/veterinarian only |
| GET/PUT /api/users/me | any | password change needs current password |
| POST/GET /api/poultry · GET/PUT/DELETE /api/poultry/{id} | farmer (vet read) | delete blocked if history |
| POST /api/predictions (multipart: poultry_id, file, symptoms, observations) | farmer | 400 invalid image · 413 too large · 503 model unavailable |
| GET /api/predictions · /{id} · /{id}/image · /summary/me | role-scoped | image is access-controlled |
| POST /api/reports {prediction_id, report_type} · GET /api/reports?prediction_id= · GET /{id} | owner/vet/admin | vet report only after review |
| GET /api/veterinary/cases · /stats · /cases/{id} | veterinarian | queue = unassigned + mine |
| POST /api/veterinary/cases/{id}/claim · PUT /cases/{id}/status | veterinarian | |
| POST /api/veterinary/review · PUT /api/veterinary/review/{id} | veterinarian (owner) | prescription needs dosage/frequency/duration |
| POST/GET /api/consultations | farmer, vet | |
| GET /api/medications · /api/diseases | authenticated | reference only |
| GET /api/notifications · PUT /api/notifications/{id}/read | owner | |
| GET /api/admin/users · statistics · logs · predictions · poultry · model · settings | admin | |
| POST/PUT /api/admin/users · PUT /diseases/{id} · POST/DELETE /medications · POST /notifications/broadcast | admin | |
| GET /health | public | `model_available` |
