CREATE TABLE cdm.provider (
			provider_id int NOT NULL,
			provider_name varchar(255) NULL,
			npi varchar(20) NULL,
			dea varchar(20) NULL,
			specialty_concept_id int NULL,
			care_site_id int NULL,
			year_of_birth int NULL,
			gender_concept_id int NULL,
			provider_source_value varchar(50) NULL,
			specialty_source_value varchar(50) NULL,
			specialty_source_concept_id int NULL,
			gender_source_value varchar(50) NULL,
			gender_source_concept_id int NULL );
