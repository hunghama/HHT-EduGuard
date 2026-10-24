using EduGuard.Core.Interfaces;
using Microsoft.Extensions.Logging;

namespace EduGuard.Infrastructure.Telegram;

/// <summary>
/// ====================================================================================
/// KIẾN TRÚC CLEAN ARCHITECTURE - TẦNG INFRASTRUCTURE (ADAPTERS / DRIVERS)
/// ------------------------------------------------------------------------------------
/// KHÁI NIỆM: "PHÍCH CẮM" (ADAPTER / CONCRETE IMPLEMENTATION)
/// 
/// 1. Hiện thực hóa "ổ cắm" (Implementing Port):
///    Class này cắm đúng chuẩn của interface `ITelegramAlertService` (ổ cắm từ tầng Core).
///    Nơi đây chứa chi tiết công nghệ thực tế: gọi Telegram Bot API, cấu hình Token,
///    HTTP Request, v.v.
/// 
/// 2. Cô lập chi tiết kỹ thuật (Isolation):
///    Tầng Core hoàn toàn không biết class này tồn tại hay dùng thư viện nào.
///    Sau này nếu đổi sang ZaloAlertService hay DiscordAlertService, chúng ta chỉ cần tạo
///    phích cắm mới mà không làm suy chuyển tầng nghiệp vụ.
/// ====================================================================================
/// </summary>
public class TelegramAlertService : ITelegramAlertService
{
    private readonly ILogger<TelegramAlertService> _logger;

    public TelegramAlertService(ILogger<TelegramAlertService> logger)
    {
        _logger = logger;
    }

    /// <summary>
    /// Giả lập việc gửi tin nhắn cảnh báo đánh thức qua Telegram Bot.
    /// In log màu mè và rõ ràng ra Console để dễ dàng theo dõi và kiểm thử.
    /// </summary>
    public Task SendWakeUpMessageAsync(long chatId, string studentName, string seatCode)
    {
        var message = $"[TELEGRAM ALERT] 🚨 Dậy thôi bạn ơi! Sinh viên {studentName} tại vị trí bàn [{seatCode}] đang ngủ gật hơn 3 phút. Hãy tập trung học tập nhé!";

        // Ghi log qua Microsoft.Extensions.Logging
        _logger.LogWarning("Đang gửi tin nhắn Telegram tới ChatId {ChatId}: {Message}", chatId, message);

        // Mô phỏng in trực tiếp ra Console theo yêu cầu
        var originalColor = Console.ForegroundColor;
        Console.ForegroundColor = ConsoleColor.Yellow;
        Console.WriteLine("---------------------------------------------------------------------------------");
        Console.WriteLine($"[TELEGRAM BOT NOTIFICATION SIMULATOR]");
        Console.WriteLine($" -> Người nhận (ChatId) : {chatId}");
        Console.WriteLine($" -> Học sinh           : {studentName}");
        Console.WriteLine($" -> Vị trí chỗ ngồi    : {seatCode}");
        Console.WriteLine($" -> Nội dung tin nhắn   : {message}");
        Console.WriteLine($" -> Trạng thái         : [200 OK] Đã chuyển phát thành công!");
        Console.WriteLine("---------------------------------------------------------------------------------");
        Console.ForegroundColor = originalColor;

        return Task.CompletedTask;
    }
}
