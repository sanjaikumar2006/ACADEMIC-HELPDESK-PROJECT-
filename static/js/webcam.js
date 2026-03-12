// Shared Webcam Logic
let currentStream = null;
let currentDeviceIndex = 0;
let videoDevices = [];

async function getDevices() {
    const devices = await navigator.mediaDevices.enumerateDevices();
    videoDevices = devices.filter(device => device.kind === 'videoinput');
}

async function startCamera(videoId) {
    const video = document.getElementById(videoId);
    if (!video) return;

    // Help users with the Localhost vs IP issue
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    if (!isLocal && window.location.protocol !== 'https:') {
        showResult('result-msg', '⚠️ <b>Security Block:</b> Camera only works on <b>localhost</b> or <b>HTTPS</b>. Please use http://localhost:5000', 'error');
        return false;
    }

    if (currentStream) {
        currentStream.getTracks().forEach(track => track.stop());
    }

    await getDevices();

    if (videoDevices.length === 0) {
        showResult('result-msg', '❌ <b>No Camera:</b> No webcam was detected.', 'error');
        return false;
    }

    const constraints = {
        video: {
            deviceId: videoDevices[currentDeviceIndex].deviceId ? { exact: videoDevices[currentDeviceIndex].deviceId } : undefined,
            width: 640,
            height: 480
        },
        audio: false
    };

    try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            showResult('result-msg', '❌ <b>Browser Not Supported:</b> Your browser does not support camera access. Please use Chrome or Edge.', 'error');
            return false;
        }

        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        currentStream = stream;
        video.srcObject = stream;

        return new Promise((resolve) => {
            video.onloadedmetadata = () => {
                video.play().then(() => resolve(true)).catch(() => resolve(false));
            };
        });

    } catch (err) {
        console.error("Camera access error:", err);
        let errorMsg = "Could not access camera.";

        if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
            errorMsg = `
                <div style="text-align: left; padding: 10px;">
                    <b>❌ Camera Blocked:</b> Please follow these steps:
                    <ol style="margin-top: 10px; font-weight: normal; font-size: 0.85rem;">
                        <li>Click the <b>🔒 Lock Icon</b> on the far LEFT of the address bar.</li>
                        <li>Switch the <b>Camera</b> toggle to <b>"On"</b> (Allow).</li>
                        <li><b>Refresh the page (F5)</b>.</li>
                    </ol>
                    <small style="display: block; margin-top: 10px; color: #94a3b8;">
                        *Note: If you see a camera icon with a red X on the RIGHT side of the address bar, click it and select "Always Allow".
                    </small>
                </div>
            `;
        } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
            errorMsg = "<b>Camera Busy:</b> Another application (like Zoom or Teams) is using your webcam. Please close it and refresh.";
        } else {
            errorMsg = "<b>Camera Initialization Error:</b> Please ensure your camera is plugged in and recognized by your computer.";
        }

        showResult('result-msg', errorMsg, 'error');
        return false;
    }
}

async function switchCamera(videoId) {
    if (videoDevices.length < 2) return;
    currentDeviceIndex = (currentDeviceIndex + 1) % videoDevices.length;
    await startCamera(videoId);
}

function captureFrame(videoId) {
    const video = document.getElementById(videoId);
    if (!video || video.readyState < 2 || video.videoWidth === 0) return null;

    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    return canvas.toDataURL("image/jpeg", 0.9);
}

function showResult(elementId, message, type) {
    const el = document.getElementById(elementId);
    if (!el) return;

    el.innerHTML = message;
    el.className = "result-msg " + type;
    el.style.display = "block";
    el.style.opacity = "1";
}
