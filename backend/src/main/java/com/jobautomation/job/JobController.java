package com.jobautomation.job;

import com.jobautomation.job.config.CandidateTargetCriteria;
import com.jobautomation.match.JobMatchService;
import com.jobautomation.resume.ResumeService;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@Controller
public class JobController {

    private final JobService jobService;
    private final ResumeService resumeService;
    private final CandidateTargetCriteria targetCriteria;
    private final CsvJobImportService csvJobImportService;
    private final JobMatchService jobMatchService;

    public JobController(JobService jobService, ResumeService resumeService, CandidateTargetCriteria targetCriteria, CsvJobImportService csvJobImportService, JobMatchService jobMatchService) {
        this.jobService = jobService;
        this.resumeService = resumeService;
        this.targetCriteria = targetCriteria;
        this.csvJobImportService = csvJobImportService;
        this.jobMatchService = jobMatchService;
    }

    // Thymeleaf Page
    @GetMapping("/jobs")
    public String jobsPage(Model model) {
        model.addAttribute("jobs", jobService.getAllActiveJobs());
        model.addAttribute("resumes", resumeService.getAllResumes());
        model.addAttribute("targetCriteria", targetCriteria);
        model.addAttribute("activePage", "jobs");
        return "jobs";
    }

    // Job-specific detail page: description + company_industry/url/addresses/employees/revenue
    @GetMapping("/jobs/{id}")
    public String jobDetailPage(@PathVariable UUID id, Model model) {
        return jobService.getJobById(id).map(job -> {
            model.addAttribute("job", job);
            model.addAttribute("activePage", "jobs");
            return "job-detail";
        }).orElse("redirect:/jobs");
    }

    // REST APIs
    @GetMapping("/api/jobs/target-criteria")
    @ResponseBody
    public CandidateTargetCriteria getTargetCriteria() {
        return targetCriteria;
    }

    @GetMapping("/api/jobs")
    @ResponseBody
    public List<JobPosting> searchJobs(
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String location,
            @RequestParam(required = false) String platform,
            @RequestParam(required = false, defaultValue = "24") Integer hoursRecent
    ) {
        return jobService.searchJobs(keyword, location, platform, hoursRecent);
    }

    @PostMapping("/api/jobs/scrape")
    @ResponseBody
    public List<JobPosting> scrapeJobs(
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String location,
            @RequestParam(required = false) String platform,
            @RequestParam(required = false, defaultValue = "24") Integer hoursRecent
    ) {
        // If keyword is null, blank, or "ALL_MATRIX", pass null to trigger full CandidateTargetCriteria multi-query matrix
        String targetKeyword = (keyword == null || keyword.isBlank() || keyword.equalsIgnoreCase("ALL_MATRIX")) ? null : keyword.trim();
        String targetLocation = (location == null || location.isBlank()) ? null : location.trim();
        return jobService.scrapeAndSaveJobs(targetKeyword, targetLocation, platform, hoursRecent);
    }

    @PostMapping("/api/jobs/scrape-by-resume/{resumeId}")
    @ResponseBody
    public List<JobPosting> scrapeByResume(
            @PathVariable UUID resumeId,
            @RequestParam(required = false, defaultValue = "24") Integer hoursRecent
    ) {
        return jobService.scrapeForResume(resumeId, hoursRecent);
    }

    @PostMapping("/api/jobs/scrape-jobspy")
    @ResponseBody
    public List<JobPosting> scrapeWithJobSpy(
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String location,
            @RequestParam(required = false, defaultValue = "24") Integer hoursRecent
    ) {
        String targetKeyword = (keyword == null || keyword.isBlank() || keyword.equalsIgnoreCase("ALL_MATRIX")) ? null : keyword.trim();
        String targetLocation = (location == null || location.isBlank()) ? null : location.trim();
        return jobService.scrapeWithJobSpy(targetKeyword, targetLocation, hoursRecent);
    }

    // ---- CSV import (dedupe by company + title) ----

    @PostMapping("/api/jobs/import-csv")
    @ResponseBody
    public java.util.Map<String, Object> importCsv(
            @RequestParam(required = false) String path
    ) {
        return csvJobImportService.importCsv(path);
    }

    // ---- Browse drill-down: search_location > search_term > platform > jobs ----

    @GetMapping("/api/jobs/browse/locations")
    @ResponseBody
    public List<java.util.Map<String, Object>> browseLocations() {
        return jobService.browseLocations();
    }

    @GetMapping("/api/jobs/browse/terms")
    @ResponseBody
    public List<java.util.Map<String, Object>> browseTerms(
            @RequestParam String searchLocation
    ) {
        return jobService.browseTerms(searchLocation);
    }

    @GetMapping("/api/jobs/browse/platforms")
    @ResponseBody
    public List<java.util.Map<String, Object>> browsePlatforms(
            @RequestParam String searchLocation,
            @RequestParam String searchTerm
    ) {
        return jobService.browsePlatforms(searchLocation, searchTerm);
    }

    @GetMapping("/api/jobs/browse/list")
    @ResponseBody
    public List<JobPosting> browseJobs(
            @RequestParam String searchLocation,
            @RequestParam String searchTerm,
            @RequestParam String platform
    ) {
        return jobService.browseJobs(searchLocation, searchTerm, platform);
    }

    @GetMapping("/api/jobs/{id}")
    @ResponseBody
    public JobPosting getJobById(@PathVariable UUID id) {
        return jobService.getJobById(id)
                .orElseThrow(() -> new IllegalArgumentException("Job not found: " + id));
    }

    // ---- Profile matching (semantic pgvector + skill + exp + domain; no location —
    // ranking happens within each location bucket in the UI) ----

    @PostMapping("/api/jobs/match")
    @ResponseBody
    public java.util.Map<String, Object> runMatching(
            @RequestParam(required = false) UUID resumeId
    ) {
        return jobMatchService.runMatching(resumeId);
    }

    @GetMapping("/api/jobs/browse/list-ranked")
    @ResponseBody
    public List<java.util.Map<String, Object>> browseJobsRanked(
            @RequestParam String searchLocation,
            @RequestParam String searchTerm,
            @RequestParam String platform,
            @RequestParam(required = false) UUID resumeId
    ) {
        return jobMatchService.rankedJobs(jobService.browseJobs(searchLocation, searchTerm, platform), resumeId);
    }
}
