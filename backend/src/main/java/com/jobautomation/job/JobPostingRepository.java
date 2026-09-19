package com.jobautomation.job;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface JobPostingRepository extends JpaRepository<JobPosting, UUID> {

    boolean existsByPlatformAndExternalId(String platform, String externalId);

    Optional<JobPosting> findByPlatformAndExternalId(String platform, String externalId);

    List<JobPosting> findByIsActiveTrueOrderByPostedAtDesc();

    List<JobPosting> findByPostedAtAfterAndIsActiveTrueOrderByPostedAtDesc(LocalDateTime since);

    @Query("SELECT j FROM JobPosting j WHERE j.isActive = true " +
           "AND (CAST(:platform AS string) IS NULL OR LOWER(j.platform) = LOWER(CAST(:platform AS string))) " +
           "AND (CAST(:keyword AS string) IS NULL OR LOWER(j.title) LIKE LOWER(CONCAT('%', CAST(:keyword AS string), '%')) OR LOWER(j.companyName) LIKE LOWER(CONCAT('%', CAST(:keyword AS string), '%')) OR LOWER(j.description) LIKE LOWER(CONCAT('%', CAST(:keyword AS string), '%'))) " +
           "AND (CAST(:location AS string) IS NULL OR LOWER(j.location) LIKE LOWER(CONCAT('%', CAST(:location AS string), '%'))) " +
           "AND (CAST(:since AS timestamp) IS NULL OR j.postedAt >= CAST(:since AS timestamp)) " +
           "ORDER BY j.postedAt DESC")
    List<JobPosting> searchJobs(@Param("keyword") String keyword,
                                @Param("location") String location,
                                @Param("platform") String platform,
                                @Param("since") LocalDateTime since);

    // ---- CSV browse drill-down (search_location > search_term > platform > jobs) ----
    // Remote bucket = union of search_location 'Remote' OR portal is_remote flag.
    // City buckets exclude portal-flagged remote jobs so buckets stay disjoint.

    @Query("SELECT new map(CASE WHEN j.searchLocation = 'Remote' OR COALESCE(j.isRemote, false) = true THEN 'Remote' ELSE j.searchLocation END AS name, COUNT(j) AS cnt) " +
           "FROM JobPosting j WHERE j.isActive = true AND j.searchLocation IS NOT NULL " +
           "GROUP BY CASE WHEN j.searchLocation = 'Remote' OR COALESCE(j.isRemote, false) = true THEN 'Remote' ELSE j.searchLocation END " +
           "ORDER BY COUNT(j) DESC")
    List<Map<String, Object>> countBySearchLocation();

    @Query("SELECT new map(j.searchTerm AS name, COUNT(j) AS cnt) FROM JobPosting j " +
           "WHERE j.isActive = true AND j.searchLocation = :searchLocation AND j.searchTerm IS NOT NULL " +
           "AND COALESCE(j.isRemote, false) = false " +
           "GROUP BY j.searchTerm ORDER BY COUNT(j) DESC")
    List<Map<String, Object>> countBySearchTermCity(@Param("searchLocation") String searchLocation);

    @Query("SELECT new map(j.searchTerm AS name, COUNT(j) AS cnt) FROM JobPosting j " +
           "WHERE j.isActive = true AND j.searchTerm IS NOT NULL " +
           "AND (j.searchLocation = 'Remote' OR COALESCE(j.isRemote, false) = true) " +
           "GROUP BY j.searchTerm ORDER BY COUNT(j) DESC")
    List<Map<String, Object>> countBySearchTermRemote();

    @Query("SELECT new map(j.platform AS name, COUNT(j) AS cnt) FROM JobPosting j " +
           "WHERE j.isActive = true AND j.searchLocation = :searchLocation AND j.searchTerm = :searchTerm " +
           "AND COALESCE(j.isRemote, false) = false " +
           "GROUP BY j.platform ORDER BY COUNT(j) DESC")
    List<Map<String, Object>> countByPlatformCity(@Param("searchLocation") String searchLocation,
                                                  @Param("searchTerm") String searchTerm);

    @Query("SELECT new map(j.platform AS name, COUNT(j) AS cnt) FROM JobPosting j " +
           "WHERE j.isActive = true AND j.searchTerm = :searchTerm " +
           "AND (j.searchLocation = 'Remote' OR COALESCE(j.isRemote, false) = true) " +
           "GROUP BY j.platform ORDER BY COUNT(j) DESC")
    List<Map<String, Object>> countByPlatformRemote(@Param("searchTerm") String searchTerm);

    @Query("SELECT j FROM JobPosting j WHERE j.isActive = true " +
           "AND j.searchLocation = :searchLocation AND j.searchTerm = :searchTerm " +
           "AND COALESCE(j.isRemote, false) = false " +
           "AND LOWER(j.platform) = LOWER(:platform) ORDER BY j.postedAt DESC NULLS LAST, j.scrapedAt DESC")
    List<JobPosting> findBrowseJobsCity(@Param("searchLocation") String searchLocation,
                                        @Param("searchTerm") String searchTerm,
                                        @Param("platform") String platform);

    @Query("SELECT j FROM JobPosting j WHERE j.isActive = true " +
           "AND j.searchTerm = :searchTerm " +
           "AND (j.searchLocation = 'Remote' OR COALESCE(j.isRemote, false) = true) " +
           "AND LOWER(j.platform) = LOWER(:platform) ORDER BY j.postedAt DESC NULLS LAST, j.scrapedAt DESC")
    List<JobPosting> findBrowseJobsRemote(@Param("searchTerm") String searchTerm,
                                          @Param("platform") String platform);
}
