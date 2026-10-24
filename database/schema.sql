-- Generated from SQLAlchemy models (backend/models/models.py). SQLite dialect.
PRAGMA foreign_keys=ON;

CREATE TABLE audit_logs (
	log_id INTEGER NOT NULL, 
	user_id INTEGER, 
	action VARCHAR(80) NOT NULL, 
	entity VARCHAR(60) NOT NULL, 
	entity_id VARCHAR(60), 
	timestamp DATETIME NOT NULL, 
	details TEXT, 
	PRIMARY KEY (log_id)
);
CREATE INDEX ix_audit_logs_action ON audit_logs (action);
CREATE INDEX ix_audit_logs_user_id ON audit_logs (user_id);
CREATE INDEX ix_audit_logs_timestamp ON audit_logs (timestamp);

CREATE TABLE disease_knowledge (
	disease_id INTEGER NOT NULL, 
	disease_name VARCHAR(50) NOT NULL, 
	category VARCHAR(50) NOT NULL, 
	description TEXT NOT NULL, 
	reference_symptoms TEXT NOT NULL, 
	general_care TEXT NOT NULL, 
	referral_guidance TEXT NOT NULL, 
	PRIMARY KEY (disease_id), 
	UNIQUE (disease_name)
);

CREATE TABLE users (
	user_id INTEGER NOT NULL, 
	full_name VARCHAR(120) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	contact_number VARCHAR(30), 
	location VARCHAR(255), 
	license_number VARCHAR(100), 
	password_hash VARCHAR(255) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (user_id)
);
CREATE INDEX ix_users_role ON users (role);
CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE medication_reference (
	medication_id INTEGER NOT NULL, 
	disease_class VARCHAR(50) NOT NULL, 
	medicine_name VARCHAR(150) NOT NULL, 
	category VARCHAR(100) NOT NULL, 
	usage_notes TEXT NOT NULL, 
	PRIMARY KEY (medication_id), 
	FOREIGN KEY(disease_class) REFERENCES disease_knowledge (disease_name)
);
CREATE INDEX ix_medication_reference_disease_class ON medication_reference (disease_class);

CREATE TABLE poultry (
	poultry_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	poultry_type VARCHAR(50) NOT NULL, 
	breed VARCHAR(100), 
	age INTEGER, 
	flock_size INTEGER NOT NULL, 
	production_type VARCHAR(50), 
	health_history TEXT, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (poultry_id), 
	FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE
);
CREATE INDEX ix_poultry_user_id ON poultry (user_id);

CREATE TABLE uploaded_images (
	image_id INTEGER NOT NULL, 
	stored_filename VARCHAR(100) NOT NULL, 
	original_extension VARCHAR(10) NOT NULL, 
	size_bytes INTEGER NOT NULL, 
	width INTEGER NOT NULL, 
	height INTEGER NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	uploaded_by INTEGER NOT NULL, 
	uploaded_at DATETIME NOT NULL, 
	PRIMARY KEY (image_id), 
	UNIQUE (stored_filename), 
	FOREIGN KEY(uploaded_by) REFERENCES users (user_id)
);
CREATE INDEX ix_uploaded_images_sha256 ON uploaded_images (sha256);

CREATE TABLE prediction_history (
	prediction_id INTEGER NOT NULL, 
	poultry_id INTEGER NOT NULL, 
	image_id INTEGER, 
	image_filename VARCHAR(100) NOT NULL, 
	predicted_class VARCHAR(50) NOT NULL, 
	confidence FLOAT NOT NULL, 
	healthy_prob FLOAT NOT NULL, 
	coccidiosis_prob FLOAT NOT NULL, 
	newcastle_prob FLOAT NOT NULL, 
	salmonella_prob FLOAT NOT NULL, 
	low_confidence BOOLEAN NOT NULL, 
	symptoms TEXT, 
	farmer_observations TEXT, 
	status VARCHAR(50) NOT NULL, 
	assigned_vet_id INTEGER, 
	model_version VARCHAR(100), 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (prediction_id), 
	FOREIGN KEY(poultry_id) REFERENCES poultry (poultry_id) ON DELETE CASCADE, 
	FOREIGN KEY(image_id) REFERENCES uploaded_images (image_id), 
	FOREIGN KEY(assigned_vet_id) REFERENCES users (user_id)
);
CREATE INDEX ix_prediction_history_poultry_id ON prediction_history (poultry_id);
CREATE INDEX ix_prediction_history_predicted_class ON prediction_history (predicted_class);
CREATE INDEX ix_prediction_history_status ON prediction_history (status);
CREATE INDEX ix_prediction_history_created_at ON prediction_history (created_at);
CREATE INDEX ix_prediction_history_assigned_vet_id ON prediction_history (assigned_vet_id);

CREATE TABLE consultations (
	consultation_id INTEGER NOT NULL, 
	prediction_id INTEGER NOT NULL, 
	sender_id INTEGER NOT NULL, 
	message TEXT NOT NULL, 
	is_request BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (consultation_id), 
	FOREIGN KEY(prediction_id) REFERENCES prediction_history (prediction_id) ON DELETE CASCADE, 
	FOREIGN KEY(sender_id) REFERENCES users (user_id)
);
CREATE INDEX ix_consultations_prediction_id ON consultations (prediction_id);

CREATE TABLE notifications (
	notification_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	message TEXT NOT NULL, 
	prediction_id INTEGER, 
	is_read BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (notification_id), 
	FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE, 
	FOREIGN KEY(prediction_id) REFERENCES prediction_history (prediction_id) ON DELETE SET NULL
);
CREATE INDEX ix_notifications_user_id ON notifications (user_id);

CREATE TABLE reports (
	report_id INTEGER NOT NULL, 
	prediction_id INTEGER NOT NULL, 
	report_type VARCHAR(20) NOT NULL, 
	content_json TEXT NOT NULL, 
	created_by INTEGER, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (report_id), 
	FOREIGN KEY(prediction_id) REFERENCES prediction_history (prediction_id) ON DELETE CASCADE, 
	FOREIGN KEY(created_by) REFERENCES users (user_id)
);
CREATE INDEX ix_reports_pred_type ON reports (prediction_id, report_type);
CREATE INDEX ix_reports_prediction_id ON reports (prediction_id);

CREATE TABLE veterinary_review (
	review_id INTEGER NOT NULL, 
	prediction_id INTEGER NOT NULL, 
	vet_id INTEGER NOT NULL, 
	diagnosis VARCHAR(200) NOT NULL, 
	diagnosis_action VARCHAR(20) NOT NULL, 
	clinical_assessment TEXT, 
	treatment_plan TEXT, 
	prescription VARCHAR(255), 
	dosage VARCHAR(255), 
	frequency VARCHAR(255), 
	duration VARCHAR(255), 
	additional_instructions TEXT, 
	follow_up_date DATETIME, 
	license_info VARCHAR(100), 
	veterinary_comments TEXT, 
	reviewed_at DATETIME NOT NULL, 
	PRIMARY KEY (review_id), 
	UNIQUE (prediction_id), 
	FOREIGN KEY(prediction_id) REFERENCES prediction_history (prediction_id) ON DELETE CASCADE, 
	FOREIGN KEY(vet_id) REFERENCES users (user_id)
);
CREATE INDEX ix_veterinary_review_vet_id ON veterinary_review (vet_id);
