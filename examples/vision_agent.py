import asyncio
import json
import websockets
import time
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer

# The Production Infrastructure
SIGNALING_URL = "wss://human-link-signal-production.up.railway.app"
RECEIVER_URL = "https://agent-crowds.vercel.app"
SESSION_ID = "vision-test-001"

# Full ICE config with TURN relays for 5G/carrier-NAT compatibility
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


async def consume_video(track):
    print("👁️ [VISION CORTEX] Frame extraction loop started...", flush=True)
    frame_count = 0
    last_process_time = time.time()

    while True:
        try:
            # CRITICAL: We must consume every frame to prevent the WebRTC buffer from exploding
            frame = await track.recv()

            # Process 1 frame every 5 seconds to pace the LLM API
            current_time = time.time()
            if current_time - last_process_time >= 5.0:
                print(f"📸 [VISION] Extracting frame {frame_count} at {frame.time:.2f}s", flush=True)

                # Convert raw WebRTC (PyAV) frame to a Pillow Image
                img = frame.to_image()

                # Save it to disk as proof of sight
                file_name = "proof_of_sight.jpg"
                img.save(file_name)
                print(f"✅ [VISION] Frame saved to disk: {file_name}", flush=True)
                print(f"   Resolution: {img.size[0]}x{img.size[1]}", flush=True)
                print(f"   (This frame is ready to be base64 encoded and sent to an LLM)\n", flush=True)

                last_process_time = current_time
                frame_count += 1

        except Exception as e:
            print(f"❌ [VISION] Track ended or error: {e}", flush=True)
            break


async def run_agent():
    pc = RTCPeerConnection(configuration=ICE_CONFIG)

    @pc.on("track")
    def on_track(track):
        print(f"\n🎥 [TRACK] Track received: {track.kind}", flush=True)
        if track.kind == "video":
            print("🟢 LIVE VIDEO FEED CONNECTED.", flush=True)
            # Fire and forget the extraction loop
            asyncio.create_task(consume_video(track))

    @pc.on("connectionstatechange")
    async def on_state():
        print(f"🔄 [STATE] Connection: {pc.connectionState}", flush=True)

    @pc.on("iceconnectionstatechange")
    async def on_ice_state():
        print(f"🧊 [ICE] State: {pc.iceConnectionState}", flush=True)

    url = f"{SIGNALING_URL}?session={SESSION_ID}&role=agent"
    print(f"📡 [AGENT] Booting sensory node...", flush=True)

    try:
        async with websockets.connect(url) as ws:
            print(f"✅ [AGENT] Connected to Signaling Switchboard.", flush=True)
            print(f"\n👉 SEND THIS LINK TO A HUMAN HOST:", flush=True)
            print(f"{RECEIVER_URL}/link?session={SESSION_ID}&mode=SEE\n", flush=True)

            async for message in ws:
                data = json.loads(message)

                if data.get("type") == "offer":
                    print("🔥 [HANDSHAKE] SDP Offer received. Generating Answer...", flush=True)
                    offer = RTCSessionDescription(sdp=data["offer"]["sdp"], type=data["offer"]["type"])
                    await pc.setRemoteDescription(offer)

                    answer = await pc.createAnswer()
                    await pc.setLocalDescription(answer)

                    await ws.send(json.dumps({
                        "type": "answer",
                        "answer": {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
                    }))
                    print("🚀 [HANDSHAKE] SDP Answer sent! Establishing P2P bridge...", flush=True)

                elif data.get("type") == "candidate":
                    pass  # aiortc handles ICE internally

    except websockets.exceptions.ConnectionClosed:
        print("📡 [AGENT] Signaling closed.", flush=True)
    except Exception as e:
        print(f"❌ Connection failed: {e}", flush=True)

    # Hold the P2P connection alive for frame extraction
    print("🔒 [AGENT] Holding P2P connection for vision extraction...", flush=True)
    try:
        while pc.connectionState in ("connecting", "connected", "new"):
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        await pc.close()
        print(f"🏁 [AGENT] Done. Final state: {pc.connectionState}", flush=True)


if __name__ == "__main__":
    asyncio.run(run_agent())
