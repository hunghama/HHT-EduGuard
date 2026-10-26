using System.Net.Http.Json;
using EduGuard.Core.Interfaces;
using Microsoft.Extensions.Logging;


namespace EduGuard.Infrastructure.Telegram;


public class TelegramAlertService : ITelegramAlertService
{
    private readonly ILogger<TelegramAlertService> _logger;
    private static readonly HttpClient _httpClient = new HttpClient { Timeout = TimeSpan.FromSeconds(5) };


    public TelegramAlertService(ILogger<TelegramAlertService> logger)
    {
        _logger = logger;
    }


    public async Task<bool> SendWakeUpMessageAsync(long chatId, string studentName, string seatCode)
    {
        string humaneMessage = $"🌱 [Trợ lý Học vụ HHT EduGuard] Chào {studentName} 👋, hệ thống nhận thấy bạn có vẻ hơi mệt tại vị trí ghế [{seatCode}]. Bạn hãy vươn vai, hít thở sâu hoặc uống chút nước để tỉnh táo tiếp tục đồng hành cùng bài giảng của Thầy nhé!";


        _logger.LogInformation("[TELEGRAM PRIVATE MESSAGE -> ChatID {ChatId}]: {Message}", chatId, humaneMessage);


        string? botToken = Environment.GetEnvironmentVariable("TELEGRAM_BOT_TOKEN");
        string? demoChatIdStr = Environment.GetEnvironmentVariable("TELEGRAM_DEMO_CHAT_ID");


        long targetChatId = chatId;
        if (!string.IsNullOrWhiteSpace(demoChatIdStr) && long.TryParse(demoChatIdStr, out long parsedDemoId))
        {
            targetChatId = parsedDemoId;
        }


        if (string.IsNullOrWhiteSpace(botToken))
        {
            _logger.LogInformation("[TELEGRAM SIMULATED] Chua cau hinh TELEGRAM_BOT_TOKEN, da ghi log local.");
            return false;
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
                _logger.LogInformation("[TELEGRAM LIVE SENT] Da ban tin nhan that toi ChatID {TargetChatId} thanh cong!", targetChatId);
                return true;
            }


            string errBody = await response.Content.ReadAsStringAsync();
            _logger.LogWarning("[TELEGRAM API WARNING] HTTP {StatusCode}: {Error}", response.StatusCode, errBody);
            return false;
        }
        catch (Exception ex)
        {
            _logger.LogWarning("[TELEGRAM NETWORK ERROR] Khong the ket noi api.telegram.org: {Message}", ex.Message);
            return false;
        }
    }
}