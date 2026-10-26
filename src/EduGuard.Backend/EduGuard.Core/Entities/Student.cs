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
    public string MatchedFaceAngle { get; private set; }
    public double BaselinePitchRatio { get; private set; }
    public EngagementStatus Status { get; private set; }
    public int ContinuousDurationSeconds { get; private set; }
    public DateTime? CheckedInAt { get; private set; }
    public DateTime? LastAlertSentAt { get; private set; }
    public int TotalSleepAlertsCount { get; private set; }


    public Student(int id, string studentCode, string fullName, string className, string defaultSeat, long telegramChatId)
    {
        Id = id;
        StudentCode = studentCode;
        FullName = fullName;
        ClassName = className;
        CurrentSeat = defaultSeat;
        TelegramChatId = telegramChatId;
        MatchedFaceAngle = "TOP_DOWN_PITCH_25_YAW_0";
        BaselinePitchRatio = 0.48;
        Status = EngagementStatus.Focused;
        ContinuousDurationSeconds = 0;
        CheckedInAt = DateTime.UtcNow;
    }


    public bool CheckIn(string seatCode, long telegramChatId, bool isLivenessVerified, string? matchedAngle = null, double? baselinePitchRatio = null)
    {
        if (!isLivenessVerified) return false;
        CurrentSeat = seatCode;
        TelegramChatId = telegramChatId;
        if (!string.IsNullOrWhiteSpace(matchedAngle))
        {
            MatchedFaceAngle = matchedAngle;
        }
        if (baselinePitchRatio.HasValue && baselinePitchRatio.Value > 0.1)
        {
            BaselinePitchRatio = Math.Round(baselinePitchRatio.Value, 3);
        }
        Status = EngagementStatus.Focused;
        ContinuousDurationSeconds = 0;
        CheckedInAt = DateTime.UtcNow;
        return true;
    }


    public void SetBreakTime(bool isBreak)
    {
        Status = isBreak ? EngagementStatus.Relaxing : EngagementStatus.Focused;
        ContinuousDurationSeconds = 0;
    }


    public void RestoreSnapshotState(string currentSeat, long telegramChatId, EngagementStatus status, int continuousSeconds, int totalAlerts, DateTime? lastAlertSentAt, string? matchedAngle, double baselinePitchRatio)
    {
        if (!string.IsNullOrWhiteSpace(currentSeat)) CurrentSeat = currentSeat;
        if (telegramChatId > 0) TelegramChatId = telegramChatId;
        if (!string.IsNullOrWhiteSpace(matchedAngle)) MatchedFaceAngle = matchedAngle;
        if (baselinePitchRatio > 0.1) BaselinePitchRatio = baselinePitchRatio;
        Status = status;
        ContinuousDurationSeconds = continuousSeconds;
        TotalSleepAlertsCount = totalAlerts;
        LastAlertSentAt = lastAlertSentAt;
    }


    public bool UpdatePoseState(string poseType, int durationSeconds, bool isClassroomBreakTime)
    {
        if (isClassroomBreakTime)
        {
            Status = EngagementStatus.Relaxing;
            ContinuousDurationSeconds = 0;
            return false;
        }


        ContinuousDurationSeconds = durationSeconds;
        var normalized = (poseType ?? "focused").Trim().ToLowerInvariant();


        if (normalized == "focused" || normalized == "normal")
        {
            Status = EngagementStatus.Focused;
            return false;
        }


        if (normalized == "distracted")
        {
            Status = durationSeconds >= 30 ? EngagementStatus.Distracted : EngagementStatus.Focused;
            return false;
        }


        if (normalized == "sleeping" || normalized == "sleep")
        {
            if (durationSeconds >= 180)
            {
                Status = EngagementStatus.Sleeping;
                if (LastAlertSentAt == null || (DateTime.UtcNow - LastAlertSentAt.Value).TotalSeconds >= 300)
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
        var elapsed = (int)(DateTime.UtcNow - LastAlertSentAt.Value).TotalSeconds;
        return elapsed >= 300 ? 0 : (300 - elapsed);
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