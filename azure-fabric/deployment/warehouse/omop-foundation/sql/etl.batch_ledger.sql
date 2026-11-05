CREATE TABLE etl.batch_ledger (
    hospital_id varchar(96) NOT NULL,
    source_system varchar(96) NOT NULL,
    batch_id varchar(128) NOT NULL,
    source_manifest_sha256 varchar(64) NOT NULL,
    mapping_profile_sha256 varchar(64) NOT NULL,
    writer_version varchar(32) NOT NULL,
    batch_status varchar(24) NOT NULL,
    expected_person_count int NOT NULL,
    expected_visit_count int NOT NULL,
    committed_person_count int NULL,
    committed_visit_count int NULL,
    committed_at_utc datetime2(6) NULL
);
