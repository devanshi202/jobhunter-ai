package com.jobautomation.match;

import com.jobautomation.ai.AiServiceClient;
import com.jobautomation.job.JobPosting;
import com.jobautomation.job.JobPostingRepository;
import com.jobautomation.resume.ResumeProfile;
import com.jobautomation.resume.ResumeRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * Profile matching for browsed jobs — a port of ai-service match_job_v3.py
 * with the LOCATION component removed (jobs are already segregated by
 * location bucket in the UI; ranking happens *within* each bucket).
 *
 * v3 weights renormalized over the remaining four components:
 *   semantic .40/.90 = .44, skill .25/.90 = .28, exp .15/.90 = .17, domain .10/.90 = .11
 *
 * Semantic similarity uses pgvector: JD embeddings (all-MiniLM-L6-v2, 384-dim,
 * L2-normalized, produced by ai-service /api/embed-batch) are stored in
 * job_postings.embedding and compared with the resume embedding via the
 * cosine-distance operator (<=>). Raw similarities are min-max normalized
 * across the run, exactly like v3 Fix #1.
 */
@Service
public class JobMatchService {
    private static final Logger log = LoggerFactory.getLogger(JobMatchService.class);

    private static final double W_SEMANTIC = 0.44;
    private static final double W_SKILL = 0.28;
    private static final double W_EXP = 0.17;
    private static final double W_DOMAIN = 0.11;

    private static final double EXP_FLOOR = 0.15;
    private static final double EXP_DECAY_YEARS = 5.0;

    private static final List<String> CORE_SKILLS = List.of(
            "Java", "Spring Boot", "Spring Security", "JWT", "Microservices",
            "REST API", "REST APIs", "RESTful", "Hibernate", "JPA",
            "SQL", "PostgreSQL", "MySQL", "Agile");
    private static final List<String> IMPORTANT_SKILLS = List.of(
            "Spring MVC", "Spring Cloud", "JDBC", "AWS", "Azure", "Docker", "Jenkins",
            "CI/CD", "Git", "Maven", "Gradle", "Debugging", "Root Cause Analysis",
            "Performance Optimization", "Postman", "API Testing", "SOLID",
            "Design Patterns", "Data Structures", "Algorithms", "Scrum");
    private static final List<String> SUPPORTING_SKILLS = List.of(
            "MongoDB", "Redis", "NoSQL", "Elasticsearch", "Kafka", "RabbitMQ", "gRPC",
            "GraphQL", "WebSocket", "Python", "JavaScript", "Node.js", "React",
            "Angular", "GCP", "Kubernetes", "Lambda", "EC2", "S3", "RDS", "Jira",
            "TDD", "JUnit", "Mockito", "Multithreading", "System Design",
            "Code Review", "Terraform", "GitHub Actions", "Log Analysis",
            "pgvector", "Apache Tika", "Ollama", "LLM Integration", "Semantic Search",
            "Vector Embeddings", "sentence-transformers", "Prompt Engineering",
            "FastAPI", "Web Scraping");

    private static final Map<String, Double> SKILL_WEIGHTS = new HashMap<>();
    private static final Map<String, String> SKILL_CANONICAL = new HashMap<>();
    private static final Map<String, Pattern> SKILL_PATTERNS = new HashMap<>();

    static {
        for (String s : CORE_SKILLS) registerSkill(s, 3.0);
        for (String s : IMPORTANT_SKILLS) registerSkill(s, 2.0);
        for (String s : SUPPORTING_SKILLS) registerSkill(s, 1.0);
    }

    private static void registerSkill(String skill, double weight) {
        String lower = skill.toLowerCase();
        SKILL_WEIGHTS.put(lower, weight);
        SKILL_CANONICAL.putIfAbsent(lower, skill);
        SKILL_PATTERNS.put(lower, Pattern.compile("\\b" + Pattern.quote(lower) + "\\b", Pattern.CASE_INSENSITIVE));
    }

    private static final List<String> DOMAIN_TERMS = List.of(
            "capital markets", "banking", "bfsi", "fintech", "financial services",
            "insurance", "asset management", "trading platform", "payments");

    private static final List<String> REQ_MARKERS = List.of(
            "requirements", "qualifications", "must have", "who you are",
            "what you'll need", "what we're looking for", "skills required", "eligibility");

    private static final List<Pattern> YOE_PATTERNS = List.of(
            Pattern.compile("(\\d+)\\s*(?:-|–|to)\\s*(\\d+)\\s*(?:years?|yrs?)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("(\\d+)\\s*\\+\\s*(?:years?|yrs?)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("minimum\\s+(\\d+)\\s*(?:years?|yrs?)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("at\\s+least\\s+(\\d+)\\s*(?:years?|yrs?)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("(\\d+)\\s*(?:years?|yrs?)\\s*(?:of\\s+)?(?:experience|exp)", Pattern.CASE_INSENSITIVE));

    /** Canonical latest profile — source of truth unless a resume is explicitly chosen. */
    private static final String DEFAULT_RESUME_TEXT = """
            Software Engineer with 2.5+ years of experience building and maintaining
            enterprise Java backend applications in the Capital Markets domain. Skilled in
            Java, Spring Boot, Microservices, REST APIs, SQL, debugging, root cause
            analysis, and performance optimization across Agile release cycles.
            Experienced with AWS, Azure, Docker, Jenkins, PostgreSQL, and backend
            engineering practices including SOLID principles and design patterns. Extends
            this into applied AI engineering — architected a production-style LLM platform
            using Spring Boot, FastAPI, Ollama, pgvector, and sentence-transformers,
            implementing semantic matching over vector embeddings that cut manual
            screening effort by 95%. Seeking Java Backend / Software Engineer roles
            focused on scalable backend, distributed systems, and AI-integrated services.

            Experience:
            - Develop and maintain enterprise Java-based backend applications for
              Société Générale's Capital Markets platform using TCS BaNCS.
            - Investigated and resolved 80+ UAT and production-impacting application issues
              through Java debugging, SQL-based data analysis, application log analysis,
              and detailed root cause analysis.
            - Implemented 20+ client-driven change requests and backend product
              enhancements across multiple release cycles, translating functional
              requirements into reliable application changes.
            - Collaborated with business users, QA teams, and client stakeholders in
              Agile delivery environments to analyze requirements, validate solutions,
              and improve release quality.
            - Supported 10+ UAT and production release cycles, performing API validation
              with Postman, troubleshooting release blockers, and contributing to
              application stability.
            - Participated in code reviews, defect triaging, and technical solution
              discussions to maintain code quality and reliable backend functionality.
            - Improved application performance by identifying inefficient processing
              paths and implementing optimizations during issue resolution and feature
              enhancements.
            - Built backend applications using Java, Spring Boot, Hibernate, Spring Security,
              REST APIs; cloud solutions on AWS and Azure; CI/CD with Jenkins.
            - Developed backend features for catalogue management at Blinkit.
            - Built AI-powered Job Search Automation using Spring Boot, Python, PostgreSQL,
              pgvector, Ollama; implemented semantic job matching with vector embeddings.
            - Built full-stack product review platform with Spring Boot, Angular, JWT,
              Spring Security, Hibernate, MySQL.

            Skills:
            Java, Spring Boot, Spring MVC, Spring Security, Microservices, REST APIs, JWT,
            Hibernate, JPA, SQL, PostgreSQL, MySQL, MongoDB, AWS, Azure, Docker, CI/CD,
            Jenkins, Git, Maven, LLM Integration, Ollama, Semantic Search, Vector
            Embeddings, sentence-transformers, pgvector, Prompt Engineering, FastAPI,
            Apache Tika, Web Scraping, SOLID Principles, Design Patterns, Data Structures
            & Algorithms, Code Review, Debugging, Root Cause Analysis, Performance
            Optimization, Python, JavaScript, React, Angular, Agile, Scrum, JIRA, API
            Testing, Postman, Log Analysis.""";
    private static final double DEFAULT_YOE = 2.5;

    private final JobPostingRepository jobPostingRepository;
    private final JobMatchRepository jobMatchRepository;
    private final ResumeRepository resumeRepository;
    private final AiServiceClient aiServiceClient;
    private final JdbcTemplate jdbcTemplate;

    public JobMatchService(JobPostingRepository jobPostingRepository,
                           JobMatchRepository jobMatchRepository,
                           ResumeRepository resumeRepository,
                           AiServiceClient aiServiceClient,
                           JdbcTemplate jdbcTemplate) {
        this.jobPostingRepository = jobPostingRepository;
        this.jobMatchRepository = jobMatchRepository;
        this.resumeRepository = resumeRepository;
        this.aiServiceClient = aiServiceClient;
        this.jdbcTemplate = jdbcTemplate;
    }

    // ------------------------------------------------------------------ run

    @Transactional
    public Map<String, Object> runMatching(UUID resumeId) {
        Profile profile = resolveProfile(resumeId);
        Set<String> candidateSkills = extractSkills(profile.text());
        log.info("[Match] Profile YOE={}, {} candidate skills from resume text", profile.yoe(), candidateSkills.size());

        int embedded = backfillEmbeddings();
        List<Double> resumeVec = aiServiceClient.embedOne(profile.text());
        if (resumeVec.isEmpty()) {
            throw new IllegalStateException("ai-service embedding failed — is it running on port 8000?");
        }
        Map<UUID, Double> rawSims = cosineSimilarities(resumeVec);
        if (rawSims.isEmpty()) {
            throw new IllegalStateException("No job embeddings available for similarity search");
        }

        double min = rawSims.values().stream().mapToDouble(Double::doubleValue).min().orElse(0);
        double max = rawSims.values().stream().mapToDouble(Double::doubleValue).max().orElse(1);
        double span = (max - min) > 1e-9 ? (max - min) : 1.0;

        List<JobPosting> jobs = jobPostingRepository.findAll().stream()
                .filter(j -> Boolean.TRUE.equals(j.getIsActive()))
                .filter(j -> j.getDescription() != null && j.getDescription().length() > 50)
                .toList();

        int scored = 0;
        for (JobPosting job : jobs) {
            Double raw = rawSims.get(job.getId());
            if (raw == null) continue; // no embedding — skip
            double semantic = (raw - min) / span;
            String matchText = buildMatchText(job.getTitle(), job.getDescription());
            Set<String> jdSkills = extractSkills(matchText);
            double skill = weightedJaccard(candidateSkills, jdSkills);
            double[] yoeRange = extractYoeRange(job.getDescription());
            double exp = experienceFit(profile.yoe(), job.getDescription(), job.getJobLevel());
            double domain = domainFit(matchText, job.getCompanyIndustry());
            double overall = Math.round((semantic * W_SEMANTIC + skill * W_SKILL
                    + exp * W_EXP + domain * W_DOMAIN) * 10000.0) / 100.0;

            Set<String> overlap = new TreeSet<>(candidateSkills);
            overlap.retainAll(jdSkills);
            List<String> reasons = buildReasons(semantic, skill, overlap, exp, yoeRange,
                    job.getJobLevel(), domain, profile.yoe());

            upsertMatch(resumeId, job.getId(), semantic, skill, exp, domain, overall, overlap, reasons);
            scored++;
        }

        log.info("[Match] Scored {} jobs ({} embeddings backfilled this run)", scored, embedded);
        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("scoredJobs", scored);
        summary.put("embeddingsBackfilled", embedded);
        summary.put("profileSource", profile.source());
        summary.put("resumeSkills", candidateSkills.stream().sorted()
                .map(s -> SKILL_CANONICAL.getOrDefault(s, s)).toList());
        summary.put("candidateYoe", profile.yoe());
        summary.put("weights", Map.of("semantic", W_SEMANTIC, "skill", W_SKILL,
                "experience", W_EXP, "domain", W_DOMAIN));
        return summary;
    }

    // ------------------------------------------------------------- ranked list

    @Transactional(readOnly = true)
    public List<Map<String, Object>> rankedJobs(List<JobPosting> jobs, UUID resumeId) {
        List<UUID> ids = jobs.stream().map(JobPosting::getId).toList();
        Map<UUID, JobMatch> byJob = new HashMap<>();
        if (!ids.isEmpty()) {
            List<JobMatch> matches = (resumeId != null)
                    ? jobMatchRepository.findByResumeIdAndJobIdIn(resumeId, ids)
                    : jobMatchRepository.findByJobIdIn(ids).stream()
                        .filter(m -> m.getResumeId() == null).toList();
            for (JobMatch m : matches) byJob.put(m.getJobId(), m);
        }
        List<Map<String, Object>> rows = new ArrayList<>();
        for (JobPosting job : jobs) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("job", job);
            JobMatch m = byJob.get(job.getId());
            if (m != null) {
                Map<String, Object> match = new LinkedHashMap<>();
                match.put("score", m.getOverallScore());
                match.put("label", scoreLabel(m.getOverallScore()));
                match.put("semantic", pct(m.getSemanticScore()));
                match.put("skill", pct(m.getSkillOverlapScore()));
                match.put("exp", pct(m.getExperienceFitScore()));
                match.put("domain", pct(m.getDomainScore()));
                match.put("skillOverlap", m.getSkillOverlap() == null || m.getSkillOverlap().isBlank()
                        ? List.of() : List.of(m.getSkillOverlap().split(",\\s*")));
                match.put("reasons", m.getMatchReason() == null || m.getMatchReason().isBlank()
                        ? List.of() : List.of(m.getMatchReason().split(" \\| ")));
                row.put("match", match);
            }
            rows.add(row);
        }
        rows.sort((a, b) -> {
            Map<String, Object> ma = (Map<String, Object>) a.get("match");
            Map<String, Object> mb = (Map<String, Object>) b.get("match");
            double sa = ma == null ? -1 : ((Number) ma.get("score")).doubleValue();
            double sb = mb == null ? -1 : ((Number) mb.get("score")).doubleValue();
            return Double.compare(sb, sa);
        });
        int rank = 0;
        for (Map<String, Object> row : rows) {
            if (row.get("match") != null) {
                ((Map<String, Object>) row.get("match")).put("rank", ++rank);
            }
        }
        return rows;
    }

    // ---------------------------------------------------------------- helpers

    private record Profile(String text, double yoe, String source) {}

    /**
     * Explicitly chosen resume wins; otherwise the canonical latest profile text
     * (DEFAULT_RESUME_TEXT) is the source of truth — DB uploads may be stale,
     * so they are never picked implicitly.
     */
    private Profile resolveProfile(UUID resumeId) {
        if (resumeId != null) {
            Optional<ResumeProfile> r = resumeRepository.findById(resumeId);
            if (r.isPresent() && r.get().getRawText() != null && !r.get().getRawText().isBlank()) {
                return new Profile(r.get().getRawText(),
                        r.get().getExperienceYears() != null ? r.get().getExperienceYears() : DEFAULT_YOE,
                        "resume:" + r.get().getFileName());
            }
        }
        return new Profile(DEFAULT_RESUME_TEXT, DEFAULT_YOE, "canonical-default");
    }

    private static String buildMatchText(String title, String description) {
        String t = title == null ? "" : title;
        String d = description == null ? "" : description;
        return (t + ". " + d).strip().replaceAll("^\\.+", "").strip();
    }

    private static Set<String> extractSkills(String text) {
        Set<String> found = new HashSet<>();
        if (text == null || text.isBlank()) return found;
        for (Map.Entry<String, Pattern> e : SKILL_PATTERNS.entrySet()) {
            if (e.getValue().matcher(text).find()) found.add(e.getKey());
        }
        return found;
    }

    private static double weightedJaccard(Set<String> candidate, Set<String> jd) {
        if (jd.isEmpty()) return 0.0;
        Set<String> union = new HashSet<>(candidate);
        union.addAll(jd);
        if (union.isEmpty()) return 0.0;
        double overlapW = 0, unionW = 0;
        for (String s : union) {
            double w = SKILL_WEIGHTS.getOrDefault(s, 1.0);
            unionW += w;
            if (candidate.contains(s) && jd.contains(s)) overlapW += w;
        }
        return unionW == 0 ? 0 : overlapW / unionW;
    }

    private static String requirementsSection(String text) {
        if (text == null) return "";
        String lower = text.toLowerCase();
        for (String marker : REQ_MARKERS) {
            int idx = lower.indexOf(marker);
            if (idx != -1) return text.substring(idx);
        }
        return text;
    }

    /** Returns {lo, hi} or {NaN, NaN} when no YOE found. */
    private static double[] extractYoeRange(String text) {
        String scoped = requirementsSection(text);
        double[] r = matchYoe(scoped);
        if (Double.isNaN(r[0]) && !scoped.equals(text)) r = matchYoe(text);
        return r;
    }

    private static double[] matchYoe(String text) {
        if (text == null) return new double[]{Double.NaN, Double.NaN};
        for (Pattern p : YOE_PATTERNS) {
            Matcher m = p.matcher(text);
            if (m.find()) {
                try {
                    if (m.groupCount() == 2) {
                        return new double[]{Double.parseDouble(m.group(1)), Double.parseDouble(m.group(2))};
                    }
                    double lo = Double.parseDouble(m.group(1));
                    return new double[]{lo, lo + 2};
                } catch (NumberFormatException ignored) {}
            }
        }
        return new double[]{Double.NaN, Double.NaN};
    }

    private static double experienceFit(double candidateYoe, String jdText, String jobLevel) {
        double[] range = extractYoeRange(jdText);
        double lo = range[0], hi = range[1];
        if (!Double.isNaN(lo)) {
            if (lo > 7) return 0.1;
            if (lo <= candidateYoe && candidateYoe <= hi) return 1.0;
            double gap = Math.min(Math.abs(candidateYoe - lo), Math.abs(candidateYoe - hi));
            return Math.max(EXP_FLOOR, 1 - gap / EXP_DECAY_YEARS);
        }
        if (jobLevel != null) {
            String lvl = jobLevel.toLowerCase();
            if (lvl.contains("mid") || lvl.contains("associate") || lvl.contains("not applicable")) return 0.80;
            if (lvl.contains("entry") || lvl.contains("intern")) return 0.55;
            if (lvl.contains("director") || lvl.contains("executive") || lvl.contains("principal")) return 0.20;
            if (lvl.contains("senior")) return 0.65;
        }
        return 0.65;
    }

    private static double domainFit(String matchText, String companyIndustry) {
        String text = ((matchText == null ? "" : matchText) + " " + (companyIndustry == null ? "" : companyIndustry)).toLowerCase();
        for (String term : DOMAIN_TERMS) {
            if (text.contains(term)) return 1.0;
        }
        return 0.45;
    }

    private static String scoreLabel(Double score) {
        double s = score == null ? 0 : score;
        if (s >= 75) return "Excellent";
        if (s >= 60) return "Strong";
        if (s >= 45) return "Good";
        if (s >= 30) return "Fair";
        return "Weak";
    }

    private static double pct(Double v) {
        return v == null ? 0 : Math.round(v * 10000.0) / 100.0;
    }

    private static String fmtYoe(double y) {
        return y == Math.rint(y) ? String.valueOf((int) y) : String.valueOf(y);
    }

    private List<String> buildReasons(double semantic, double skill, Set<String> overlap,
                                      double exp, double[] yoeRange, String jobLevel,
                                      double domain, double candidateYoe) {
        List<String> reasons = new ArrayList<>();
        if (semantic >= 0.75) {
            reasons.add("Very close semantic fit to your resume (" + (int) Math.round(semantic * 100) + "/100)");
        } else if (semantic >= 0.5) {
            reasons.add("Good semantic fit to your resume (" + (int) Math.round(semantic * 100) + "/100)");
        }
        if (!overlap.isEmpty()) {
            List<String> top = overlap.stream().sorted()
                    .map(s -> SKILL_CANONICAL.getOrDefault(s, s)).toList();
            String shown = top.size() <= 5 ? String.join(", ", top)
                    : String.join(", ", top.subList(0, 5)) + " (+" + (top.size() - 5) + " more)";
            reasons.add("Matches your skills: " + shown);
        }
        if (!Double.isNaN(yoeRange[0])) {
            if (yoeRange[0] <= candidateYoe && candidateYoe <= yoeRange[1]) {
                reasons.add("Asks " + fmtYoe(yoeRange[0]) + "–" + fmtYoe(yoeRange[1])
                        + " yrs — fits your " + fmtYoe(candidateYoe) + " yrs");
            } else if (yoeRange[0] > candidateYoe) {
                reasons.add("Wants " + fmtYoe(yoeRange[0]) + "+ yrs — senior for your " + fmtYoe(candidateYoe) + " yrs");
            } else {
                reasons.add("YOE band " + fmtYoe(yoeRange[0]) + "–" + fmtYoe(yoeRange[1]) + " yrs vs your " + fmtYoe(candidateYoe) + " yrs");
            }
        } else if (jobLevel != null && !jobLevel.isBlank()) {
            reasons.add("Level listed as " + jobLevel.trim());
        }
        if (domain >= 1.0) {
            reasons.add("Fintech / Capital Markets domain matches your background");
        }
        if (reasons.isEmpty()) {
            reasons.add("General fit — review description for stack details");
        }
        return reasons.subList(0, Math.min(3, reasons.size()));
    }

    // --------------------------------------------------------------- pgvector

    private String toVectorLiteral(List<Double> vec) {
        return vec.stream().map(d -> String.format(Locale.ROOT, "%.6f", d))
                .collect(Collectors.joining(",", "[", "]"));
    }

    /** Embed JDs missing embeddings and persist to job_postings.embedding. */
    private int backfillEmbeddings() {
        List<Map<String, Object>> missing = jdbcTemplate.queryForList(
                "SELECT id, title, description FROM job_postings " +
                "WHERE is_active IS DISTINCT FROM FALSE AND embedding IS NULL " +
                "AND description IS NOT NULL AND LENGTH(description) > 50");
        if (missing.isEmpty()) return 0;
        int done = 0;
        for (int i = 0; i < missing.size(); i += 40) {
            List<Map<String, Object>> chunk = missing.subList(i, Math.min(i + 40, missing.size()));
            List<String> texts = chunk.stream()
                    .map(r -> buildMatchText((String) r.get("title"), (String) r.get("description")))
                    .map(t -> t.length() > 4000 ? t.substring(0, 4000) : t)
                    .toList();
            List<List<Double>> vecs = aiServiceClient.embedBatch(texts);
            if (vecs.size() != chunk.size()) {
                log.warn("[Match] embed-batch returned {} vectors for {} texts — skipping chunk",
                        vecs.size(), chunk.size());
                continue;
            }
            for (int k = 0; k < chunk.size(); k++) {
                jdbcTemplate.update("UPDATE job_postings SET embedding = CAST(? AS vector) WHERE id = ?::uuid",
                        toVectorLiteral(vecs.get(k)), chunk.get(k).get("id").toString());
                done++;
            }
            log.info("[Match] Embedded {}/{} JDs", done, missing.size());
        }
        return done;
    }

    /** Cosine similarity (embeddings are L2-normalized, so 1 - distance). */
    private Map<UUID, Double> cosineSimilarities(List<Double> resumeVec) {
        String vec = toVectorLiteral(resumeVec);
        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                "SELECT id, 1 - (embedding <=> CAST(? AS vector)) AS sim " +
                "FROM job_postings WHERE embedding IS NOT NULL", vec);
        Map<UUID, Double> out = new HashMap<>(rows.size() * 2);
        for (Map<String, Object> r : rows) {
            Object id = r.get("id");
            UUID uuid = id instanceof UUID u ? u : UUID.fromString(String.valueOf(id));
            out.put(uuid, ((Number) r.get("sim")).doubleValue());
        }
        return out;
    }

    private void upsertMatch(UUID resumeId, UUID jobId, double semantic, double skill,
                             double exp, double domain, double overall,
                             Set<String> overlap, List<String> reasons) {
        String overlapStr = overlap.stream().sorted()
                .map(s -> SKILL_CANONICAL.getOrDefault(s, s))
                .collect(Collectors.joining(", "));
        String reasonStr = String.join(" | ", reasons);
        Optional<JobMatch> existing = (resumeId != null)
                ? jobMatchRepository.findByResumeIdAndJobId(resumeId, jobId)
                : jobMatchRepository.findByJobIdAndResumeIdIsNull(jobId);
        JobMatch m = existing.orElseGet(() -> JobMatch.builder()
                .resumeId(resumeId).jobId(jobId).status("NEW").build());
        m.setSemanticScore(semantic);
        m.setSkillOverlapScore(skill);
        m.setExperienceFitScore(exp);
        m.setDomainScore(domain);
        m.setOverallScore(overall);
        m.setSkillOverlap(overlapStr);
        m.setMatchReason(reasonStr);
        jobMatchRepository.save(m);
    }
}
