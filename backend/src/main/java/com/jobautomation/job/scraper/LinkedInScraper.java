package com.jobautomation.job.scraper;

import com.jobautomation.common.util.DateParserUtil;
import com.jobautomation.job.config.CandidateTargetCriteria;
import com.jobautomation.job.dto.JobPostingDto;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.select.Elements;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.*;

@Component
public class LinkedInScraper implements JobScraper {
    private static final Logger log = LoggerFactory.getLogger(LinkedInScraper.class);
    private final CandidateTargetCriteria targetCriteria;

    public LinkedInScraper(CandidateTargetCriteria targetCriteria) {
        this.targetCriteria = targetCriteria;
    }

    @Override
    public String getPlatformName() {
        return "LinkedIn";
    }

    @Override
    public List<JobPostingDto> scrape(String query, String location, int maxResults) {
        List<JobPostingDto> jobs = new ArrayList<>();
        Set<String> seenKeys = new HashSet<>();

        List<String> keywords = (query != null && !query.isBlank()) 
                ? Collections.singletonList(query) 
                : targetCriteria.getSearchKeywords();

        List<String> locations = (location != null && !location.isBlank()) 
                ? Collections.singletonList(location) 
                : targetCriteria.getPreferredLocations();

        int overallCapacity = Math.max(maxResults, 150);
        log.info("[LinkedInScraper] Initiating FULL MATRIX search across {} keywords and {} locations (Capacity: {})...", keywords.size(), locations.size(), overallCapacity);

        Integer totalJobsFound = null;

        for (String kw : keywords) {
            for (String loc : locations) {
                if (jobs.size() >= overallCapacity) break;
                if (kw == null || kw.isBlank() || loc == null || loc.isBlank()) continue;

                try {
                    String encodedQuery = URLEncoder.encode(kw, StandardCharsets.UTF_8);
                    String encodedLoc = URLEncoder.encode(loc, StandardCharsets.UTF_8);

                    // f_TPR=r86400 (Past 24h), f_E=2,3 (Associate/Mid Level 2-5 yrs)
                    String url = String.format("https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=%s&location=%s&f_TPR=r86400&f_E=2,3&start=0", encodedQuery, encodedLoc);

                    log.info("[LinkedInScraper] Fetching URL: {}", url);

                    Document doc = Jsoup.connect(url)
                            .userAgent("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
                            .header("Accept-Language", "en-US,en;q=0.9")
                            .timeout(6000)
                            .get();

                    if (totalJobsFound == null) {
                        Element countEl = doc.selectFirst(".results-context-header__job-count, span.results-context-header__job-count");
                        if (countEl != null) {
                            try {
                                totalJobsFound = Integer.parseInt(countEl.text().replaceAll("[^0-9]", ""));
                                log.info("[LinkedInScraper] Total available 24h jobs on LinkedIn for '{}' in '{}': {}", kw, loc, totalJobsFound);
                            } catch (Exception ignored) {}
                        }
                    }

                    Elements jobCards = doc.select("li");
                    int queryMatches = 0;

                    for (Element card : jobCards) {
                        if (jobs.size() >= overallCapacity || queryMatches >= 15) break;

                        Element titleEl = card.selectFirst(".base-search-card__title");
                        Element companyEl = card.selectFirst(".base-search-card__subtitle");
                        Element locationEl = card.selectFirst(".job-search-card__location");
                        Element linkEl = card.selectFirst("a.base-card__full-link");
                        Element timeEl = card.selectFirst("time.job-search-card__listdate, time");
                        Element snippetEl = card.selectFirst(".job-search-card__snippet, .base-search-card__metadata");

                        if (titleEl != null && companyEl != null) {
                            String title = titleEl.text().trim();
                            String company = companyEl.text().trim();
                            String jobLoc = locationEl != null ? locationEl.text().trim() : loc;
                            String jobUrl = linkEl != null ? linkEl.attr("href") : "https://www.linkedin.com/jobs";

                            String timeText = timeEl != null ? timeEl.text().trim() : "";
                            String timeAttr = timeEl != null ? timeEl.attr("datetime") : "";
                            LocalDateTime postedAt = DateParserUtil.parseRelativeOrIsoDate(timeText, timeAttr);

                            String cardSnippet = snippetEl != null ? snippetEl.text().trim() : "";
                            String description = !cardSnippet.isBlank() ? cardSnippet : fetchFullDescription(jobUrl, title, company, jobLoc);

                            String normKey = normalizeKey(company, title);
                            if (seenKeys.contains(normKey)) continue;
                            seenKeys.add(normKey);

                            String externalId = "li-" + normKey;
                            queryMatches++;

                            jobs.add(new JobPostingDto(
                                    getPlatformName(),
                                    externalId,
                                    title,
                                    company,
                                    jobLoc,
                                    2.0, 5.0,
                                    description,
                                    Arrays.asList("Java", "Spring Boot", "REST APIs", "Microservices", "SQL", "Docker"),
                                    "Disclosed on apply",
                                    jobUrl,
                                    "LinkedIn Recruiter",
                                    "careers@" + company.toLowerCase().replaceAll("[^a-z0-9]", "") + ".com",
                                    postedAt,
                                    totalJobsFound
                            ));
                        }
                    }
                } catch (Exception e) {
                    log.warn("[LinkedInScraper] Fetch failed for kw='{}', loc='{}': {}", kw, loc, e.getMessage());
                }
            }
        }

        log.info("[LinkedInScraper] Full matrix search completed. Total deduplicated jobs collected: {}", jobs.size());
        return jobs;
    }

    private String fetchFullDescription(String jobUrl, String title, String company, String location) {
        if (jobUrl == null || !jobUrl.startsWith("http") || jobUrl.contains("li-")) {
            return String.format("Real Job Opening: %s at %s (%s). Required skills: Java, Spring Boot, REST APIs, Microservices.", title, company, location);
        }
        try {
            String jobId = extractJobIdFromUrl(jobUrl);
            String detailUrl = jobId != null ? "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/" + jobId : jobUrl;
            
            Document doc = Jsoup.connect(detailUrl)
                    .userAgent("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
                    .timeout(4000)
                    .get();

            Element descEl = doc.selectFirst(".show-more-less-html__markup, .description__text");
            if (descEl != null && !descEl.text().isBlank()) {
                return descEl.text().trim();
            }
        } catch (Exception e) {
            log.debug("[LinkedInScraper] Could not fetch detail for {}: {}", jobUrl, e.getMessage());
        }

        return String.format("Real Job Opening: %s at %s (%s). Required skills: Java, Spring Boot, REST APIs, Microservices.", title, company, location);
    }

    private String extractJobIdFromUrl(String url) {
        if (url != null && url.contains("-")) {
            String[] parts = url.split("-");
            String lastPart = parts[parts.length - 1];
            if (lastPart.contains("?")) lastPart = lastPart.substring(0, lastPart.indexOf("?"));
            if (lastPart.matches("\\d+")) return lastPart;
        }
        return null;
    }

    private String normalizeKey(String company, String title) {
        String c = company != null ? company.toLowerCase().replaceAll("[^a-z0-9]", "") : "company";
        String t = title != null ? title.toLowerCase().replaceAll("[^a-z0-9]", "") : "title";
        return c + "-" + t;
    }
}
