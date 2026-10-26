using System.Text.Json;
using EduGuard.Core.Entities;
using EduGuard.Core.Enums;
using EduGuard.Core.Interfaces;


namespace EduGuard.Infrastructure.Persistence;


public class InMemoryStudentRepository : IStudentRepository
{
    private readonly List<Student> _students;
    private readonly string _snapshotFilePath;
    private readonly object _syncLock = new();


    public bool IsBreakTime { get; private set; } = false;


    public InMemoryStudentRepository()
    {
        _snapshotFilePath = Path.Combine(AppContext.BaseDirectory, "eduguard_persistent_state.json");
        _students = new List<Student>
        {
            new Student(1, "SV001", "Sái Công Phi Hùng", "UDPM2.K16.CĐ", "A1-01", 100001),
            new Student(2, "SV002", "Lưu Thị Kim Liên", "UDPM1-K16-CĐ", "A1-02", 100002),
            new Student(3, "SV003", "Bùi Thị Hương Quỳnh", "UDPM1-K16-CĐ", "A2-01", 100003),
            new Student(4, "SV004", "Nguyễn Quang Huy", "UDPM1-K16-CĐ", "A2-02", 100004),
            new Student(5, "SV005", "Lê Văn An", "UDPM1-K16-CĐ", "A3-01", 100005)
        };


        LoadSnapshotIfExists();
        SaveChanges();
    }


    public IReadOnlyList<Student> GetAll() => _students;


    public Student? GetBySeatCode(string seatCode) =>
        _students.FirstOrDefault(s => s.CurrentSeat.Equals(seatCode, StringComparison.OrdinalIgnoreCase));


    public Student? GetByStudentCode(string studentCode) =>
        _students.FirstOrDefault(s => s.StudentCode.Equals(studentCode, StringComparison.OrdinalIgnoreCase));


    public void SetBreakTime(bool isBreak)
    {
        lock (_syncLock)
        {
            IsBreakTime = isBreak;
            foreach (var student in _students)
            {
                student.SetBreakTime(isBreak);
            }
            SaveChangesInternal();
        }
    }


    public void SaveChanges()
    {
        lock (_syncLock)
        {
            SaveChangesInternal();
        }
    }


    private void LoadSnapshotIfExists()
    {
        try
        {
            if (!File.Exists(_snapshotFilePath)) return;
            string json = File.ReadAllText(_snapshotFilePath);
            var dto = JsonSerializer.Deserialize<RepositorySnapshotDto>(json);
            if (dto == null || dto.Students == null) return;


            IsBreakTime = dto.IsBreakTime;
            foreach (var item in dto.Students)
            {
                var student = GetByStudentCode(item.StudentCode);
                if (student != null && Enum.TryParse<EngagementStatus>(item.Status, true, out var parsedStatus))
                {
                    student.RestoreSnapshotState(
                        item.CurrentSeat,
                        item.TelegramChatId,
                        parsedStatus,
                        item.ContinuousDurationSeconds,
                        item.TotalSleepAlertsCount,
                        item.LastAlertSentAt,
                        item.MatchedFaceAngle,
                        item.BaselinePitchRatio
                    );
                }
            }
        }
        catch
        {
            // Giữ nguyên Seed Data mặc định nếu snapshot cũ không tương thích
        }
    }


    private void SaveChangesInternal()
    {
        try
        {
            var dto = new RepositorySnapshotDto
            {
                SavedAtUtc = DateTime.UtcNow,
                SqlServerConnectionConfigured = !string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable("EDUGUARD_SQL_CONNECTION")),
                IsBreakTime = IsBreakTime,
                Students = _students.Select(s => new StudentSnapshotItemDto
                {
                    StudentCode = s.StudentCode,
                    CurrentSeat = s.CurrentSeat,
                    TelegramChatId = s.TelegramChatId,
                    MatchedFaceAngle = s.MatchedFaceAngle,
                    BaselinePitchRatio = s.BaselinePitchRatio,
                    Status = s.Status.ToString(),
                    ContinuousDurationSeconds = s.ContinuousDurationSeconds,
                    TotalSleepAlertsCount = s.TotalSleepAlertsCount,
                    LastAlertSentAt = s.LastAlertSentAt
                }).ToList()
            };


            string json = JsonSerializer.Serialize(dto, new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(_snapshotFilePath, json);
        }
        catch
        {
            // Đảm bảo không làm gián đoạn luồng API chính
        }
    }


    private sealed class RepositorySnapshotDto
    {
        public DateTime SavedAtUtc { get; set; }
        public bool SqlServerConnectionConfigured { get; set; }
        public bool IsBreakTime { get; set; }
        public List<StudentSnapshotItemDto> Students { get; set; } = new();
    }


    private sealed class StudentSnapshotItemDto
    {
        public string StudentCode { get; set; } = string.Empty;
        public string CurrentSeat { get; set; } = string.Empty;
        public long TelegramChatId { get; set; }
        public string MatchedFaceAngle { get; set; } = "TOP_DOWN_PITCH_25_YAW_0";
        public double BaselinePitchRatio { get; set; } = 0.48;
        public string Status { get; set; } = "Focused";
        public int ContinuousDurationSeconds { get; set; }
        public int TotalSleepAlertsCount { get; set; }
        public DateTime? LastAlertSentAt { get; set; }
    }
}