import React, { useRef, useEffect } from 'react';

interface AudioVisualizerProps {
  isActive: boolean;
  color?: string;
  height?: number;
  mode?: 'bars' | 'wave';
}

export const AudioVisualizer: React.FC<AudioVisualizerProps> = ({
  isActive,
  color = '#6366f1',
  height = 42,
  mode = 'wave',
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationId: number;
    let phase = 0;

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const width = canvas.width;
      const h = canvas.height;
      const centerY = h / 2;

      if (mode === 'wave') {
        ctx.beginPath();
        ctx.lineWidth = 2;
        ctx.strokeStyle = color;

        if (!isActive) {
          // Flat baseline
          ctx.moveTo(0, centerY);
          ctx.lineTo(width, centerY);
          ctx.stroke();
        } else {
          // Dynamic sine wave
          ctx.moveTo(0, centerY);
          for (let x = 0; x < width; x++) {
            const freq1 = Math.sin((x * 0.05) + phase);
            const freq2 = Math.sin((x * 0.02) - phase * 0.7);
            const amp = (h / 3) * (0.6 + 0.4 * Math.sin(phase * 0.5));
            const y = centerY + (freq1 + freq2) * amp * 0.5;
            ctx.lineTo(x, y);
          }
          ctx.stroke();

          // Subtle glow
          ctx.shadowBlur = 8;
          ctx.shadowColor = color;
        }
      } else {
        // Bars mode
        const barCount = 28;
        const barWidth = 3;
        const gap = (width - (barCount * barWidth)) / (barCount - 1);

        for (let i = 0; i < barCount; i++) {
          const x = i * (barWidth + gap);
          let barH = 3;
          if (isActive) {
            barH = 4 + Math.abs(Math.sin(phase + i * 0.35)) * (h - 8);
          }
          const y = centerY - barH / 2;

          ctx.fillStyle = color;
          ctx.fillRect(x, y, barWidth, barH);
        }
      }

      phase += 0.08;
      animationId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationId);
    };
  }, [isActive, color, height, mode]);

  return (
    <canvas
      ref={canvasRef}
      width={240}
      height={height}
      style={{ display: 'block', width: '100%', height: `${height}px`, background: 'transparent' }}
    />
  );
};
