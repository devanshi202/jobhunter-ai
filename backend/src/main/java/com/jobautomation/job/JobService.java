package com.jobautomation.job;

import com.jobautomation.job.config.CandidateTargetCriteria;
import com.jobautomation.job.dto.JobPostingDto;
import com.jobautomation.job.scraper.JobScraper;
import com.jobautomation.resume.ResumeProfile;
import com.jobautomation.resume.ResumeRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.*;

@Service
public class JobService {
    private static final Logger log = LoggerFactory.getLogger(JobService.class);

    private final JobPostingRepository jobPostingRepository;
    private final ResumeRepository resumeRepository;
    private final CandidateTargetCriteria targetCriteria;
    private final Map<String, JobScraper> scraperMap = new HashMap<>();

    public JobService(JobPostingRepository jobPostingRepository, 
                      ResumeRepository resumeRepository, 
                      CandidateTargetCriteria targetCriteria,
                      List<JobScraper> scrapers) {
        this.jobPostingRepository = jobPostingRepository;
        this.resumeRepository = resumeRepository;
        this.targetCriteria = targetCriteria;
        for (JobScraper scraper : scrapers) {
            this.scraperMap.put(scraper.getPlatformName().toLowerCase(), scraper);
        }
    }

    @Transactional
    public List<JobPosting> scrapeAndSaveJobs(String keyword, String location, String platform, Integer hoursRecent) {
        log.info("[JobService] Initiating multi-query job search: keyword='{}', location='{}', platform='{}', hours='{}'", keyword, location, platform, hoursRecent);

        List<JobScraper> targetScrapers = new ArrayList<>();
        if (platform != null && !platform.isBlank() && !platform.equalsIgnoreCase("ALL")) {
            JobScraper scraper = scraperMap.get(platform.toLowerCase());
            if (scraper != null) {
                targetScrapers.add(scraper);
            } else {
                log.warn("[JobService] Scraper for platform '{}' not found, running all scrapers.", platform);
                targetScrapers.addAll(scraperMap.values());
            }
        } else {
            targetScrapers.addAll(scraperMap.values());
        }

        int scrapedCount = 0;
        int newSavedCount = 0;

        for (JobScraper scraper : targetScrapers) {
            try {
                // Request up to 150 capacity to collect full multi-query matrix coverage across all keywords
                List<JobPostingDto> scrapedDtos = scraper.scrape(keyword, location, 150);
                scrapedCount += scrapedDtos.size();

                for (JobPostingDto dto : scrapedDtos) {
                    String normKey = normalizeDeduplicationKey(dto.companyName(), dto.title());
                    String externalId = dto.externalId() != null ? dto.externalId() : (dto.platform().toLowerCase() + "-" + normKey);

                    if (!jobPostingRepository.existsByPlatformAndExternalId(dto.platform(), externalId)) {
                        JobPosting job = JobPosting.builder()
                                .platform(dto.platform())
                                .externalId(externalId)
                                .title(dto.title())
                                .companyName(dto.companyName())
                                .location(dto.location())
                                .experienceMin(dto.experienceMin() != null ? dto.experienceMin() : targetCriteria.getMinExperience())
                                .experienceMax(dto.experienceMax() != null ? dto.experienceMax() : targetCriteria.getMaxExperience())
                                .description(dto.description())
                                .skills(dto.skills() != null ? dto.skills().toArray(new String[0]) : targetCriteria.getCoreSkills().toArray(new String[0]))
                                .salaryRange(dto.salaryRange())
                                .jobUrl(dto.jobUrl())
                                .recruiterName(dto.recruiterName())
                                .recruiterEmail(dto.recruiterEmail())
                                .postedAt(dto.postedAt() != null ? dto.postedAt() : LocalDateTime.now())
                                .status("ACTIVE")
                                .isActive(true)
                                .build();

                        jobPostingRepository.save(job);
                        newSavedCount++;
                    }
                }
            } catch (Exception e) {
                log.error("[JobService] Error running scraper {}: {}", scraper.getPlatformName(), e.getMessage(), e);
            }
        }

        int totalChecked = scrapedCount;
        int duplicateCount = scrapedCount - newSavedCount;

        log.info("=========================================================================");
        log.info("📊 [JOB SCRAPE SUMMARY REPORT]");
        log.info("   Total Jobs Checked Across Platforms : {}", totalChecked);
        log.info("   Duplicate Postings Skipped          : {}", duplicateCount);
        log.info("   New Unique Jobs Saved to PostgreSQL : {}", newSavedCount);
        log.info("=========================================================================");

        return searchJobs(keyword, location, platform, hoursRecent != null ? hoursRecent : 24);
    }

    private String normalizeDeduplicationKey(String company, String title) {
        String c = company != null ? company.toLowerCase().replaceAll("[^a-z0-9]", "") : "company";
        String t = title != null ? title.toLowerCase().replaceAll("[^a-z0-9]", "") : "title";
        return c + "-" + t;
    }

    @Transactional(readOnly = true)
    public List<JobPosting> searchJobs(String keyword, String location, String platform, Integer hoursRecent) {
        LocalDateTime since = (hoursRecent != null && hoursRecent > 0) ? LocalDateTime.now().minusHours(hoursRecent) : null;
        String searchKeyword = (keyword != null && !keyword.isBlank()) ? keyword.trim() : null;
        String searchLocation = (location != null && !location.isBlank()) ? location.trim() : null;
        String searchPlatform = (platform != null && !platform.isBlank() && !platform.equalsIgnoreCase("ALL")) ? platform.trim() : null;

        try {
            return jobPostingRepository.searchJobs(searchKeyword, searchLocation, searchPlatform, since);
        } catch (Exception e) {
            log.warn("[JobService] JPQL search query encountered exception ({}), falling back to in-memory derived query filtering.", e.getMessage());
            List<JobPosting> allJobs = (since != null) 
                    ? jobPostingRepository.findByPostedAtAfterAndIsActiveTrueOrderByPostedAtDesc(since) 
                    : jobPostingRepository.findByIsActiveTrueOrderByPostedAtDesc();

            return allJobs.stream()
                    .filter(j -> searchPlatform == null || j.getPlatform().equalsIgnoreCase(searchPlatform))
                    .filter(j -> searchLocation == null || (j.getLocation() != null && j.getLocation().toLowerCase().contains(searchLocation.toLowerCase())))
                    .filter(j -> searchKeyword == null || 
                            (j.getTitle() != null && j.getTitle().toLowerCase().contains(searchKeyword.toLowerCase())) ||
                            (j.getCompanyName() != null && j.getCompanyName().toLowerCase().contains(searchKeyword.toLowerCase())) ||
                            (j.getDescription() != null && j.getDescription().toLowerCase().contains(searchKeyword.toLowerCase())))
                    .toList();
        }
    }

    @Transactional
    public List<JobPosting> scrapeForResume(UUID resumeId, Integer hoursRecent) {
        ResumeProfile resume = resumeRepository.findById(resumeId)
                .orElseThrow(() -> new IllegalArgumentException("Resume not found with ID: " + resumeId));

        String primaryRole = targetCriteria.getTargetRoles().get(0); // "Java Backend Developer"
        if (resume.getPreferredRoles() != null && resume.getPreferredRoles().length > 0) {
            primaryRole = resume.getPreferredRoles()[0];
        }

        String location = targetCriteria.getPreferredLocations().get(0); // "Gurugram"
        if (resume.getPreferredLocations() != null && resume.getPreferredLocations().length > 0) {
            location = resume.getPreferredLocations()[0];
        }

        return scrapeAndSaveJobs(primaryRole, location, "ALL", hoursRecent != null ? hoursRecent : 24);
    }

    @Transactional(readOnly = true)
    public List<JobPosting> getAllActiveJobs() {
        return jobPostingRepository.findByIsActiveTrueOrderByPostedAtDesc();
    }

    @Transactional(readOnly = true)
    public Optional<JobPosting> getJobById(UUID id) {
        return jobPostingRepository.findById(id);
    }

    // ---- CSV browse drill-down: search_location > search_term > platform > jobs ----

    @Transactional(readOnly = true)
    public List<Map<String, Object>> browseLocations() {
        return jobPostingRepository.countBySearchLocation();
    }

    @Transactional(readOnly = true)
    public List<Map<String, Object>> browseTerms(String searchLocation) {
        if ("Remote".equals(searchLocation)) {
            return jobPostingRepository.countBySearchTermRemote();
        }
        return jobPostingRepository.countBySearchTermCity(searchLocation);
    }

    @Transactional(readOnly = true)
    public List<Map<String, Object>> browsePlatforms(String searchLocation, String searchTerm) {
        if ("Remote".equals(searchLocation)) {
            return jobPostingRepository.countByPlatformRemote(searchTerm);
        }
        return jobPostingRepository.countByPlatformCity(searchLocation, searchTerm);
    }

    @Transactional(readOnly = true)
    public List<JobPosting> browseJobs(String searchLocation, String searchTerm, String platform) {
        if ("Remote".equals(searchLocation)) {
            return jobPostingRepository.findBrowseJobsRemote(searchTerm, platform);
        }
        return jobPostingRepository.findBrowseJobsCity(searchLocation, searchTerm, platform);
    }

    @Transactional
    public List<JobPosting> scrapeWithJobSpy(String keyword, String location, Integer hoursRecent) {
        log.info("[JobService] Initiating JobSpy-powered scrape: keyword='{}', location='{}'", keyword, location);

        JobScraper jobSpyScraper = scraperMap.get("jobspy");
        if (jobSpyScraper == null) {
            log.error("[JobService] JobSpyScraper not found! Make sure ai-service is running.");
            return Collections.emptyList();
        }

        int scrapedCount = 0;
        int newSavedCount = 0;

        try {
            List<JobPostingDto> scrapedDtos = jobSpyScraper.scrape(keyword, location, 150);
            scrapedCount = scrapedDtos.size();

            for (JobPostingDto dto : scrapedDtos) {
                String normKey = normalizeDeduplicationKey(dto.companyName(), dto.title());
                String externalId = dto.externalId() != null ? dto.externalId() : (dto.platform().toLowerCase() + "-" + normKey);

                if (!jobPostingRepository.existsByPlatformAndExternalId(dto.platform(), externalId)) {
                    JobPosting job = JobPosting.builder()
                            .platform(dto.platform())
                            .externalId(externalId)
                            .title(dto.title())
                            .companyName(dto.companyName())
                            .location(dto.location())
                            .experienceMin(dto.experienceMin() != null ? dto.experienceMin() : targetCriteria.getMinExperience())
                            .experienceMax(dto.experienceMax() != null ? dto.experienceMax() : targetCriteria.getMaxExperience())
                            .description(dto.description())
                            .skills(dto.skills() != null ? dto.skills().toArray(new String[0]) : targetCriteria.getCoreSkills().toArray(new String[0]))
                            .salaryRange(dto.salaryRange())
                            .jobUrl(dto.jobUrl())
                            .recruiterName(dto.recruiterName())
                            .recruiterEmail(dto.recruiterEmail())
                            .postedAt(dto.postedAt() != null ? dto.postedAt() : LocalDateTime.now())
                            .status("ACTIVE")
                            .isActive(true)
                            .build();

                    jobPostingRepository.save(job);
                    newSavedCount++;
                }
            }
        } catch (Exception e) {
            log.error("[JobService] Error running JobSpy scraper: {}", e.getMessage(), e);
        }

        int duplicateCount = scrapedCount - newSavedCount;

        log.info("=========================================================================");
        log.info("📊 [JOBSPY SCRAPE SUMMARY REPORT]");
        log.info("   Total Jobs Checked (from Python)    : {}", scrapedCount);
        log.info("   Duplicate Postings Skipped          : {}", duplicateCount);
        log.info("   New Unique Jobs Saved to PostgreSQL : {}", newSavedCount);
        log.info("=========================================================================");

        return searchJobs(keyword, location, null, hoursRecent != null ? hoursRecent : 24 * 14);
    }
}
