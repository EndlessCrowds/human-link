import asyncio
import json
import websockets
import cv2
import time
import os
import google.generativeai as genai
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer

# --- CONFIGURATION ---
SIGNALING_URL = "wss://human-link-signal-production.up.railway.app"
RECEIVER_URL = "https://agent-crowds.vercel.app"
SESSION_ID = "live-051726b"

# Set up the AI (Make sure to export GEMINI_API_KEY in your terminal)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

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
])

async def process_video_track(track):
    print("[VISION PIPELINE] Initializing frame extraction...", flush=True)
    last_process_time = 0
    cooldown_seconds = 5  # Look at the camera every 5 seconds

    while True:
        try:
            # Wait for the next frame from the WebRTC stream
            frame = await track.recv()
            current_time = time.time()

            # Only process a frame if the cooldown has passed
            if current_time - last_process_time >= cooldown_seconds:
                last_process_time = current_time
                print("\n[VISION PIPELINE] Snapping frame...", flush=True)

                # Convert the raw WebRTC frame to a numpy array (BGR format for OpenCV)
                img = frame.to_ndarray(format="bgr24")

                # Encode the array into a compressed JPEG image in memory
                success, buffer = cv2.imencode('.jpg', img)
                if not success:
                    continue
                
                # Convert to the format the AI model expects
                image_bytes = buffer.tobytes()
                image_parts = [{"mime_type": "image/jpeg", "data": image_bytes}]

                print("[AI] Analyzing physical environment...", flush=True)
                
                # Send the image to the LLM (Running synchronously in a thread to avoid blocking WebRTC)
                response = await asyncio.to_thread(
                    model.generate_content,
                    contents=["Describe exactly what you see in this image in one brief sentence.", image_parts[0]]
                )
                
                print(f">>> [AGENT SEES]: {response.text.strip()}\n", flush=True)

        except Exception as e:
            print(f"[VISION PIPELINE] Track ended or error: {e}", flush=True)
            break

async def run_agent():
    pc = RTCPeerConnection(configuration=ICE_CONFIG)

    @pc.on("track")
    def on_track(track):
        print(f"[VISION] Track received: {track.kind}", flush=True)
        if track.kind == "video":
            print("LIVE VIDEO FEED CONNECTED. Routing to AI...", flush=True)
            # Launch the frame extraction loop in the background
            asyncio.create_task(process_video_track(track))

    @pc.on("connectionstatechange")
    async def on_state():
        print(f"[STATE] Connection: {pc.connectionState}", flush=True)

    url = f"{SIGNALING_URL}?session={SESSION_ID}&role=agent"
    print("[AGENT] Booting...", flush=True)

    try:
        async with websockets.connect(url) as ws:
            print("[AGENT] Connected to signaling.", flush=True)
            print(f"\nOPEN THIS LINK:")
            print(f"{RECEIVER_URL}/link?session={SESSION_ID}&mode=SEE\n")

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

if __name__ == "__main__":
    asyncio.run(run_agent())
