CREATE TABLE cdm.metadata (
			metadata_id int NOT NULL,
			metadata_concept_id int NOT NULL,
			metadata_type_concept_id int NOT NULL,
			name varchar(250) NOT NULL,
			value_as_string varchar(250) NULL,
			value_as_concept_id int NULL,
			value_as_number float NULL,
			metadata_date date NULL,
			metadata_datetime datetime2(6) NULL );
