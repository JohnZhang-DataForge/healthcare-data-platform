CREATE TABLE audit.omop_commit_check (
    batch_id varchar(128) NOT NULL,
    check_name varchar(96) NOT NULL,
    expected_count bigint NOT NULL,
    observed_count bigint NOT NULL,
    check_status varchar(24) NOT NULL,
    checked_at_utc datetime2(6) NOT NULL
);
