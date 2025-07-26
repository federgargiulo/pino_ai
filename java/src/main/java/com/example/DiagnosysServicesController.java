package com.example;

import java.net.URI;
import java.net.http.*;
import com.google.gson.*;

public class DiagnosysServicesController {

    public static class DiagnosysResultsTO {
        public String statusCode;
        public String statusDescription;
        @Override public String toString() {
            return "statusCode=" + statusCode + ", statusDescription=" + statusDescription;
        }
    }

    public static class DiagnosysEngineRequestTO {
        public String[] values;
        public String[] getValues() { return values; }
        public void setValues(String[] values) { this.values = values; }
    }

    public DiagnosysResultsTO exeDiagnosys(DiagnosysEngineRequestTO dRequest) {
        try {
            HttpClient client = HttpClient.newHttpClient();
            HttpRequest  req  = HttpRequest.newBuilder()
                    .uri(new URI("http://ai-service:5000/predict"))
                    .GET().build();
            HttpResponse<String> res = client.send(req, HttpResponse.BodyHandlers.ofString());
            return new Gson().fromJson(res.body(), DiagnosysResultsTO.class);
        } catch (Exception ex) { throw new RuntimeException(ex); }
    }

    public static void main(String[] args) {
        DiagnosysEngineRequestTO req = new DiagnosysEngineRequestTO();
        req.values = new String[]{"dummy"};
        DiagnosysServicesController svc = new DiagnosysServicesController();
        System.out.println(svc.exeDiagnosys(req));
    }
}
