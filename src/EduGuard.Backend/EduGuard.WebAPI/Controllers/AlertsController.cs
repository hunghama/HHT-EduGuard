using EduGuard.Core.Interfaces;
using Microsoft.AspNetCore.Mvc;


namespace EduGuard.WebAPI.Controllers;


[ApiController]
[Route("api/alerts")]
public class AlertsController : ControllerBase
{
    private readonly IStudentRepository _studentRepo;
    private readonly ITelegramAlertService _telegramService;


    public AlertsController(IStudentRepository studentRepo, ITelegramAlertService telegramService)
    {
        _studentRepo = studentRepo;
        _telegramService = telegramService;
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
        bool triggered = student.UpdatePoseState(effectivePose, request.DurationSeconds, _studentRepo.IsBreakTime);
        _studentRepo.SaveChanges();


        if (triggered)
        {
            await _telegramService.SendWakeUpMessageAsync(student.TelegramChatId, student.FullName, student.CurrentSeat);
        }


        string msg = _studentRepo.IsBreakTime
            ? "Đang trong giờ giải lao. Tạm dừng cảnh báo tự động."
            : triggered
                ? "Phát hiện gục đầu vượt 180s. Đã gửi tin nhắn khích lệ riêng qua Telegram!"
                : student.GetCooldownRemainingSeconds() > 0 && student.Status == EduGuard.Core.Enums.EngagementStatus.Sleeping
                    ? $"Đang trong thời gian khóa Cooldown chống spam (còn {student.GetCooldownRemainingSeconds()}s)."
                    : $"Đã cập nhật trạng thái ghế {student.CurrentSeat}: {student.Status.ToString().ToLower()}";


        return Ok(new
        {
            success = true,
            triggeredAlert = triggered,
            seatCode = student.CurrentSeat,
            studentName = student.FullName,
            currentStatus = student.Status.ToString().ToLower(),
            cooldownRemainingSeconds = student.GetCooldownRemainingSeconds(),
            message = msg
        });
    }
}


public class PoseAlertRequest
{
    public string SeatCode { get; set; } = "A2-01";
    public string PoseType { get; set; } = "sleeping";
    public int DurationSeconds { get; set; }
}