package com.jobautomation.resume.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record ParsedResumeData(
        String name,
        String email,
        String phone,
        @JsonProperty("experience_years")
        Double experienceYears,
        @JsonProperty("current_role")
        String currentRole,
        List<String> skills,
        List<Experience> experience,
        List<String> education,
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
}
