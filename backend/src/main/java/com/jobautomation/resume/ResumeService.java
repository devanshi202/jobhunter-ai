package com.jobautomation.resume;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.jobautomation.ai.AiServiceClient;
import com.jobautomation.resume.dto.ParsedResumeData;
import com.jobautomation.resume.dto.ResumeUploadResponse;
import org.apache.tika.Tika;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.UUID;

@Service
public class ResumeService {
    private static final Logger log = LoggerFactory.getLogger(ResumeService.class);

    private final ResumeRepository resumeRepository;
    private final AiServiceClient aiServiceClient;
    private final ObjectMapper objectMapper;
    private final String uploadDir;

    public ResumeService(ResumeRepository resumeRepository, AiServiceClient aiServiceClient, ObjectMapper objectMapper, @Value("${app.upload-dir}") String uploadDir) {
        this.resumeRepository = resumeRepository;
        this.aiServiceClient = aiServiceClient;
        this.objectMapper = objectMapper;
        this.uploadDir = uploadDir;
    }

    public ResumeUploadResponse uploadAndParse(MultipartFile file) throws IOException {
        if (file.isEmpty()) {
            throw new IllegalArgumentException("File is empty");
        }
        
        String contentType = file.getContentType();
        if (contentType == null || (!contentType.equals("application/pdf") && 
                !contentType.equals("application/vnd.openxmlformats-officedocument.wordprocessingml.document"))) {
            throw new IllegalArgumentException("Only PDF and DOCX files are supported");
        }

        // Ensure directory exists
        Path dirPath = Paths.get(uploadDir);
        if (!Files.exists(dirPath)) {
            Files.createDirectories(dirPath);
        }

        // Save file
        String originalFilename = file.getOriginalFilename();
        String fileExtension = originalFilename != null && originalFilename.contains(".") ? 
                originalFilename.substring(originalFilename.lastIndexOf(".")) : ".pdf";
        String uniqueFileName = UUID.randomUUID().toString() + fileExtension;
        Path filePath = dirPath.resolve(uniqueFileName);
        
        file.transferTo(filePath.toAbsolutePath().toFile());

        // Extract text
        Tika tika = new Tika();
        String rawText;
        try {
            rawText = tika.parseToString(filePath.toFile());
        } catch (org.apache.tika.exception.TikaException e) {
            throw new IOException("Failed to parse file text", e);
        }

        // Parse with AI
        ParsedResumeData parsedData = aiServiceClient.parseResume(rawText);

        // Convert structured data back to JSON string for storage
        String parsedDataJson = objectMapper.writeValueAsString(parsedData);

        // Save to DB
        ResumeProfile profile = ResumeProfile.builder()
                .filePath(filePath.toString())
                .fileName(originalFilename)
                .rawText(rawText)
                .parsedData(parsedDataJson)
                .skills(parsedData.skills() != null ? parsedData.skills().toArray(new String[0]) : new String[0])
                .experienceYears(parsedData.experienceYears())
                .preferredRoles(parsedData.preferredRoles() != null ? parsedData.preferredRoles().toArray(new String[0]) : new String[0])
                .preferredLocations(parsedData.preferredLocations() != null ? parsedData.preferredLocations().toArray(new String[0]) : new String[0])
                .build();

        ResumeProfile savedProfile = resumeRepository.save(profile);

        return new ResumeUploadResponse(
                savedProfile.getId(),
                savedProfile.getFileName(),
                parsedData,
                savedProfile.getCreatedAt()
        );
    }

    public List<ResumeProfile> getAllResumes() {
        return resumeRepository.findAllByOrderByCreatedAtDesc();
    }

    public ResumeProfile getResumeById(UUID id) {
        return resumeRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Resume not found with id: " + id));
    }
}
