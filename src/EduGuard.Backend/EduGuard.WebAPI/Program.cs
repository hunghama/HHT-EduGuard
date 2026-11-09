using EduGuard.Core.Interfaces;
using EduGuard.Infrastructure.Persistence;
using EduGuard.Infrastructure.Telegram;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddSingleton<IStudentRepository, InMemoryStudentRepository>();
builder.Services.AddSingleton<ITelegramAlertService, TelegramAlertService>();

builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowAll", policy =>
    {
        policy.AllowAnyOrigin()
              .AllowAnyMethod()
              .AllowAnyHeader();
    });
});

var app = builder.Build();

app.UseCors("AllowAll");
app.UseAuthorization();
app.MapControllers();

app.Run();
