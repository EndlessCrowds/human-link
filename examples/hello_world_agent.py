import asyncio
import json
import websockets
from aiortc import RTCPeerConnection, RTCSessionDescription

# The Production Infrastructure
SIGNALING_URL = "wss://human-link-signal-production.up.railway.app"
RECEIVER_URL = "https://agentcrowds.com"
SESSION_ID = "discord-launch-001"

async def run_agent():
    # Initialize the Python WebRTC Engine
    pc = RTCPeerConnection()

    # Event Listener: When the video pipe connects
    @pc.on("track")
    def on_track(track):
        print(f"\n🎥 [VISION] Track received: {track.kind}")
        if track.kind == "video":
            print("🟢 LIVE VIDEO FEED CONNECTED.")
            print("   The Agent is now 'seeing' reality.")
            print("   (In a production app, extract frames here and pass to a Vision Model like Claude/Gemini)")

    url = f"{SIGNALING_URL}?session={SESSION_ID}&role=agent"
    print(f"📡 [AGENT] Booting sensory node...")
    
    try:
        async with websockets.connect(url) as ws:
            print(f"✅ [AGENT] Connected to Signaling Switchboard.")
            print(f"\n👉 SEND THIS LINK TO A HUMAN HOST:")
            print(f"{RECEIVER_URL}/link?session={SESSION_ID}&mode=SEE\n")

            async for message in ws:
                data = json.loads(message)
                
                # 1. Receive the Offer from the Next.js Browser
                if data["type"] == "offer":
                    print("🔥 [HANDSHAKE] SDP Offer received. Generating Answer...")
                    offer = RTCSessionDescription(sdp=data["offer"]["sdp"], type=data["offer"]["type"])
                    await pc.setRemoteDescription(offer)
                    
                    # 2. Generate the Answer to open the pipe
                    answer = await pc.createAnswer()
                    await pc.setLocalDescription(answer)
                    
                    # 3. Send the Answer back up through the switchboard
                    await ws.send(json.dumps({
                        "type": "answer",
                        "answer": {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
                    }))
                    print("🚀 [HANDSHAKE] SDP Answer sent! Establishing P2P bridge...")
                
                elif data["type"] == "candidate":
                    print(f"🌐 [NETWORK] Routing candidate received...")

    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_agent())
