package com.example;

import java.io.IOException;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.nio.charset.StandardCharsets;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

public class DiagnosysServicesController {

    // ====== DTOs (compatibili col requisito) ======
    public static class DiagnosysResultsTO {
        public String statusCode;
        public String statusDescription;

        @Override
        public String toString() {
            return "DiagnosysResultsTO{statusCode=" + statusCode +
                   ", statusDescription=" + statusDescription + "}";
        }
    }

    public static class DiagnosysEngineRequestTO {
        private String[] values;

        public String[] getValues() { return values; }
        public void setValues(String[] values) { this.values = values; }
    }

    // ====== HTTP client ======
    private final HttpClient http;
    private final Gson gson = new Gson();
    private final String baseUrl;

    public DiagnosysServicesController(String baseUrl) {
        this.baseUrl = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        this.http = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5))
                .build();
    }

    // GET /values?asset_id=...
    public String[] fetchValues(String assetId) throws IOException, InterruptedException {
        String q = URLEncoder.encode(assetId, StandardCharsets.UTF_8);
        URI uri = URI.create(baseUrl + "/values?asset_id=" + q);
        HttpRequest req = HttpRequest.newBuilder(uri).GET().timeout(Duration.ofSeconds(5)).build();
        HttpResponse<String> resp = http.send(req, HttpResponse.BodyHandlers.ofString());
        if (resp.statusCode() != 200) {
            throw new IOException("GET " + uri + " -> HTTP " + resp.statusCode() + " body=" + resp.body());
        }
        JsonObject obj = JsonParser.parseString(resp.body()).getAsJsonObject();
        JsonArray arr = obj.getAsJsonArray("values");
        String[] values = new String[arr.size()];
        for (int i = 0; i < arr.size(); i++) values[i] = arr.get(i).getAsString();
        return values;
    }

    // POST /diagnosys/engine { "values": [...] }
    public DiagnosysResultsTO exeDiagnosys(DiagnosysEngineRequestTO dRequest) throws IOException, InterruptedException {
        String body = gson.toJson(dRequest);
        URI uri = URI.create(baseUrl + "/diagnosys/engine");
        HttpRequest req = HttpRequest.newBuilder(uri)
                .timeout(Duration.ofSeconds(5))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(body))
                .build();
        HttpResponse<String> resp = http.send(req, HttpResponse.BodyHandlers.ofString());
        if (resp.statusCode() != 200) {
            throw new IOException("POST " + uri + " -> HTTP " + resp.statusCode() + " body=" + resp.body());
        }
        return gson.fromJson(resp.body(), DiagnosysResultsTO.class);
    }

    // ====== Esecuzione end-to-end ======
    public static void main(String[] args) throws Exception {
        // Base URL del servizio Python (FastAPI)
        // - se giri su host: http://localhost:5000
        // - se giri in Docker accanto ad ai-service: http://ai-service:5000
        String base = System.getenv().getOrDefault("DIAG_BASE_URL", "http://localhost:5000");
        // Asset da analizzare (default M1)
        String assetId = (args.length > 0 && args[0] != null && !args[0].isBlank())
                ? args[0] : System.getenv().getOrDefault("ASSET_ID", "M1");
        // Polling (ms). Se 0 o assente, esegue una sola diagnosi e termina.
        long pollMs = 0L;
        try { pollMs = Long.parseLong(System.getenv().getOrDefault("DIAG_POLL_MS", "0")); } catch (Exception ignored) {}

        DiagnosysServicesController service = new DiagnosysServicesController(base);

        while (true) {
            try {
                // 1) prendo i values per l'asset
                String[] values = service.fetchValues(assetId);

                // 2) chiamo la diagnosi (POST /diagnosys/engine)
                DiagnosysEngineRequestTO req = new DiagnosysEngineRequestTO();
                req.setValues(values);
                DiagnosysResultsTO res = service.exeDiagnosys(req);

                System.out.println("[JAVA] asset=" + assetId + " -> " + res);

            } catch (IOException ioe) {
                System.err.println("[JAVA] Errore HTTP: " + ioe.getMessage());
            } catch (InterruptedException ie) {
                Thread.currentThread().interrupt();
                break;
            } catch (Exception e) {
                System.err.println("[JAVA] Errore: " + e.getMessage());
            }

            if (pollMs <= 0) break;
            Thread.sleep(pollMs);
        }
    }
}
