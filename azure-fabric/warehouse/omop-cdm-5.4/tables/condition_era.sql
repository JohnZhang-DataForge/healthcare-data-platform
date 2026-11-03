CREATE TABLE cdm.condition_era (
			condition_era_id int NOT NULL,
			person_id int NOT NULL,
			condition_concept_id int NOT NULL,
			condition_era_start_date date NOT NULL,
			condition_era_end_date date NOT NULL,
			condition_occurrence_count int NULL );
