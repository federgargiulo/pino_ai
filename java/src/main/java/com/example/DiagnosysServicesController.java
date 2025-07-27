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
        private String statusCode;
        private String statusDescription;

        @Override
        public String toString() {
            return "DiagnosysResultsTO{statusCode=" + statusCode +
                   ", statusDescription=" + statusDescription + "}";
        }
    }

    public static class DiagnosysEngineRequestTO {
        private String values[];

        public String[] getValues() {
            return values;
        }

        public void setValues(String[] values) {
            this.values = values;
        }
    }

    // ====== HTTP client ======
    private final HttpClient http;
    private final Gson gson = new Gson();
    private final String baseUrl;

    // Costruttore di default (compatibile con requisito)
    public DiagnosysServicesController() {
        this(System.getenv().getOrDefault("DIAG_BASE_URL", "http://localhost:5001"));
    }

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
    public DiagnosysResultsTO exeDiagnosys(DiagnosysEngineRequestTO dRequest) {
        try {
            String body = gson.toJson(dRequest);
            URI uri = URI.create(baseUrl + "/diagnosys/engine");
            HttpRequest req = HttpRequest.newBuilder(uri)
                    .timeout(Duration.ofSeconds(5))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(body))
                    .build();
            HttpResponse<String> resp = http.send(req, HttpResponse.BodyHandlers.ofString());
            if (resp.statusCode() != 200) {
                System.err.println("HTTP Error " + resp.statusCode() + ": " + resp.body());
                return createErrorResult();
            }
            return gson.fromJson(resp.body(), DiagnosysResultsTO.class);
        } catch (Exception e) {
            System.err.println("Error in exeDiagnosys: " + e.getMessage());
            return createErrorResult();
        }
    }

    private DiagnosysResultsTO createErrorResult() {
        DiagnosysResultsTO result = new DiagnosysResultsTO();
        result.statusCode = "ERROR";
        result.statusDescription = "Service unavailable";
        return result;
    }

    // ====== Esecuzione end-to-end ======
    public static void main(String[] args) throws Exception {
        // Test esatto come nel requisito (con 10 feature per compatibilità)
        DiagnosysEngineRequestTO req = new DiagnosysEngineRequestTO();
        String[] values = new String[]{"1", "3", "0", "0", "0", "0", "0", "0", "0", "0"};
        req.values = values;

        DiagnosysServicesController service = new DiagnosysServicesController();
        System.out.println(service.exeDiagnosys(req));

        // Execution loop per demo continua
        String assetId = System.getenv().getOrDefault("ASSET_ID", "M1");
        long pollMs = 0L;
        try { pollMs = Long.parseLong(System.getenv().getOrDefault("DIAG_POLL_MS", "0")); } catch (Exception ignored) {}

        if (pollMs > 0) {
            System.out.println("[JAVA] Starting continuous monitoring for asset " + assetId + " every " + pollMs + "ms");
            while (true) {
                try {
                    // 1) prendo i values per l'asset
                    String[] fetchedValues = service.fetchValues(assetId);

                    // 2) chiamo la diagnosi (POST /diagnosys/engine)
                    DiagnosysEngineRequestTO liveReq = new DiagnosysEngineRequestTO();
                    liveReq.setValues(fetchedValues);
                    DiagnosysResultsTO res = service.exeDiagnosys(liveReq);

                    System.out.println("[JAVA] asset=" + assetId + " -> " + res +
                        " (features: " + fetchedValues.length + ", score: " + 
                        (res.statusCode != null && res.statusCode.equals("1") ? "ANOMALY" : "OK") + ")");

                } catch (Exception e) {
                    System.err.println("[JAVA] Errore: " + e.getMessage());
                }

                Thread.sleep(pollMs);
            }
        }
    }
}

