namespace EduGuard.Core.Interfaces;

/// <summary>
/// ====================================================================================
/// KIẾN TRÚC CLEAN ARCHITECTURE - TẦNG CORE (ABSTRACTIONS / PORTS)
/// ------------------------------------------------------------------------------------
/// KHÁI NIỆM: "Ổ CẮM" (PORT / ABSTRACTION)
/// 
/// 1. Nguyên lý đảo ngược phụ thuộc (Dependency Inversion Principle - DIP):
///    Tầng Core định nghĩa HỢP ĐỒNG (Contract) mà nó mong muốn thế giới bên ngoài cung cấp.
///    Tầng Core TUYỆT ĐỐI KHÔNG phụ thuộc vào thư viện cụ thể như Telegram.Bot, HTTP Client,
///    hay SDK của bên thứ 3.
/// 
/// 2. Khả năng thay thế linh hoạt (Pluggability):
///    Tương tự như ổ điện trên tường, bất kỳ dịch vụ thông báo nào (Telegram, Zalo, SMS,
///    hoặc Mock test) chỉ cần tuân thủ "chân cắm" của Interface này là có thể hoạt động
///    mà không làm thay đổi 1 dòng code nào trong tầng Core.
/// ====================================================================================
/// </summary>
public interface ITelegramAlertService
{
    /// <summary>
    /// Gửi tin nhắn cảnh báo đánh thức tới học sinh/sinh viên qua Telegram.
    /// </summary>
    /// <param name="chatId">Mã định danh phòng chat Telegram của sinh viên hoặc phụ huynh.</param>
    /// <param name="studentName">Họ tên sinh viên đang ngủ gật.</param>
    /// <param name="seatCode">Vị trí chỗ ngồi của sinh viên trong lớp học.</param>
    /// <returns>Task đại diện cho tác vụ bất đồng bộ.</returns>
    Task SendWakeUpMessageAsync(long chatId, string studentName, string seatCode);
}
