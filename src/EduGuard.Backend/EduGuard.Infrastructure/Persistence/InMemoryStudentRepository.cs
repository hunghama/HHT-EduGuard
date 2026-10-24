
using EduGuard.Core.Entities;

using EduGuard.Core.Interfaces;



namespace EduGuard.Infrastructure.Persistence;



public class InMemoryStudentRepository : IStudentRepository

{

    private readonly List<Student> _students;

    public bool IsBreakTime { get; private set; } = false;



    public InMemoryStudentRepository()

    {

        _students = new List<Student>

        {

            new Student(1, "SV001", "Sái Công Phi Hùng", "UDPM2.K16.CĐ", "A1-01", 100001),

            new Student(2, "SV002", "Lưu Thị Kim Liên", "UDPM1-K16-CĐ", "A1-02", 100002),

            new Student(3, "SV003", "Bùi Thị Hương Quỳnh", "UDPM1-K16-CĐ", "A2-01", 100003),

            new Student(4, "SV004", "Nguyễn Quang Huy", "UDPM1-K16-CĐ", "A2-02", 100004),

            new Student(5, "SV005", "Lê Văn An", "UDPM1-K16-CĐ", "A3-01", 100005)

        };

    }



    public IReadOnlyList<Student> GetAll() => _students;



    public Student? GetBySeatCode(string seat)

        => _students.FirstOrDefault(s =>

            s.CurrentSeat.Equals(seat, StringComparison.OrdinalIgnoreCase));



    public Student? GetByStudentCode(string code)

        => _students.FirstOrDefault(s =>

            s.StudentCode.Equals(code, StringComparison.OrdinalIgnoreCase));



    public void SetBreakTime(bool isBreak)

    {

        IsBreakTime = isBreak;

        foreach (var s in _students)

        {

            s.SetBreakTime(isBreak);

        }

    }

}
