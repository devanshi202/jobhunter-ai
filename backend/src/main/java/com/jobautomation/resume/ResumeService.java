package com.jobautomation.resume;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.jobautomation.ai.AiServiceClient;
import com.jobautomation.resume.dto.ParsedResumeData;
import com.jobautomation.resume.dto.ResumeUploadResponse;
import org.apache.tika.Tika;
import org.apache.tika.metadata.Metadata;
import org.apache.tika.parser.AutoDetectParser;
import org.apache.tika.parser.ParseContext;
import org.apache.tika.sax.LinkContentHandler;
import org.apache.tika.sax.Link;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

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

        // Extract PDF/DOCX annotations and embedded hyperlinks
        List<String> extractedUrls = extractHyperlinks(filePath, rawText);
        log.info("[DEBUG] Extracted {} hyperlinks from document: {}", extractedUrls.size(), extractedUrls);

        StringBuilder enrichedText = new StringBuilder(rawText);
        if (!extractedUrls.isEmpty()) {
            enrichedText.append("\n\nExtracted Hyperlinks from Document:\n");
            for (String url : extractedUrls) {
                enrichedText.append("- ").append(url).append("\n");
            }
        }

        // Parse with AI
        ParsedResumeData parsedData = aiServiceClient.parseResume(enrichedText.toString());

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

        // Keep ai-service resume_profile.json and resume_experience.json in sync
        syncProfileFiles(parsedData, rawText);

        return new ResumeUploadResponse(
                savedProfile.getId(),
                savedProfile.getFileName(),
                parsedData,
                savedProfile.getCreatedAt()
        );
    }

    private void syncProfileFiles(ParsedResumeData parsedData, String rawText) {
        try {
            Path aiServiceDir = Paths.get("../ai-service").toAbsolutePath().normalize();
            if (Files.exists(aiServiceDir)) {
                // Write resume_profile.json (backup any pre-existing hand-curated copy)
                Path profileJsonPath = aiServiceDir.resolve("resume_profile.json");
                backupExisting(profileJsonPath);
                objectMapper.writerWithDefaultPrettyPrinter().writeValue(profileJsonPath.toFile(), parsedData);
                log.info("[ResumeService] Synchronized active profile to {}", profileJsonPath);

                // Write resume_experience.json for enhance_resume.py
                if (parsedData.experience() != null && !parsedData.experience().isEmpty()) {
                    Path expJsonPath = aiServiceDir.resolve("resume_experience.json");
                    List<Map<String, Object>> expList = new ArrayList<>();
                    for (ParsedResumeData.Experience exp : parsedData.experience()) {
                        Map<String, Object> jobMap = new LinkedHashMap<>();
                        jobMap.put("company", exp.company());
                        jobMap.put("role", exp.role());
                        jobMap.put("duration", exp.duration());
                        jobMap.put("bullets", toActionBullets(exp.description()));
                        expList.add(jobMap);
                    }
                    backupExisting(expJsonPath);
                    objectMapper.writerWithDefaultPrettyPrinter().writeValue(expJsonPath.toFile(), expList);
                    log.info("[ResumeService] Synchronized experience bullets to {}", expJsonPath);
                }
            }
        } catch (Exception e) {
            log.warn("[ResumeService] Could not synchronize profile files to ai-service: {}", e.getMessage());
        }
    }

    /**
     * Preserves a previous version of a synced file as <name>.bak so a
     * hand-curated copy is never silently destroyed by re-sync.
     */
    private void backupExisting(Path target) {
        try {
            if (Files.exists(target)) {
                Path backup = target.resolveSibling(target.getFileName() + ".bak");
                Files.copy(target, backup, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
            }
        } catch (Exception e) {
            log.warn("[ResumeService] Could not back up {}: {}", target, e.getMessage());
        }
    }

    /**
     * Converts an experience description blob into discrete action bullets:
     * splits on newlines and bullet markers first, then breaks multi-sentence
     * paragraphs at sentence boundaries so enhance_resume.py gets one
     * actionable statement per bullet.
     */
    private List<String> toActionBullets(String description) {
        List<String> bullets = new ArrayList<>();
        if (description == null || description.isBlank()) {
            return bullets;
        }
        for (String line : description.split("\\R")) {
            String trimmed = line.trim().replaceFirst("^[-•*]\\s*", "");
            if (!trimmed.isEmpty()) {
                bullets.add(trimmed);
            }
        }
        // Multi-sentence paragraphs -> one bullet per sentence (capital after ". ")
        List<String> expanded = new ArrayList<>();
        for (String b : bullets) {
            String[] sentences = b.split("(?<=\\.)\\s+(?=[A-Z])");
            if (sentences.length > 1) {
                for (String s : sentences) {
                    if (!s.isBlank()) {
                        expanded.add(s.trim());
                    }
                }
            } else {
                expanded.add(b);
            }
        }
        return expanded;
    }

    private List<String> extractHyperlinks(Path filePath, String rawText) {
        Set<String> urls = new LinkedHashSet<>();

        // 1. Extract embedded hyperlinks via Tika SAX parser
        try (InputStream is = Files.newInputStream(filePath)) {
            LinkContentHandler linkHandler = new LinkContentHandler();
            AutoDetectParser parser = new AutoDetectParser();
            Metadata metadata = new Metadata();
            parser.parse(is, linkHandler, metadata, new ParseContext());

            for (Link link : linkHandler.getLinks()) {
                String uri = link.getUri();
                if (uri != null && (uri.startsWith("http://") || uri.startsWith("https://") || uri.contains("linkedin.com") || uri.contains("github.com"))) {
                    urls.add(uri.trim());
                }
            }
        } catch (Exception e) {
            log.warn("Failed to extract SAX links from document: {}", e.getMessage());
        }

        // 2. Regex search raw text for explicit URLs
        Pattern pattern = Pattern.compile("(https?://[^\s<\"'>]+|(?:www\\.)?(?:linkedin\\.com/in/|github\\.com/)[^\s<\"'>]+)", Pattern.CASE_INSENSITIVE);
        Matcher matcher = pattern.matcher(rawText);
        while (matcher.find()) {
            String match = matcher.group();
            if (!match.startsWith("http://") && !match.startsWith("https://")) {
                match = "https://" + match;
            }
            urls.add(match.trim());
        }

        return new ArrayList<>(urls);
    }

    public List<ResumeProfile> getAllResumes() {
        return resumeRepository.findAllByOrderByCreatedAtDesc();
    }

    /**
     * Re-syncs the active (latest) resume profile to the ai-service JSON files
     * (resume_profile.json + resume_experience.json) so Python scripts can read
     * them directly without re-parsing. Also repairs the case where the DB has a
     * profile but the JSON files were never written (e.g. after a project move).
     */
    public ResumeProfile syncActiveProfile() {
        Optional<ResumeProfile> latest = getLatestResume();
        if (latest.isEmpty()) {
            throw new IllegalArgumentException("No resume profile found in database. Upload a resume first.");
        }
        ResumeProfile profile = latest.get();
        syncProfileFiles(getParsedData(profile), profile.getRawText());
        log.info("[ResumeService] Active profile sync requested; files refreshed at {}", Paths.get("../ai-service").toAbsolutePath().normalize());
        return profile;
    }

    /**
     * Deserializes the stored parsed_data JSONB into the typed ParsedResumeData.
     */
    public ParsedResumeData getParsedData(ResumeProfile profile) {
        return deserializeParsedData(profile.getParsedData());
    }

    private ParsedResumeData deserializeParsedData(String parsedDataJson) {
        if (parsedDataJson == null || parsedDataJson.isBlank()) {
            throw new IllegalArgumentException("Resume profile has no parsed data");
        }
        try {
            return objectMapper.readValue(parsedDataJson, ParsedResumeData.class);
        } catch (Exception e) {
            throw new IllegalStateException("Failed to read stored parsed data: " + e.getMessage(), e);
        }
    }

    public Optional<ResumeProfile> getLatestResume() {
        List<ResumeProfile> list = resumeRepository.findAllByOrderByCreatedAtDesc();
        return list.isEmpty() ? Optional.empty() : Optional.of(list.get(0));
    }

    public ResumeProfile getResumeById(UUID id) {
        return resumeRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Resume not found with id: " + id));
    }
}
