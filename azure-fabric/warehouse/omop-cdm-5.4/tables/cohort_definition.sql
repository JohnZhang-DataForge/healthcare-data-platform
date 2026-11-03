CREATE TABLE cdm.cohort_definition (
			cohort_definition_id int NOT NULL,
			cohort_definition_name varchar(255) NOT NULL,
			cohort_definition_description varchar(MAX) NULL,
			definition_type_concept_id int NOT NULL,
			cohort_definition_syntax varchar(MAX) NULL,
			subject_concept_id int NOT NULL,
			cohort_initiation_date date NULL );
