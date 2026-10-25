using System.Net.Http.Json;
using EduGuard.Core.Interfaces;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;

namespace EduGuard.Infrastructure.Telegram;

public class TelegramAlertService : ITelegramAlertService
{
    private readonly ILogger<TelegramAlertService> _logger;
    private readonly IConfiguration _config;
    private static readonly HttpClient _httpClient = new HttpClient { Timeout = TimeSpan.FromSeconds(5) };

    public TelegramAlertService(ILogger<TelegramAlertService> logger, IConfiguration config)
    {
        _logger = logger;
        _config = config;
    }

    public async Task SendWakeUpMessageAsync(long chatId, string studentName, string seatCode)
    {
        string humaneMessage = $"🌱 [Trợ lý Học vụ HHT EduGuard]\nChào {studentName} 👋, hệ thống nhận thấy bạn có vẻ hơi mệt tại vị trí ghế [{seatCode}].\nBạn hãy vươn vai, hít thở sâu hoặc uống chút nước để tỉnh táo tiếp tục đồng hành cùng bài giảng của Thầy nhé!";

        _logger.LogInformation("[TELEGRAM PRIVATE MESSAGE -> ChatID {ChatId}]: {Message}", chatId, humaneMessage);

        // Đọc Bot Token từ biến môi trường hoặc appsettings.json
        string? botToken = Environment.GetEnvironmentVariable("TELEGRAM_BOT_TOKEN")
                           ?? _config["TelegramBot:BotToken"];

        // Nếu có cấu hình DemoChatId (để mọi cảnh báo đều bắn về máy điện thoại cầm lên sân khấu demo)
        string? demoChatIdStr = Environment.GetEnvironmentVariable("TELEGRAM_DEMO_CHAT_ID")
                                ?? _config["TelegramBot:DemoChatId"];

        long targetChatId = chatId;
        if (!string.IsNullOrWhiteSpace(demoChatIdStr) && long.TryParse(demoChatIdStr, out long parsedDemoId))
        {
            targetChatId = parsedDemoId;
        }

        if (string.IsNullOrWhiteSpace(botToken) || botToken == "YOUR_TELEGRAM_BOT_TOKEN_HERE")
        {
            _logger.LogWarning("[TELEGRAM SIMULATED] Chưa cấu hình TELEGRAM_BOT_TOKEN. Đã ghi log nội bộ thành công.");
            return;
        }

        try
        {
            string url = $"https://api.telegram.org/bot{botToken.Trim()}/sendMessage";
            var payload = new
            {
                chat_id = targetChatId,
                text = humaneMessage
            };

            var response = await _httpClient.PostAsJsonAsync(url, payload);
            if (response.IsSuccessStatusCode)
            {
                _logger.LogInformation("✅ [TELEGRAM LIVE SENT] Đã bắn tin nhắn thật tới ChatID {TargetChatId} thành công!", targetChatId);
            }
            else
            {
                string errBody = await response.Content.ReadAsStringAsync();
                _logger.LogWarning("⚠️ [TELEGRAM API WARNING] HTTP {StatusCode}: {Error}", response.StatusCode, errBody);
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning("⚠️ [TELEGRAM NETWORK ERROR] Không thể kết nối api.telegram.org: {Message}", ex.Message);
        }
    }
}