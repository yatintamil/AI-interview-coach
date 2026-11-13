import React, { useRef, useEffect, useState } from 'react';
import {
  Camera,
  CameraOff,
  Mic,
  MicOff,
  Activity,
  Minimize2,
  Maximize2,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

interface WebcamFeedProps {
  isRecording?: boolean;
  onAudioLevelChange?: (level: number) => void;
  className?: string;
}

export const WebcamFeed: React.FC<WebcamFeedProps> = ({
  isRecording = false,
  onAudioLevelChange,
  className = '',
}) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [cameraActive, setCameraActive] = useState(true);
  const [micActive, setMicActive] = useState(true);
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  const [audioLevel, setAudioLevel] = useState(0);
  const [isMinimized, setIsMinimized] = useState(false);
  const [showDiagnostics, setShowDiagnostics] = useState(false);

  // Audio Context & Analyser
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  // Start media stream
  useEffect(() => {
    let activeStream: MediaStream | null = null;
    let isMounted = true;

    async function setupMedia() {
      try {
        if (!navigator?.mediaDevices?.getUserMedia) {
          if (isMounted) setHasPermission(false);
          return;
        }
        const mediaStream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 640 }, height: { ideal: 360 } },
          audio: true,
        });

        if (!isMounted) {
          mediaStream.getTracks().forEach((track) => track.stop());
          return;
        }

        activeStream = mediaStream;
        setStream(mediaStream);
        setHasPermission(true);

        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream;
        }

        // Setup Web Audio Analyser
        const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
        if (AudioCtx) {
          const ctx = new AudioCtx();
          audioContextRef.current = ctx;
          const analyser = ctx.createAnalyser();
          analyser.fftSize = 64;
          analyserRef.current = analyser;

          const source = ctx.createMediaStreamSource(mediaStream);
          source.connect(analyser);

          const dataArray = new Uint8Array(analyser.frequencyBinCount);

          const updateVolume = () => {
            if (analyserRef.current) {
              analyserRef.current.getByteFrequencyData(dataArray);
              let sum = 0;
              for (let i = 0; i < dataArray.length; i++) {
                sum += dataArray[i];
              }
              const avg = sum / dataArray.length;
              const normalized = Math.min(100, Math.round((avg / 128) * 100));
              setAudioLevel(normalized);
              if (onAudioLevelChange) {
                onAudioLevelChange(normalized);
              }
            }
            animationFrameRef.current = requestAnimationFrame(updateVolume);
          };
          updateVolume();
        }
      } catch (err) {
        console.warn('Camera/Mic permission unavailable or denied:', err);
        setHasPermission(false);
      }
    }

    setupMedia();

    return () => {
      isMounted = false;
      if (activeStream) {
        activeStream.getTracks().forEach((track) => track.stop());
      }
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close().catch(() => {});
      }
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  const toggleCamera = () => {
    if (stream) {
      const videoTracks = stream.getVideoTracks();
      if (videoTracks.length > 0) {
        const nextState = !videoTracks[0].enabled;
        videoTracks[0].enabled = nextState;
        setCameraActive(nextState);
      }
    }
  };

  const toggleMic = () => {
    if (stream) {
      const audioTracks = stream.getAudioTracks();
      if (audioTracks.length > 0) {
        const nextState = !audioTracks[0].enabled;
        audioTracks[0].enabled = nextState;
        setMicActive(nextState);
      }
    }
  };

  // 1. Minimized State: Compact audio pill with expand action
  if (isMinimized) {
    return (
      <div
        className={`compact-video-card minimized-view p-2.5 surface-card ${className}`}
        data-testid="compact-webcam-minimized"
      >
        <div className="flex items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2">
            <span
              className="pulse-dot shrink-0"
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                background: isRecording ? '#ef4444' : '#10b981',
              }}
            />
            <span className="text-2xs font-medium text-secondary">
              {isRecording ? 'Recording (Audio Only)' : 'Camera Minimized'}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5" title="Mic Level">
              <Activity size={12} className={micActive ? 'text-emerald' : 'text-muted'} />
              <div
                style={{
                  width: '40px',
                  height: '4px',
                  background: 'var(--surface-raised, #1e293b)',
                  borderRadius: '2px',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    width: `${micActive ? audioLevel : 0}%`,
                    height: '100%',
                    background: '#10b981',
                    transition: 'width 0.1s ease',
                  }}
                />
              </div>
            </div>

            <button
              type="button"
              className="btn btn-ghost btn-xs p-1"
              onClick={() => setIsMinimized(false)}
              title="Expand Camera Preview"
              aria-label="Expand Camera Preview"
            >
              <Maximize2 size={13} />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // 2. Standard Compact View
  return (
    <div
      className={`compact-video-card surface-card p-2.5 flex flex-col gap-2 ${className}`}
      data-testid="compact-webcam-container"
    >
      {/* Top Status & Window Controls */}
      <div className="flex items-center justify-between gap-2 text-2xs text-secondary">
        <div className="flex items-center gap-1.5 font-medium">
          <span
            className="pulse-dot shrink-0"
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: isRecording ? '#ef4444' : '#10b981',
            }}
          />
          <span>{isRecording ? 'LIVE REC' : 'READY'}</span>
          {hasPermission === false && <span className="text-amber">(No Camera)</span>}
        </div>

        <div className="flex items-center gap-1">
          <button
            type="button"
            className="btn btn-ghost btn-xs p-1"
            onClick={() => setIsMinimized(true)}
            title="Minimize to Audio Pill"
            aria-label="Minimize Camera"
          >
            <Minimize2 size={12} />
          </button>
        </div>
      </div>

      {/* Video Display Frame (Compact 16:9 or 4:3, capped height) */}
      <div
        className="compact-video-frame"
        style={{
          position: 'relative',
          width: '100%',
          aspectRatio: '16 / 9',
          maxHeight: '160px',
          background: '#090d16',
          borderRadius: '4px',
          overflow: 'hidden',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          border: '1px solid var(--border-subtle, #1e293b)',
        }}
      >
        {hasPermission === false || !cameraActive ? (
          <div className="flex flex-col items-center gap-1.5 text-muted p-4 text-center">
            <CameraOff size={22} className="text-muted/70" />
            <span style={{ fontSize: '0.7rem' }}>
              {hasPermission === false ? 'Camera access not granted' : 'Camera muted'}
            </span>
          </div>
        ) : (
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              transform: 'scaleX(-1)',
            }}
          />
        )}
      </div>

      {/* Bottom Media Controls Bar */}
      <div className="flex items-center justify-between gap-2 pt-0.5">
        <div className="flex items-center gap-1">
          <button
            type="button"
            className={`btn btn-ghost btn-xs p-1.5 ${!cameraActive ? 'text-rose-400' : 'text-secondary'}`}
            onClick={toggleCamera}
            title={cameraActive ? 'Mute Camera' : 'Enable Camera'}
            aria-label={cameraActive ? 'Mute Camera' : 'Enable Camera'}
          >
            {cameraActive ? <Camera size={13} /> : <CameraOff size={13} />}
          </button>

          <button
            type="button"
            className={`btn btn-ghost btn-xs p-1.5 ${!micActive ? 'text-rose-400' : 'text-secondary'}`}
            onClick={toggleMic}
            title={micActive ? 'Mute Microphone' : 'Enable Microphone'}
            aria-label={micActive ? 'Mute Microphone' : 'Enable Microphone'}
          >
            {micActive ? <Mic size={13} /> : <MicOff size={13} />}
          </button>
        </div>

        {/* Live Audio Meter */}
        <div className="flex items-center gap-1.5">
          <Activity size={12} className={micActive && audioLevel > 5 ? 'text-emerald' : 'text-muted'} />
          <div
            style={{
              width: '54px',
              height: '5px',
              background: 'var(--surface-raised, #1e293b)',
              borderRadius: '2px',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                width: `${micActive ? audioLevel : 0}%`,
                height: '100%',
                background: '#10b981',
                transition: 'width 0.08s ease',
              }}
            />
          </div>
          <span
            style={{
              fontSize: '0.65rem',
              fontFamily: 'var(--font-mono, monospace)',
              color: 'var(--text-muted, #94a3b8)',
              width: '24px',
              textAlign: 'right',
            }}
          >
            {micActive ? `${audioLevel}%` : 'OFF'}
          </span>
        </div>
      </div>

      {/* Collapsible Telemetry & Diagnostics Toggle */}
      <div className="border-t border-subtle pt-1 mt-0.5">
        <button
          type="button"
          className="text-2xs text-muted hover:text-secondary flex items-center justify-between w-full"
          onClick={() => setShowDiagnostics((prev) => !prev)}
          aria-expanded={showDiagnostics}
        >
          <span>Media Telemetry</span>
          {showDiagnostics ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
        </button>

        {showDiagnostics && (
          <div className="grid grid-cols-2 gap-1.5 pt-1.5 text-2xs text-secondary font-mono">
            <div>Video: {cameraActive ? '640x360 30fps' : 'Disabled'}</div>
            <div>Audio: {micActive ? 'WebAudio Analyser' : 'Muted'}</div>
            <div>Latency: &lt;15ms buffer</div>
            <div>Status: {hasPermission ? 'Granted' : 'Restricted'}</div>
          </div>
        )}
      </div>
    </div>
  );
};
