
using EduGuard.Core.Interfaces;

using Microsoft.Extensions.Logging;



namespace EduGuard.Infrastructure.Telegram;



public class TelegramAlertService : ITelegramAlertService

{

    private readonly ILogger<TelegramAlertService> _logger;



    public TelegramAlertService(ILogger<TelegramAlertService> logger)

    {

        _logger = logger;

    }



    public Task SendWakeUpMessageAsync(

        long chatId,

        string studentName,

        string seatCode)

    {

        var msg = "[Trợ lý Học vụ HHT EduGuard] "

            + $"Chào {studentName}, hệ thống nhận thấy bạn hơi mệt tại ghế [{seatCode}]. "

            + "Bạn hãy vươn vai hoặc uống chút nước để tỉnh táo tiếp tục bài học nhé!";

        _logger.LogInformation("[TELEGRAM -> {ChatId}]: {Msg}", chatId, msg);

        return Task.CompletedTask;

    }

}
