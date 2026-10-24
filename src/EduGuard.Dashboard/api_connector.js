// ĐỊA CHỈ BACKEND C# CỦA HÙNG
const BACKEND_BASE_URL = "http://localhost:5160";

/**
 * Hàm lấy trạng thái lớp học thời gian thực cho Dashboard của Liên
 */
async function fetchClassroomState() {
    try {
        const response = await fetch(`${BACKEND_BASE_URL}/api/dashboard/classroom-state`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        console.log("[Dashboard] Dữ liệu lớp học nhận về:", data);
        return data;
    } catch (error) {
        console.error("[Dashboard] Lỗi kết nối tới Backend C#:", error);
        return null;
    }
}
