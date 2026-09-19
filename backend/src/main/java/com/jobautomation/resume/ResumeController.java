package com.jobautomation.resume;

import com.jobautomation.resume.dto.ParsedResumeData;
import com.jobautomation.resume.dto.ResumeUploadResponse;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Controller
public class ResumeController {

    private final ResumeService resumeService;

    public ResumeController(ResumeService resumeService) {
        this.resumeService = resumeService;
    }

    // Thymeleaf Pages
    @GetMapping("/")
    public String index(Model model) {
        model.addAttribute("resumeCount", resumeService.getAllResumes().size());
        model.addAttribute("activePage", "dashboard");
        return "index";
    }

    @GetMapping("/resume")
    public String resumePage(Model model) {
        model.addAttribute("resumes", resumeService.getAllResumes());
        model.addAttribute("activePage", "resume");
        return "resume";
    }

    // REST APIs for Frontend JS
    @PostMapping("/api/resume/upload")
    @ResponseBody
    public ResumeUploadResponse uploadResume(@RequestParam("file") MultipartFile file) throws IOException {
        return resumeService.uploadAndParse(file);
    }

    @GetMapping("/api/resume/latest")
    @ResponseBody
    public org.springframework.http.ResponseEntity<ResumeProfile> getLatestResume() {
        return resumeService.getLatestResume()
                .map(org.springframework.http.ResponseEntity::ok)
                .orElse(org.springframework.http.ResponseEntity.noContent().build());
    }

    @GetMapping("/api/resume/{id}")
    @ResponseBody
    public ResumeProfile getResume(@PathVariable UUID id) {
        return resumeService.getResumeById(id);
    }

    @GetMapping("/api/resume")
    @ResponseBody
    public List<ResumeProfile> getAllResumes() {
        return resumeService.getAllResumes();
    }

    /**
     * Step 1 highlights payload: the active (latest) resume profile plus its
     * fully-typed parsed data for rendering the profile dashboard.
     */
    @GetMapping("/api/resume/profile/current")
    @ResponseBody
    public org.springframework.http.ResponseEntity<Map<String, Object>> getCurrentProfile() {
        return resumeService.getLatestResume()
                .map(profile -> {
                    Map<String, Object> payload = new LinkedHashMap<>();
                    payload.put("id", profile.getId());
                    payload.put("fileName", profile.getFileName());
                    payload.put("experienceYears", profile.getExperienceYears());
                    payload.put("skills", profile.getSkills());
                    payload.put("preferredRoles", profile.getPreferredRoles());
                    payload.put("preferredLocations", profile.getPreferredLocations());
                    payload.put("createdAt", profile.getCreatedAt());
                    payload.put("updatedAt", profile.getUpdatedAt());
                    payload.put("parsed", resumeService.getParsedData(profile));
                    return org.springframework.http.ResponseEntity.ok(payload);
                })
                .orElse(org.springframework.http.ResponseEntity.noContent().build());
    }

    /**
     * Re-writes ai-service/resume_profile.json + resume_experience.json from the
     * active DB profile so Python scripts (match_job_v3, enhance_resume,
     * generate_emails) always read current data.
     */
    @PostMapping("/api/resume/sync-files")
    @ResponseBody
    public Map<String, Object> syncProfileFiles() {
        ResumeProfile profile = resumeService.syncActiveProfile();
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("status", "SYNCED");
        result.put("profileId", profile.getId());
        result.put("fileName", profile.getFileName());
        result.put("syncedAt", LocalDateTime.now().toString());
        return result;
    }
}
