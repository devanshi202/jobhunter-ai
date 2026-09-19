package com.jobautomation.job;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.*;

/**
 * Imports JobSpy-scraped CSV (ai-service/manual_pipeline/outputs/.../swe_jobs_scraped.csv)
 * into {@code job_postings}, de-duplicating records with the same company + title.
 */
@Service
public class CsvJobImportService {
    private static final Logger log = LoggerFactory.getLogger(CsvJobImportService.class);

    private final JobPostingRepository jobPostingRepository;

    @Value("${app.csv.path:}")
    private String configuredCsvPath;

    public CsvJobImportService(JobPostingRepository jobPostingRepository) {
        this.jobPostingRepository = jobPostingRepository;
    }

    @Transactional
    public Map<String, Object> importCsv(String requestedPath) {
        Path csvPath = resolvePath(requestedPath);
        if (!Files.exists(csvPath)) {
            throw new IllegalArgumentException("CSV not found: " + csvPath.toAbsolutePath());
        }

        List<Map<String, String>> rows;
        try {
            rows = parseCsv(csvPath);
        } catch (IOException e) {
            throw new IllegalStateException("Failed to read CSV: " + e.getMessage(), e);
        }

        int totalRows = rows.size();
        // In-file dedupe by normalized company + title (keep first occurrence)
        Map<String, Map<String, String>> unique = new LinkedHashMap<>();
        int inFileDupes = 0;
        for (Map<String, String> row : rows) {
            String key = dedupeKey(row.get("company"), row.get("title"));
            if (unique.containsKey(key)) {
                inFileDupes++;
            } else {
                unique.put(key, row);
            }
        }

        int alreadyInDb = 0;
        int newlySaved = 0;
        int backfilled = 0;
        for (Map<String, String> row : unique.values()) {
            String platform = mapPlatform(row.get("site"));
            String externalId = orDefault(row.get("id"), platform.toLowerCase() + "-" + dedupeKey(row.get("company"), row.get("title")));
            Boolean isRemote = parseIsRemote(row.get("is_remote"));
            var existing = jobPostingRepository.findByPlatformAndExternalId(platform, externalId);
            if (existing.isPresent()) {
                alreadyInDb++;
                // Sync portal flag from CSV (source of truth; rows imported before V3 got DEFAULT FALSE)
                if (isRemote != null && !isRemote.equals(existing.get().getIsRemote())) {
                    existing.get().setIsRemote(isRemote);
                    jobPostingRepository.save(existing.get());
                    backfilled++;
                }
                continue;
            }
            JobPosting job = toJobPosting(platform, externalId, row);
            job.setIsRemote(isRemote != null ? isRemote : false);
            jobPostingRepository.save(job);
            newlySaved++;
        }

        log.info("=========================================================================");
        log.info("📊 [CSV IMPORT SUMMARY] file={}", csvPath.toAbsolutePath());
        log.info("   Total rows in CSV                 : {}", totalRows);
        log.info("   Unique (company+title)            : {}", unique.size());
        log.info("   In-file duplicates skipped        : {}", inFileDupes);
        log.info("   Already in DB (platform+ext id)   : {}", alreadyInDb);
        log.info("   Newly saved                       : {}", newlySaved);
        log.info("=========================================================================");

        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("csvPath", csvPath.toAbsolutePath().toString());
        summary.put("totalRows", totalRows);
        summary.put("uniqueJobs", unique.size());
        summary.put("duplicatesSkipped", inFileDupes);
        summary.put("alreadyInDb", alreadyInDb);
        summary.put("newlySaved", newlySaved);
        summary.put("backfilledIsRemote", backfilled);
        summary.put("locations", jobPostingRepository.countBySearchLocation());
        return summary;
    }

    private Path resolvePath(String requestedPath) {
        if (requestedPath != null && !requestedPath.isBlank()) {
            return Paths.get(requestedPath);
        }
        if (configuredCsvPath != null && !configuredCsvPath.isBlank()) {
            return Paths.get(configuredCsvPath);
        }
        // Default: <repo>/ai-service/manual_pipeline/outputs/2026-09-17/swe_jobs_scraped.csv
        // Backend runs from <repo>/backend, so go one level up.
        return Paths.get(System.getProperty("user.dir"))
                .resolve("../ai-service/manual_pipeline/outputs/2026-09-17/swe_jobs_scraped.csv")
                .normalize();
    }

    static String dedupeKey(String company, String title) {
        return norm(company) + "|" + norm(title);
    }

    private static String norm(String s) {
        return s == null ? "" : s.toLowerCase().replaceAll("[^a-z0-9]", "");
    }

    private static String orDefault(String v, String fallback) {
        return (v == null || v.isBlank()) ? fallback : v.trim();
    }

    private static String mapPlatform(String site) {
        if (site == null) return "JobSpy";
        return switch (site.trim().toLowerCase()) {
            case "linkedin" -> "LinkedIn";
            case "indeed" -> "Indeed";
            case "naukri" -> "Naukri";
            default -> site.trim().isEmpty() ? "JobSpy" : site.trim();
        };
    }

    private JobPosting toJobPosting(String platform, String externalId, Map<String, String> row) {
        return JobPosting.builder()
                .platform(platform)
                .externalId(externalId)
                .title(orDefault(row.get("title"), "Untitled"))
                .companyName(orDefault(row.get("company"), "Unknown"))
                .location(emptyToNull(row.get("location")))
                .description(emptyToNull(row.get("description")))
                .jobUrl(emptyToNull(row.get("job_url")))
                .jobUrlDirect(emptyToNull(row.get("job_url_direct")))
                .jobType(emptyToNull(row.get("job_type")))
                .jobLevel(emptyToNull(row.get("job_level")))
                .jobFunction(emptyToNull(row.get("job_function")))
                .emails(emptyToNull(row.get("emails")))
                .companyIndustry(emptyToNull(row.get("company_industry")))
                .companyUrl(emptyToNull(row.get("company_url")))
                .companyUrlDirect(emptyToNull(row.get("company_url_direct")))
                .companyAddresses(emptyToNull(row.get("company_addresses")))
                .companyNumEmployees(emptyToNull(row.get("company_num_employees")))
                .companyRevenue(emptyToNull(row.get("company_revenue")))
                .companyDescription(emptyToNull(row.get("company_description")))
                .searchTerm(emptyToNull(row.get("search_term")))
                .searchLocation(emptyToNull(row.get("search_location")))
                .experienceMin(2.0)
                .experienceMax(5.0)
                .postedAt(parsePostedAt(row.get("date_posted")))
                .status("ACTIVE")
                .isActive(true)
                .build();
    }

    private static String emptyToNull(String v) {
        if (v == null) return null;
        String t = v.trim();
        if (t.isEmpty() || t.equalsIgnoreCase("nan") || t.equalsIgnoreCase("none")) return null;
        return t;
    }

    private static Boolean parseIsRemote(String v) {
        if (v == null) return null;
        String t = v.trim().toLowerCase();
        if (t.equals("true") || t.equals("1") || t.equals("yes")) return true;
        if (t.equals("false") || t.equals("0") || t.equals("no")) return false;
        return null;
    }

    private static LocalDateTime parsePostedAt(String v) {
        if (v != null && !v.isBlank()) {
            try {
                return LocalDate.parse(v.trim()).atStartOfDay();
            } catch (Exception ignored) {
                try {
                    return LocalDateTime.parse(v.trim().substring(0, Math.min(19, v.trim().length())));
                } catch (Exception ignored2) {}
            }
        }
        return LocalDateTime.now();
    }

    // Minimal RFC-4180 parser (handles quoted commas, escaped quotes, embedded newlines)
    private static List<Map<String, String>> parseCsv(Path path) throws IOException {
        String content = Files.readString(path, StandardCharsets.UTF_8);
        List<List<String>> records = new ArrayList<>();
        List<String> current = new ArrayList<>();
        StringBuilder field = new StringBuilder();
        boolean inQuotes = false;
        for (int i = 0; i < content.length(); i++) {
            char c = content.charAt(i);
            if (inQuotes) {
                if (c == '"') {
                    if (i + 1 < content.length() && content.charAt(i + 1) == '"') {
                        field.append('"');
                        i++;
                    } else {
                        inQuotes = false;
                    }
                } else {
                    field.append(c);
                }
            } else {
                if (c == '"') {
                    inQuotes = true;
                } else if (c == ',') {
                    current.add(field.toString());
                    field.setLength(0);
                } else if (c == '\r') {
                    // skip, handle \n
                } else if (c == '\n') {
                    current.add(field.toString());
                    field.setLength(0);
                    records.add(current);
                    current = new ArrayList<>();
                } else {
                    field.append(c);
                }
            }
        }
        if (!field.isEmpty() || !current.isEmpty()) {
            current.add(field.toString());
            records.add(current);
        }
        if (records.isEmpty()) return List.of();
        List<String> header = records.get(0);
        List<Map<String, String>> rows = new ArrayList<>();
        for (int r = 1; r < records.size(); r++) {
            List<String> rec = records.get(r);
            if (rec.size() == 1 && rec.get(0).isBlank()) continue;
            Map<String, String> row = new LinkedHashMap<>();
            for (int c = 0; c < header.size(); c++) {
                row.put(header.get(c).trim(), c < rec.size() ? rec.get(c) : "");
            }
            rows.add(row);
        }
        return rows;
    }
}
