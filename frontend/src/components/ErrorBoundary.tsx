import { Component, ReactNode } from 'react';

interface Props { children: ReactNode; }
interface State { error: Error | null; }

/** Catches render errors so a single throwing panel doesn't blank the editor. */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: { componentStack: string }) {
    console.error('Editor error:', error, info.componentStack);
  }

  reset = () => this.setState({ error: null });

  render() {
    if (this.state.error) {
      return (
        <div className="h-full flex items-center justify-center p-4">
          <div className="max-w-md text-center">
            <div className="text-red-400 text-sm mb-2">Something broke</div>
            <pre className="text-[10px] font-mono text-muted whitespace-pre-wrap text-left bg-panel-2 p-3 rounded mb-3 overflow-auto max-h-48">
              {this.state.error.message}
              {'\n\n'}
              {this.state.error.stack}
            </pre>
            <button
              onClick={this.reset}
              className="text-xs px-3 py-1 bg-accent text-white rounded"
            >
              Try again
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
