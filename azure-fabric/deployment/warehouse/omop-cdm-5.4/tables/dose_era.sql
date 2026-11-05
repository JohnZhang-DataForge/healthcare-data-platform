CREATE TABLE cdm.dose_era (
			dose_era_id int NOT NULL,
			person_id int NOT NULL,
			drug_concept_id int NOT NULL,
			unit_concept_id int NOT NULL,
			dose_value float NOT NULL,
			dose_era_start_date date NOT NULL,
			dose_era_end_date date NOT NULL );
