package com.jobautomation.job.scraper;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.jobautomation.common.util.DateParserUtil;
import com.jobautomation.job.config.CandidateTargetCriteria;
import com.jobautomation.job.dto.JobPostingDto;
import org.jsoup.Connection;
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
public class NaukriScraper implements JobScraper {
    private static final Logger log = LoggerFactory.getLogger(NaukriScraper.class);
    private final CandidateTargetCriteria targetCriteria;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public NaukriScraper(CandidateTargetCriteria targetCriteria) {
        this.targetCriteria = targetCriteria;
    }

    @Override
    public String getPlatformName() {
        return "Naukri";
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
        log.info("[NaukriScraper] Initiating FULL MATRIX search across {} keywords and {} locations (Capacity: {})...", keywords.size(), locations.size(), overallCapacity);

        for (String kw : keywords) {
            for (String loc : locations) {
                if (jobs.size() >= overallCapacity) break;
                if (kw == null || kw.isBlank() || loc == null || loc.isBlank()) continue;

                // 1. Try Naukri public JSON API first
                try {
                    String encodedKw = URLEncoder.encode(kw, StandardCharsets.UTF_8);
                    String encodedLoc = URLEncoder.encode(loc, StandardCharsets.UTF_8);
                    String apiUrl = String.format("https://www.naukri.com/jobapi/v3/search?noOfResults=20&urlType=search_by_keyword&searchType=adv&keyword=%s&location=%s&experience=2&jobAge=1", encodedKw, encodedLoc);

                    log.info("[NaukriScraper] Fetching URL (JSON API): {}", apiUrl);

                    Connection.Response response = Jsoup.connect(apiUrl)
                            .ignoreContentType(true)
                            .userAgent("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
                            .header("clientid", "idp")
                            .header("appid", "109")
                            .header("systemid", "109")
                            .header("Accept", "application/json")
                            .timeout(6000)
                            .execute();

                    if (response.statusCode() == 200 && response.body() != null && response.body().contains("jobDetails")) {
                        JsonNode root = objectMapper.readTree(response.body());
                        JsonNode jobDetails = root.path("jobDetails");

                        if (jobDetails.isArray()) {
                            int queryMatches = 0;
                            for (JsonNode node : jobDetails) {
                                if (jobs.size() >= overallCapacity || queryMatches >= 15) break;

                                String title = node.path("title").asText("");
                                String company = node.path("companyName").asText("");
                                String jobUrl = node.path("staticUrl").asText("");
                                if (jobUrl.isBlank()) jobUrl = "https://www.naukri.com" + node.path("jdURL").asText("");

                                String description = node.path("jobDescription").asText(title);
                                long createdDateMs = node.path("createdDate").asLong(0);
                                LocalDateTime postedAt = createdDateMs > 0 
                                        ? LocalDateTime.ofInstant(java.time.Instant.ofEpochMilli(createdDateMs), java.time.ZoneId.systemDefault()) 
                                        : LocalDateTime.now();

                                if (!title.isBlank() && !company.isBlank()) {
                                    String normKey = normalizeKey(company, title);
                                    if (seenKeys.contains(normKey)) continue;
                                    seenKeys.add(normKey);

                                    String externalId = "nk-" + normKey;
                                    queryMatches++;

                                    jobs.add(new JobPostingDto(
                                            getPlatformName(),
                                            externalId,
                                            title,
                                            company,
                                            loc,
                                            2.0, 5.0,
                                            description,
                                            Arrays.asList("Java", "Spring Boot", "Microservices", "REST APIs", "SQL"),
                                            "Disclosed on apply",
                                            jobUrl,
                                            "Naukri Talent Manager",
                                            "careers@" + company.toLowerCase().replaceAll("[^a-z0-9]", "") + ".com",
                                            postedAt,
                                            jobDetails.size()
                                    ));
                                }
                            }

                            if (queryMatches > 0) continue; // Successfully processed query
                        }
                    }
                } catch (Exception e) {
                    log.debug("[NaukriScraper] JSON API failed for kw='{}', loc='{}': {}", kw, loc, e.getMessage());
                }

                // 2. Fallback to HTML Web Parsing
                try {
                    String encodedQuery = URLEncoder.encode(kw, StandardCharsets.UTF_8).toLowerCase().replace("+", "-");
                    String encodedLoc = URLEncoder.encode(loc, StandardCharsets.UTF_8).toLowerCase().replace("+", "-");
                    String webUrl = String.format("https://www.naukri.com/%s-jobs-in-%s?experience=2&jobAge=1", encodedQuery, encodedLoc);

                    log.info("[NaukriScraper] Fetching URL (Web HTML): {}", webUrl);

                    Document doc = Jsoup.connect(webUrl)
                            .userAgent("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
                            .header("Accept-Language", "en-US,en;q=0.9")
                            .timeout(6000)
                            .get();

                    Elements jobCards = doc.select(".srp-jobtuple-wrapper, article.jobTuple, .cust-job-tuple");
                    int queryMatches = 0;

                    for (Element card : jobCards) {
                        if (jobs.size() >= overallCapacity || queryMatches >= 15) break;

                        Element titleEl = card.selectFirst("a.title, .title");
                        Element companyEl = card.selectFirst("a.subTitle, .comp-name");
                        Element locationEl = card.selectFirst(".loc-wrap, .location");
                        Element timeEl = card.selectFirst("span.job-post-day, .posted-date");
                        Element snippetEl = card.selectFirst(".job-desc, ul.tags-gt, .row6");

                        if (titleEl != null && companyEl != null) {
                            String title = titleEl.text().trim();
                            String company = companyEl.text().trim();
                            String jobLoc = locationEl != null ? locationEl.text().trim() : loc;
                            String jobUrl = titleEl.hasAttr("href") ? titleEl.attr("href") : "https://www.naukri.com";

                            String timeText = timeEl != null ? timeEl.text().trim() : "";
                            LocalDateTime postedAt = DateParserUtil.parseRelativeOrIsoDate(timeText, null);
                            String description = snippetEl != null ? snippetEl.text().trim() : title;

                            String normKey = normalizeKey(company, title);
                            if (seenKeys.contains(normKey)) continue;
                            seenKeys.add(normKey);

                            String externalId = "nk-" + normKey;
                            queryMatches++;

                            jobs.add(new JobPostingDto(
                                    getPlatformName(),
                                    externalId,
                                    title,
                                    company,
                                    jobLoc,
                                    2.0, 5.0,
                                    description,
                                    Arrays.asList("Java", "Spring Boot", "Microservices", "PostgreSQL", "REST APIs"),
                                    "Disclosed on apply",
                                    jobUrl,
                                    "Naukri Talent Manager",
                                    "careers@" + company.toLowerCase().replaceAll("[^a-z0-9]", "") + ".com",
                                    postedAt,
                                    null
                            ));
                        }
                    }
                } catch (Exception e) {
                    log.warn("[NaukriScraper] Web HTML fetch failed for kw='{}', loc='{}': {}", kw, loc, e.getMessage());
                }
            }
        }

        log.info("[NaukriScraper] Full matrix search completed. Total deduplicated jobs collected: {}", jobs.size());
        return jobs;
    }

    private String normalizeKey(String company, String title) {
        String c = company != null ? company.toLowerCase().replaceAll("[^a-z0-9]", "") : "company";
        String t = title != null ? title.toLowerCase().replaceAll("[^a-z0-9]", "") : "title";
        return c + "-" + t;
    }
}
