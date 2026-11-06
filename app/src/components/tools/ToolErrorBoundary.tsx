import { Component, Fragment, type ReactNode } from "react";

interface ToolErrorBoundaryProps {
  children: ReactNode;
}

interface ToolErrorBoundaryState {
  failed: boolean;
  attempt: number;
}

/**
 * Local error boundary for one decision tool.
 *
 * A tool that throws — a malformed archive payload, an unexpected field — is
 * contained here instead of unmounting the workspace, mirroring S1's
 * containment boundary. The boundary never renders or logs the thrown error,
 * because its message can contain user-entered financing inputs.
 */
export default class ToolErrorBoundary extends Component<
  ToolErrorBoundaryProps,
  ToolErrorBoundaryState
> {
  state: ToolErrorBoundaryState = { failed: false, attempt: 0 };

  static getDerivedStateFromError(): Partial<ToolErrorBoundaryState> {
    return { failed: true };
  }

  private handleRetry = () => {
    this.setState((previous) => ({
      failed: false,
      attempt: previous.attempt + 1,
    }));
  };

  render() {
    if (this.state.failed) {
      return (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-800 dark:bg-red-900/20 dark:text-red-200"
        >
          <p className="font-bold">This tool could not be displayed.</p>
          <p className="mt-2">
            Its published data could not be read, so the results are hidden
            rather than shown incorrectly. The other tools in this workspace
            still work — choose another tool, or retry this one.
          </p>
          <button
            type="button"
            onClick={this.handleRetry}
            className="mt-3 rounded border border-red-300 bg-white px-3 py-2 font-bold text-red-800 transition-colors hover:bg-red-100 dark:border-red-700 dark:bg-gray-900 dark:text-red-200 dark:hover:bg-red-900/40"
          >
            Retry this tool
          </button>
        </div>
      );
    }

    // Remount only this tool on retry so its state is rebuilt from scratch.
    return <Fragment key={this.state.attempt}>{this.props.children}</Fragment>;
  }
}
