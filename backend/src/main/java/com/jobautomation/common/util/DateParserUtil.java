package com.jobautomation.common.util;

import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class DateParserUtil {

    private static final Pattern NUMERIC_PATTERN = Pattern.compile("(\\d+)");

    public static LocalDateTime parseRelativeOrIsoDate(String rawDateText, String isoDatetimeAttr) {
        // 1. Try ISO datetime attribute first (e.g. "2026-08-23", "2026-08-23T14:30:00")
        if (isoDatetimeAttr != null && !isoDatetimeAttr.isBlank()) {
            try {
                String cleanAttr = isoDatetimeAttr.trim();
                if (cleanAttr.contains("T")) {
                    return LocalDateTime.parse(cleanAttr, DateTimeFormatter.ISO_LOCAL_DATE_TIME);
                } else if (cleanAttr.matches("\\d{4}-\\d{2}-\\d{2}")) {
                    return LocalDateTime.parse(cleanAttr + "T00:00:00", DateTimeFormatter.ISO_LOCAL_DATE_TIME);
                }
            } catch (Exception ignored) {}
        }

        if (rawDateText == null || rawDateText.isBlank()) {
            return LocalDateTime.now();
        }

        String text = rawDateText.toLowerCase().trim();

        // 2. Immediate relative matches
        if (text.contains("just now") || text.contains("today") || text.contains("active today") || text.contains("posted today")) {
            return LocalDateTime.now();
        }
        if (text.contains("yesterday") || text.contains("1 day ago") || text.contains("1d ago")) {
            return LocalDateTime.now().minusDays(1);
        }

        // 3. Extract numeric value
        Matcher matcher = NUMERIC_PATTERN.matcher(text);
        int number = 1;
        if (matcher.find()) {
            try {
                number = Integer.parseInt(matcher.group(1));
            } catch (NumberFormatException ignored) {}
        }

        // 4. Minute / Hour / Day / Week / Month matching
        if (text.contains("minute") || text.contains("min") || text.contains("m ago")) {
            return LocalDateTime.now().minusMinutes(number);
        }
        if (text.contains("hour") || text.contains("hr") || text.contains("h ago")) {
            return LocalDateTime.now().minusHours(number);
        }
        if (text.contains("day") || text.contains("d ago")) {
            return LocalDateTime.now().minusDays(number);
        }
        if (text.contains("week") || text.contains("w ago")) {
            return LocalDateTime.now().minusWeeks(number);
        }
        if (text.contains("month") || text.contains("mo ago")) {
            return LocalDateTime.now().minusMonths(number);
        }

        return LocalDateTime.now();
    }
}
