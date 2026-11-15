# Stage 1: Build & Publish
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src

COPY ["EduGuard.sln", "./"]
COPY ["EduGuard.Core/EduGuard.Core.csproj", "EduGuard.Core/"]
COPY ["EduGuard.Infrastructure/EduGuard.Infrastructure.csproj", "EduGuard.Infrastructure/"]
COPY ["EduGuard.WebAPI/EduGuard.WebAPI.csproj", "EduGuard.WebAPI/"]
RUN dotnet restore "EduGuard.WebAPI/EduGuard.WebAPI.csproj"

COPY . .
WORKDIR "/src/EduGuard.WebAPI"
RUN dotnet publish "EduGuard.WebAPI.csproj" -c Release -o /app/publish --no-restore

# Stage 2: Runtime gọn nhẹ
FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS runtime
WORKDIR /app
COPY --from=build /app/publish .

ENV ASPNETCORE_URLS=http://+:8080
EXPOSE 8080
ENTRYPOINT ["dotnet", "EduGuard.WebAPI.dll"]
