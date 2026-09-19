package com.jobautomation.ai;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.jobautomation.resume.dto.ParsedResumeData;
import okhttp3.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Collections;

@Service
public class AiServiceClient {

    private static final Logger log = LoggerFactory.getLogger(AiServiceClient.class);
    private final OkHttpClient httpClient;
    private final ObjectMapper objectMapper;
    private final String aiServiceUrl;

    public AiServiceClient(OkHttpClient httpClient, ObjectMapper objectMapper, @Value("${app.ai-service.url}") String aiServiceUrl) {
        this.httpClient = httpClient;
        this.objectMapper = objectMapper;
        this.aiServiceUrl = aiServiceUrl;
    }

    public ParsedResumeData parseResume(String rawText) {
        try {
            Map<String, String> payload = new HashMap<>();
            payload.put("text", rawText);
            
            String jsonBody = objectMapper.writeValueAsString(payload);
            RequestBody body = RequestBody.create(jsonBody, MediaType.parse("application/json"));
            
            Request request = new Request.Builder()
                    .url(aiServiceUrl + "/api/parse-resume")
                    .post(body)
                    .build();
                    
            try (Response response = httpClient.newCall(request).execute()) {
                if (response.isSuccessful() && response.body() != null) {
                    String responseBody = response.body().string();
                    return objectMapper.readValue(responseBody, ParsedResumeData.class);
                } else {
                    log.error("AI service returned error: {}", response.code());
                }
            }
        } catch (Exception e) {
            log.error("Failed to call AI service for resume parsing", e);
        }
        
        // Fallback
        return new ParsedResumeData(
                "Unknown", "", "",          // name, email, phone
                "", "", "",                 // currentLocation, linkedinUrl, githubUrl
                0.0, "Unknown",             // experienceYears, currentRole
                Collections.emptyList(),    // skills
                Collections.emptyList(),    // experience
                Collections.emptyList(),    // projects
                Collections.emptyList(),    // education
                Collections.emptyList(),    // achievements
                Collections.emptyList(),    // preferredRoles
                Collections.emptyList(),    // preferredLocations
                "Failed to parse resume automatically"  // summary
        );
    }

    /** Batch embeddings via ai-service (all-MiniLM-L6-v2, 384-dim, L2-normalized). */
    @SuppressWarnings("unchecked")
    public List<List<Double>> embedBatch(List<String> texts) {
        if (texts == null || texts.isEmpty()) return Collections.emptyList();
        try {
            Map<String, Object> payload = new HashMap<>();
            payload.put("texts", texts);
            String jsonBody = objectMapper.writeValueAsString(payload);
            RequestBody body = RequestBody.create(jsonBody, MediaType.parse("application/json"));
            Request request = new Request.Builder()
                    .url(aiServiceUrl + "/api/embed-batch")
                    .post(body)
                    .build();
            try (Response response = httpClient.newCall(request).execute()) {
                if (response.isSuccessful() && response.body() != null) {
                    Map<String, Object> root = objectMapper.readValue(response.body().string(), Map.class);
                    List<List<Number>> vecs = (List<List<Number>>) root.get("embeddings");
                    List<List<Double>> out = new ArrayList<>(vecs.size());
                    for (List<Number> v : vecs) {
                        List<Double> d = new ArrayList<>(v.size());
                        for (Number n : v) d.add(n.doubleValue());
                        out.add(d);
                    }
                    return out;
                }
                log.error("AI embed-batch returned HTTP {}", response.code());
            }
        } catch (Exception e) {
            log.error("Failed to call AI service for batch embeddings", e);
        }
        return Collections.emptyList();
    }

    public List<Double> embedOne(String text) {
        List<List<Double>> out = embedBatch(List.of(text == null ? "" : text));
        return out.isEmpty() ? Collections.emptyList() : out.get(0);
    }
}
