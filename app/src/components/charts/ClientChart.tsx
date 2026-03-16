import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react';

interface ChartContainerSize {
  width: number;
  height: number;
}

interface ClientChartProps {
  children: ReactNode | ((size: ChartContainerSize) => ReactNode);
  className?: string;
  style?: CSSProperties;
}

export default function ClientChart({ children, className, style }: ClientChartProps) {
  const [isMounted, setIsMounted] = useState(false);
  const [size, setSize] = useState<ChartContainerSize>({ width: 0, height: 0 });
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    if (!isMounted || !containerRef.current) {
      return;
    }

    const updateSize = () => {
      const rect = containerRef.current?.getBoundingClientRect();
      const nextSize = {
        width: rect?.width ?? 0,
        height: rect?.height ?? 0,
      };

      setSize((currentSize) => (
        currentSize.width === nextSize.width && currentSize.height === nextSize.height
          ? currentSize
          : nextSize
      ));
    };

    updateSize();

    const observer = new ResizeObserver(() => updateSize());
    observer.observe(containerRef.current);

    return () => observer.disconnect();
  }, [isMounted]);

  return (
    <div
      ref={containerRef}
      className={className}
      style={{ minHeight: 240, ...style }}
    >
      {isMounted && size.width > 0 && size.height > 0
        ? typeof children === 'function'
          ? children(size)
          : children
        : null}
    </div>
  );
}
