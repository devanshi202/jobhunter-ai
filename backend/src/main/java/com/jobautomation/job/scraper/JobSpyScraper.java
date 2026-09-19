package com.jobautomation.job.scraper;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.jobautomation.job.config.CandidateTargetCriteria;
import com.jobautomation.job.dto.JobPostingDto;
import okhttp3.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.TimeUnit;

/**
 * Scraper that delegates to the Python JobSpy FastAPI endpoint.
 * Calls POST /api/scrape/jobspy on the ai-service and returns parsed DTOs.
 */
@Component
public class JobSpyScraper implements JobScraper {
    private static final Logger log = LoggerFactory.getLogger(JobSpyScraper.class);
    private final CandidateTargetCriteria targetCriteria;
    private final ObjectMapper objectMapper = new ObjectMapper();

    // Allow up to 10 minutes for a full matrix scrape
    private final OkHttpClient httpClient = new OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(10, TimeUnit.MINUTES)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build();

    @Value("${app.ai-service.url:http://localhost:8000}")
    private String aiServiceUrl;

    public JobSpyScraper(CandidateTargetCriteria targetCriteria) {
        this.targetCriteria = targetCriteria;
    }

    @Override
    public String getPlatformName() {
        return "JobSpy";
    }

    @Override
    public List<JobPostingDto> scrape(String query, String location, int maxResults) {
        log.info("[JobSpyScraper] Triggering Python JobSpy scrape via {}/api/scrape/jobspy ...", aiServiceUrl);

        try {
            // Build JSON request body
            Map<String, Object> requestBody = new HashMap<>();

            if (query != null && !query.isBlank()) {
                requestBody.put("search_terms", Collections.singletonList(query));
            }
            // else: Python side uses its own SEARCH_TERMS default list

            if (location != null && !location.isBlank()) {
                requestBody.put("locations", Collections.singletonList(location + ", India"));
            }
            // else: Python side uses its own LOCATIONS default list

            requestBody.put("results_per_query", 15);
            requestBody.put("hours_old", 24 * 14); // 2 weeks
            requestBody.put("include_remote", true);

            String jsonBody = objectMapper.writeValueAsString(requestBody);
            log.info("[JobSpyScraper] Request body: {}", jsonBody);

            Request request = new Request.Builder()
                    .url(aiServiceUrl + "/api/scrape/jobspy")
                    .post(RequestBody.create(jsonBody, MediaType.parse("application/json")))
                    .build();

            try (Response response = httpClient.newCall(request).execute()) {
                if (!response.isSuccessful() || response.body() == null) {
                    log.error("[JobSpyScraper] HTTP {} from ai-service: {}", response.code(), response.message());
                    return Collections.emptyList();
                }

                String responseBody = response.body().string();
                JsonNode root = objectMapper.readTree(responseBody);
                int totalJobs = root.path("totalJobs").asInt(0);
                JsonNode jobsArray = root.path("jobs");

                log.info("[JobSpyScraper] Received {} jobs from Python JobSpy service", totalJobs);

                List<JobPostingDto> jobs = new ArrayList<>();
                if (jobsArray.isArray()) {
                    for (JsonNode node : jobsArray) {
                        try {
                            String title = node.path("title").asText("");
                            String company = node.path("companyName").asText("");
                            String platform = node.path("platform").asText("JobSpy");
                            String externalId = node.path("externalId").asText("");
                            String jobLocation = node.path("location").asText("");
                            String description = node.path("description").asText("");
                            String salaryRange = node.path("salaryRange").asText("Disclosed on apply");
                            String jobUrl = node.path("jobUrl").asText("");
                            String recruiterName = node.path("recruiterName").asText("");
                            String recruiterEmail = node.path("recruiterEmail").asText(null);

                            LocalDateTime postedAt = LocalDateTime.now();
                            String postedAtStr = node.path("postedAt").asText("");
                            if (!postedAtStr.isBlank() && !postedAtStr.equals("null")) {
                                try {
                                    postedAt = LocalDateTime.parse(postedAtStr, DateTimeFormatter.ISO_LOCAL_DATE_TIME);
                                } catch (Exception e) {
                                    try {
                                        postedAt = LocalDateTime.parse(postedAtStr.substring(0, 19), DateTimeFormatter.ISO_LOCAL_DATE_TIME);
                                    } catch (Exception ignored) {}
                                }
                            }

                            if (!title.isBlank() && !company.isBlank()) {
                                jobs.add(new JobPostingDto(
                                        platform,
                                        externalId,
                                        title,
                                        company,
                                        jobLocation,
                                        node.path("experienceMin").asDouble(2.0),
                                        node.path("experienceMax").asDouble(5.0),
                                        description,
                                        List.of("Java", "Spring Boot", "REST APIs", "Microservices", "SQL"),
                                        salaryRange,
                                        jobUrl,
                                        recruiterName,
                                        recruiterEmail,
                                        postedAt,
                                        totalJobs
                                ));
                            }
                        } catch (Exception e) {
                            log.debug("[JobSpyScraper] Failed to parse job node: {}", e.getMessage());
                        }
                    }
                }

                log.info("[JobSpyScraper] Parsed {} valid job DTOs from Python response", jobs.size());
                return jobs;
            }
        } catch (Exception e) {
            log.error("[JobSpyScraper] Failed to call Python JobSpy service: {}", e.getMessage(), e);
            return Collections.emptyList();
        }
    }
}
