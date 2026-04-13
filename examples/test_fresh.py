import asyncio
import json
import websockets
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer

SIGNALING_URL = "wss://human-link-signal-production.up.railway.app"
RECEIVER_URL = "https://agent-crowds.vercel.app"
SESSION_ID = "smartphone-test-002"

ICE_CONFIG = RTCConfiguration(iceServers=[
    RTCIceServer(urls="stun:stun.l.google.com:19302"),
    RTCIceServer(urls="stun:stun1.l.google.com:19302"),
    RTCIceServer(
        urls="turn:a.relay.metered.ca:80",
        username="e8dd65d92f6e885be7826971",
        credential="5B1dU+hSVSJINPrB"
    ),
    RTCIceServer(
        urls="turn:a.relay.metered.ca:443",
        username="e8dd65d92f6e885be7826971",
        credential="5B1dU+hSVSJINPrB"
    ),
    RTCIceServer(
        urls="turn:a.relay.metered.ca:443?transport=tcp",
        username="e8dd65d92f6e885be7826971",
        credential="5B1dU+hSVSJINPrB"
    ),
])

async def run_agent():
    pc = RTCPeerConnection(configuration=ICE_CONFIG)

    @pc.on("track")
    def on_track(track):
        print(f"[VISION] Track received: {track.kind}", flush=True)
        if track.kind == "video":
            print("LIVE VIDEO FEED CONNECTED.", flush=True)

    @pc.on("connectionstatechange")
    async def on_state():
        print(f"[STATE] Connection: {pc.connectionState}", flush=True)

    @pc.on("iceconnectionstatechange")
    async def on_ice_state():
        print(f"[ICE] State: {pc.iceConnectionState}", flush=True)

    url = f"{SIGNALING_URL}?session={SESSION_ID}&role=agent"
    print("[AGENT] Booting...", flush=True)

    try:
        async with websockets.connect(url) as ws:
            print("[AGENT] Connected to signaling.", flush=True)
            print(f"\nOPEN THIS LINK:", flush=True)
            print(f"{RECEIVER_URL}/link?session={SESSION_ID}&mode=SEE\n", flush=True)

            async for message in ws:
                data = json.loads(message)

                if data["type"] == "offer":
                    print("[HANDSHAKE] SDP Offer received.", flush=True)
                    offer = RTCSessionDescription(sdp=data["offer"]["sdp"], type=data["offer"]["type"])
                    await pc.setRemoteDescription(offer)

                    answer = await pc.createAnswer()
                    await pc.setLocalDescription(answer)

                    await ws.send(json.dumps({
                        "type": "answer",
                        "answer": {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
                    }))
                    print("[HANDSHAKE] SDP Answer sent.", flush=True)

                elif data["type"] == "candidate":
                    pass

    except websockets.exceptions.ConnectionClosed:
        print("[AGENT] Signaling closed.", flush=True)
    except Exception as e:
        print(f"Error: {e}", flush=True)

    print("[AGENT] Holding P2P connection...", flush=True)
    try:
        while pc.connectionState in ("connecting", "connected", "new"):
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        await pc.close()
        print(f"[AGENT] Done. Final: {pc.connectionState}", flush=True)

if __name__ == "__main__":
    asyncio.run(run_agent())
