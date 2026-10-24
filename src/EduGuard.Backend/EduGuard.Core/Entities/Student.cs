namespace EduGuard.Core.Entities;

/// <summary>
/// ====================================================================================
/// KIẾN TRÚC CLEAN ARCHITECTURE - TẦNG CORE (DOMAIN ENTITY)
/// ------------------------------------------------------------------------------------
/// KHÁI NIỆM: "ĐỐI TƯỢNG CÓ NÃO" (RICH DOMAIN MODEL)
/// 
/// 1. Tính đóng gói (Encapsulation): 
///    Mọi thuộc tính đều có `private set`. Thế giới bên ngoài không được phép tự ý thay đổi
///    trạng thái của sinh viên (như gán `student.IsSleeping = true` một cách tùy tiện).
/// 
/// 2. Nghiệp vụ tập trung (Core Business Rules):
///    Entity không phải là túi chứa dữ liệu rỗng (Anemic Domain Model) mà tự nó quản lý
///    quy tắc nghiệp vụ của chính mình. Hành vi `RecordSleepDuration(int seconds)` là logic
///    nghiệp vụ: chỉ khi ngủ gật liên tục từ 180 giây (3 phút) trở lên thì mới xác nhận
///    trạng thái ngủ gật và kích hoạt cờ cảnh báo.
/// ====================================================================================
/// </summary>
public class Student
{
    public Guid Id { get; private set; }
    public string StudentCode { get; private set; }
    public string FullName { get; private set; }
    public string CurrentSeat { get; private set; }
    public long TelegramChatId { get; private set; }
    public bool IsSleeping { get; private set; }

    // Constructor đảm bảo tính hợp lệ khi khởi tạo đối tượng (Invariants)
    public Student(Guid id, string studentCode, string fullName, string currentSeat, long telegramChatId)
    {
        if (string.IsNullOrWhiteSpace(studentCode))
            throw new ArgumentException("Mã sinh viên không được để trống.", nameof(studentCode));

        if (string.IsNullOrWhiteSpace(fullName))
            throw new ArgumentException("Họ tên sinh viên không được để trống.", nameof(fullName));

        Id = id;
        StudentCode = studentCode;
        FullName = fullName;
        CurrentSeat = currentSeat ?? string.Empty;
        TelegramChatId = telegramChatId;
        IsSleeping = false;
    }

    /// <summary>
    /// Hàm nghiệp vụ cốt lõi: Ghi nhận thời lượng cúi gục/ngủ gật (tính bằng giây).
    /// </summary>
    /// <param name="seconds">Số giây hệ thống AI ghi nhận trạng thái ngủ gật.</param>
    /// <returns>True nếu vượt ngưỡng cảnh báo (>= 180s), ngược lại False.</returns>
    public bool RecordSleepDuration(int seconds)
    {
        if (seconds < 0)
        {
            throw new ArgumentOutOfRangeException(nameof(seconds), "Thời gian ngủ không thể là số âm.");
        }

        // Quy tắc nghiệp vụ cốt lõi: Ngủ liên tục từ 180s (3 phút) trở lên mới kích hoạt báo thức
        const int SleepAlertThresholdSeconds = 180;

        if (seconds >= SleepAlertThresholdSeconds)
        {
            IsSleeping = true;
            return true;
        }

        // Nếu dưới ngưỡng thì chưa kết luận ngủ gật kéo dài
        IsSleeping = false;
        return false;
    }

    /// <summary>
    /// Đánh thức sinh viên và reset trạng thái về tỉnh táo
    /// </summary>
    public void WakeUp()
    {
        IsSleeping = false;
    }
}
