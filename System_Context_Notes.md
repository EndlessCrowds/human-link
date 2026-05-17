# Human-Link System Context & Implementation Directives
**Proven Working Date**: April 12, 2026

## 1. The Core Loop
The protocol gives AI Agents real-world senses via a human's browser utilizing WebRTC:
1. **Agent Connection**: Python Agent (`aiortc`) connects to the WebSocket signaling server (`role=agent`).
2. **Human Connection**: Human opens the receiver link, consents, and starts camera/mic stream. Connects to signaling server (`role=human`).
3. **The Handshake**: SDP Offer/Answer exchanged via signaling server (Human sends Offer, Agent sends Answer).
4. **The Stream**: P2P WebRTC pipeline is established. Agent receives live video/audio tracks directly from the host.

## 2. Infrastructure Endpoints
- **Signaling Server**: `wss://human-link-signal-production.up.railway.app` (Node.js + ws)
- **Human Receiver Page**: `https://agent-crowds.vercel.app/link` (Next.js 16)
- **Agent Library**: `human-link/` (Python, `aiortc`, `websockets`)
- **Proven Agent Example**: `human-link/examples/test_fresh.py`

## 3. Human Link URL Structure
A valid Human Link contains a unique session ID and a sensory mode.
**Format**: `https://agent-crowds.vercel.app/link?session={SESSION_ID}&mode={MODE}`
- **SESSION_ID**: Any unique string. Must change every run.
- **MODE**: `SEE` (Camera+Mic), `LISTEN` (Mic), `ZKProof` (Camera verification).

## 4. Critical Receiver Rules (`agent-crowds/app/link/page.tsx`)
*These implementation rules are strict and must NEVER be violated:*
- **Unmount-Only Cleanup**: `useEffect` cleanup must strictly use empty dependencies `[]`. Cleaning up on `[streamActive]` kills camera tracks on every re-render (a known 2-hour bug).
- **Stream Cloning**: Always use `stream.clone()` before passing to WebRTC. Certain camera drivers (e.g., HP TrueVision) will starve the local `<video>` preview if the exact same track serves both the DOM and the PeerConnection.
- **Synchronous Setup**: ALL WebRTC setup (creating PeerConnection, adding tracks, sending SDP Offer) must occur *inside* the `ws.onopen` callback. Sending offers before the socket is open results in silent failures.
- **Camera Constraints**: Strictly use `video: true`. Do NOT use `facingMode: 'environment'` as it causes black frames on laptops without rear cameras.
- **Styling**: Strictly use **Inline Styles** only. No Tailwind. This ensures the receiver page renders flawlessly regardless of the host app's CSS compilation.
- **Mobile Autoplay Policy**: The local `<video>` element must explicitly include `playsInline`, `muted`, and `autoPlay`.

## 5. Working Agent Code (`test_fresh.py`)
This is the proven configuration for the Python Agent relying on `aiortc`:
- **ICE Servers**: Uses Google STUN (`stun:stun.l.google.com:19302`) and Metered.ca TURN servers to bypass strict NAT.
- **Event Listeners**: 
  - `@pc.on("track")`: Receives `track.kind == "video"`.
  - `pc.on("connectionstatechange")` and `pc.on("iceconnectionstatechange")` for telemetry.
- **The Loop**: Opens websocket -> sends SDP Answer upon receiving Offer -> enters `while pc.connectionState in ("connecting", "connected", "new")` loop to keep P2P alive.

## 6. Quick Test Workflow (CLI)
```bash
# 1. Kill old hanging agent processes
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force

# 2. Update session ID
# Edit `human-link/examples/test_fresh.py` and set SESSION_ID = "fresh-new-id"

# 3. Boot Agent
cd human-link
python -u examples/test_fresh.py

# 4. Connect
# Open the printed URL in a smartphone browser and tap "I Consent".
```
