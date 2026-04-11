import { Component, type ReactNode, type ErrorInfo } from "react";
import { AlertTriangle } from "lucide-react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-[60vh] flex-col items-center justify-center px-6 py-20 text-center">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
            <AlertTriangle className="h-6 w-6 text-destructive" />
          </div>
          <h2 className="mb-2">Something went wrong</h2>
          <p className="mb-6 max-w-sm text-sm text-muted-foreground">
            {this.state.error.message}
          </p>
          <button
            onClick={() => this.setState({ error: null })}
            className="inline-flex items-center gap-2 rounded-lg border border-border px-5 py-2.5 text-sm transition-colors hover:bg-accent"
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
