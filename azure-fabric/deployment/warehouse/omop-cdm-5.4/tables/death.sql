CREATE TABLE cdm.death (
			person_id int NOT NULL,
			death_date date NOT NULL,
			death_datetime datetime2(6) NULL,
			death_type_concept_id int NULL,
			cause_concept_id int NULL,
			cause_source_value varchar(50) NULL,
			cause_source_concept_id int NULL );
