package com.jobautomation.match;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "job_matches", uniqueConstraints = {
    @UniqueConstraint(columnNames = {"resume_id", "job_id"})
})
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class JobMatch {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "resume_id")
    private UUID resumeId;

    @Column(name = "job_id", nullable = false)
    private UUID jobId;

    @Column(name = "semantic_score")
    private Double semanticScore;

    @Column(name = "skill_overlap_score")
    private Double skillOverlapScore;

    @Column(name = "experience_fit_score")
    private Double experienceFitScore;

    @Column(name = "domain_score")
    private Double domainScore;

    @Column(name = "overall_score")
    private Double overallScore;

    @Column(name = "callback_probability")
    private Double callbackProbability;

    @Column(name = "skill_overlap", columnDefinition = "text")
    private String skillOverlap;

    @Column(name = "match_reason", columnDefinition = "text")
    private String matchReason;

    @Column(name = "status", length = 50)
    @Builder.Default
    private String status = "NEW";

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}
