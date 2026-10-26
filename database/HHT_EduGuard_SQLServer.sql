/* ====================================================================================
   DỰ ÁN: HHT-EDUGUARD (CUỘC THI SÁNG TẠO TRẺ HÀ NỘI 2026)
   ĐƠN VỊ: KHOA CNTT - TRƯỜNG CAO ĐẲNG CÔNG NGHỆ CAO HÀ NỘI (HHT)
   MÔ-ĐUN: CƠ SỞ DỮ LIỆU QUAN HỆ MICROSOFT SQL SERVER (CHUẨN 3NF)
   PHỤ TRÁCH: SÁI CÔNG PHI HÙNG (TECH LEAD - UDPM2.K16.CĐ)
   ==================================================================================== */


IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'HHT_EduGuard_DB')
BEGIN
    CREATE DATABASE [HHT_EduGuard_DB];
END
GO


USE [HHT_EduGuard_DB];
GO


-- 1. BẢNG DANH MỤC SINH VIÊN & MÃ BĂM ĐA TRỤC 2FA (NGANG + TRÊN CAO CHIẾU XUỐNG)
IF OBJECT_ID('dbo.Students', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.Students (
        StudentId INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_Students PRIMARY KEY,
        StudentCode VARCHAR(20) NOT NULL CONSTRAINT UQ_Students_StudentCode UNIQUE,
        FullName NVARCHAR(100) NOT NULL,
        ClassName NVARCHAR(50) NOT NULL,
        DefaultSeatCode VARCHAR(20) NOT NULL,
        TelegramChatId BIGINT NOT NULL,
        FaceFrontal0Hash VARCHAR(128) NULL,     -- Vector băm góc trực diện (Yaw 0°, Pitch 0°)
        FaceTopDownPitchHash VARCHAR(128) NULL, -- Vector băm góc đặt Camera/DroidCam trên cao chiếu xuống (Pitch -15° đến -35°)
        FaceYawLeft30Hash VARCHAR(128) NULL,    -- Vector băm góc nghiêng trái kết hợp góc cao (Yaw -30°, Pitch -25°)
        FaceYawRight30Hash VARCHAR(128) NULL,   -- Vector băm góc nghiêng phải kết hợp góc cao (Yaw +30°, Pitch -25°)
        CreatedAt DATETIME2 NOT NULL CONSTRAINT DF_Students_CreatedAt DEFAULT SYSUTCDATETIME()
    );


    CREATE NONCLUSTERED INDEX IX_Students_DefaultSeatCode ON dbo.Students(DefaultSeatCode);
END
GO


-- 2. BẢNG CA HỌC THỰC HÀNH (CLASS SESSIONS)
IF OBJECT_ID('dbo.ClassSessions', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.ClassSessions (
        SessionId INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_ClassSessions PRIMARY KEY,
        SessionCode VARCHAR(50) NOT NULL CONSTRAINT UQ_ClassSessions_SessionCode UNIQUE,
        RoomName NVARCHAR(100) NOT NULL,
        LecturerName NVARCHAR(100) NOT NULL,
        IsBreakTime BIT NOT NULL CONSTRAINT DF_ClassSessions_IsBreakTime DEFAULT 0,
        CurrentCeiPercentage DECIMAL(5,2) NOT NULL CONSTRAINT DF_ClassSessions_Cei DEFAULT 100.00,
        StartedAt DATETIME2 NOT NULL CONSTRAINT DF_ClassSessions_StartedAt DEFAULT SYSUTCDATETIME(),
        EndedAt DATETIME2 NULL
    );
END
GO


-- 3. BẢNG PHIÊN ĐIỂM DANH KÉP 2FA & HIỆU CHUẨN GÓC ĐẶT CAMERA TỪ TRÊN XUỐNG (SEAT CHECK-INS)
IF OBJECT_ID('dbo.SeatCheckIns', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.SeatCheckIns (
        CheckInId INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_SeatCheckIns PRIMARY KEY,
        SessionId INT NOT NULL CONSTRAINT FK_SeatCheckIns_ClassSessions FOREIGN KEY REFERENCES dbo.ClassSessions(SessionId),
        StudentId INT NOT NULL CONSTRAINT FK_SeatCheckIns_Students FOREIGN KEY REFERENCES dbo.Students(StudentId),
        SeatCode VARCHAR(20) NOT NULL,
        IsLivenessVerified BIT NOT NULL CONSTRAINT DF_SeatCheckIns_Liveness DEFAULT 1,
        LivenessMotionScore DECIMAL(8,5) NOT NULL CONSTRAINT DF_SeatCheckIns_Score DEFAULT 0.00250,
        MatchedFaceAngle VARCHAR(40) NOT NULL CONSTRAINT DF_SeatCheckIns_Angle DEFAULT 'TOP_DOWN_PITCH_25_YAW_0',
        CameraPitchDeg DECIMAL(5,2) NOT NULL CONSTRAINT DF_SeatCheckIns_CamPitch DEFAULT -25.00,
        BaselinePitchRatio DECIMAL(6,3) NOT NULL CONSTRAINT DF_SeatCheckIns_Baseline DEFAULT 0.480,
        CurrentEngagementStatus VARCHAR(20) NOT NULL CONSTRAINT DF_SeatCheckIns_Status DEFAULT 'focused',
        ContinuousDurationSeconds INT NOT NULL CONSTRAINT DF_SeatCheckIns_Duration DEFAULT 0,
        TotalSleepAlertsCount INT NOT NULL CONSTRAINT DF_SeatCheckIns_Alerts DEFAULT 0,
        LastAlertSentAt DATETIME2 NULL,
        CheckedInAt DATETIME2 NOT NULL CONSTRAINT DF_SeatCheckIns_CheckedInAt DEFAULT SYSUTCDATETIME()
    );


    CREATE NONCLUSTERED INDEX IX_SeatCheckIns_Session_Seat ON dbo.SeatCheckIns(SessionId, SeatCode);
END
GO


-- 4. BẢNG NHẬT KÝ CẢNH BÁO TƯ THẾ & TIN NHẮN TELEGRAM NHÂN VĂN (POSE ALERT LOGS)
IF OBJECT_ID('dbo.PoseAlertLogs', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.PoseAlertLogs (
        AlertId BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_PoseAlertLogs PRIMARY KEY,
        SessionId INT NOT NULL CONSTRAINT FK_PoseAlertLogs_ClassSessions FOREIGN KEY REFERENCES dbo.ClassSessions(SessionId),
        StudentCode VARCHAR(20) NOT NULL,
        SeatCode VARCHAR(20) NOT NULL,
        PoseType VARCHAR(20) NOT NULL,
        DurationSeconds INT NOT NULL,
        NormalizedPitchRatio DECIMAL(6,3) NULL,
        RetentionAgainstBaseline DECIMAL(6,3) NULL,
        TriggeredTelegram BIT NOT NULL CONSTRAINT DF_PoseAlertLogs_Triggered DEFAULT 0,
        TelegramMessageSent NVARCHAR(500) NULL,
        LoggedAt DATETIME2 NOT NULL CONSTRAINT DF_PoseAlertLogs_LoggedAt DEFAULT SYSUTCDATETIME()
    );


    CREATE NONCLUSTERED INDEX IX_PoseAlertLogs_Session_LoggedAt ON dbo.PoseAlertLogs(SessionId, LoggedAt DESC);
END
GO


-- 5. NẠP DỮ LIỆU GỐC 5 THÀNH VIÊN THẬT CỦA NHÓM HHT-EDUGUARD (SEED DATA)
IF NOT EXISTS (SELECT 1 FROM dbo.Students WHERE StudentCode = 'SV001')
BEGIN
    INSERT INTO dbo.Students (StudentCode, FullName, ClassName, DefaultSeatCode, TelegramChatId, FaceFrontal0Hash, FaceTopDownPitchHash, FaceYawLeft30Hash, FaceYawRight30Hash)
    VALUES
        ('SV001', N'Sái Công Phi Hùng',   N'UDPM2.K16.CĐ', 'A1-01', 100001, 'SHA256_HUNG_0DEG',  'SHA256_HUNG_TOPDOWN25',  'SHA256_HUNG_L30',  'SHA256_HUNG_R30'),
        ('SV002', N'Lưu Thị Kim Liên',    N'UDPM1-K16-CĐ', 'A1-02', 100002, 'SHA256_LIEN_0DEG',  'SHA256_LIEN_TOPDOWN25',  'SHA256_LIEN_L30',  'SHA256_LIEN_R30'),
        ('SV003', N'Bùi Thị Hương Quỳnh', N'UDPM1-K16-CĐ', 'A2-01', 100003, 'SHA256_QUYNH_0DEG', 'SHA256_QUYNH_TOPDOWN25', 'SHA256_QUYNH_L30', 'SHA256_QUYNH_R30'),
        ('SV004', N'Nguyễn Quang Huy',    N'UDPM1-K16-CĐ', 'A2-02', 100004, 'SHA256_HUY_0DEG',   'SHA256_HUY_TOPDOWN25',   'SHA256_HUY_L30',   'SHA256_HUY_R30'),
        ('SV005', N'Lê Văn An',           N'UDPM1-K16-CĐ', 'A3-01', 100005, 'SHA256_AN_0DEG',    'SHA256_AN_TOPDOWN25',    'SHA256_AN_L30',    'SHA256_AN_R30');
END
GO


-- 6. STORED PROCEDURE TRUY VẤN TRẠNG THÁI LỚP HỌC THỜI GIAN THỰC & TÍNH CHỈ SỐ CEI
CREATE OR ALTER PROCEDURE dbo.sp_GetClassroomRealtimeState
    @SessionId INT
AS
BEGIN
    SET NOCOUNT ON;


    SELECT
        sc.SeatCode,
        s.StudentCode,
        s.FullName,
        s.ClassName,
        sc.MatchedFaceAngle,
        sc.CameraPitchDeg,
        sc.BaselinePitchRatio,
        sc.CurrentEngagementStatus AS Status,
        sc.ContinuousDurationSeconds,
        sc.TotalSleepAlertsCount AS TotalAlerts
    FROM dbo.SeatCheckIns sc
    INNER JOIN dbo.Students s ON sc.StudentId = s.StudentId
    WHERE sc.SessionId = @SessionId
    ORDER BY sc.SeatCode ASC;
END
GO