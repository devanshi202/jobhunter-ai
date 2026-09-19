package com.jobautomation.job.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import java.time.LocalDateTime;
import java.util.List;

public record JobPostingDto(
        String platform,
        String externalId,
        String title,
        String companyName,
        String location,
        Double experienceMin,
        Double experienceMax,
        String description,
        List<String> skills,
        String salaryRange,
        String jobUrl,
        String recruiterName,
        String recruiterEmail,
        @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss")
        LocalDateTime postedAt,
        Integer totalJobsOnPlatform
) {
    public JobPostingDto(
            String platform, String externalId, String title, String companyName,
            String location, Double experienceMin, Double experienceMax, String description,
            List<String> skills, String salaryRange, String jobUrl, String recruiterName,
            String recruiterEmail, LocalDateTime postedAt
    ) {
        this(platform, externalId, title, companyName, location, experienceMin, experienceMax, description, skills, salaryRange, jobUrl, recruiterName, recruiterEmail, postedAt, null);
    }
}
