CREATE TABLE cdm.drug_strength (
			drug_concept_id int NOT NULL,
			ingredient_concept_id int NOT NULL,
			amount_value float NULL,
			amount_unit_concept_id int NULL,
			numerator_value float NULL,
			numerator_unit_concept_id int NULL,
			denominator_value float NULL,
			denominator_unit_concept_id int NULL,
			box_size int NULL,
			valid_start_date date NOT NULL,
			valid_end_date date NOT NULL,
			invalid_reason varchar(1) NULL );
