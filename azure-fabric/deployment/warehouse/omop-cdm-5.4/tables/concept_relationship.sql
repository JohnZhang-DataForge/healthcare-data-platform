CREATE TABLE cdm.concept_relationship (
			concept_id_1 int NOT NULL,
			concept_id_2 int NOT NULL,
			relationship_id varchar(20) NOT NULL,
			valid_start_date date NOT NULL,
			valid_end_date date NOT NULL,
			invalid_reason varchar(1) NULL );
