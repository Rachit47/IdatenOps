-- IdatenOps: MVP schema for MySQL 8.0.16+
-- Scope: one retailer, modular monolith, internal follow-up tasks and test-drive bookings.
-- Synthetic demo data only. Run against a fresh database; this is not an in-place migration.
-- Keep business eligibility in the application service. Keep referential integrity,
-- simple value bounds, idempotency, and resource-conflict protection in MySQL.

CREATE DATABASE IF NOT EXISTS IdatenOps
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE IdatenOps;

CREATE TABLE retail_locations (
  location_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  location_code VARCHAR(24) NOT NULL,
  location_name VARCHAR(160) NOT NULL,
  city VARCHAR(100) NOT NULL,
  state VARCHAR(100) NOT NULL,
  timezone VARCHAR(64) NOT NULL DEFAULT 'Asia/Kolkata',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (location_id),
  UNIQUE KEY uq_location_code (location_code),
  KEY ix_location_city_active (city, is_active)
) ENGINE=InnoDB;

CREATE TABLE team_members (
  team_member_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  location_id BIGINT UNSIGNED NOT NULL,
  staff_code VARCHAR(24) NOT NULL,
  display_name VARCHAR(120) NOT NULL,
  job_title VARCHAR(80) NOT NULL DEFAULT 'sales_executive',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  is_test_drive_eligible BOOLEAN NOT NULL DEFAULT FALSE,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (team_member_id),
  UNIQUE KEY uq_staff_code (staff_code),
  KEY ix_member_location_active (location_id, is_active),
  CONSTRAINT fk_member_location FOREIGN KEY (location_id)
    REFERENCES retail_locations(location_id) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE vehicle_models (
  vehicle_model_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  make VARCHAR(80) NOT NULL,
  model_name VARCHAR(100) NOT NULL,
  variant VARCHAR(120) NOT NULL DEFAULT '',
  model_year SMALLINT UNSIGNED NULL,
  fuel_type VARCHAR(24) NULL,
  transmission VARCHAR(24) NULL,
  body_type VARCHAR(32) NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (vehicle_model_id),
  KEY ix_model_search (make, model_name)
) ENGINE=InnoDB;

CREATE TABLE vehicle_listings (
  listing_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  stock_number VARCHAR(32) NOT NULL,
  location_id BIGINT UNSIGNED NOT NULL,
  vehicle_model_id BIGINT UNSIGNED NOT NULL,
  registration_year SMALLINT UNSIGNED NOT NULL,
  odometer_km INT UNSIGNED NOT NULL DEFAULT 0,
  asking_price DECIMAL(12,2) NOT NULL,
  condition_grade VARCHAR(24) NOT NULL DEFAULT 'needs_review',
  inspection_status VARCHAR(24) NOT NULL DEFAULT 'not_started',
  listing_status VARCHAR(24) NOT NULL DEFAULT 'available',
  acquired_at DATE NULL,
  listed_at DATE NULL,
  sold_at DATETIME(3) NULL,
  data_origin VARCHAR(32) NOT NULL DEFAULT 'synthetic_scenario',
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (listing_id),
  UNIQUE KEY uq_stock_number (stock_number),
  KEY ix_listing_queue (location_id, listing_status, inspection_status),
  KEY ix_listing_model_status (vehicle_model_id, listing_status),
  CONSTRAINT fk_listing_location FOREIGN KEY (location_id)
    REFERENCES retail_locations(location_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_listing_model FOREIGN KEY (vehicle_model_id)
    REFERENCES vehicle_models(vehicle_model_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT chk_listing_price CHECK (asking_price > 0),
  CONSTRAINT chk_listing_status CHECK (listing_status IN ('available','reserved','sold','withdrawn')),
  CONSTRAINT chk_inspection_status CHECK (inspection_status IN ('not_started','in_progress','passed','needs_review','failed'))
) ENGINE=InnoDB;

CREATE TABLE prospects (
  prospect_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  prospect_code VARCHAR(32) NOT NULL,
  display_name VARCHAR(120) NOT NULL,
  city VARCHAR(100) NOT NULL,
  preferred_contact_channel VARCHAR(24) NOT NULL DEFAULT 'unknown',
  contact_permission VARCHAR(24) NOT NULL DEFAULT 'unknown',
  budget_min DECIMAL(12,2) NULL,
  budget_max DECIMAL(12,2) NULL,
  preferred_make VARCHAR(80) NULL,
  preferred_model VARCHAR(100) NULL,
  preferred_body_type VARCHAR(32) NULL,
  preferred_fuel_type VARCHAR(24) NULL,
  preferred_transmission VARCHAR(24) NULL,
  purchase_timeframe VARCHAR(32) NOT NULL DEFAULT 'unknown',
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (prospect_id),
  UNIQUE KEY uq_prospect_code (prospect_code),
  KEY ix_prospect_city (city),
  KEY ix_prospect_permission (contact_permission),
  CONSTRAINT chk_prospect_budget CHECK (
    (budget_min IS NULL OR budget_min >= 0) AND
    (budget_max IS NULL OR budget_max >= 0) AND
    (budget_min IS NULL OR budget_max IS NULL OR budget_max >= budget_min)
  ),
  CONSTRAINT chk_contact_permission CHECK (contact_permission IN ('permitted','unknown','do_not_contact'))
) ENGINE=InnoDB;

CREATE TABLE sales_leads (
  lead_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  lead_code VARCHAR(32) NOT NULL,
  prospect_id BIGINT UNSIGNED NOT NULL,
  location_id BIGINT UNSIGNED NOT NULL,
  assigned_team_member_id BIGINT UNSIGNED NULL,
  primary_listing_id BIGINT UNSIGNED NULL,
  lead_source VARCHAR(32) NOT NULL,
  stage VARCHAR(32) NOT NULL DEFAULT 'new',
  requested_budget_min DECIMAL(12,2) NULL,
  requested_budget_max DECIMAL(12,2) NULL,
  requested_make VARCHAR(80) NULL,
  requested_model VARCHAR(100) NULL,
  requested_body_type VARCHAR(32) NULL,
  requested_fuel_type VARCHAR(24) NULL,
  requested_transmission VARCHAR(24) NULL,
  purchase_timeframe VARCHAR(32) NOT NULL DEFAULT 'unknown',
  next_follow_up_at DATETIME(3) NULL,
  last_contact_at DATETIME(3) NULL,
  closed_at DATETIME(3) NULL,
  closed_reason VARCHAR(300) NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (lead_id),
  UNIQUE KEY uq_lead_code (lead_code),
  KEY ix_lead_recovery_queue (stage, next_follow_up_at, location_id),
  KEY ix_lead_assignee (assigned_team_member_id, stage, next_follow_up_at),
  KEY ix_lead_prospect (prospect_id, created_at),
  CONSTRAINT fk_lead_prospect FOREIGN KEY (prospect_id)
    REFERENCES prospects(prospect_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_lead_location FOREIGN KEY (location_id)
    REFERENCES retail_locations(location_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_lead_assignee FOREIGN KEY (assigned_team_member_id)
    REFERENCES team_members(team_member_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_lead_listing FOREIGN KEY (primary_listing_id)
    REFERENCES vehicle_listings(listing_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT chk_lead_budget CHECK (
    (requested_budget_min IS NULL OR requested_budget_min >= 0) AND
    (requested_budget_max IS NULL OR requested_budget_max >= 0) AND
    (requested_budget_min IS NULL OR requested_budget_max IS NULL OR requested_budget_max >= requested_budget_min)
  ),
  CONSTRAINT chk_lead_stage CHECK (stage IN ('new','attempted_contact','contacted','qualified','test_drive_requested','negotiation','won','lost','invalid'))
) ENGINE=InnoDB;

CREATE TABLE lead_activities (
  lead_activity_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  lead_id BIGINT UNSIGNED NOT NULL,
  recorded_by_team_member_id BIGINT UNSIGNED NULL,
  activity_type VARCHAR(48) NOT NULL,
  direction VARCHAR(16) NOT NULL DEFAULT 'internal',
  channel VARCHAR(24) NOT NULL DEFAULT 'unknown',
  outcome VARCHAR(32) NOT NULL DEFAULT 'not_applicable',
  summary_text VARCHAR(1000) NOT NULL,
  unstructured_note TEXT NULL,
  occurred_at DATETIME(3) NOT NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  data_origin VARCHAR(32) NOT NULL DEFAULT 'synthetic_scenario',
  PRIMARY KEY (lead_activity_id),
  KEY ix_activity_timeline (lead_id, occurred_at, lead_activity_id),
  KEY ix_activity_type_time (activity_type, occurred_at),
  CONSTRAINT fk_activity_lead FOREIGN KEY (lead_id)
    REFERENCES sales_leads(lead_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_activity_staff FOREIGN KEY (recorded_by_team_member_id)
    REFERENCES team_members(team_member_id) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE policy_documents (
  policy_document_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  document_code VARCHAR(100) NOT NULL,
  title VARCHAR(200) NOT NULL,
  version_label VARCHAR(40) NOT NULL,
  source_path VARCHAR(500) NOT NULL,
  content_sha256 CHAR(64) NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'draft',
  effective_from DATE NULL,
  effective_to DATE NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (policy_document_id),
  UNIQUE KEY uq_policy_version (document_code, version_label),
  KEY ix_policy_status_dates (status, effective_from, effective_to),
  CONSTRAINT chk_policy_dates CHECK (effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from)
) ENGINE=InnoDB;

CREATE TABLE policy_chunks (
  policy_chunk_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  policy_document_id BIGINT UNSIGNED NOT NULL,
  chunk_index INT UNSIGNED NOT NULL,
  section_title VARCHAR(240) NULL,
  chunk_text MEDIUMTEXT NOT NULL,
  vector_record_id VARCHAR(120) NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (policy_chunk_id),
  UNIQUE KEY uq_policy_chunk_index (policy_document_id, chunk_index),
  UNIQUE KEY uq_vector_record_id (vector_record_id),
  CONSTRAINT fk_chunk_policy FOREIGN KEY (policy_document_id)
    REFERENCES policy_documents(policy_document_id) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE agent_runs (
  agent_run_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  run_uuid CHAR(36) NOT NULL,
  run_type VARCHAR(40) NOT NULL,
  run_status VARCHAR(24) NOT NULL DEFAULT 'queued',
  initiated_by VARCHAR(100) NOT NULL DEFAULT 'local_operator',
  model_provider VARCHAR(80) NULL,
  model_name VARCHAR(120) NULL,
  candidate_count INT UNSIGNED NOT NULL DEFAULT 0,
  proposal_count INT UNSIGNED NOT NULL DEFAULT 0,
  prompt_tokens INT UNSIGNED NULL,
  completion_tokens INT UNSIGNED NULL,
  estimated_cost_usd DECIMAL(12,8) NULL,
  duration_ms INT UNSIGNED NULL,
  result_summary JSON NULL,
  error_code VARCHAR(80) NULL,
  error_summary VARCHAR(500) NULL,
  started_at DATETIME(3) NULL,
  completed_at DATETIME(3) NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (agent_run_id),
  UNIQUE KEY uq_agent_run_uuid (run_uuid),
  KEY ix_agent_run_status_time (run_status, created_at),
  CONSTRAINT chk_run_cost CHECK (estimated_cost_usd IS NULL OR estimated_cost_usd >= 0),
  CONSTRAINT chk_run_timing CHECK (completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at)
) ENGINE=InnoDB;

CREATE TABLE agent_run_events (
  agent_run_event_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  agent_run_id BIGINT UNSIGNED NOT NULL,
  event_sequence INT UNSIGNED NOT NULL,
  event_type VARCHAR(32) NOT NULL,
  component_name VARCHAR(120) NOT NULL,
  event_status VARCHAR(24) NOT NULL,
  input_summary JSON NULL,
  output_summary JSON NULL,
  duration_ms INT UNSIGNED NULL,
  prompt_tokens INT UNSIGNED NULL,
  completion_tokens INT UNSIGNED NULL,
  error_code VARCHAR(80) NULL,
  error_summary VARCHAR(500) NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (agent_run_event_id),
  UNIQUE KEY uq_run_event_sequence (agent_run_id, event_sequence),
  KEY ix_event_type_time (event_type, created_at),
  CONSTRAINT fk_run_event_run FOREIGN KEY (agent_run_id)
    REFERENCES agent_runs(agent_run_id) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE test_drive_slots (
  test_drive_slot_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  slot_code VARCHAR(40) NOT NULL,
  location_id BIGINT UNSIGNED NOT NULL,
  starts_at_utc DATETIME(3) NOT NULL,
  ends_at_utc DATETIME(3) NOT NULL,
  turnaround_buffer_minutes SMALLINT UNSIGNED NOT NULL DEFAULT 15,
  slot_status VARCHAR(16) NOT NULL DEFAULT 'open',
  closure_reason VARCHAR(300) NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (test_drive_slot_id),
  UNIQUE KEY uq_slot_code (slot_code),
  UNIQUE KEY uq_location_slot_start (location_id, starts_at_utc),
  KEY ix_slot_schedule (location_id, starts_at_utc, slot_status),
  CONSTRAINT fk_slot_location FOREIGN KEY (location_id)
    REFERENCES retail_locations(location_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT chk_slot_window CHECK (ends_at_utc > starts_at_utc),
  CONSTRAINT chk_slot_buffer CHECK (turnaround_buffer_minutes <= 120),
  CONSTRAINT chk_slot_status CHECK (slot_status IN ('open','closed'))
) ENGINE=InnoDB;

CREATE TABLE action_proposals (
  action_proposal_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  proposal_uuid CHAR(36) NOT NULL,
  agent_run_id BIGINT UNSIGNED NOT NULL,
  lead_id BIGINT UNSIGNED NOT NULL,
  action_type VARCHAR(32) NOT NULL,
  proposed_task_type VARCHAR(40) NULL,
  title VARCHAR(200) NOT NULL,
  task_instructions TEXT NULL,
  suggested_channel VARCHAR(24) NOT NULL DEFAULT 'unknown',
  draft_message TEXT NULL,
  proposed_assignee_team_member_id BIGINT UNSIGNED NULL,
  proposed_due_at DATETIME(3) NULL,
  proposed_listing_id BIGINT UNSIGNED NULL,
  proposed_salesperson_team_member_id BIGINT UNSIGNED NULL,
  proposed_test_drive_slot_id BIGINT UNSIGNED NULL,
  test_drive_intent_activity_id BIGINT UNSIGNED NULL,
  priority VARCHAR(16) NOT NULL DEFAULT 'normal',
  evidence_refs JSON NULL,
  policy_citations JSON NULL,
  proposal_status VARCHAR(16) NOT NULL DEFAULT 'pending',
  idempotency_key VARCHAR(128) NOT NULL,
  expires_at DATETIME(3) NOT NULL,
  decision_at DATETIME(3) NULL,
  decided_by VARCHAR(100) NULL,
  decision_note VARCHAR(500) NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (action_proposal_id),
  UNIQUE KEY uq_action_proposal_uuid (proposal_uuid),
  UNIQUE KEY uq_proposal_idempotency (idempotency_key),
  KEY ix_proposal_review_queue (proposal_status, priority, created_at),
  KEY ix_proposal_lead_status (lead_id, proposal_status),
  CONSTRAINT fk_proposal_run FOREIGN KEY (agent_run_id)
    REFERENCES agent_runs(agent_run_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_proposal_lead FOREIGN KEY (lead_id)
    REFERENCES sales_leads(lead_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_proposal_assignee FOREIGN KEY (proposed_assignee_team_member_id)
    REFERENCES team_members(team_member_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_proposal_listing FOREIGN KEY (proposed_listing_id)
    REFERENCES vehicle_listings(listing_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_proposal_salesperson FOREIGN KEY (proposed_salesperson_team_member_id)
    REFERENCES team_members(team_member_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_proposal_slot FOREIGN KEY (proposed_test_drive_slot_id)
    REFERENCES test_drive_slots(test_drive_slot_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_proposal_intent_activity FOREIGN KEY (test_drive_intent_activity_id)
    REFERENCES lead_activities(lead_activity_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT chk_proposal_expiry CHECK (expires_at > created_at),
  CONSTRAINT chk_proposal_decision CHECK (
    (proposal_status = 'pending' AND decision_at IS NULL AND decided_by IS NULL) OR
    (proposal_status <> 'pending' AND decision_at IS NOT NULL AND decided_by IS NOT NULL)
  ),
  CONSTRAINT chk_proposal_status CHECK (proposal_status IN ('pending','approved','rejected','expired','stale')),
  CONSTRAINT chk_proposal_action CHECK (action_type IN ('create_follow_up_task','book_test_drive'))
) ENGINE=InnoDB;



CREATE TABLE test_drive_bookings (
  test_drive_booking_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  booking_code VARCHAR(32) NOT NULL,
  location_id BIGINT UNSIGNED NOT NULL,
  lead_id BIGINT UNSIGNED NOT NULL,
  listing_id BIGINT UNSIGNED NOT NULL,
  assigned_team_member_id BIGINT UNSIGNED NOT NULL,
  test_drive_slot_id BIGINT UNSIGNED NOT NULL,
  source_proposal_id BIGINT UNSIGNED NULL,
  booking_origin VARCHAR(32) NOT NULL,
  booking_status VARCHAR(24) NOT NULL DEFAULT 'scheduled',
  customer_confirmation_status VARCHAR(24) NOT NULL DEFAULT 'not_recorded',
  checked_out_at_utc DATETIME(3) NULL,
  actual_return_at_utc DATETIME(3) NULL,
  completion_outcome VARCHAR(32) NULL,
  outcome_note VARCHAR(1000) NULL,
  completed_at_utc DATETIME(3) NULL,
  cancelled_at_utc DATETIME(3) NULL,
  cancellation_reason VARCHAR(500) NULL,
  no_show_at_utc DATETIME(3) NULL,
  idempotency_key VARCHAR(128) NOT NULL,
  active_vehicle_slot_key VARCHAR(100) GENERATED ALWAYS AS
    (CASE WHEN booking_status IN ('scheduled','checked_out') THEN CONCAT(listing_id, ':', test_drive_slot_id) ELSE NULL END) STORED,
  active_staff_slot_key VARCHAR(100) GENERATED ALWAYS AS
    (CASE WHEN booking_status IN ('scheduled','checked_out') THEN CONCAT(assigned_team_member_id, ':', test_drive_slot_id) ELSE NULL END) STORED,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (test_drive_booking_id),
  UNIQUE KEY uq_booking_code (booking_code),
  UNIQUE KEY uq_booking_source_proposal (source_proposal_id),
  UNIQUE KEY uq_booking_idempotency (idempotency_key),
  UNIQUE KEY uq_active_vehicle_slot (active_vehicle_slot_key),
  UNIQUE KEY uq_active_staff_slot (active_staff_slot_key),
  KEY ix_booking_schedule (location_id, test_drive_slot_id, booking_status),
  KEY ix_booking_lead (lead_id, created_at),
  CONSTRAINT fk_booking_location FOREIGN KEY (location_id)
    REFERENCES retail_locations(location_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_booking_lead FOREIGN KEY (lead_id)
    REFERENCES sales_leads(lead_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_booking_listing FOREIGN KEY (listing_id)
    REFERENCES vehicle_listings(listing_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_booking_staff FOREIGN KEY (assigned_team_member_id)
    REFERENCES team_members(team_member_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_booking_slot FOREIGN KEY (test_drive_slot_id)
    REFERENCES test_drive_slots(test_drive_slot_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_booking_proposal FOREIGN KEY (source_proposal_id)
    REFERENCES action_proposals(action_proposal_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT chk_booking_return CHECK (
    actual_return_at_utc IS NULL OR checked_out_at_utc IS NOT NULL
  ),
  CONSTRAINT chk_booking_return_time CHECK (
    actual_return_at_utc IS NULL OR actual_return_at_utc >= checked_out_at_utc
  ),
  CONSTRAINT chk_booking_completed CHECK (
    booking_status <> 'completed' OR (completed_at_utc IS NOT NULL AND actual_return_at_utc IS NOT NULL)
  ),
  CONSTRAINT chk_booking_cancelled CHECK (
    booking_status <> 'cancelled' OR cancelled_at_utc IS NOT NULL
  ),
  CONSTRAINT chk_booking_no_show CHECK (
    booking_status <> 'no_show' OR no_show_at_utc IS NOT NULL
  ),
  CONSTRAINT chk_booking_status CHECK (booking_status IN ('scheduled','checked_out','returned','completed','cancelled','no_show')),
  CONSTRAINT chk_booking_confirmation CHECK (customer_confirmation_status IN ('not_recorded','confirmed','declined')),
  CONSTRAINT chk_booking_origin CHECK (booking_origin IN ('operator','approved_agent_proposal'))
) ENGINE=InnoDB;

CREATE TABLE follow_up_tasks (
  follow_up_task_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  task_code VARCHAR(32) NOT NULL,
  lead_id BIGINT UNSIGNED NOT NULL,
  assigned_team_member_id BIGINT UNSIGNED NULL,
  source_proposal_id BIGINT UNSIGNED NULL,
  task_type VARCHAR(40) NOT NULL,
  channel VARCHAR(24) NOT NULL DEFAULT 'unknown',
  title VARCHAR(200) NOT NULL,
  task_instructions TEXT NOT NULL,
  draft_message TEXT NULL,
  priority VARCHAR(16) NOT NULL DEFAULT 'normal',
  task_status VARCHAR(24) NOT NULL DEFAULT 'open',
  due_at DATETIME(3) NOT NULL,
  created_origin VARCHAR(32) NOT NULL,
  idempotency_key VARCHAR(128) NULL,
  completion_note VARCHAR(1000) NULL,
  completed_at DATETIME(3) NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (follow_up_task_id),
  UNIQUE KEY uq_task_code (task_code),
  UNIQUE KEY uq_task_source_proposal (source_proposal_id),
  UNIQUE KEY uq_task_idempotency (idempotency_key),
  KEY ix_task_queue (task_status, due_at, priority),
  KEY ix_task_lead_status (lead_id, task_status, task_type),
  KEY ix_task_assignee_queue (assigned_team_member_id, task_status, due_at),
  CONSTRAINT fk_task_lead FOREIGN KEY (lead_id)
    REFERENCES sales_leads(lead_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_task_assignee FOREIGN KEY (assigned_team_member_id)
    REFERENCES team_members(team_member_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_task_proposal FOREIGN KEY (source_proposal_id)
    REFERENCES action_proposals(action_proposal_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT chk_task_completion CHECK (
    (task_status = 'completed' AND completed_at IS NOT NULL) OR
    (task_status <> 'completed' AND completed_at IS NULL)
  ),
  CONSTRAINT chk_task_status CHECK (task_status IN ('open','in_progress','completed','cancelled')),
  CONSTRAINT chk_task_origin CHECK (created_origin IN ('operator','approved_agent_proposal'))
) ENGINE=InnoDB;

CREATE TABLE audit_logs (
  audit_log_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  agent_run_id BIGINT UNSIGNED NULL,
  actor_type VARCHAR(16) NOT NULL,
  actor_label VARCHAR(100) NOT NULL,
  action_name VARCHAR(120) NOT NULL,
  target_type VARCHAR(80) NOT NULL,
  target_id BIGINT UNSIGNED NULL,
  action_outcome VARCHAR(16) NOT NULL,
  before_state JSON NULL,
  after_state JSON NULL,
  correlation_uuid CHAR(36) NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (audit_log_id),
  KEY ix_audit_target (target_type, target_id, created_at),
  KEY ix_audit_run (agent_run_id, created_at),
  KEY ix_audit_correlation (correlation_uuid),
  CONSTRAINT fk_audit_run FOREIGN KEY (agent_run_id)
    REFERENCES agent_runs(agent_run_id) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB;

-- Booking transaction guidance (implement in application service):
-- 1. Begin transaction.
-- 2. Lock the chosen slot, listing, and salesperson rows with SELECT ... FOR UPDATE.
-- 3. Re-read eligibility, permission, location, inspection, slot time, and conflicts.
-- 4. Insert booking and audit record; update proposal status.
-- 5. Commit only if all writes succeed; otherwise roll back.
-- The generated unique resource keys provide a final duplicate-conflict guard for
-- the same vehicle/slot and salesperson/slot. They do not detect arbitrary time-range overlap.