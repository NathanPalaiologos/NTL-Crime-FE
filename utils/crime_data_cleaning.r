# utils/crime_data_cleaning.r

# Add nanoparquet to the suppressed messages
suppressPackageStartupMessages({
    library(tidyverse)
    library(nanoparquet)
})

# Clean a single offenses CSV and return long-format tibble
clean_offense_file <- function(file_path,
                                territories = c("AS", "GU", "MP", "PR", "VI"),
                                exclude_index_total = TRUE) {
    # Using readr::read_csv
    df <- readr::read_csv(file_path, show_col_types = FALSE, guess_max = 100000)

    # Implement specific cleaning pipeline
    out <- df |>
        dplyr::filter(!state_abb %in% territories) |>
        dplyr::mutate(geoid = stringr::str_c(fips_state_code, fips_place_code)) |>
        # Select identification columns and the value columns we want to pivot
        dplyr::select(
            geoid, state, state_abb, address_city, census_name, year, month, date, 
            population, population_group, core_city_indication, 
            officers_killed_by_felony:officers_assaulted, 
            dplyr::starts_with("actual_"),
            dplyr::starts_with("total_cleared_")
        ) |>
        # Pivot both actual and cleared counts simultaneously
        tidyr::pivot_longer(
            cols = c(dplyr::starts_with("actual_"), dplyr::starts_with("total_cleared_")),
            names_to = c(".value", "offense_type"),
            names_pattern = "(actual|total_cleared)_(.*)"
        ) |>
        # Rename to match output variables
        dplyr::rename(actual_count = actual, cleared_count = total_cleared) |>
        dplyr::mutate(
            crime_rate = dplyr::if_else(population > 0, actual_count / population * 100000, NA_real_),
            clear_occurrence_ratio = dplyr::if_else(!is.na(actual_count) & actual_count > 0,
                                                    cleared_count / actual_count,
                                                    NA_real_)
        ) |>
        dplyr::select(-cleared_count)

    # Handle exclude_index_total from signature
    if (exclude_index_total) {
        out <- out |> dplyr::filter(offense_type != "index_total")
    }

    out
}

# Clean multiple files and return a single combined tibble
clean_offense_files <- function(file_paths,
                                territories = c("AS", "GU", "MP", "PR", "VI"),
                                exclude_index_total = TRUE) {
    purrr::map_dfr(
        file_paths,
        ~ clean_offense_file(.x, territories = territories, exclude_index_total = exclude_index_total) |>
            dplyr::mutate(source_file = .x),
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

# New function: Save data as Parquet
save_offense_parquet <- function(data, output_path) {
    if (!grepl("\\.parquet$", output_path)) {
        output_path <- paste0(output_path, ".parquet")
    }
    nanoparquet::write_parquet(data, output_path)
    message("Saved parquet file to: ", output_path)
}
