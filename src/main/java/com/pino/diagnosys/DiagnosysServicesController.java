package com.pino.diagnosys;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

public class DiagnosysServicesController {

    public static class DiagnosysResultsTO {
        public String statusCode;
        public String statusDescription;
    }

    public static class DiagnosysEngineRequestTO {
        private String[] values;
        public String[] getValues() { return values; }
        public void setValues(String[] values) { this.values = values; }
    }

    public DiagnosysResultsTO exeDiagnosys(DiagnosysEngineRequestTO req) {
        DiagnosysResultsTO res = new DiagnosysResultsTO();
        try {
            /* 1. crea JSON con la singola finestra di 100 campioni */
            String json = "{\"windows\":[" + Arrays.toString(req.getValues()) + "]}";

            /* 2. lancia il Python via ProcessBuilder */
            Process p = new ProcessBuilder("python3", "ai/inference_service.py")
                    .directory(new File("."))
                    .start();

            try (OutputStream os = p.getOutputStream()) {
                os.write(json.getBytes(StandardCharsets.UTF_8));
            }

            /* 3. leggi risposta */
            String out = new String(p.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
            p.waitFor();

            if (out.contains("\"predictions\"")) {
                res.statusCode = "OK";
                res.statusDescription = out;
            } else {
                res.statusCode = "ERROR";
                res.statusDescription = out;
            }
        } catch (Exception e) {
            res.statusCode = "EXCEPTION";
            res.statusDescription = e.getMessage();
        }
        return res;
    }

    public static void main(String[] args) {
        DiagnosysEngineRequestTO r = new DiagnosysEngineRequestTO();
        /* demo con 100 numeri casuali */
        String[] vals = new String[100];
        for (int i = 0; i < 100; i++) vals[i] = String.valueOf(Math.random());
        r.setValues(vals);

        DiagnosysResultsTO res = new DiagnosysServicesController().exeDiagnosys(r);
        System.out.printf("[%s] %s%n", res.statusCode, res.statusDescription);
    }
}
