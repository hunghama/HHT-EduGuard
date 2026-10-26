
using System.Text.Json;

using EduGuard.Core.Interfaces;

using EduGuard.Infrastructure.Persistence;

using EduGuard.Infrastructure.Telegram;



var builder = WebApplication.CreateBuilder(args);



builder.WebHost.UseUrls("http://localhost:5160", "http://0.0.0.0:5160");



builder.Services.AddCors(o =>

{

    o.AddPolicy("AllowAll", p => p.AllowAnyOrigin().AllowAnyMethod().AllowAnyHeader());

});



builder.Services.AddControllers().AddJsonOptions(o =>

{

    o.JsonSerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.CamelCase;

});



builder.Services.AddEndpointsApiExplorer();

builder.Services.AddSwaggerGen();



builder.Services.AddSingleton<IStudentRepository, InMemoryStudentRepository>();

builder.Services.AddScoped<ITelegramAlertService, TelegramAlertService>();



var app = builder.Build();



app.UseSwagger();

app.UseSwaggerUI(c =>

{

    c.SwaggerEndpoint("/swagger/v1/swagger.json", "HHT EduGuard API v2");

    c.RoutePrefix = string.Empty;

});



app.UseCors("AllowAll");

app.UseAuthorization();

app.MapControllers();

app.Run();
