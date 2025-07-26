# ---- build stage: Maven ----
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /app
COPY pom.xml .
RUN mvn -q dependency:go-offline
COPY src src
RUN mvn -q package -DskipTests

# ---- runtime stage ----
FROM eclipse-temurin:17-jre
WORKDIR /opt/app

# Py + reqs
RUN apt-get update && apt-get install -y python3 python3-pip && \
    pip3 install --no-cache-dir numpy scikit-learn joblib

# copia artefatti
COPY --from=build /app/target/diagnosys-*.jar app.jar
COPY ai ai

CMD ["java","-jar","app.jar"]

