using EduGuard.Core.Interfaces;
using Microsoft.AspNetCore.Mvc;

namespace EduGuard.WebAPI.Controllers;

[ApiController]
[Route("api/alerts")]
public class AlertsController : ControllerBase
{
    private readonly IStudentRepository _studentRepo;
    private readonly ITelegramAlertService _telegramService;
    private readonly IWebHostEnvironment _env;

    public AlertsController(
        IStudentRepository studentRepo,
        ITelegramAlertService telegramService,
        IWebHostEnvironment env)
    {
        _studentRepo = studentRepo;
        _telegramService = telegramService;
        _env = env;
    }

    [HttpPost("pose")]
    [HttpPost("sleep")]
    public async Task<IActionResult> ProcessPoseAlert([FromBody] PoseAlertRequest request)
    {
        var student = _studentRepo.GetBySeatCode(request.SeatCode);
        if (student == null)
        {
            return NotFound(new { success = false, message = $"Không tìm thấy sinh viên tại ghế {request.SeatCode}" });
        }

        string effectivePose = string.IsNullOrWhiteSpace(request.PoseType) ? "sleeping" : request.PoseType;
        bool shouldTrigger = student.UpdatePoseState(effectivePose, request.DurationSeconds, _studentRepo.IsBreakTime);
        bool delivered = false;

        if (shouldTrigger)
        {
            delivered = await _telegramService.SendWakeUpMessageAsync(student.TelegramChatId, student.FullName, student.CurrentSeat);
            if (delivered)
            {
                student.RecordConfirmedAlertDelivery();
            }
        }

        _studentRepo.SaveChanges();

        string msg = _studentRepo.IsBreakTime
            ? "Đang trong giờ giải lao. Tạm dừng cảnh báo tự động."
            : shouldTrigger
                ? (delivered
                    ? "Phát hiện gục đầu vượt 180s. Đã gửi tin nhắn khích lệ riêng qua Telegram!"
                    : "Phát hiện gục đầu vượt 180s. Đã ghi nhận cảnh báo tại hệ thống (chế độ Local Log).")
                : student.GetCooldownRemainingSeconds() > 0 && student.Status == EduGuard.Core.Enums.EngagementStatus.Sleeping
                    ? $"Đang trong thời gian khóa Cooldown chống spam (còn {student.GetCooldownRemainingSeconds()}s)."
                    : $"Đã cập nhật trạng thái ghế {student.CurrentSeat}: {student.Status.ToString().ToLower()}";

        return Ok(new
        {
            success = true,
            triggeredAlert = shouldTrigger,
            telegramDelivered = delivered,
            seatCode = student.CurrentSeat,
            studentName = student.FullName,
            currentStatus = student.Status.ToString().ToLower(),
            cooldownRemainingSeconds = student.GetCooldownRemainingSeconds(),
            message = msg
        });
    }

    [HttpPost("test-telegram")]
    public async Task<IActionResult> TestLiveTelegram([FromBody] TestTelegramRequest request)
    {
        if (!_env.IsDevelopment())
        {
            return Forbid();
        }

        var student = _studentRepo.GetBySeatCode(request.SeatCode);
        if (student == null)
        {
            return NotFound(new { success = false, message = $"Không tìm thấy sinh viên tại ghế {request.SeatCode}" });
        }

        if (student.GetCooldownRemainingSeconds() > 0)
        {
            return StatusCode(429, new
            {
                success = false,
                telegramDelivered = false,
                seatCode = student.CurrentSeat,
                cooldownRemainingSeconds = student.GetCooldownRemainingSeconds(),
                message = $"Đang trong thời gian Cooldown chống spam (còn {student.GetCooldownRemainingSeconds()}s)."
            });
        }

        bool delivered = await _telegramService.SendWakeUpMessageAsync(student.TelegramChatId, student.FullName, student.CurrentSeat);
        if (delivered)
        {
            student.RecordCooldownOnly();
            _studentRepo.SaveChanges();
        }

        return Ok(new
        {
            success = delivered,
            telegramDelivered = delivered,
            seatCode = student.CurrentSeat,
            studentName = student.FullName,
            message = delivered
                ? $"ĐÃ BẮN TIN NHẮN TELEGRAM THẬT TỚI ĐIỆN THOẠI ({student.FullName} - Ghế {student.CurrentSeat}) THÀNH CÔNG!"
                : "Chưa gửi được tin nhắn thật. Hãy kiểm tra biến môi trường TELEGRAM_BOT_TOKEN và TELEGRAM_DEMO_CHAT_ID."
        });
    }
}

public class PoseAlertRequest
{
    public string SeatCode { get; set; } = "A2-01";
    public string PoseType { get; set; } = "sleeping";
    public int DurationSeconds { get; set; } = 0;
}

public class TestTelegramRequest
{
    public string SeatCode { get; set; } = "A1-01";
}