package com.jobautomation.job.config;

import org.springframework.stereotype.Component;

import java.util.Arrays;
import java.util.List;

@Component
public class CandidateTargetCriteria {

    public double getExperienceYears() {
        return 2.5;
    }

    public double getMinExperience() {
        return 2.0;
    }

    public double getMaxExperience() {
        return 5.0;
    }

    public List<String> getTargetRoles() {
        return Arrays.asList(
                "Java Backend Developer",
                "Java Software Engineer",
                "Java Developer",
                "Backend Engineer",
                "Software Engineer",
                "Spring Boot Developer",
                "Java Microservices Developer",
                "Software Engineer II",
                "SDE II",
                "SDE 2",
                "Full Stack Developer Java"
        );
    }

    public List<String> getSearchKeywords() {
        return Arrays.asList(
                "Java Backend Developer",
                "Java Software Engineer",
                "Java Developer",
                "Backend Engineer",
                "Software Engineer",
                "Spring Boot Developer",
                "Java Microservices",
                "Backend Engineer Java",
                "Software Engineer Java",
                "Software Engineer Backend",
                "SDE II",
                "SDE 2",
                "Full Stack Developer Java",
                "Java OR Spring Boot OR Microservices"
        );
    }

    public List<String> getCoreSkills() {
        return Arrays.asList(
                "Java",
                "Spring Boot",
                "REST APIs",
                "SQL",
                "Hibernate",
                "JPA",
                "Spring Security",
                "Microservices"
        );
    }

    public List<String> getSecondarySkills() {
        return Arrays.asList(
                "Python",
                "PostgreSQL",
                "MySQL",
                "Docker",
                "AWS",
                "Azure",
                "Jenkins",
                "Git",
                "Maven",
                "JWT",
                "JavaScript"
        );
    }

    public List<String> getPreferredLocations() {
        return Arrays.asList(
                "Gurugram",
                "Delhi NCR",
                "Noida",
                "Delhi"
        );
    }

    public boolean isRemoteAllowed() {
        return true;
    }
}
