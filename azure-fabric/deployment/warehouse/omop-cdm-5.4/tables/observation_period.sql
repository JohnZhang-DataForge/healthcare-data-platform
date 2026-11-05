CREATE TABLE cdm.observation_period (
			observation_period_id int NOT NULL,
			person_id int NOT NULL,
			observation_period_start_date date NOT NULL,
			observation_period_end_date date NOT NULL,
			period_type_concept_id int NOT NULL );
