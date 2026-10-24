using EduGuard.Core.Interfaces;
using EduGuard.Infrastructure.Telegram;

/// <summary>
/// ====================================================================================
/// KIẾN TRÚC CLEAN ARCHITECTURE - TẦNG WEB API (COMPOSITION ROOT & DI CONTAINER)
/// ------------------------------------------------------------------------------------
/// KHÁI NIỆM: NƠI GẮN "PHÍCH CẮM" VÀO "Ổ CẮM"
/// 
/// 1. Composition Root:
///    Tầng WebAPI là điểm khởi đầu duy nhất của ứng dụng. Đây là nơi duy nhất được phép
///    biết cả Core (chứa Ổ cắm) và Infrastructure (chứa Phích cắm).
/// 
/// 2. Dependency Injection Registration:
///    Dòng lệnh `builder.Services.AddScoped<ITelegramAlertService, TelegramAlertService>();`
///    chính là hành động cắm "phích cắm" `TelegramAlertService` vào "ổ cắm" `ITelegramAlertService`.
///    Bất kỳ Controller hay UseCase nào cần gửi cảnh báo chỉ cần yêu cầu `ITelegramAlertService`,
///    hệ thống DI sẽ tự động bơm đối tượng cụ thể vào.
/// ====================================================================================
/// </summary>

var builder = WebApplication.CreateBuilder(args);

// 1. Đăng ký Controllers
builder.Services.AddControllers();

// 2. Cấu hình Swagger/OpenAPI cho phép test API trực tiếp từ trình duyệt
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(options =>
{
    options.SwaggerDoc("v1", new Microsoft.OpenApi.Models.OpenApiInfo
    {
        Title = "EduGuard Alert API",
        Version = "v1",
        Description = "Hệ thống giám sát lớp học thông minh - Clean Architecture .NET 8"
    });
});

// 3. ĐĂNG KÝ DEPENDENCY INJECTION: Cắm phích cắm Infrastructure vào ổ cắm Core
builder.Services.AddScoped<ITelegramAlertService, TelegramAlertService>();

var app = builder.Build();

// 4. Cấu hình HTTP request pipeline
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI(c =>
    {
        c.SwaggerEndpoint("/swagger/v1/swagger.json", "EduGuard API v1");
        c.RoutePrefix = string.Empty; // Mở Swagger ngay tại root URL (http://localhost:port/)
    });
}

app.UseHttpsRedirection();

app.UseAuthorization();

app.MapControllers();

app.Run();
