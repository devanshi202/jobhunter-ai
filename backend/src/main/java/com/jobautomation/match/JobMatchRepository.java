package com.jobautomation.match;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface JobMatchRepository extends JpaRepository<JobMatch, UUID> {

    Optional<JobMatch> findByResumeIdAndJobId(UUID resumeId, UUID jobId);

    List<JobMatch> findByResumeIdAndJobIdIn(UUID resumeId, List<UUID> jobIds);

    List<JobMatch> findByJobIdIn(List<UUID> jobIds);

    Optional<JobMatch> findByJobIdAndResumeIdIsNull(UUID jobId);
}
