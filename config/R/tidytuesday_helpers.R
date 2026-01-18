# tidytuesday_helpers.R
# =====================
# TidyTuesday / MakeoverMonday visualization helpers
# Author: chokotto
# 
# Usage in .qmd:
#   source(here::here("config", "R", "tidytuesday_helpers.R"))
#   p + tt_caption(source = "Personal Trading Data")

# ============================================================================
# Configuration
# ============================================================================

.tt_config <- list(

  # Author info
  author = "chokotto",
  

  # Social links
  social = list(
    x = "@Chokotto_Quant",
    github = "Chiquitos-JP"
  ),
  
  # Font settings
  fonts = list(
    title = "Roboto",
    body = "Roboto",
    jp = "Noto Sans JP"
  ),
  
  # Colors
  colors = list(
    title = "#1e293b",
    subtitle = "#64748b",
    caption = "#94a3b8",
    profit = "#22c55e",
    loss = "#ef4444",
    neutral = "#64748b"
  )
)

# ============================================================================
# Font Setup
# ============================================================================

tt_setup_fonts <- function() {
  if (requireNamespace("showtext", quietly = TRUE)) {
    showtext::showtext_auto(enable = TRUE)
    try(showtext::font_add_google("Roboto", "Roboto"), silent = TRUE)
    try(showtext::font_add_google("Noto Sans JP", "Noto Sans JP"), silent = TRUE)
  }
}

# ============================================================================
# Caption / Credit Functions
# ============================================================================

#' Create TidyTuesday Caption
#' 
#' @param source Data source description
#' @param year Year for copyright (default: current year)
#' @param show_author Show author name (default: TRUE)
#' @param show_social Show social links (default: TRUE)
#' @param show_tt_link Show TidyTuesday hashtag (default: TRUE)
#' @return Character string for ggplot caption
#' 
#' @examples
#' p + labs(caption = tt_caption(source = "Personal Trading Data"))
tt_caption <- function(
    source = NULL,
    year = format(Sys.Date(), "%Y"),
    show_author = TRUE,
    show_social = TRUE,
    show_tt_link = TRUE
) {
  parts <- c()
  
  # Source
  if (!is.null(source) && nzchar(source)) {
    parts <- c(parts, paste0("Source: ", source))
  }
  
  # TidyTuesday link
  if (show_tt_link) {
    parts <- c(parts, "#TidyTuesday")
  }
  
  # Author
  if (show_author) {
    parts <- c(parts, paste0("Author: ", .tt_config$author))
  }
  
  # Social
  if (show_social) {
    social_parts <- c()
    if (!is.null(.tt_config$social$x)) {
      social_parts <- c(social_parts, paste0("X: ", .tt_config$social$x))
    }
    if (!is.null(.tt_config$social$github)) {
      social_parts <- c(social_parts, paste0("GitHub: ", .tt_config$social$github))
    }
    if (length(social_parts) > 0) {
      parts <- c(parts, paste(social_parts, collapse = " | "))
    }
  }
  
  # Year
  if (!is.null(year)) {
    parts <- c(parts, paste0("\u00a9 ", year))
  }
  
  paste(parts, collapse = " | ")
}

#' Create MakeoverMonday Caption
#' 
#' @param source Data source description
#' @param year Year for copyright (default: current year)
#' @return Character string for plot caption
mm_caption <- function(source = NULL, year = format(Sys.Date(), "%Y")) {
  tt_caption(source = source, year = year, show_tt_link = FALSE) |>
    gsub("#TidyTuesday", "#MakeoverMonday", x = _)
}

# ============================================================================
# Theme Functions
# ============================================================================

#' TidyTuesday Base Theme
#' 
#' @param base_size Base font size
#' @param base_family Base font family
#' @return ggplot2 theme object
tt_theme <- function(base_size = 12, base_family = "Roboto") {
  ggplot2::theme_minimal(base_size = base_size, base_family = base_family) +
    ggplot2::theme(
      # Title
      plot.title = ggplot2::element_text(
        face = "bold",
        size = base_size * 1.4,
        color = .tt_config$colors$title,
        margin = ggplot2::margin(b = 8)
      ),
      plot.subtitle = ggplot2::element_text(
        size = base_size * 0.9,
        color = .tt_config$colors$subtitle,
        margin = ggplot2::margin(b = 12)
      ),
      plot.caption = ggplot2::element_text(
        size = base_size * 0.7,
        color = .tt_config$colors$caption,
        hjust = 1,
        margin = ggplot2::margin(t = 12)
      ),
      
      # Legend
      legend.position = "top",
      legend.title = ggplot2::element_text(face = "bold", size = base_size * 0.85),
      
      # Panel
      panel.grid.minor = ggplot2::element_blank(),
      panel.grid.major = ggplot2::element_line(color = "#e2e8f0", linewidth = 0.3),
      
      # Margins
      plot.margin = ggplot2::margin(20, 20, 20, 20)
    )
}

# ============================================================================
# Save Functions
# ============================================================================

#' Save TidyTuesday Plot
#' 
#' @param plot ggplot object
#' @param filename Output filename (without extension)
#' @param width Width in inches
#' @param height Height in inches
#' @param dpi Resolution
#' @param format Output format ("png", "svg", or "both")
#' @return Invisible path to saved file
tt_save <- function(
    plot,
    filename,
    width = 10,
    height = 8,
    dpi = 300,
    format = "png"
) {
  if (!requireNamespace("ggplot2", quietly = TRUE)) {
    stop("ggplot2 is required for tt_save()")
  }
  
  formats <- if (format == "both") c("png", "svg") else format
  paths <- c()
  
  for (fmt in formats) {
    path <- paste0(filename, ".", fmt)
    ggplot2::ggsave(
      filename = path,
      plot = plot,
      width = width,
      height = height,
      dpi = dpi,
      bg = "white"
    )
    paths <- c(paths, path)
    message("Saved: ", path)
  }
  
  invisible(paths)
}

# ============================================================================
# Color Scales
# ============================================================================

#' Profit/Loss Color Scale
#' 
#' @param ... Additional arguments passed to scale_fill_gradient2
#' @return ggplot2 scale object
scale_fill_pl <- function(...) {
  ggplot2::scale_fill_gradient2(
    low = .tt_config$colors$loss,
    mid = "#f8fafc",
    high = .tt_config$colors$profit,
    midpoint = 0,
    na.value = "#e2e8f0",
    ...
  )
}

#' Profit/Loss Color Scale (for color aesthetic)
scale_color_pl <- function(...) {
  ggplot2::scale_color_gradient2(
    low = .tt_config$colors$loss,
    mid = .tt_config$colors$neutral,
    high = .tt_config$colors$profit,
    midpoint = 0,
    na.value = "#e2e8f0",
    ...
  )
}

# ============================================================================
# Initialize
# ============================================================================

# Setup fonts on load
tt_setup_fonts()

message("[tidytuesday_helpers.R loaded]")
