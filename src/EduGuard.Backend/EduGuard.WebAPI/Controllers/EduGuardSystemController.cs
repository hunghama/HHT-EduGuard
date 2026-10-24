
using EduGuard.Core.Enums;

using EduGuard.Core.Interfaces;

using Microsoft.AspNetCore.Mvc;



namespace EduGuard.WebAPI.Controllers;



[ApiController]

[Route("api")]

public class EduGuardSystemController : ControllerBase

{

    private readonly IStudentRepository _repo;



    public EduGuardSystemController(IStudentRepository repo)

    {

        _repo = repo;

    }



    [HttpPost("attendance/check-in")]

    public IActionResult CheckIn([FromBody] CheckInRequest req)

    {

        var st = _repo.GetByStudentCode(req.StudentCode);

        if (st == null)

        {

            return NotFound(new

            {

                success = false,

                message = "Không tìm thấy SV " + req.StudentCode

            });

        }



        bool ok = st.CheckIn(req.SeatCode, req.TelegramChatId, req.IsLivenessVerified);

        if (!ok)

        {

            return BadRequest(new

            {

                success = false,

                message = "Từ chối: Phát hiện ảnh A4 (Liveness Failed)!",

                data = (object?)null

            });

        }



        return Ok(new

        {

            success = true,

            message = "Điểm danh 2FA thành công!",

            data = new

            {

                studentCode = st.StudentCode,

                fullName = st.FullName,

                seatCode = st.CurrentSeat,

                status = st.Status.ToString().ToLower(),

                checkedInAt = st.CheckedInAt

            }

        });

    }



    [HttpGet("dashboard/classroom-state")]

    public IActionResult GetClassroomState()

    {

        var list = _repo.GetAll();

        int total = list.Count;

        int foc = list.Count(s => s.Status == EngagementStatus.Focused || s.Status == EngagementStatus.Relaxing);

        int dis = list.Count(s => s.Status == EngagementStatus.Distracted);

        int slp = list.Count(s => s.Status == EngagementStatus.Sleeping);

        double cei = total > 0 ? Math.Round((double)foc / total * 100, 1) : 100.0;



        return Ok(new

        {

            classEngagementIndex = cei,

            totalCheckedIn = total,

            focusedCount = foc,

            distractedCount = dis,

            sleepingCount = slp,

            isBreakTime = _repo.IsBreakTime,

            generatedAt = DateTime.UtcNow,

            seats = list.Select(s => new

            {

                seatCode = s.CurrentSeat,

                studentCode = s.StudentCode,

                fullName = s.FullName,

                className = s.ClassName,

                status = s.Status.ToString().ToLower(),

                continuousDurationSeconds = s.ContinuousDurationSeconds,

                totalAlerts = s.TotalSleepAlertsCount,

                colorCode = s.GetColorHex()

            })

        });

    }



    [HttpPost("classroom/break-time")]

    public IActionResult ToggleBreak([FromBody] BreakTimeRequest req)

    {

        _repo.SetBreakTime(req.IsBreak);

        return Ok(new

        {

            success = true,

            isBreakTime = _repo.IsBreakTime,

            message = req.IsBreak ? "Đã bật chế độ Giờ giải lao." : "Đã kết thúc Giờ giải lao."

        });

    }



    [HttpGet("dashboard/analytics")]

    public IActionResult GetAnalytics()

    {

        return Ok(new

        {

            timelineBlocks = new[]

            {

                new { blockTime = "0-15p", ceiPercentage = 96.0 },

                new { blockTime = "15-30p", ceiPercentage = 92.5 },

                new { blockTime = "30-45p", ceiPercentage = 88.0 },

                new { blockTime = "45-60p", ceiPercentage = 85.0 },

                new { blockTime = "60-75p", ceiPercentage = 78.0 },

                new { blockTime = "75-90p", ceiPercentage = 72.0 },

                new { blockTime = "90-105p", ceiPercentage = 54.0 },

                new { blockTime = "105-120p", ceiPercentage = 48.0 }

            },

            isFinal30Minutes = true,

            pedagogicalAlert = new

            {

                isDropDetected = true,

                dropRatePercentage = 42.0,

                recommendation = "Cảnh báo: Tập trung giảm còn 48% ở 30 phút cuối. Khuyến nghị chuyển sang thảo luận nhóm hoặc mini-game."

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

}



public class BreakTimeRequest

{

    public bool IsBreak { get; set; }

}
