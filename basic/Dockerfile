FROM eclipse-temurin:17-jdk-alpine as build

WORKDIR /workspace/app

# Copy gradle configuration
COPY gradle gradle
COPY build.gradle settings.gradle gradlew ./

# Copy source code
COPY src src

# Build the application
RUN ./gradlew bootJar --no-daemon

# Production stage
FROM eclipse-temurin:17-jre-alpine

WORKDIR /app

# Create a non-root user
RUN addgroup -S spring && adduser -S spring -G spring
USER spring:spring

# Copy the jar file from the build stage
COPY --from=build /workspace/app/build/libs/*.jar app.jar

# Expose the port the app runs on
EXPOSE 8081

# Run the jar file
ENTRYPOINT ["java", "-jar", "app.jar"]
