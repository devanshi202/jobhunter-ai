package com.jobautomation.job.scraper;

import com.jobautomation.job.dto.JobPostingDto;
import java.util.List;

public interface JobScraper {
    String getPlatformName();
    List<JobPostingDto> scrape(String query, String location, int maxResults);
}
