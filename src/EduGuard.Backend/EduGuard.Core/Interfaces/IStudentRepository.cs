
using EduGuard.Core.Entities;



namespace EduGuard.Core.Interfaces;



public interface IStudentRepository

{

    IReadOnlyList<Student> GetAll();

    Student? GetBySeatCode(string seatCode);

    Student? GetByStudentCode(string code);

    bool IsBreakTime { get; }

    void SetBreakTime(bool isBreak);

}
