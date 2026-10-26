namespace EduGuard.Core.Interfaces;


public interface ITelegramAlertService
{
    Task<bool> SendWakeUpMessageAsync(long chatId, string studentName, string seatCode);
}