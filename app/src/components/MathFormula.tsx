import React, { useEffect } from 'react';
import katex from 'katex';

interface MathFormulaProps {
  formula: string;
  display?: boolean;
}

export default function MathFormula({ formula, display = true }: MathFormulaProps) {
  const containerRef = React.useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current && !containerRef.current.hasChildNodes()) {
      try {
        katex.render(formula, containerRef.current, {
          displayMode: display ? 'display' : 'inline',
          throwOnError: false,
        });
      } catch (error) {
        console.error('KaTeX render error:', error);
        // Fallback: display as plain text
        if (containerRef.current) {
          containerRef.current.textContent = formula;
        }
      }
    }
  }, [formula, display]);

  return (
    <div
      ref={containerRef}
      className={`math-formula ${display ? 'block' : 'inline'}`}
    />
  );
}
