using EduGuard.Core.Interfaces;
using EduGuard.Infrastructure.Persistence;
using EduGuard.Infrastructure.Telegram;
using EduGuard.WebAPI.Hubs;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddSignalR();
builder.Services.AddSingleton<IStudentRepository, InMemoryStudentRepository>();
builder.Services.AddSingleton<ITelegramAlertService, TelegramAlertService>();

builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowAll", policy =>
    {
        policy.SetIsOriginAllowed(_ => true)
              .AllowAnyMethod()
              .AllowAnyHeader()
              .AllowCredentials();
    });
});

var app = builder.Build();

app.UseCors("AllowAll");
app.UseAuthorization();
app.MapControllers();
app.MapHub<EduGuardHub>("/hubs/eduguard");

app.Run();
