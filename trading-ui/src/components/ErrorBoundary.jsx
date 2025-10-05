// src/components/ErrorBoundary.jsx
import { Component } from "react";

export default class ErrorBoundary extends Component {
  state = { hasError: false, error: null };
  static getDerivedStateFromError(error) { return { hasError: true, error }; }
  componentDidCatch(error, info) { console.error(error, info); }
  render() {
    if (this.state.hasError) {
      return (
        <div className="p-6 text-red-300">
          <div className="text-lg font-semibold mb-2">Something went wrong.</div>
          <pre className="text-sm whitespace-pre-wrap">{String(this.state.error)}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}
