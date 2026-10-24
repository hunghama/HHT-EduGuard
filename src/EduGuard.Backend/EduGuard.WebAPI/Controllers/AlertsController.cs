
using EduGuard.Core.Enums;

using EduGuard.Core.Interfaces;

using Microsoft.AspNetCore.Mvc;



namespace EduGuard.WebAPI.Controllers;



[ApiController]

[Route("api/alerts")]

public class AlertsController : ControllerBase

{

    private readonly IStudentRepository _repo;

    private readonly ITelegramAlertService _tg;



    public AlertsController(

        IStudentRepository repo,

        ITelegramAlertService tg)

    {

        _repo = repo;

        _tg = tg;

    }



    [HttpPost("pose")]

    [HttpPost("sleep")]

    public async Task<IActionResult> ProcessPose([FromBody] PoseAlertRequest req)

    {

        var st = _repo.GetBySeatCode(req.SeatCode);

        if (st == null)

        {

            return NotFound(new

            {

                success = false,

                message = "Không tìm thấy ghế " + req.SeatCode

            });

        }



        var pose = string.IsNullOrWhiteSpace(req.PoseType) ? "sleeping" : req.PoseType;

        bool trig = st.UpdatePoseState(pose, req.DurationSeconds, _repo.IsBreakTime);



        if (trig)

        {

            await _tg.SendWakeUpMessageAsync(st.TelegramChatId, st.FullName, st.CurrentSeat);

        }



        int cd = st.GetCooldownRemainingSeconds();

        string msg = _repo.IsBreakTime

            ? "Đang giờ giải lao, tạm dừng cảnh báo."

            : trig

                ? "Đã gửi tin nhắn khích lệ Telegram!"

                : (cd > 0 && st.Status == EngagementStatus.Sleeping)

                    ? $"Đang khóa Cooldown ({cd}s)."

                    : "Đã cập nhật trạng thái ghế.";



        return Ok(new

        {

            success = true,

            triggeredAlert = trig,

            seatCode = st.CurrentSeat,

            studentName = st.FullName,

            currentStatus = st.Status.ToString().ToLower(),

            cooldownRemainingSeconds = cd,

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
