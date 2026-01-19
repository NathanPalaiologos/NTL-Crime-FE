# utils/crime_data_cleaning.r

suppressPackageStartupMessages({
    library(tidyverse)
})

# Clean a single offenses CSV and return long-format tibble
clean_offense_file <- function(file_path,
                                                             territories = c("AS", "GU", "MP", "PR", "VI"),
                                                             exclude_index_total = TRUE) {
    df <- readr::read_csv(file_path, show_col_types = FALSE, guess_max = 100000)

    # Determine available population column
    has_pop1 <- "population_1" %in% names(df)
    has_pop  <- "population"   %in% names(df)
    df <- df |>
        mutate(
            population_std = dplyr::coalesce(
                if (has_pop) .data$population else NULL,
                if (has_pop1) .data$population_1 else NULL
            )
        )

    # Build offense columns dynamically
    offense_cols <- grep("^actual_", names(df), value = TRUE)
    if (exclude_index_total) {
        offense_cols <- setdiff(offense_cols, "actual_index_total")
    }
    if (length(offense_cols) == 0) {
        stop("No offense columns starting with 'actual_' were found in: ", file_path)
    }

    # Base columns to keep if present
    base_cols <- c(
        "state", "state_abb", "address_city", "census_name",
        "year", "month", "date", "core_city_indication",
        "population", "population_1", "population_std",
        "officers_killed_by_felony"
    )
    keep_cols <- intersect(c(base_cols, offense_cols), names(df))

    # Clean, filter, and pivot to long format
    out <- df |>
        select(all_of(keep_cols)) |>
        filter(!.data$state_abb %in% territories) |>
        filter(!is.na(.data$census_name)) |>
        pivot_longer(
            cols = all_of(offense_cols),
            names_to = "offense_type",
            values_to = "offense_count"
        ) |>
        mutate(
            offense_count = as.numeric(offense_count),
            crime_rate = ifelse(!is.na(population_std) & population_std > 0,
                                                    offense_count / population_std * 100000,
                                                    NA_real_)
        )

    out
}

# Clean multiple files and return a single combined tibble
clean_offense_files <- function(file_paths,
                                                                territories = c("AS", "GU", "MP", "PR", "VI"),
                                                                exclude_index_total = TRUE) {
    purrr::map_dfr(
        file_paths,
        ~ clean_offense_file(.x, territories = territories, exclude_index_total = exclude_index_total) |>
            mutate(source_file = .x),
        .id = "file_id"
    )
}

# Clean all CSVs in a directory (non-recursive) and return combined tibble
clean_offense_dir <- function(dir_path,
                                                            pattern = "\\.csv$",
                                                            territories = c("AS", "GU", "MP", "PR", "VI"),
                                                            exclude_index_total = TRUE) {
    files <- list.files(dir_path, pattern = pattern, full.names = TRUE)
    if (length(files) == 0) {
        stop("No files matched pattern in directory: ", dir_path)
    }
    clean_offense_files(files, territories = territories, exclude_index_total = exclude_index_total)
}