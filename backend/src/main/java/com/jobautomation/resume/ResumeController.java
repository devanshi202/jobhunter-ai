package com.jobautomation.resume;

import com.jobautomation.resume.dto.ResumeUploadResponse;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.List;
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
}
