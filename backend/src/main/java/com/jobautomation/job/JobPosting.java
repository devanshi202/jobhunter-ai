package com.jobautomation.job;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import com.fasterxml.jackson.annotation.JsonFormat;

import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "job_postings", uniqueConstraints = {
    @UniqueConstraint(columnNames = {"platform", "external_id"})
})
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class JobPosting {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "platform", nullable = false, length = 50)
    private String platform;

    @Column(name = "external_id", nullable = false)
    private String externalId;

    @Column(name = "title", nullable = false, length = 500)
    private String title;

    @Column(name = "company_name", nullable = false)
    private String companyName;

    @Column(name = "location")
    private String location;

    @Column(name = "experience_min")
    private Double experienceMin;

    @Column(name = "experience_max")
    private Double experienceMax;

    @Column(name = "description", columnDefinition = "text")
    private String description;

    @Column(name = "skills", columnDefinition = "text[]")
    @JdbcTypeCode(SqlTypes.ARRAY)
    private String[] skills;

    @Column(name = "salary_range", length = 100)
    private String salaryRange;

    @Column(name = "job_url", columnDefinition = "text")
    private String jobUrl;

    @Column(name = "job_url_direct", columnDefinition = "text")
    private String jobUrlDirect;

    @Column(name = "job_type", length = 100)
    private String jobType;

    @Column(name = "job_level", length = 100)
    private String jobLevel;

    @Column(name = "job_function", length = 500)
    private String jobFunction;

    @Column(name = "emails", columnDefinition = "text")
    private String emails;

    @Column(name = "company_industry", length = 255)
    private String companyIndustry;

    @Column(name = "company_url", columnDefinition = "text")
    private String companyUrl;

    @Column(name = "company_url_direct", columnDefinition = "text")
    private String companyUrlDirect;

    @Column(name = "company_addresses", columnDefinition = "text")
    private String companyAddresses;

    @Column(name = "company_num_employees", length = 100)
    private String companyNumEmployees;

    @Column(name = "company_revenue", length = 100)
    private String companyRevenue;

    @Column(name = "company_description", columnDefinition = "text")
    private String companyDescription;

    @Column(name = "search_term", length = 255)
    private String searchTerm;

    @Column(name = "search_location", length = 255)
    private String searchLocation;

    @Column(name = "is_remote")
    @Builder.Default
    private Boolean isRemote = false;

    @Column(name = "recruiter_name")
    private String recruiterName;

    @Column(name = "recruiter_email")
    private String recruiterEmail;

    @Column(name = "posted_at")
    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss")
    private LocalDateTime postedAt;

    @CreationTimestamp
    @Column(name = "scraped_at", updatable = false)
    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss")
    private LocalDateTime scrapedAt;

    @Column(name = "status", length = 20)
    @Builder.Default
    private String status = "ACTIVE";

    @Column(name = "is_active")
    @Builder.Default
    private Boolean isActive = true;
}
