using Microsoft.AspNetCore.SignalR;

namespace EduGuard.WebAPI.Hubs;

public class EduGuardHub : Hub
{
    public override async Task OnConnectedAsync()
    {
        var httpContext = Context.GetHttpContext();
        var classCode = httpContext?.Request.Query["classCode"].ToString();
        if (string.IsNullOrWhiteSpace(classCode)) classCode = "UDPM2";

        await Groups.AddToGroupAsync(Context.ConnectionId, classCode);
        await Clients.Caller.SendAsync("ReceiveConnectionInfo", new
        {
            connectionId = Context.ConnectionId,
            classCode,
            transport = "SignalR WebSocket",
            connectedAt = DateTime.UtcNow
        });

        await base.OnConnectedAsync();
    }

    public async Task JoinClassroomGroup(string classCode)
    {
        if (!string.IsNullOrWhiteSpace(classCode))
            await Groups.AddToGroupAsync(Context.ConnectionId, classCode);
    }
}
