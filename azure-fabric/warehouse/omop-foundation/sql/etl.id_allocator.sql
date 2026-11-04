CREATE TABLE etl.id_allocator (
    entity_type varchar(32) NOT NULL,
    next_omop_id int NOT NULL,
    mapping_version varchar(32) NOT NULL,
    updated_at_utc datetime2(6) NOT NULL
);
