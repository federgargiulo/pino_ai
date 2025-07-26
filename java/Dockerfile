# build
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /src
COPY pom.xml .
RUN mvn -q -e -DskipTests dependency:go-offline
COPY src ./src
RUN mvn -q -e -DskipTests clean package

# run
FROM eclipse-temurin:17-jre
WORKDIR /app
COPY --from=build /src/target/*-shaded.jar /app/app.jar
# DIAG_BASE_URL: http://ai-service:5000 in rete docker; http://localhost:5000 su host
ENV DIAG_BASE_URL=http://ai-service:5000 ASSET_ID=M1 DIAG_POLL_MS=10000
ENTRYPOINT ["java","-jar","/app/app.jar"]
