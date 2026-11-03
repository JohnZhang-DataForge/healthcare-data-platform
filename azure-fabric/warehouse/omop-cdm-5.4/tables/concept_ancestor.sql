CREATE TABLE cdm.concept_ancestor (
			ancestor_concept_id int NOT NULL,
			descendant_concept_id int NOT NULL,
			min_levels_of_separation int NOT NULL,
			max_levels_of_separation int NOT NULL );
