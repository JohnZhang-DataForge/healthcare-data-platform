#!/usr/bin/env Rscript
# OpenSpec-Change: deploy-local-ohdsi-atlas
# OpenSpec-Task: 4.0.4, 4.0.5
# Exactly official OHDSI Achilles 1.7.2 analysis IDs 200 and 201.
# NO full Achilles rerun; NO table recreation, no JSON export or CDM writes.
# Only existing atlas_results.achilles_results rows for these IDs may mutate.
suppressPackageStartupMessages(library(Achilles))
suppressPackageStartupMessages(library(DatabaseConnector))

require_env <- function(key, expected = NULL) {
  x <- Sys.getenv(key, unset = "")
  if (identical(x, "")) stop("ATLAS_REQUIRED_ACHILLES_ENV_MISSING")
  if (!is.null(expected) && !identical(x, expected)) {
    stop("ATLAS_ACHILLES_SCOPE_ENV_DRIFT")
  }
  invisible(x)
}
require_env("ACHILLES_DB_USERNAME", "atlas_webapi")
require_env("ACHILLES_DB_PASSWORD")
require_env("ACHILLES_SOURCE", "LOCAL_OMOP")
require_env("ACHILLES_CDM_SCHEMA", "cdm")
require_env("ACHILLES_VOCAB_SCHEMA", "cdm")
require_env("ACHILLES_RES_SCHEMA", "atlas_results")
require_env("ACHILLES_CDM_VERSION", "5.4")
require_env("ACHILLES_NUM_THREADS", "1")
require_env("ACHILLES_DB_URI",
            "postgresql://dw-postgre.dw-postgre.svc.cluster.local:5432/omop")

details <- DatabaseConnector::createConnectionDetails(
  dbms = "postgresql",
  server = "dw-postgre.dw-postgre.svc.cluster.local/omop",
  port = 5432,
  user = Sys.getenv("ACHILLES_DB_USERNAME"),
  password = Sys.getenv("ACHILLES_DB_PASSWORD")
)

scratch <- file.path("/opt/achilles/workspace", "visit-200-201")
dir.create(scratch, recursive = TRUE, showWarnings = FALSE)
if (!dir.exists(scratch)) stop("ATLAS_ACHILLES_WORKSPACE_MISSING")
cat("ATLAS_OFFICIAL_ACHILLES_PACKAGE_VERSION=", as.character(packageVersion("Achilles")), "\n", sep="")
if (as.character(packageVersion("Achilles")) != "1.7.2") {
  stop("ATLAS_OFFICIAL_ACHILLES_VERSION_DRIFT")
}
cat("ATLAS_ACHILLES_ANALYSIS_IDS=200,201\n")
cat("ATLAS_ACHILLES_CREATE_TABLE=FALSE\n")
cat("ATLAS_ACHILLES_UPDATE_GIVEN_ONLY=TRUE\n")
cat("ATLAS_ACHILLES_JSON_EXPORT=DISABLED\n")

Achilles::achilles(
  connectionDetails = details,
  cdmDatabaseSchema = "cdm",
  resultsDatabaseSchema = "atlas_results",
  scratchDatabaseSchema = "#",
  vocabDatabaseSchema = "cdm",
  tempEmulationSchema = "atlas_temp",
  sourceName = "LOCAL_OMOP",
  analysisIds = c(200L, 201L),
  createTable = FALSE,
  smallCellCount = 5,
  cdmVersion = "5.4",
  createIndices = FALSE,
  numThreads = 1,
  dropScratchTables = TRUE,
  sqlOnly = FALSE,
  outputFolder = scratch,
  verboseMode = FALSE,
  optimizeAtlasCache = FALSE,
  defaultAnalysesOnly = FALSE,
  updateGivenAnalysesOnly = TRUE
)
cat("ATLAS_OFFICIAL_ACHILLES_VISIT200201=COMPLETED\n")
