import { TriangleAlert } from 'lucide-react'
import { Component, type ReactNode } from 'react'

/** If a screen fails to render, show a way back instead of a blank phone. */
export class ErrorBoundary extends Component<{ onReset: () => void; children: ReactNode }, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch(error: unknown) {
    console.error('Screen failed to render', error)
  }

  render() {
    if (!this.state.failed) return this.props.children
    return (
      <div className="crash" role="alert">
        <TriangleAlert size={32} aria-hidden="true" />
        <h1>This screen didn't load</h1>
        <p className="lede">Your answers and cart are safe. Go back and try again.</p>
        <button type="button" className="btn btn-primary btn-lg" onClick={() => { this.setState({ failed: false }); this.props.onReset() }}>
          Back to Careem home
        </button>
      </div>
    )
  }
}
