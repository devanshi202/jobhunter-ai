package com.jobautomation.resume.dto;

import java.time.LocalDateTime;
import java.util.UUID;

public record ResumeUploadResponse(
        UUID id,
        String fileName,
        ParsedResumeData parsedData,
        LocalDateTime createdAt
) {
}
