CREATE TABLE etl.identity_map (
    entity_type varchar(32) NOT NULL,
    hospital_id varchar(96) NOT NULL,
    source_system varchar(96) NOT NULL,
    source_business_key varchar(256) NOT NULL,
    omop_id int NOT NULL,
    first_batch_id varchar(128) NOT NULL,
    mapping_version varchar(32) NOT NULL,
    created_at_utc datetime2(6) NOT NULL
);
