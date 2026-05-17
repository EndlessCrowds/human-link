# Human-Link Bug Report: "eyes-023" (The Black Stream Issue)

**Date**: April 12, 2026
**Status**: ✅ LIVE AND STABLE
**Session**: `eyes-023`

## 1. Overview & Architecture
Successfully established a real-time WebRTC P2P bridge allowing an AI Agent to see and hear through a human's device (laptop/smartphone). 
- **Flow**: `[Human's Camera] -> [Browser WebRTC] -> [P2P over Internet] -> [Python aiortc Agent] -> [Vision Model]`
- **Components**:
  - Receiver UI: `agent-crowds/app/link/page.tsx`
  - Signaling Server: `human-link-signal` (Railway)
  - Python Agent: `human-link/examples/test_fresh.py` (aiortc)

## 2. The Root Cause Bug (The Black Stream)
After 22 test sessions where the camera preview was completely black despite APIs reporting success, the root cause was identified as a single React lifecycle error in the Receiver UI.

**The Bug**:
```javascript
useEffect(() => {
    if (hasConsented && !streamActive) startHardware();
    // THIS LINE KILLS THE TRACKS
    return () => { streamRef.current?.getTracks().forEach(t => t.stop()); }; 
}, [hasConsented, streamActive, startHardware]);
```
*Why it failed*: When `startHardware()` ran, it called `setStreamActive(true)`, causing React to re-run the effect. The cleanup function fired first, calling `t.stop()` on all tracks, instantly killing the stream ~1s after acquisition.

**The Fix**:
Split the effects. One for setup, one purely for unmount-only cleanup.
```javascript
// Effect 1: Setup
useEffect(() => {
    if (hasConsented && !streamActive) startHardware();
}, [hasConsented, streamActive, startHardware]);

// Effect 2: Cleanup ONLY on unmount
useEffect(() => {
    return () => { streamRef.current?.getTracks().forEach(t => t.stop()); };
}, []);
```

## 3. Key Technical Decisions 
1. **Trickle ICE Disabled**: `aiortc` does not support trickle ICE. The browser must gather all candidates before sending the SDP offer.
2. **Stream Cloning**: Separate `MediaStream` (`stream.clone()`) is required to serve the local `<video>` preview and WebRTC transmission to prevent driver starvation.
3. **Flexible Camera Constraints**: strictly `video: true` with NO `facingMode` constraint. `facingMode: 'environment'` caused black frames on laptops lacking rear cameras.
4. **Canvas Fallback**: Implemented a manual `drawImage` loop for pixel debugging (`rgba(0,0,0,255)` proved the stream was dead vs `rgba(20,23,17,255)` proving real photons).
5. **Lifecycle Management**: Camera tracks must ONLY be stopped when the component unmounts.

## 4. Next Steps for Human-Link
- **Vision Integration**: Feed P2P frames into Claude/Gemini.
- **Audio Processing**: Pipe audio to speech-to-text.
- **Mobile Verification**: Test on iPhone Safari and Android Chrome.
- **Production Hardening**: Add dedicated TURN credentials, reconnection logic, session management.
- **Multi-Sense**: Integrate Gyroscope, GPS, and Ambient Light sensors into the bridge.
