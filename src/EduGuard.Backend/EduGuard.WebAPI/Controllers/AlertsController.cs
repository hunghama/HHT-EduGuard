using EduGuard.Core.Entities;
using EduGuard.Core.Interfaces;
using Microsoft.AspNetCore.Mvc;

namespace EduGuard.WebAPI.Controllers;

/// <summary>
/// ====================================================================================
/// KIẾN TRÚC CLEAN ARCHITECTURE - TẦNG PRESENTATION / WEB API (DRIVING ADAPTER)
/// ------------------------------------------------------------------------------------
/// KHÁI NIỆM: ĐIỀU PHỐI LUỒNG NGHIỆP VỤ (ORCHESTRATION)
/// 
/// 1. Vai trò của Controller:
///    Controller là cổng đón nhận HTTP request từ bên ngoài (Client UI hoặc AI Camera Model).
///    Controller KHÔNG chứa quy tắc nghiệp vụ (Business Rules). 
///    Thay vào đó, nó đóng vai trò "nhạc trưởng":
///      - Nhận dữ liệu (DTO Request).
///      - Lấy đối tượng Domain ("đối tượng có não" - Student) và trao quyền cho nó tự quyết định.
///      - Nếu điều kiện nghiệp vụ thỏa mãn, gọi dịch vụ phụ trợ thông qua "ổ cắm" (ITelegramAlertService).
/// 
/// 2. Dependency Injection:
///    Controller chỉ biết tới `ITelegramAlertService` (ổ cắm ở tầng Core), hoàn toàn không
///    quan tâm bên dưới là Telegram thật, Telegram giả lập hay SMS.
/// ====================================================================================
/// </summary>
[ApiController]
[Route("api/[controller]")]
public class AlertsController : ControllerBase
{
    private readonly ITelegramAlertService _telegramAlertService;
    private readonly ILogger<AlertsController> _logger;

    // Giả lập danh sách sinh viên trong lớp học gắn với vị trí bàn ghế
    private static readonly List<Student> MockStudents = new()
    {
        new Student(Guid.NewGuid(), "SV2026-001", "Nguyễn Văn An", "A1-01", 123456789),
        new Student(Guid.NewGuid(), "SV2026-002", "Trần Thị Bình", "A1-02", 987654321),
        new Student(Guid.NewGuid(), "SV2026-003", "Lê Hoàng Cường", "B2-05", 555666777)
    };

    public AlertsController(ITelegramAlertService telegramAlertService, ILogger<AlertsController> logger)
    {
        _telegramAlertService = telegramAlertService;
        _logger = logger;
    }

    /// <summary>
    /// Model nhận dữ liệu từ AI Camera truyền lên
    /// </summary>
    public record SleepAlertRequest(string SeatCode, int DurationSeconds);

    /// <summary>
    /// API tiếp nhận sự kiện phát hiện tư thế ngủ gật từ module AI
    /// POST /api/alerts/sleep
    /// </summary>
    [HttpPost("sleep")]
    public async Task<IActionResult> RecordSleepAlert([FromBody] SleepAlertRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.SeatCode))
        {
            return BadRequest(new { Message = "Vị trí chỗ ngồi (SeatCode) không được để trống." });
        }

        _logger.LogInformation("Nhận tín hiệu từ AI: Chỗ ngồi {SeatCode}, Thời gian ngủ: {Duration}s", 
            request.SeatCode, request.DurationSeconds);

        // 1. Tìm sinh viên tương ứng với chỗ ngồi (mô phỏng truy xuất DB / Repository)
        var student = MockStudents.FirstOrDefault(s => 
            s.CurrentSeat.Equals(request.SeatCode, StringComparison.OrdinalIgnoreCase));

        if (student == null)
        {
            // Nếu là chỗ ngồi mới chưa cấu hình sẵn, tạo đối tượng tạm thời để minh họa
            student = new Student(
                Guid.NewGuid(), 
                "SV-GUEST", 
                $"Sinh viên bàn {request.SeatCode}", 
                request.SeatCode, 
                1122334455);
        }

        // 2. Trao quyền cho "ĐỐI TƯỢNG CÓ NÃO" xử lý nghiệp vụ:
        //    Entity tự thẩm định xem thời gian ngủ có vượt ngưỡng 180s (3 phút) hay không.
        bool shouldAlert = student.RecordSleepDuration(request.DurationSeconds);

        // 3. Nếu đối tượng quyết định cần cảnh báo -> Kích hoạt qua "Ổ cắm"
        if (shouldAlert)
        {
            await _telegramAlertService.SendWakeUpMessageAsync(
                student.TelegramChatId, 
                student.FullName, 
                student.CurrentSeat);

            return Ok(new
            {
                Success = true,
                TriggeredAlert = true,
                Message = $"Đã phát hiện sinh viên {student.FullName} ngủ gật {request.DurationSeconds}s (vượt ngưỡng 180s) và đã kích hoạt báo thức Telegram!",
                Student = new
                {
                    student.StudentCode,
                    student.FullName,
                    student.CurrentSeat,
                    student.IsSleeping
                }
            });
        }

        // 4. Nếu chưa vượt ngưỡng cảnh báo (ngủ gật dưới 180s)
        return Ok(new
        {
            Success = true,
            TriggeredAlert = false,
            Message = $"Sinh viên {student.FullName} tại bàn {student.CurrentSeat} mới chợp mắt {request.DurationSeconds}s (chưa đủ 180s để kích hoạt báo động).",
            Student = new
            {
                student.StudentCode,
                student.FullName,
                student.CurrentSeat,
                student.IsSleeping
            }
        });
    }
}
