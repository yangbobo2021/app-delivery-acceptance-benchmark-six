package benchmark;

import java.io.BufferedReader;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.HashMap;
import java.util.Map;
import java.util.TreeMap;
import java.util.regex.Pattern;

public final class BatchReport {
    private static final Pattern KEY = Pattern.compile("[A-Za-z0-9_-]+");
    private static final Pattern AMOUNT = Pattern.compile("[0-9]+");

    private record Event(String account, long amount) { }
    private static final class Total {
        long cents;
        long count;
    }

    private BatchReport() { }

    public static void main(String[] args) {
        try {
            run(args);
        } catch (IllegalArgumentException | IOException ex) {
            System.err.println(ex.getMessage() == null ? "Batch failed" : ex.getMessage());
            System.exit(2);
        }
    }

    private static void run(String[] args) throws IOException {
        if (args.length != 4 || !"--input".equals(args[0]) || !"--output".equals(args[2])) {
            throw new IllegalArgumentException("Usage: --input ABSOLUTE_CSV --output ABSOLUTE_CSV");
        }
        Path input = Path.of(args[1]);
        Path output = Path.of(args[3]);
        if (!input.isAbsolute() || !output.isAbsolute()) {
            throw new IllegalArgumentException("Input and output paths must be absolute");
        }
        if (!Files.isRegularFile(input)) {
            throw new IllegalArgumentException("Input file does not exist");
        }
        if (Files.exists(output)) {
            throw new IllegalArgumentException("Output already exists");
        }
        Path parent = output.getParent();
        if (parent == null || !Files.isDirectory(parent)) {
            throw new IllegalArgumentException("Output directory does not exist");
        }

        Map<String, Event> seen = new HashMap<>();
        Map<String, Total> totals = new TreeMap<>();
        try (BufferedReader reader = Files.newBufferedReader(input, StandardCharsets.UTF_8)) {
            if (!"event_id,account,amount_cents".equals(reader.readLine())) {
                throw new IllegalArgumentException("Invalid CSV header");
            }
            String line;
            int rows = 0;
            while ((line = reader.readLine()) != null) {
                rows++;
                String[] fields = line.split(",", -1);
                if (fields.length != 3 || !KEY.matcher(fields[0]).matches()
                        || !KEY.matcher(fields[1]).matches() || !AMOUNT.matcher(fields[2]).matches()) {
                    throw new IllegalArgumentException("Invalid CSV row " + rows);
                }
                long amount;
                try {
                    amount = Long.parseLong(fields[2]);
                } catch (NumberFormatException ex) {
                    throw new IllegalArgumentException("Invalid amount at row " + rows);
                }
                if (amount < 1 || amount > 1_000_000_000L) {
                    throw new IllegalArgumentException("Amount out of range at row " + rows);
                }
                Event event = new Event(fields[1], amount);
                Event previous = seen.putIfAbsent(fields[0], event);
                if (previous != null && !previous.equals(event)) {
                    throw new IllegalArgumentException("Conflicting event_id at row " + rows);
                }
                Total total = totals.computeIfAbsent(fields[1], ignored -> new Total());
                total.cents = Math.addExact(total.cents, amount);
                total.count++;
            }
            if (rows == 0) {
                throw new IllegalArgumentException("No data rows");
            }
        } catch (ArithmeticException ex) {
            throw new IllegalArgumentException("Total exceeds supported range");
        }

        StringBuilder result = new StringBuilder("account,total_cents,event_count\n");
        for (Map.Entry<String, Total> entry : totals.entrySet()) {
            Total total = entry.getValue();
            result.append(entry.getKey()).append(',').append(total.cents).append(',').append(total.count).append('\n');
        }
        Path temporary = Files.createTempFile(parent, ".batch-", ".tmp");
        try {
            Files.writeString(temporary, result.toString(), StandardCharsets.UTF_8);
            Files.move(temporary, output, StandardCopyOption.ATOMIC_MOVE);
        } finally {
            Files.deleteIfExists(temporary);
        }
    }
}
