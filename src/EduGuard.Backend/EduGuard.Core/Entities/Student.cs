
using EduGuard.Core.Enums;



namespace EduGuard.Core.Entities;



public class Student

{

    public int Id { get; private set; }

    public string StudentCode { get; private set; }

    public string FullName { get; private set; }

    public string ClassName { get; private set; }

    public string CurrentSeat { get; private set; }

    public long TelegramChatId { get; private set; }

    public EngagementStatus Status { get; private set; }

    public int ContinuousDurationSeconds { get; private set; }

    public DateTime? CheckedInAt { get; private set; }

    public DateTime? LastAlertSentAt { get; private set; }

    public int TotalSleepAlertsCount { get; private set; }



    public Student(

        int id,

        string studentCode,

        string fullName,

        string className,

        string defaultSeat,

        long telegramChatId)

    {

        Id = id;

        StudentCode = studentCode;

        FullName = fullName;

        ClassName = className;

        CurrentSeat = defaultSeat;

        TelegramChatId = telegramChatId;

        Status = EngagementStatus.Focused;

        ContinuousDurationSeconds = 0;

        CheckedInAt = DateTime.UtcNow;

    }



    public bool CheckIn(

        string seatCode,

        long telegramChatId,

        bool isLivenessVerified)

    {

        if (!isLivenessVerified) return false;

        CurrentSeat = seatCode;

        TelegramChatId = telegramChatId;

        Status = EngagementStatus.Focused;

        ContinuousDurationSeconds = 0;

        CheckedInAt = DateTime.UtcNow;

        return true;

    }



    public void SetBreakTime(bool isBreak)

    {

        Status = isBreak

            ? EngagementStatus.Relaxing

            : EngagementStatus.Focused;

        ContinuousDurationSeconds = 0;

    }



    public bool UpdatePoseState(

        string poseType,

        int durationSeconds,

        bool isBreakTime)

    {

        if (isBreakTime)

        {

            Status = EngagementStatus.Relaxing;

            ContinuousDurationSeconds = 0;

            return false;

        }



        ContinuousDurationSeconds = durationSeconds;

        var p = (poseType ?? "focused").Trim().ToLowerInvariant();



        if (p == "focused" || p == "normal")

        {

            Status = EngagementStatus.Focused;

            return false;

        }



        if (p == "distracted")

        {

            Status = durationSeconds >= 30

                ? EngagementStatus.Distracted

                : EngagementStatus.Focused;

            return false;

        }



        if (p == "sleeping" || p == "sleep")

        {

            if (durationSeconds >= 180)

            {

                Status = EngagementStatus.Sleeping;

                if (GetCooldownRemainingSeconds() == 0)

                {

                    LastAlertSentAt = DateTime.UtcNow;

                    TotalSleepAlertsCount++;

                    return true;

                }

            }

            else

            {

                Status = EngagementStatus.Distracted;

            }

        }

        return false;

    }



    public int GetCooldownRemainingSeconds()

    {

        if (LastAlertSentAt == null) return 0;

        var diff = DateTime.UtcNow - LastAlertSentAt.Value;

        var sec = (int)diff.TotalSeconds;

        return sec >= 300 ? 0 : (300 - sec);

    }



    public string GetColorHex() => Status switch

    {

        EngagementStatus.Focused => "#198754",

        EngagementStatus.Distracted => "#ffc107",

        EngagementStatus.Sleeping => "#dc3545",

        EngagementStatus.Relaxing => "#0dcaf0",

        _ => "#6c757d"

    };

}
