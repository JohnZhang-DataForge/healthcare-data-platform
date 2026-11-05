CREATE TABLE cdm.drug_era (
			drug_era_id int NOT NULL,
			person_id int NOT NULL,
			drug_concept_id int NOT NULL,
			drug_era_start_date date NOT NULL,
			drug_era_end_date date NOT NULL,
			drug_exposure_count int NULL,
			gap_days int NULL );
