import { useEffect, useState, type CSSProperties, type ReactNode } from 'react';

interface ClientChartProps {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
}

export default function ClientChart({ children, className, style }: ClientChartProps) {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  return (
    <div className={className} style={style}>
      {isMounted ? children : null}
    </div>
  );
}
