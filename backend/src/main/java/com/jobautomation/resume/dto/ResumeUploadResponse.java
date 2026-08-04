package com.jobautomation.resume.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import java.time.LocalDateTime;
import java.util.UUID;

public record ResumeUploadResponse(
        UUID id,
        String fileName,
        ParsedResumeData parsedData,
        @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss")
        LocalDateTime createdAt
) {
}
