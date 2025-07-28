import java.net.http.*;
import java.net.URI;
import java.time.Duration;
import java.io.IOException;
import com.google.gson.*;

public class DiagnosysServicesController {

    // DTO della risposta di diagnostica
    public static class DiagnoseResponse {
        String statusCode;
        String statusDescription;
        @Override
        public String toString() {
            return statusCode + " - " + statusDescription;
        }
    }

    public static void main(String[] args) throws IOException, InterruptedException {
        HttpClient client = HttpClient.newHttpClient();
        Gson gson = new Gson();

        // 1) Prendi i campioni dal generator
        HttpRequest getSamples = HttpRequest.newBuilder()
                .uri(URI.create("http://localhost:9104/generate"))
                .timeout(Duration.ofSeconds(5))
                .GET()
                .build();

        HttpResponse<String> samplesResp = client.send(getSamples, HttpResponse.BodyHandlers.ofString());
        if (samplesResp.statusCode() != 200) {
            System.err.println("Errore GET /generate -> HTTP " + samplesResp.statusCode());
            System.exit(1);
        }
        String jsonSamples = samplesResp.body();

        // 2) Invia i campioni al motore di diagnostica
        HttpRequest diagnoseReq = HttpRequest.newBuilder()
                .uri(URI.create("http://localhost:9141/diagnose"))
                .timeout(Duration.ofSeconds(5))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(jsonSamples))
                .build();

        HttpResponse<String> diagResp = client.send(diagnoseReq, HttpResponse.BodyHandlers.ofString());
        if (diagResp.statusCode() != 200) {
            System.err.println("Errore POST /diagnose -> HTTP " + diagResp.statusCode() + " body=" + diagResp.body());
            System.exit(1);
        }
        DiagnoseResponse result = gson.fromJson(diagResp.body(), DiagnoseResponse.class);

        System.out.println("Diagnosi: " + result);
    }
}
