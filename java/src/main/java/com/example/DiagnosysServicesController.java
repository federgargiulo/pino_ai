import java.net.http.*;
import java.net.URI;
import java.time.Duration;
import java.io.IOException;
import com.google.gson.*;

public class DiagnosysServicesController {

    public static class DiagnoseResponse {
        String statusCode;
        String statusDescription;

        public String toString() {
            return statusCode + " - " + statusDescription;
        }
    }

    public static void main(String[] args) throws IOException, InterruptedException {
        HttpClient client = HttpClient.newHttpClient();
        Gson gson = new Gson();

        // Step 1: Get samples from generator
        HttpRequest getSamples = HttpRequest.newBuilder()
                .uri(URI.create("http://localhost:8000/generate"))
                .timeout(Duration.ofSeconds(5))
                .GET()
                .build();

        HttpResponse<String> samplesResp = client.send(getSamples, HttpResponse.BodyHandlers.ofString());
        String jsonSamples = samplesResp.body();

        // Step 2: Send samples to diagnostic engine
        HttpRequest diagnoseReq = HttpRequest.newBuilder()
                .uri(URI.create("http://localhost:5000/diagnose"))
                .timeout(Duration.ofSeconds(5))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(jsonSamples))
                .build();

        HttpResponse<String> diagResp = client.send(diagnoseReq, HttpResponse.BodyHandlers.ofString());
        DiagnoseResponse result = gson.fromJson(diagResp.body(), DiagnoseResponse.class);

        System.out.println("Diagnosi: " + result);
    }
}
