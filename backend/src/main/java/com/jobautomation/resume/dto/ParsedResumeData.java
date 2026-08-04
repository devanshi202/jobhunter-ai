package com.jobautomation.resume.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record ParsedResumeData(
        String name,
        String email,
        String phone,
        @JsonProperty("current_location")
        String currentLocation,
        @JsonProperty("linkedin_url")
        String linkedinUrl,
        @JsonProperty("github_url")
        String githubUrl,
        @JsonProperty("experience_years")
        Double experienceYears,
        @JsonProperty("current_role")
        String currentRole,
        List<String> skills,
        List<Experience> experience,
        List<Project> projects,
        List<String> education,
        List<String> achievements,
        @JsonProperty("preferred_roles")
        List<String> preferredRoles,
        @JsonProperty("preferred_locations")
        List<String> preferredLocations,
        String summary
) {
    public record Experience(
            String company,
            String role,
            String duration,
            String description
    ) {}

    public record Project(
            String title,
            List<String> technologies,
            String description
    ) {}
}
