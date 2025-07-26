# build Java app
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /app
COPY pom.xml .
RUN mvn -q dependency:go-offline
COPY src src
RUN mvn -q package -DskipTests

# runtime
FROM eclipse-temurin:17-jre
WORKDIR /opt/app

# installa Python e pip con flag per evitare errore
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-pip && \
    pip3 install --break-system-packages numpy scikit-learn joblib

COPY --from=build /app/target/diagnosys-*.jar app.jar
COPY ai ai

CMD ["java","-jar","app.jar"]
