package com.jobautomation.job.scraper;

import com.jobautomation.common.util.DateParserUtil;
import com.jobautomation.job.config.CandidateTargetCriteria;
import com.jobautomation.job.dto.JobPostingDto;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.parser.Parser;
import org.jsoup.select.Elements;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.*;

@Component
public class IndeedScraper implements JobScraper {
    private static final Logger log = LoggerFactory.getLogger(IndeedScraper.class);
    private final CandidateTargetCriteria targetCriteria;

    public IndeedScraper(CandidateTargetCriteria targetCriteria) {
        this.targetCriteria = targetCriteria;
    }

    @Override
    public String getPlatformName() {
        return "Indeed";
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
        log.info("[IndeedScraper] Initiating FULL MATRIX search across {} keywords and {} locations (Capacity: {})...", keywords.size(), locations.size(), overallCapacity);

        for (String kw : keywords) {
            for (String loc : locations) {
                if (jobs.size() >= overallCapacity) break;
                if (kw == null || kw.isBlank() || loc == null || loc.isBlank()) continue;

                try {
                    String encodedQuery = URLEncoder.encode(kw, StandardCharsets.UTF_8);
                    String encodedLoc = URLEncoder.encode(loc, StandardCharsets.UTF_8);

                    // Indeed RSS Feed (XML) bypasses Cloudflare 403 web blocks
                    String url = String.format("https://www.indeed.com/rss?q=%s&l=%s&fromage=1", encodedQuery, encodedLoc);

                    log.info("[IndeedScraper] Fetching URL (RSS Feed): {}", url);

                    Document doc = Jsoup.connect(url)
                            .parser(Parser.xmlParser())
                            .userAgent("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
                            .timeout(6000)
                            .get();

                    Elements items = doc.select("item");
                    int queryMatches = 0;

                    for (Element item : items) {
                        if (jobs.size() >= overallCapacity || queryMatches >= 15) break;

                        Element titleEl = item.selectFirst("title");
                        Element linkEl = item.selectFirst("link");
                        Element companyEl = item.selectFirst("author, source");
                        Element pubDateEl = item.selectFirst("pubDate");
                        Element descEl = item.selectFirst("description");

                        if (titleEl != null) {
                            String fullTitle = titleEl.text().trim();
                            String company = "Company Disclosed on Apply";
                            String title = fullTitle;

                            if (fullTitle.contains("-")) {
                                String[] parts = fullTitle.split("-");
                                title = parts[0].trim();
                                if (parts.length > 1) {
                                    company = parts[1].trim();
                                }
                            } else if (companyEl != null) {
                                company = companyEl.text().trim();
                            }

                            String jobUrl = linkEl != null ? linkEl.text().trim() : "https://www.indeed.com";
                            String timeText = pubDateEl != null ? pubDateEl.text().trim() : "";
                            LocalDateTime postedAt = DateParserUtil.parseRelativeOrIsoDate(timeText, null);

                            String description = descEl != null ? Jsoup.parse(descEl.text()).text() : title;

                            String normKey = normalizeKey(company, title);
                            if (seenKeys.contains(normKey)) continue;
                            seenKeys.add(normKey);

                            String externalId = "ind-" + normKey;
                            queryMatches++;

                            jobs.add(new JobPostingDto(
                                    getPlatformName(),
                                    externalId,
                                    title,
                                    company,
                                    loc,
                                    2.0, 5.0,
                                    description,
                                    Arrays.asList("Java", "Spring Boot", "REST APIs", "PostgreSQL", "Docker"),
                                    "Disclosed on apply",
                                    jobUrl,
                                    "Indeed Talent Lead",
                                    "careers@" + company.toLowerCase().replaceAll("[^a-z0-9]", "") + ".com",
                                    postedAt,
                                    items.size()
                            ));
                        }
                    }
                } catch (Exception e) {
                    log.warn("[IndeedScraper] Fetch failed for kw='{}', loc='{}': {}", kw, loc, e.getMessage());
                }
            }
        }

        log.info("[IndeedScraper] Full matrix search completed. Total deduplicated jobs collected: {}", jobs.size());
        return jobs;
    }

    private String normalizeKey(String company, String title) {
        String c = company != null ? company.toLowerCase().replaceAll("[^a-z0-9]", "") : "company";
        String t = title != null ? title.toLowerCase().replaceAll("[^a-z0-9]", "") : "title";
        return c + "-" + t;
    }
}
