using EduGuard.Core.Enums;
using EduGuard.Core.Interfaces;
using Microsoft.AspNetCore.Mvc;


namespace EduGuard.WebAPI.Controllers;


[ApiController]
[Route("api")]
public class EduGuardSystemController : ControllerBase
{
    private readonly IStudentRepository _studentRepo;


    public EduGuardSystemController(IStudentRepository studentRepo)
    {
        _studentRepo = studentRepo;
    }


    [HttpPost("attendance/check-in")]
    public IActionResult CheckIn([FromBody] CheckInRequest request)
    {
        var student = _studentRepo.GetByStudentCode(request.StudentCode);
        if (student == null)
            return NotFound(new { success = false, message = $"Không tìm thấy mã sinh viên {request.StudentCode}" });


        bool ok = student.CheckIn(
            request.SeatCode,
            request.TelegramChatId,
            request.IsLivenessVerified,
            request.MatchedFaceAngle,
            request.BaselinePitchRatio
        );
        if (!ok)
        {
            return BadRequest(new
            {
                success = false,
                message = "Từ chối điểm danh: Phát hiện giả mạo khuôn mặt (Không đạt chỉ số cử động sống Liveness - Nghi vấn ảnh in A4)!",
                data = (object?)null
            });
        }


        _studentRepo.SaveChanges();


        return Ok(new
        {
            success = true,
            message = $"Điểm danh 2FA (Khớp góc {student.MatchedFaceAngle}, hiệu chuẩn BaselinePitch={student.BaselinePitchRatio}) và khóa tọa độ ghế {student.CurrentSeat} thành công cho {student.FullName}.",
            data = new
            {
                studentCode = student.StudentCode,
                fullName = student.FullName,
                seatCode = student.CurrentSeat,
                matchedFaceAngle = student.MatchedFaceAngle,
                baselinePitchRatio = student.BaselinePitchRatio,
                status = student.Status.ToString().ToLower(),
                checkedInAt = student.CheckedInAt
            }
        });
    }


    [HttpGet("dashboard/classroom-state")]
    public IActionResult GetClassroomState()
    {
        var students = _studentRepo.GetAll();
        int total = students.Count;
        int focused = students.Count(s => s.Status == EngagementStatus.Focused || s.Status == EngagementStatus.Relaxing);
        int distracted = students.Count(s => s.Status == EngagementStatus.Distracted);
        int sleeping = students.Count(s => s.Status == EngagementStatus.Sleeping);
        double cei = total > 0 ? Math.Round((double)focused / total * 100.0, 1) : 100.0;


        return Ok(new
        {
            classEngagementIndex = cei,
            totalCheckedIn = total,
            focusedCount = focused,
            distractedCount = distracted,
            sleepingCount = sleeping,
            isBreakTime = _studentRepo.IsBreakTime,
            generatedAt = DateTime.UtcNow,
            seats = students.Select(s => new
            {
                seatCode = s.CurrentSeat,
                studentCode = s.StudentCode,
                fullName = s.FullName,
                className = s.ClassName,
                matchedFaceAngle = s.MatchedFaceAngle,
                baselinePitchRatio = s.BaselinePitchRatio,
                status = s.Status.ToString().ToLower(),
                continuousDurationSeconds = s.ContinuousDurationSeconds,
                totalAlerts = s.TotalSleepAlertsCount,
                colorCode = s.GetColorHex()
            })
        });
    }


    [HttpPost("classroom/break-time")]
    public IActionResult ToggleBreakTime([FromBody] BreakTimeRequest request)
    {
        _studentRepo.SetBreakTime(request.IsBreak);
        return Ok(new
        {
            success = true,
            isBreakTime = _studentRepo.IsBreakTime,
            message = request.IsBreak
                ? "Đã kích hoạt chế độ Giờ giải lao. Hệ thống tạm dừng toàn bộ cảnh báo tự động."
                : "Đã kết thúc Giờ giải lao. Hệ thống quay lại chế độ đo lường nhịp độ lớp học."
        });
    }


    [HttpGet("dashboard/analytics")]
    public IActionResult GetAnalytics()
    {
        var students = _studentRepo.GetAll();
        int totalAlerts = students.Sum(s => s.TotalSleepAlertsCount);


        return Ok(new
        {
            timelineBlocks = new[]
            {
                new { blockTime = "Phút 0-15", ceiPercentage = 96.0 },
                new { blockTime = "Phút 15-30", ceiPercentage = 92.5 },
                new { blockTime = "Phút 30-45", ceiPercentage = 88.0 },
                new { blockTime = "Phút 45-60", ceiPercentage = 85.0 },
                new { blockTime = "Phút 60-75", ceiPercentage = 78.0 },
                new { blockTime = "Phút 75-90", ceiPercentage = 72.0 },
                new { blockTime = "Phút 90-105", ceiPercentage = 54.0 },
                new { blockTime = "Phút 105-120", ceiPercentage = 48.0 }
            },
            isFinal30Minutes = true,
            metricsSummary = new
            {
                peakCeiPercentage = 96.0,
                final30MinAverageCei = 51.0,
                endingCeiPercentage = 48.0,
                dropAmplitudePercentage = 42.0,
                totalTelegramAlertsSent = totalAlerts,
                statisticalNote = $"Số liệu thống kê khung giờ 90–120 phút: Chỉ số tập trung CEI trung bình đạt 51.0% (chạm đáy 48.0% ở phút 105–120, biên độ giảm 42.0% so với đầu ca học; tổng số tin nhắn nhắc nhở riêng đã gửi: {totalAlerts} lượt)."
            }
        });
    }
}


public class CheckInRequest
{
    public string StudentCode { get; set; } = "SV003";
    public string SeatCode { get; set; } = "A2-01";
    public long TelegramChatId { get; set; } = 100003;
    public bool IsLivenessVerified { get; set; } = true;
    public string? MatchedFaceAngle { get; set; } = "TOP_DOWN_PITCH_25_YAW_0";
    public double? BaselinePitchRatio { get; set; } = 0.48;
}


public class BreakTimeRequest
{
    public bool IsBreak { get; set; }
}