CREATE TABLE audit.vocabulary_source_file (
    vocabulary_release_key varchar(128) NOT NULL,
    blob_file_name varchar(128) NOT NULL,
    sha256_hex varchar(64) NOT NULL,
    source_bytes bigint NOT NULL,
    source_rows bigint NOT NULL,
    verified_at_utc datetime2(6) NOT NULL
);
