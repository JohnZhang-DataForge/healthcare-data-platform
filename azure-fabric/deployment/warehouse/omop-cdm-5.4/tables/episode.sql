CREATE TABLE cdm.episode (
			episode_id int NOT NULL,
			person_id int NOT NULL,
			episode_concept_id int NOT NULL,
			episode_start_date date NOT NULL,
			episode_start_datetime datetime2(6) NULL,
			episode_end_date date NULL,
			episode_end_datetime datetime2(6) NULL,
			episode_parent_id int NULL,
			episode_number int NULL,
			episode_object_concept_id int NOT NULL,
			episode_type_concept_id int NOT NULL,
			episode_source_value varchar(50) NULL,
			episode_source_concept_id int NULL );
